/**
 * course-utils.js — 课程数据共享工具
 *
 * 暴露: window.xsCourseUtils
 *  - outlineToScenes(outline): 脑暴的 outline.scenes 翻译成 CourseData.outlines
 *  - normalizeScenes(scenes): 同样转换, 直接接受 scenes 数组
 *  - getComponent(courseData, name): 优先 *_data 顶层, fallback 到 bundle.components[name]
 *
 * 跨文件复用, 避免 brainstorm.js / classroom.js 各写一份
 */
(function () {
    'use strict';

    function _one(outline, s, i) {
        const rawId = s && (s.id ?? s.scene_id);
        let intId = i + 1;
        if (typeof rawId === 'number' && Number.isFinite(rawId)) {
            intId = rawId;
        } else if (typeof rawId === 'string' && /^\d+$/.test(rawId)) {
            intId = parseInt(rawId, 10);
        } else if (typeof rawId === 'string' && /^s\d+$/.test(rawId)) {
            intId = parseInt(rawId.slice(1), 10) || (i + 1);
        }
        const keyPoints = (s && s.key_points) || [];
        return {
            id: intId,
            title: (s && s.title) || `场景 ${i + 1}`,
            type: (s && s.type) || 'slide',
            points: Array.isArray(keyPoints) ? keyPoints.length : 0,
            key_points: Array.isArray(keyPoints) ? keyPoints : [],
            description: (s && s.description) || '',
        };
    }

    function normalizeScenes(scenes) {
        return (scenes || []).map(function (s, i) { return _one({}, s, i); });
    }

    function outlineToScenes(outline) {
        const scenes = (outline && outline.scenes) || [];
        return scenes.map(function (s, i) { return _one(outline, s, i); });
    }

    function getComponent(courseData, name) {
        if (!courseData) return null;
        const flatKey = name === 'ppt' ? 'ppt_data' : (name + '_data');
        if (courseData[flatKey] && typeof courseData[flatKey] === 'object') {
            return courseData[flatKey];
        }
        const bundle = courseData.bundle;
        if (bundle && bundle.components && bundle.components[name]) {
            return bundle.components[name];
        }
        return null;
    }

    window.xsCourseUtils = {
        outlineToScenes: outlineToScenes,
        normalizeScenes: normalizeScenes,
        getComponent: getComponent,
    };
})();
