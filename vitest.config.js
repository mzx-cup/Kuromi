/**
 * Vitest 配置 — JS 单元测试
 *
 * 运行:
 *   npx vitest run                          # 所有单测
 *   npx vitest run tests/frontend/unit/     # 仅 unit
 *   npx vitest                              # watch 模式
 */

import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    // jsdom 模拟浏览器 DOM 环境
    environment: 'jsdom',

    // 全局测试超时
    testTimeout: 10000,

    // 测试文件匹配
    include: ['tests/frontend/unit/**/*.test.js'],

    // 解析项目根路径
    root: path.resolve(__dirname),

    // 覆盖率配置（可选: npx vitest run --coverage）
    coverage: {
      provider: 'v8',
      include: ['js/toast.js', 'js/auth.js', 'js/theme.js'],
      reporter: ['text', 'lcov', 'html'],
    },
  },
});
