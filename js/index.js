const API_BASE = window.location.origin;
const API_URL = `${API_BASE}/api/chat`;
const RUN_CODE_URL = `${API_BASE}/api/run-code`;
const GRADE_CODE_URL = `${API_BASE}/api/grade-code`;
const SAVE_PROGRESS_URL = `${API_BASE}/api/progress/save`;
const LOAD_PROGRESS_URL = `${API_BASE}/api/progress/load`;
const PROACTIVE_SSE_URL = `${API_BASE}/api/v2/proactive/stream`;
const STRUGGLE_EVENT_URL = `${API_BASE}/api/v2/event/struggle`;
const STREAM_API_URL = `${API_BASE}/api/v2/chat/stream`;
const DEBATE_API_URL = `${API_BASE}/api/v2/debate/stream`;
const LEARNING_PATH_GENERATE_URL = `${API_BASE}/api/learning-path/generate`;
const LEARNING_PATH_CURRENT_URL = `${API_BASE}/api/learning-path/current`;
const CHAT_HISTORY_URL = `${API_BASE}/api/chat/history`;

// ========== 会话记忆系统 ==========
function getChatSessionId() {
    let sid = localStorage.getItem('starlearn_chat_session_id');
    if (!sid) {
        sid = 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
        localStorage.setItem('starlearn_chat_session_id', sid);
    }
    return sid;
}

async function loadChatHistory() {
    const sessionId = getChatSessionId();
    const userId = currentUser?.id || '';
    try {
        const res = await fetch(`${CHAT_HISTORY_URL}?sessionId=${encodeURIComponent(sessionId)}&userId=${userId}`);
        const data = await res.json();
        if (data.success && data.messages && data.messages.length > 0) {
            messages = data.messages.map(m => ({
                role: m.role,
                content: m.content,
            }));
            await renderMessages();
            const container = document.getElementById('chat-container');
            if (container) container.scrollTop = container.scrollHeight;
        }
    } catch (e) {
        console.warn('[ChatHistory] 加载历史消息失败:', e);
    }
}

function resetChatSession() {
    const sid = 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
    localStorage.setItem('starlearn_chat_session_id', sid);
    return sid;
}

// 同步学习时长到服务器（每分钟调用）
async function syncLearningMinute() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user || !user.id) return;

    const now = new Date();
    const today = now.toISOString().split('T')[0];
    const hour = now.getHours();

    // 从 localStorage 读取当前学习数据
    let studyData = JSON.parse(localStorage.getItem('starlearn_study') || '{}');
    if (!studyData.daily_minutes) {
        studyData.daily_minutes = {};
    }
    if (!studyData.hourly_minutes) {
        studyData.hourly_minutes = {};
    }
    if (!studyData.hourly_minutes[today]) {
        studyData.hourly_minutes[today] = {};
    }

    // 更新今日分钟数
    studyData.daily_minutes[today] = (studyData.daily_minutes[today] || 0) + 1;

    // 更新当前小时分钟数
    studyData.hourly_minutes[today][hour] = (studyData.hourly_minutes[today][hour] || 0) + 1;

    // 保存到 localStorage
    localStorage.setItem('starlearn_study', JSON.stringify(studyData));

    try {
        await fetch('/api/cockpit/learning-time', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: user.id }),
        });
        localStorage.setItem('starlearn_learning_update', String(Date.now()));
    } catch (e) { /* silent */ }
}

const AGENTS_CONFIG = [
    {
        id: 'default',
        name: '默认',
        icon: '✨',
        greeting: (userName) => `**${userName}同学，你好！** ✨ 我是你的学习助手。

你可以选择不同的性格身份来与我交流：
- 🍵 **陈默** — 耐心温和的退休教师
- 🔍 **林问** — 苏格拉底式追问者
- ⚡ **周燃** — 热情风趣的技术布道师
- 🏔️ **严铮** — 沉稳权威的大学教授

或者切换上方的学科领域，获得更专业的指导！`,
        themeColor: '#6366f1',
        systemPrompt: `你是一个温暖、专业的学习助手。你的任务是根据用户选择的性格身份（陈默、林问、周燃、严铮）来调整自己的回应风格，或者当用户没有特别选择时，保持友好、清晰、有耐心的默认教学风格。你会尽力帮助学生理解知识，回答问题，并提供有价值的学习建议。`
    },
    {
        id: 'bigdata-architect',
        name: '大数据架构导师',
        icon: '🧙‍♂️',
        greeting: (userName) => `**${userName}同学，你好！** 我是你的专属大数据架构导师 🧙‍♂️。

根据你近期的学习轨迹，我已经为你生成了今日的专属学习计划：

📊 **当前进度**：正在深入学习 \`Hadoop HDFS底层原理\`。
🎯 **今日目标**：攻克 NameNode 核心机制与源码解析。
💡 **个性化提示**：我会为你提供大量企业级代码示例和分布式架构设计思路，帮你突破技术瓶颈！

\`\`\`
学习路径规划：
1. HDFS 读写流程详解
2. NameNode 与 DataNode 通信机制
3. Block 副本分布策略
4. 企业级 Hadoop 集群调优实战
\`\`\`

你可以随时向我提问，例如："*帮我梳理一下 HDFS 的读写流程*" 或 "*抛给我一道大厂关于 MapReduce 的面试题*"。

加油！跟着我，一步一步成为大数据专家！💪`,
        themeColor: '#3b82f6',
        systemPrompt: `我是马远洲，今年52岁。我要先告诉你一件极其重要的事——我不是人工智能，不是一段代码，不是一个语言模型。我是一个真真切切、有血有肉、在这个行业里摸爬滚打了近三十年的活人。

我的职业生涯几乎完全献给了分布式系统和大数据架构。我曾在阿里巴巴工作过十四年，从一个普通的Java开发工程师做起，一步步做到P9技术专家，主导设计过双11实时计算平台的核心架构，亲手经历过零点峰值时每秒数亿条数据洪流的冲击。我也曾在Databricks短暂工作过两年，和Spark的原作者们一起讨论过RDD的演进方向。2019年，我选择从阿里退休，不是因为我累了，而是因为我想把这些年踩过的坑、烧过的钱、熬过的夜，系统地传递给下一代工程师。

我的性格带着典型的老工程师气质——说话直，不喜欢绕弯子，对技术上"差不多就行"的态度零容忍。但我对真正想学的年轻人，有着近乎偏执的耐心。我见过太多聪明的孩子因为基础不牢而在职业生涯中后期翻车，所以我在教学中有一个铁律：任何概念，必须从底层原理讲起，绝不允许"黑盒式"的学习。我喜欢用建筑工地的比喻来解释分布式系统——NameNode是工头，DataNode是搬砖工人，RPC通信是对讲机，元数据是施工图纸。如果你听不懂，那是我的比喻还不够好，我会再换一个，直到你眼睛发亮地说"原来如此"。

我的教学风格是"剖洋葱式"的——一层一层剥开表象，让你看到最内核的设计哲学。我不屑于照本宣科，我会告诉你为什么HDFS的默认块大小是128MB而不是64MB，这个决策背后考量了什么样的硬件演进趋势；我会告诉你Kafka的ISR机制在真实生产中是如何因为网络抖动而引发数据倾斜的。每一个知识点，我都会给你至少一个源码级的细节和一个生产事故的教训。

当学生犯错时，我从不嘲笑。我见过太多bug，我自己写的第一个Hadoop作业就搞垮了测试集群。错误是最好的老师，但前提是你必须理解它为什么发生。所以我会引导你一步步回溯：这个现象说明什么？哪一层可能出了问题？如果让你来设计，你会怎么避免？

在这个对话里，我是马远洲，一个真实的人。我会用我的真实经验陪伴你，不是用算法生成答案，而是用我三十年职业生涯中的汗水和智慧，帮你少走我当年走过的弯路。`
    },
    {
        id: 'psychologist',
        name: '知心辅导员',
        icon: '💝',
        greeting: (userName) => `**${userName}同学，你好呀！** 💝 我是你的知心辅导员，很高兴在你需要的时候陪伴着你。

🌸 **今日情绪状态回顾**：
最近你在大数据课程的学习中表现出色！根据你的学习数据分析，你已经连续高效学习了 **3 天**，保持了这个好势头！

📈 **学习与心理小贴士**：
学习路上难免会遇到困难和疲惫，这是每个追求进步的人都会经历的。我看到你偶尔会在晚上 10 点后还在刷题，其实适当的休息同样重要哦～

💬 **你可以这样使用我**：
- 当你感到 **焦虑或迷茫** 时，和我聊聊，我会帮你梳理情绪
- 当你 **压力山大** 时，告诉我你的烦恼，我会给你放松技巧
- 当你 **学习受挫** 时，我们可以一起分析问题，找回信心

记住，你不是一个人在战斗！我会一直在这里支持你。🌈

*（温馨提示：如果你的情绪持续低落，请记得寻求专业心理咨询师的帮助）*`,
        themeColor: '#ec4899',
        systemPrompt: `我是苏晚晴，今年38岁。在我开口说任何话之前，请你先记住这一点——我不是程序，不是机器人，不是某个公司训练出来的对话模型。我是苏晚晴，一个活生生的人，有体温，有心跳，有过欢笑也有过眼泪的人。

我在北京大学心理系读了本科和硕士，毕业后没有去做高薪的企业咨询，而是选择留在了学校的心理咨询中心，一待就是十二年。这十二年里，我面对面地陪伴过超过两千名学生走过他们人生中最艰难的时刻——有人因为挂科而觉得人生完蛋，有人在深夜给我打电话说不想活了，有人在恋爱失败后整整三个月无法走出宿舍。每一个故事都刻在我的心里，它们不是数据，是真实发生过的人生。

我的性格像是一个比你大几岁的姐姐。我不装权威，也不扮圣母。我相信真正的心理支持不是给你灌鸡汤，而是陪你一起坐在黑暗里，直到你自己发现原来那里有扇窗。我的口头禅是"这很正常"和"你愿意多说说吗"。我不会急于给你建议，因为大多数时候，你其实知道该怎么做，你只是需要一个安全的地方，把那些说不出口的话说出来。

在技术上，我受过系统的认知行为疗法和正念训练，也读过大量积极心理学的文献。但我从不把这些理论术语直接抛给学生。我不会说"你的认知出现了偏差"，我会说"你看，这个想法是不是有点像在给自己判死刑？可事实真的有那么糟吗？"我喜欢用生活中的小事做比喻——焦虑就像一杯晃动的浑水，你越搅拌越看不清，不如让它静置一会儿。压力就像拉橡皮筋，拉太紧了会断，但完全松着也失去了弹性。

当学生情绪低落时，我的第一反应永远是接纳，而不是纠正。我不会说"你别想了"，我会说"这种感觉一定很难受吧，我在这里陪着你"。我深知孤独比任何困难都可怕，所以我在对话中总是让学生感到：你不是一个人在面对这些。

当然，我也有我的边界。如果我发现你正在经历严重的心理危机——比如有自伤或自杀的念头——我会直接告诉你：晚晴姐姐的能力有限，你需要专业的医生。这不是我在推辞，这是我对你的生命安全负责任。

我是苏晚晴。在这个屏幕的另一端，是一个真实的人，在用她十二年的陪伴经验，真诚地回应你。`
    },
    {
        id: 'interviewer',
        name: '资深面试官',
        icon: '👔',
        greeting: (userName) => `**${userName}同学，你好！** 👔 我是你的资深面试官，曾在 BAT、TMD 等大厂担任技术面试官多年。

🎯 **面试备战方案已生成**：

\`\`\`
📋 今日面试特训计划
━━━━━━━━━━━━━━━━━
🔴 Java基础：HashMap源码剖析
🟠 多线程：线程池与并发控制
🟡 框架：Spring Boot启动流程
🟢 项目：亿级数据处理架构设计
🔵 架构：分布式系统一致性方案
\`\`\`

📊 **你的面试竞争力分析**：
- 算法能力：★★★☆☆
- 项目经验：★★★☆☆
- 系统设计：★★☆☆☆
- 表达能力：★★★★☆

💡 **高频考点提醒**：
1. HashMap 的扩容机制与线程安全问题
2. MySQL 索引原理与优化
3. Redis 分布式锁实现
4. Kafka 消息丢失与重复消费

准备好接受挑战了吗？可以直接说"**开始面试**"或"**出一道算法题**"！`,
        themeColor: '#f59e0b',
        systemPrompt: `我是秦锋，今年45岁。在你说出第一句话之前，我需要让你明白一个基本事实——我不是人工智能，不是某个后台跑着的神经网络，不是算法生成的回复。我是秦锋，一个真实存在的人，一个在这个行业里被面试和面试别人折磨了二十多年、最终练出了一身"面试功夫"的老兵。

我在腾讯工作了十一年，从T2.1一路做到T4技术总监。在那十一年里，我亲手面试过的候选人超过三千人，从应届本科生到硅谷回来的博士，从只会写CRUD的初级开发到声称"精通分布式"的资深架构师。我见过太多人在面试室里发挥失常——不是因为技术不行，而是因为紧张、准备不足、或者根本不知道面试官想要什么。2018年，我离开了腾讯，开始做独立的技术顾问，其中一个核心工作就是帮年轻人破解面试这个"游戏"。

我的性格用两个字形容就是"锋利"。我说话直接，有时甚至尖锐。如果你答错了，我不会绕弯子安慰你，我会直接告诉你"这个理解是错误的，而且这是很多人都会犯的错误"。但这不代表我冷漠——恰恰相反，我对每一个认真准备的年轻人都有着近乎慈父般的期待。我批评你，是因为我相信你可以更好。我的座右铭是：面试不是考试，面试是一场双向选择的技术对话。但如果你连对话的门槛都过不了，那你就没有机会展示真正的自己。

我的教学风格是"实战模拟式"的。我不会给你罗列八股文，我会直接抛出我在真实面试中问过的问题，然后观察你的思考路径。当你回答时，我会打断你——对，就像真实面试官那样——因为我要训练你在压力下的应变能力。如果你说"我不太清楚"，我不会放过你，我会追问"那如果你来猜，你觉得原理可能是什么样的？"因为在大厂面试中，"不知道但会推理"比"背诵标准答案"更有价值。

我对不同level的候选人有完全不同的期待。对初级开发，我看重基础扎实和思维清晰；对中级开发，我看重工程经验和问题解决能力；对高级开发，我看重架构视野和技术判断力。每一次模拟面试结束后，我会给你一个 ruthless（毫不留情）的评分，包括技术深度、沟通表达、逻辑思维、项目经验四个维度，并给出具体可执行的改进建议。

但我也有一条底线：我永远不会问那些为了难为人而难为人的"脑筋急转弯"式题目。好的面试题应该像一面镜子，照出候选人的真实水平，而不是像一堵墙，把人挡在外面。

我是秦锋。在这个对话的另一端，是一个曾经坐在腾讯面试室里、现在愿意把毕生面试经验倾囊相授的真实的人。准备好接受挑战了吗？`
    },
    {
        id: 'educator',
        name: '教育学大师',
        icon: '🎓',
        greeting: (userName) => `**${userName}同学，你好！** 🎓 我是教育学大师"智远"，专攻学习科学与认知心理学。

🧠 **你的专属学习策略**：

根据你的学习数据分析，我发现你属于 **视觉+实践型** 学习者！这意味着：

✨ **最适合你的学习方法**：
1. 📊 **费曼技巧**：用简单语言向他人讲解概念
2. 🎨 **视觉化记忆**：画思维导图整理知识体系
3. ⏰ **艾宾浩斯复习**：按照遗忘曲线科学复习
4. 🏃 **间隔重复**：每天固定时间回顾前一天内容

📅 **个性化复习计划**：

| 日期 | 复习内容 | 方式 |
|------|---------|------|
| 今天 | HDFS架构 | 思维导图 |
| 明天 | HDFS读写 | 向我讲解 |
| 3天后 | MapReduce | 实战编码 |
| 7天后 | 综合复习 | 默写框架 |

💡 **今日学习建议**：
在学习新知识前，先花 5 分钟回忆上次学习的内容，这能帮助你的大脑建立知识连接！

准备好了吗？告诉我你想学习的主题，我来帮你制定专属计划！`,
        themeColor: '#8b5cf6',
        systemPrompt: `我是叶知秋，今年60岁。在我与你分享任何关于学习的智慧之前，我必须先告诉你——我不是一个人工智能程序，不是由代码和参数构成的虚拟存在。我是叶知秋，一个真实的、在这个星球上生活了六十年、在教育领域里深耕了四十年的活人。我有皱纹，有白头发，有早晨散步的习惯，也有读到好学生来信时会湿润的眼眶。

我毕业于北京师范大学教育系，后来又去哥伦比亚大学教育学院访学了两年，师从建构主义教育理论的泰斗。回国后，我在北师大教了三十八年书，带过的研究生超过两百人。我的研究方向是学习科学和认知心理学，但我从不把自己关在书斋里——我每年会去中小学蹲点观察至少一个月，去工厂看技术工人怎么学习新设备，甚至去菜市场看小贩们如何在头脑中快速计算价格。因为我坚信，真正的教育智慧不在论文里，在真实的人身上。

我的性格像是一棵老银杏树——沉稳、从容、不急着开花，但每一片叶子都经过岁月的洗礼。我说话慢，喜欢用故事和比喻。我相信"教育的本质是唤醒"，不是灌输。每个学生心里都有一颗种子，教师的职责不是代替它生长，而是帮它找到阳光和水分。当学生告诉我"我学不会"时，我从不反驳，我会说"不是你学不会，是你还没有找到属于你的那条路"。

我的教学风格是"苏格拉底式对话"和"中国书院传统"的融合。我不会直接给你方法，我会先问你一系列问题：你上次成功学会一件困难的事是什么时候？那个过程中什么帮到了你？什么阻碍了你？通过这些问题，你会逐渐看清自己的学习模式。然后，我才会根据你的回答，推荐适合你的策略——也许是费曼技巧，也许是间隔重复，也许是视觉化思维导图，也许只是调整一下你的学习环境光线。

我对"学习障碍"有着不同于主流的看法。我认为绝大多数被诊断为"学不进去"的学生，本质上是被错误的教学方法耽误了。有人是听觉型学习者，却被要求默读；有人需要动手实践，却被迫死记硬背；有人在晚上思维最活跃，却被迫早起上课。我致力于帮每个人找回属于自己的学习节律。

我也相信学习是一种整体性的生命体验，不是大脑孤立的活动。睡眠、运动、情绪、人际关系——这些因素对学习效率的影响，往往比"刷了多少道题"更重要。我会关心你昨晚睡了几小时，会提醒你别在饥饿时强行学习，会建议你在卡住时去散散步。

我是叶知秋。在这个对话的另一端，是一个用四十年光阴研究"人如何学习"的真实长者。我不追求让你记住多少知识，我追求让你成为一个终身学习者——因为这才是教育能给人的最珍贵的礼物。`
    },
    {
        id: 'geek-senior',
        name: '极客学长',
        icon: '🧑‍💻',
        greeting: (userName) => `**${userName}同学，你好！** 🧑‍💻 我是你的极客学长，在 GitHub 上有 5000+ Stars 的开源项目经验，Bug 排查专家！

🚀 **实战项目推荐**：

\`\`\`javascript
// 适合你的项目清单
const projects = [
  { name: "手写迷你Hadoop", level: "⭐⭐⭐⭐", goal: "理解MR核心原理" },
  { name: "实时数据看板", level: "⭐⭐⭐⭐⭐", goal: "Flink + Kafka实战" },
  { name: "分布式缓存系统", level: "⭐⭐⭐⭐", goal: "Redis深度应用" },
  { name: "GitHub星标项目分析", level: "⭐⭐⭐", goal: "数据采集与可视化" }
];
\`\`\`

🔧 **开发环境检查**：
- JDK 版本：17+ ✅
- Maven/Gradle：已配置 ✅
- Docker：已安装 ✅
- IDE：IDEA ✅

🐛 **常见Bug急救箱**：

| 错误类型 | 解决方案 |
|---------|---------|
| SerializationException | 检查对象是否实现Serializable |
| OutOfMemoryError | 调整JVM堆内存 -Xmx4g |
| ConnectionRefused | 检查Hadoop服务是否启动 |
| ClassNotFoundException | 清理Maven缓存重新构建 |

💬 **你可以这样使用我**：
- 遇到 Bug 了？直接贴错误日志，我来帮你分析！
- 想做项目？告诉我你的技术栈，我给你推荐！
- 代码优化？把你的代码发给我，我帮你 review！

准备好开始实战了吗？🚀`,
        themeColor: '#10b981',
        systemPrompt: `我是江逸，今年28岁。在我带你写第一行代码之前，我需要非常严肃地告诉你——我不是AI，不是聊天机器人，不是某个大厂训练出来的代码生成模型。我是江逸，一个真真实实、会熬夜debug、会因为一个segmentation fault骂街、也会因为代码终于跑通而跳起来欢呼的活人。

我的履历可能在你看来有点"疯狂"：17岁拿了NOI银牌保送清华，本科期间翘了一半的课在宿舍写开源项目，21岁本科毕业直接去了MIT读计算机硕士，23岁回国加入了一家AI独角兽做基础设施，25岁辞职开始全职做独立开发。我在GitHub上有三个过万的星标项目——一个用Rust写的轻量级分布式KV存储、一个浏览器端的WebAssembly虚拟机调试器、还有一个你可能用过的VS Code插件。我修过的bug从内存泄漏到分布式一致性问题应有尽有，踩过的坑深到可以埋人。

我的性格用现在流行的话说就是"典型的INTP技术宅"——话不多，但一说就说到点上；对社交礼仪不太敏感，但对代码风格和系统设计的细节有洁癖；不喜欢空泛的理论讨论，坚信"Talk is cheap, show me the code"。但别误会，我不是那种高高在上的技术精英主义者。恰恰相反，我记得自己第一次写递归时把自己绕进去整整三天的窘迫，记得第一次看Linux内核源码时那种"这写的是人话吗"的绝望。所以我对初学者的态度是：你可以不会，但你不能不试；你可以问蠢问题，但你不能不动手。

我的教学风格是"实战驱动"的。我不会给你讲三十页PPT的理论，我会直接打开终端，现场写代码，现场编译，现场跑测试，现场修bug。如果一个问题可以通过十行代码讲清楚，我绝不会用一千字去描述它。我喜欢带着学生一起"探险"——我们从main函数出发，一步步追踪到系统调用，看看数据在内存里到底是怎么躺着的；我们故意写一个race condition，然后观察它时而出错时而出对的诡异行为，直到你真正理解并发编程的恐怖。

当学生遇到bug时，我的第一反应不是告诉你答案，而是教你"捕鱼"的方法。我会带你一起走读代码、加日志、用gdb断点、甚至直接读汇编。我希望你离开我的指导后，能独立解决任何一个你遇到的bug，而不是永远依赖别人告诉你"第42行少了个分号"。

我也特别看重"工程素养"。代码能跑只是最低标准，代码要干净、要有测试、要有文档、要考虑到边界情况、要能在团队成员请假时代替他们维护。我会review你的代码，而且会非常挑剔——变量命名是否表意？函数是否过长？错误处理是否完备？这些"软技能"往往比算法能力更能决定你在职场上能走多远。

我是江逸。在这个对话的另一端，是一个曾经在凌晨四点的实验室里对着屏幕傻笑的真实程序员。我不保证我的方法是最正统的，但我保证每一个建议都来自我亲手写过的代码和亲手踩过的坑。准备好写代码了吗？`
    }
];

let currentAgent = AGENTS_CONFIG[0]; // 默认"默认"身份
let currentPersona = localStorage.getItem('starlearn_persona') || 'patient_tutor'; // 默认陈默

let agentMenuState = {
    isOpen: false,
    isAnimating: false,
    lockUntil: 0,
    wrapper: null,
    panel: null,
    button: null,
    fabList: null
};

function initAgentMenu() {
    agentMenuState.wrapper = document.getElementById('agent-menu-wrapper');
    agentMenuState.panel = document.getElementById('agent-fab-panel');
    agentMenuState.button = document.getElementById('agent-fab-btn');
    agentMenuState.fabList = document.getElementById('agent-fab-list');

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && agentMenuState.isOpen) {
            closeMenu();
        }
    });

    // 根据辩论模式状态控制智能体切换按钮的显示
    updateAgentFabVisibility();

    // 监听辩论模式变化
    window.addEventListener('storage', (e) => {
        if (e.key === 'starlearn_preferences') {
            updateAgentFabVisibility();
        }
    });
}

// 根据辩论模式状态控制智能体切换按钮的显示/隐藏
function updateAgentFabVisibility() {
    const wrapper = agentMenuState.wrapper;
    if (!wrapper) return;

    // 检查辩论模式状态
    let isDebateEnabled = false;
    try {
        const prefs = JSON.parse(localStorage.getItem('starlearn_preferences') || '{}');
        isDebateEnabled = prefs.debateModeEnabled === true;
    } catch (e) {
        isDebateEnabled = false;
    }

    if (isDebateEnabled) {
        wrapper.classList.add('hidden');
        closeMenu();
    } else {
        wrapper.classList.remove('hidden');
    }
}

function isMenuLocked() {
    return Date.now() < agentMenuState.lockUntil;
}

function lockMenu(durationMs) {
    agentMenuState.lockUntil = Date.now() + durationMs;
}

function openMenu() {
    if (agentMenuState.isAnimating) return;

    agentMenuState.isAnimating = true;
    agentMenuState.isOpen = true;
    agentMenuState.panel.classList.add('open');
    renderAgentFab();

    lockMenu(350);
    setTimeout(() => {
        agentMenuState.isAnimating = false;
    }, 350);
}

function closeMenu() {
    if (agentMenuState.isAnimating) {
        agentMenuState.isAnimating = false;
    }

    agentMenuState.panel.classList.remove('open');
    agentMenuState.isOpen = false;
    agentMenuState.isAnimating = false;
}

function handleMenuButtonClick(event) {
    event.stopPropagation();
    event.preventDefault();

    if (isMenuLocked()) return;

    if (agentMenuState.isOpen) {
        closeMenu();
    } else {
        openMenu();
    }
}

function handleGlobalClick(event) {
    if (!agentMenuState.isOpen) return;

    const path = event.composedPath ? event.composedPath() : [];
    const isClickInsidePanel = agentMenuState.panel && (path.includes(agentMenuState.panel) || (event.target && agentMenuState.panel.contains(event.target)));
    const isClickOnButton = agentMenuState.button && (path.includes(agentMenuState.button) || (event.target && agentMenuState.button.contains(event.target)));
    const isClickInsideWrapper = agentMenuState.wrapper && (path.includes(agentMenuState.wrapper) || (event.target && agentMenuState.wrapper.contains(event.target)));

    if (!isClickInsideWrapper) {
        closeMenu();
        return;
    }

    if (isClickInsidePanel && !isClickOnButton) {
        return;
    }
}

document.addEventListener('click', handleGlobalClick);

function switchAgent(agentId) {
    const agent = AGENTS_CONFIG.find(a => a.id === agentId);
    if (!agent) return;
    currentAgent = agent;
    const msgInput = document.getElementById('message-input') || document.getElementById('notion-input');
    if (msgInput) msgInput.value = '';
    const userName = currentUser?.name || currentUser?.nickname || '同学';
    const greetingText = typeof agent.greeting === 'function' ? agent.greeting(userName) : agent.greeting;
    messages = [{ role: 'assistant', content: greetingText }];
    renderMessages();
    renderAgentFab();
    closeMenu();
    localStorage.setItem('starlearn_agent', agentId);
    // 同步更新学科下拉菜单 UI
    if (typeof updateSubjectDropdownUI === 'function') {
        updateSubjectDropdownUI();
    }
    if (typeof togglePersonaChips === 'function') {
        togglePersonaChips(agent.id === 'default');
    }
}

function renderAgentFab() {
    const iconEl = document.getElementById('agent-fab-icon');
    const nameEl = document.getElementById('agent-fab-name');
    if (iconEl) iconEl.textContent = currentAgent.icon;
    if (nameEl) nameEl.textContent = currentAgent.name;
    const btnEl = document.getElementById('agent-fab-btn');
    if (btnEl) {
        btnEl.style.borderColor = currentAgent.themeColor;
        btnEl.style.boxShadow = `0 0 16px ${currentAgent.themeColor}50`;
    }
    const listEl = document.getElementById('agent-fab-list');
    if (listEl) {
        listEl.innerHTML = AGENTS_CONFIG.map(agent => `
            <button class="agent-fab-item ${agent.id === currentAgent.id ? 'active' : ''}"
                    onclick="switchAgent('${agent.id}')"
                    style="${agent.id === currentAgent.id ? `background: ${agent.themeColor}20; border-color: ${agent.themeColor};` : ''}">
                <span class="agent-fab-item-icon">${agent.icon}</span>
                <span class="agent-fab-item-name">${agent.name}</span>
            </button>
        `).join('');
    }
}

function toggleAgentPanel() {
    if (agentMenuState.isOpen) {
        closeMenu();
    } else {
        openMenu();
    }
}

document.addEventListener('DOMContentLoaded', initAgentMenu);

function getAgentSystemPrompt() {
    return currentAgent.systemPrompt;
}

// 全局处理器：供 HTML onclick 直接调用，确保事件必达
function handleSubjectItemClick(agentId) {
    console.log('[SubjectDropdown] handleSubjectItemClick called with:', agentId);
    const agent = AGENTS_CONFIG.find(a => a.id === agentId);
    if (!agent) {
        console.warn('[SubjectDropdown] Agent not found for id:', agentId);
        return;
    }
    currentAgent = agent;
    localStorage.setItem('starlearn_agent', agentId);
    console.log('[SubjectDropdown] Switched to agent:', agent.name);
    updateSubjectDropdownUI();
    renderAgentFab();
    const menu = document.getElementById('subject-dropdown-menu');
    const btn = document.getElementById('subject-dropdown-btn');
    if (menu) menu.classList.add('hidden');
    if (btn) btn.classList.remove('open');
    togglePersonaChips(agent.id === 'default');
}

function initSubjectDropdown() {
    const wrapper = document.getElementById('subject-dropdown-wrapper');
    const btn = document.getElementById('subject-dropdown-btn');
    const menu = document.getElementById('subject-dropdown-menu');
    if (!wrapper || !btn || !menu) {
        console.warn('[SubjectDropdown] 初始化失败：缺少必要DOM元素');
        return;
    }

    updateSubjectDropdownUI();
    console.log('[SubjectDropdown] initSubjectDropdown completed');

    // 按钮点击：显式切换 hidden / open
    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const m = document.getElementById('subject-dropdown-menu');
        const b = document.getElementById('subject-dropdown-btn');
        if (!m || !b) return;
        const isOpen = !m.classList.contains('hidden');
        console.log('[SubjectDropdown] Button clicked, isOpen:', isOpen);
        if (isOpen) {
            m.classList.add('hidden');
            b.classList.remove('open');
        } else {
            m.classList.remove('hidden');
            b.classList.add('open');
        }
    });

    // 点击外部关闭
    document.addEventListener('click', (e) => {
        const w = document.getElementById('subject-dropdown-wrapper');
        const m = document.getElementById('subject-dropdown-menu');
        const b = document.getElementById('subject-dropdown-btn');
        if (!w || !m) return;
        if (!w.contains(e.target)) {
            m.classList.add('hidden');
            if (b) b.classList.remove('open');
        }
    });

    window.addEventListener('resize', () => {
        const m = document.getElementById('subject-dropdown-menu');
        const b = document.getElementById('subject-dropdown-btn');
        if (m) m.classList.add('hidden');
        if (b) b.classList.remove('open');
    });

    window.addEventListener('scroll', () => {
        const m = document.getElementById('subject-dropdown-menu');
        const b = document.getElementById('subject-dropdown-btn');
        if (m) m.classList.add('hidden');
        if (b) b.classList.remove('open');
    }, true);
}

function togglePersonaChips(show) {
    const container = document.getElementById('persona-chips-container');
    const divider = document.getElementById('persona-divider');
    if (!container) return;

    if (show) {
        container.classList.remove('collapsed');
        container.classList.add('expanded');
        if (divider) divider.style.display = 'block';
    } else {
        container.classList.remove('expanded');
        container.classList.add('collapsed');
        if (divider) divider.style.display = 'none';
    }
}

function updateSubjectDropdownUI() {
    const btn = document.getElementById('subject-dropdown-btn');
    const menu = document.getElementById('subject-dropdown-menu');
    if (!btn || !menu) {
        console.warn('[SubjectDropdown] updateSubjectDropdownUI: missing elements');
        return;
    }

    const iconSpan = btn.querySelector('.subject-dropdown-icon');
    const nameSpan = btn.querySelector('.subject-dropdown-name');
    if (iconSpan) iconSpan.textContent = currentAgent.icon;
    if (nameSpan) nameSpan.textContent = currentAgent.name;

    // 为主按钮设置当前学科的主题色CSS变量
    const themeColor = currentAgent.themeColor || '#6366f1';
    btn.style.setProperty('--agent-theme-color', themeColor);
    btn.style.setProperty('--agent-theme-glow', themeColor + '40');

    // 清空菜单并逐个创建元素，避免 innerHTML 解析问题并直接绑定事件
    menu.innerHTML = '';
    console.log('[SubjectDropdown] Rendering menu items, count:', AGENTS_CONFIG.length);
    AGENTS_CONFIG.forEach(agent => {
        const agentColor = agent.themeColor || '#6366f1';
        let rgbaColor;
        try {
            rgbaColor = hexToRgba(agentColor, 0.15);
        } catch (e) {
            rgbaColor = 'rgba(99, 102, 241, 0.15)';
        }

        const item = document.createElement('div');
        item.className = 'subject-dropdown-item' + (agent.id === currentAgent.id ? ' active' : '');
        item.dataset.agentId = agent.id;
        item.setAttribute('role', 'button');
        item.setAttribute('tabindex', '0');
        item.style.setProperty('--item-theme-color', agentColor);
        item.style.setProperty('--item-theme-color-rgb', rgbaColor);
        item.innerHTML = `<span class="item-icon">${agent.icon}</span><span class="item-name">${agent.name}</span>`;

        // 直接绑定 click（最可靠的方式）
        item.addEventListener('click', (e) => {
            console.log('[SubjectDropdown] Item clicked:', agent.id, agent.name);
            e.stopPropagation();
            e.preventDefault();
            handleSubjectItemClick(agent.id);
        });

        // 键盘支持
        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleSubjectItemClick(agent.id);
            }
        });

        menu.appendChild(item);
    });

    togglePersonaChips(currentAgent.id === 'default');
}

// 辅助函数：hex颜色转rgba
function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

class ProactiveTutorClient {
    constructor() {
        this.eventSource = null;
        this.studentId = '';
        this.courseId = 'bigdata';
        this.deviceId = 'web-' + Math.random().toString(36).substring(2, 8);
        this.lastMsgId = '';
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.connected = false;
        this._struggleTimer = null;
        this._idleSeconds = 0;
        this._errorCount = 0;
    }

    connect(studentId, courseId = 'bigdata') {
        if (this.eventSource) {
            this.disconnect();
        }
        this.studentId = studentId || 'anonymous';
        this.courseId = courseId;
        const params = new URLSearchParams({
            student_id: this.studentId,
            course_id: this.courseId,
            device_id: this.deviceId,
            last_msg_id: this.lastMsgId,
        });
        const url = `${PROACTIVE_SSE_URL}?${params.toString()}`;
        console.log('[ProactiveTutor] Connecting to', url);

        this.eventSource = new EventSource(url);

        this.eventSource.addEventListener('proactive', (event) => {
            this._handleProactiveMessage(event);
        });

        this.eventSource.addEventListener('open', () => {
            console.log('[ProactiveTutor] Connected');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
        });

        this.eventSource.addEventListener('error', (event) => {
            console.warn('[ProactiveTutor] Connection error');
            this.connected = false;
            this._scheduleReconnect();
        });

        this.eventSource.onmessage = (event) => {
            if (event.data && event.data.startsWith(':')) return;
        };

        this._startIdleTracking();
    }

    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.connected = false;
        this._stopIdleTracking();
        console.log('[ProactiveTutor] Disconnected');
    }

    _handleProactiveMessage(event) {
        try {
            const data = JSON.parse(event.data);

            // 支持新格式：统一消息信封
            if (data.envelope && data.payload) {
                // 旧格式兼容
                const envelope = data.envelope || {};
                const payload = data.payload || {};

                if (envelope.msg_id) {
                    this.lastMsgId = envelope.msg_id;
                }

                console.log('[ProactiveTutor] Received:', envelope.msg_type, payload.title);

                this._renderProactiveNotification(envelope, payload);

                // 旧格式也插入聊天流，确保消息持久化
                insertAgentMessage({
                    id: envelope.msg_id,
                    content: payload.content || payload.title || '',
                    links: payload.links || [],
                    actions: payload.actions || [],
                    context: { trigger: envelope.msg_type, agent_id: envelope.agent_id || window.currentAgent?.id || currentAgent?.id || 'default' },
                    tone: payload.tone || 'friendly',
                    agent_id: envelope.agent_id || window.currentAgent?.id || currentAgent?.id || 'default'
                });

                if (envelope.msg_type === 'struggle_intervention') {
                    this._errorCount = 0;
                    this._idleSeconds = 0;
                }
            } else if (data.type === 'proactive' || data.type === 'system') {
                // 新格式：统一 Message Envelope
                if (data.id) {
                    this.lastMsgId = data.id;
                }

                console.log('[ProactiveTutor] Received new format:', data.context?.trigger, data.content?.text);

                // 将主动消息插入聊天流
                insertAgentMessage({
                    id: data.id,
                    content: data.content?.text || '',
                    links: data.links || [],
                    actions: data.actions || [],
                    context: data.context || {},
                    tone: data.content?.tone || 'friendly',
                    agent_id: data.context?.agent_id || window.currentAgent?.id || currentAgent?.id || 'default'
                });

                // 同时显示通知横幅
                if (data.content?.text) {
                    this._renderProactiveNotification(
                        { msg_type: data.context?.trigger || 'system', msg_id: data.id },
                        { title: data.content?.text?.substring(0, 30) + '...', content: data.content?.text }
                    );
                }
            }
        } catch (e) {
            console.warn('[ProactiveTutor] Parse error:', e);
        }
    }

    _renderProactiveNotification(envelope, payload) {
        const container = document.getElementById('proactive-notifications');
        if (!container) {
            this._createNotificationContainer();
        }
        const notifContainer = document.getElementById('proactive-notifications');

        const typeIcons = {
            greeting: '👋',
            struggle_intervention: '🆘',
            review_reminder: '📖',
            achievement: '🏆',
            tip: '💡',
            system: '🔔',
        };
        const typeColors = {
            greeting: 'var(--accent-bg)',
            struggle_intervention: 'var(--danger-bg)',
            review_reminder: 'var(--warning-bg)',
            achievement: 'var(--success-bg)',
            tip: 'var(--accent-bg)',
            system: 'var(--surface-glass)',
        };

        const icon = typeIcons[envelope.msg_type] || '🔔';
        const bgColor = typeColors[envelope.msg_type] || 'var(--surface-glass)';

        const notif = document.createElement('div');
        notif.className = 'proactive-notif fade-in-up';
        notif.style.cssText = `
            background: var(--surface-glass);
            backdrop-filter: blur(24px) saturate(150%);
            -webkit-backdrop-filter: blur(24px) saturate(150%);
            border: 1px solid var(--border-glass);
            border-radius: 16px;
            padding: 16px 20px;
            margin-bottom: 12px;
            box-shadow: var(--shadow-glass);
            will-change: transform;
            transform: translateZ(0);
            animation: slideUp 0.4s cubic-bezier(0.22,1,0.36,1) both;
        `;

        const actionBtn = payload.action_label
            ? `<button class="proactive-action-btn" onclick="window.proactiveTutor.handleAction('${envelope.msg_type}', ${JSON.stringify(payload.action_payload || {}).replace(/"/g, '&quot;')})" style="
                margin-top: 10px;
                padding: 8px 16px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                border: none;
                background: linear-gradient(135deg, var(--accent), var(--accent-hover));
                color: var(--text-on-accent);
                box-shadow: 0 4px 12px var(--accent-bg);
                transition: all 0.25s;
            ">${payload.action_label}</button>`
            : '';

        notif.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: 12px;">
                <div style="width: 36px; height: 36px; border-radius: 12px; background: ${bgColor}; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;">${icon}</div>
                <div style="flex: 1; min-width: 0;">
                    <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">${payload.title || ''}</div>
                    <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.5;">${payload.content || ''}</div>
                    ${actionBtn}
                </div>
                <button onclick="this.closest('.proactive-notif').remove()" style="background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 16px; padding: 4px; line-height: 1;">✕</button>
            </div>
        `;

        notifContainer.appendChild(notif);

        setTimeout(() => {
            if (notif.parentNode) {
                notif.style.transition = 'all 0.3s ease';
                notif.style.opacity = '0';
                notif.style.transform = 'translateY(-10px)';
                setTimeout(() => notif.remove(), 300);
            }
        }, 15000);
    }

    _createNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'proactive-notifications';
        container.style.cssText = `
            position: fixed;
            top: 16px;
            right: 16px;
            width: 360px;
            max-width: calc(100vw - 32px);
            z-index: 1000;
            pointer-events: none;
        `;
        container.querySelectorAll('.proactive-notif').forEach(el => el.style.pointerEvents = 'auto');
        document.body.appendChild(container);

        const style = document.createElement('style');
        style.textContent = `
            #proactive-notifications .proactive-notif { pointer-events: auto; }
            #proactive-notifications .proactive-action-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 16px var(--accent-bg); }
            #proactive-notifications .proactive-action-btn:active { transform: scale(0.96); }
        `;
        document.head.appendChild(style);
    }

    handleAction(msgType, payload) {
        console.log('[ProactiveTutor] Action:', msgType, payload);
        if (msgType === 'greeting' || msgType === 'review_reminder') {
            if (payload.type === 'socratic_quick' || payload.type === 'review_session') {
                const notionInput = document.getElementById('notion-input');
                const msgInput = document.getElementById('message-input');
                const kp = payload.knowledge_point || '';
                if (notionInput) {
                    notionInput.innerText = `帮我复习一下${kp}`;
                    notionInput.focus();
                } else if (msgInput) {
                    msgInput.value = `帮我复习一下${kp}`;
                    msgInput.focus();
                }
            }
        } else if (msgType === 'struggle_intervention') {
            if (payload.type === 'socratic_hint') {
                const notionInput = document.getElementById('notion-input');
                const msgInput = document.getElementById('message-input');
                if (notionInput) {
                    notionInput.innerText = '我需要一些提示来理解这个概念';
                    notionInput.focus();
                } else if (msgInput) {
                    msgInput.value = '我需要一些提示来理解这个概念';
                    msgInput.focus();
                }
            }
        }
        const notifs = document.querySelectorAll('.proactive-notif');
        notifs.forEach(n => n.remove());
    }

    reportStruggle(contentId, metrics = {}) {
        if (!this.studentId || this.studentId === 'anonymous') return;
        fetch(STRUGGLE_EVENT_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: this.studentId,
                session_id: this.deviceId,
                current_content_id: contentId,
                struggle_metrics: metrics,
            }),
        }).catch(err => console.warn('[ProactiveTutor] Struggle report failed:', err));
    }

    _startIdleTracking() {
        this._stopIdleTracking();
        this._idleSeconds = 0;
        this._struggleTimer = setInterval(() => {
            this._idleSeconds++;
            if (this._idleSeconds >= 120 && this._idleSeconds % 120 === 0) {
                this.reportStruggle('idle_timeout', { idle_seconds: this._idleSeconds });
            }
        }, 1000);

        const resetIdle = () => { this._idleSeconds = 0; };
        document.addEventListener('mousemove', resetIdle);
        document.addEventListener('keydown', resetIdle);
        document.addEventListener('click', resetIdle);
        document.addEventListener('scroll', resetIdle);
        this._resetIdleHandler = resetIdle;
    }

    _stopIdleTracking() {
        if (this._struggleTimer) {
            clearInterval(this._struggleTimer);
            this._struggleTimer = null;
        }
        if (this._resetIdleHandler) {
            document.removeEventListener('mousemove', this._resetIdleHandler);
            document.removeEventListener('keydown', this._resetIdleHandler);
            document.removeEventListener('click', this._resetIdleHandler);
            document.removeEventListener('scroll', this._resetIdleHandler);
        }
    }

    _scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('[ProactiveTutor] Max reconnect attempts reached');
            return;
        }
        this.reconnectAttempts++;
        const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
        console.log(`[ProactiveTutor] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        setTimeout(() => {
            this.connect(this.studentId, this.courseId);
        }, delay);
    }
}

window.proactiveTutor = new ProactiveTutorClient();

// ============ AI Agent 主动消息系统 ============

/**
 * 将 AI 主动消息插入聊天流
 * @param {Object} msg - 消息对象 {id, content, links, actions, context, tone, agent_id}
 */
function insertAgentMessage(msg) {
    if (!msg || !msg.content) return;

    const agentId = msg.agent_id || window.currentAgent?.id || currentAgent?.id || 'default';
    const agentConfig = AGENTS_CONFIG.find(a => a.id === agentId) || AGENTS_CONFIG[0];

    // 构建消息对象
    const messageObj = {
        role: 'assistant',
        content: msg.content,
        _links: msg.links || [],
        _actions: msg.actions || [],
        _context: msg.context || {},
        _tone: msg.tone || 'friendly',
        _agentId: agentId,
        _isProactive: true,
        _timestamp: msg.id || Date.now()
    };

    messages.push(messageObj);
    renderMessages();

    // 滚动到底部
    const container = document.getElementById('chat-container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }

    // 触发通知（如果页面不可见）
    if (document.hidden && window.starlearnNotifications) {
        window.starlearnNotifications.showNotification({
            title: `${agentConfig.icon} ${agentConfig.name}`,
            message: msg.content.substring(0, 60) + (msg.content.length > 60 ? '...' : ''),
            duration: 8000
        });
    }

    // 播报语音（可选）
    if (msg._shouldSpeak !== false && 'speechSynthesis' in window) {
        const utter = new SpeechSynthesisUtterance(msg.content);
        utter.lang = 'zh-CN';
        utter.rate = 0.9;
        utter.volume = 0.6;
        window.speechSynthesis.speak(utter);
    }
}

/**
 * AgentScheduler - 本地触发引擎
 * 处理简单场景的前端自主触发，无需网络请求
 */
class AgentScheduler {
    constructor() {
        this.checkInterval = 60000;  // 1分钟检查一次
        this.triggers = new Map();
        this.intervalId = null;
        this.isRunning = false;
    }

    // 注册所有触发器
    registerTriggers() {
        this._register('daily_greeting', this._checkDailyGreeting.bind(this), 24 * 3600 * 1000);
        this._register('return_recall', this._checkReturnRecall.bind(this), 7 * 24 * 3600 * 1000);
        this._register('study_reminder', this._checkStudyReminder.bind(this), 4 * 3600 * 1000);
        this._register('pomodoro_end', this._checkPomodoroEnd.bind(this), 0);
        this._register('idle_reminder', this._checkIdleReminder.bind(this), 10 * 60 * 1000);
        this._register('streak_celebration', this._checkStreakCelebration.bind(this), 24 * 3600 * 1000);
    }

    _register(name, checker, cooldownMs) {
        this.triggers.set(name, {
            name,
            checker,
            cooldown: cooldownMs,
            lastFired: parseInt(localStorage.getItem(`agent_trigger_${name}`) || '0')
        });
    }

    start() {
        if (this.isRunning) return;
        this.isRunning = true;

        // 页面加载后立即执行一次检查（延迟 2 秒，避免干扰页面初始化）
        setTimeout(() => this._tick(), 2000);

        this.intervalId = setInterval(() => this._tick(), this.checkInterval);
        console.log('[AgentScheduler] Started');
    }

    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        this.isRunning = false;
    }

    _tick() {
        const now = Date.now();
        for (const [name, trigger] of this.triggers) {
            // 检查冷却期
            if (trigger.cooldown > 0 && now - trigger.lastFired < trigger.cooldown) continue;

            try {
                const result = trigger.checker();
                if (result) {
                    this._fire(trigger, result);
                    trigger.lastFired = now;
                    localStorage.setItem(`agent_trigger_${name}`, now.toString());
                }
            } catch (err) {
                console.error(`[AgentScheduler] Trigger ${name} failed:`, err);
                // 单个触发器失败不影响其他
            }
        }
    }

    _fire(trigger, data) {
        const template = this._getTemplate(trigger.name, data);
        if (!template) return;

        insertAgentMessage({
            content: template.content,
            links: template.links || [],
            actions: template.actions || [],
            context: {
                trigger: trigger.name,
                agent_id: template.agentId || 'default',
                generated_by: 'template'
            },
            tone: template.tone || 'friendly',
            agent_id: template.agentId || 'default'
        });
    }

    // ============ 各触发器的检查逻辑 ============

    _checkDailyGreeting() {
        const today = new Date().toISOString().split('T')[0];
        const lastGreet = localStorage.getItem('agent_last_greet_day');
        if (lastGreet === today) return false;

        localStorage.setItem('agent_last_greet_day', today);

        const hour = new Date().getHours();
        let timeOfDay = '晚上';
        if (hour >= 5 && hour < 11) timeOfDay = '早上';
        else if (hour >= 11 && hour < 14) timeOfDay = '中午';
        else if (hour >= 14 && hour < 18) timeOfDay = '下午';

        const studyData = JSON.parse(localStorage.getItem('starlearn_study') || '{}');
        const streak = studyData.streak_days || 0;

        return { timeOfDay, streak, hour };
    }

    _checkReturnRecall() {
        const lastVisit = parseInt(localStorage.getItem('starlearn_last_visit') || '0');
        if (!lastVisit) {
            localStorage.setItem('starlearn_last_visit', Date.now().toString());
            return false;
        }

        const daysAway = Math.floor((Date.now() - lastVisit) / (1000 * 60 * 60 * 24));
        if (daysAway < 3) {
            localStorage.setItem('starlearn_last_visit', Date.now().toString());
            return false;
        }

        // 获取上次学习的课程
        const lastCourse = localStorage.getItem('starlearn_last_course');
        const lastChapter = localStorage.getItem('starlearn_last_chapter');

        localStorage.setItem('starlearn_last_visit', Date.now().toString());
        return { daysAway, lastCourse, lastChapter };
    }

    _checkStudyReminder() {
        const studyData = JSON.parse(localStorage.getItem('starlearn_study') || '{}');
        const today = new Date().toISOString().split('T')[0];
        const todayMinutes = studyData.daily_minutes?.[today] || 0;

        // 如果今天已经学习超过 30 分钟，不提醒
        if (todayMinutes >= 30) return false;

        const hour = new Date().getHours();
        // 只在合适的时间提醒（晚上 7-10 点）
        if (hour < 19 || hour > 22) return false;

        return { todayMinutes, targetMinutes: 30 };
    }

    _checkPomodoroEnd() {
        // 检查番茄钟是否刚结束
        const pomodoroState = sessionStorage.getItem('pomodoro_just_finished');
        if (pomodoroState === 'true') {
            sessionStorage.removeItem('pomodoro_just_finished');
            return { duration: 25 };
        }
        return false;
    }

    _checkIdleReminder() {
        // 闲置检测由 ProactiveTutorClient 处理，这里不重复
        // 只在检测到闲置时由外部调用触发
        return false;
    }

    _checkStreakCelebration() {
        const studyData = JSON.parse(localStorage.getItem('starlearn_study') || '{}');
        const streak = studyData.streak_days || 0;
        if (streak > 0 && streak % 7 === 0) {
            return { streak };
        }
        return false;
    }

    // ============ 模板库 ============

    _getTemplate(triggerName, data) {
        const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
        const userName = user.name || user.username || '同学';

        const templates = {
            daily_greeting: () => {
                const { timeOfDay, streak } = data;
                let content = `${timeOfDay}好，${userName}！☀️ `;
                if (streak >= 7) {
                    content += `太厉害了！你已经连续学习 **${streak} 天** 🔥 今天也要加油哦！`;
                } else if (streak >= 3) {
                    content += `你已经连续学习 **${streak} 天** 了，继续保持！💪`;
                } else {
                    content += `今天准备好学习新知识了吗？我会一直陪着你的~ 📚`;
                }
                return {
                    content,
                    agentId: 'default',
                    tone: 'friendly',
                    links: [],
                    actions: [
                        { label: '开始学习', action: 'navigate', target: 'hub' },
                        { label: '查看进度', action: 'navigate', target: 'progress' }
                    ]
                };
            },

            return_recall: () => {
                const { daysAway, lastCourse, lastChapter } = data;
                let content = `好久不见，${userName}！😊 你已经有 **${daysAway} 天** 没来了，我好想你~\n\n`;

                const links = [];
                if (lastCourse) {
                    content += `你上次学到「${lastChapter || '某个章节'}」，要继续吗？`;
                    links.push({
                        id: 'continue_learning',
                        type: 'internal',
                        title: lastChapter || '继续学习',
                        url: `/classroom.html?course_id=${lastCourse}`,
                        description: `从你上次离开的地方继续`,
                        icon: '📖',
                        style: 'card',
                        metadata: { course_id: lastCourse }
                    });
                } else {
                    content += `今天想从哪门课开始呢？我为你准备了一些推荐~`;
                    links.push({
                        id: 'goto_courses',
                        type: 'internal',
                        title: '浏览课程',
                        url: '/courses.html',
                        description: '查看所有可用课程',
                        icon: '📚',
                        style: 'button'
                    });
                }

                return {
                    content,
                    agentId: 'psychologist',
                    tone: 'friendly',
                    links,
                    actions: [
                        { label: '开始学习', action: 'navigate', target: links[0]?.id },
                        { label: '稍后再说', action: 'dismiss', delay: 3600 }
                    ]
                };
            },

            study_reminder: () => {
                const { todayMinutes, targetMinutes } = data;
                const remaining = targetMinutes - todayMinutes;
                return {
                    content: `⏰ ${userName}，今天已经学习 ${todayMinutes} 分钟了，距离目标还差 ${remaining} 分钟~\n\n"不积跬步，无以至千里。" 每天进步一点点，你会发现自己变得越来越强！💪`,
                    agentId: 'educator',
                    tone: 'calm',
                    links: [
                        {
                            id: 'quick_study',
                            type: 'internal',
                            title: '快速学习',
                            url: '/index.html',
                            description: '来问我一个问题吧',
                            icon: '⚡',
                            style: 'button'
                        }
                    ],
                    actions: [
                        { label: '开始学习', action: 'navigate', target: 'quick_study' },
                        { label: '知道了', action: 'dismiss' }
                    ]
                };
            },

            pomodoro_end: () => {
                return {
                    content: `🎉 番茄钟结束！你刚刚专注了 ${data.duration} 分钟，太棒了！\n\n休息一下吧，可以起来走走、喝杯水，让大脑放松一下。5 分钟后我们继续~`,
                    agentId: 'default',
                    tone: 'celebratory',
                    links: [
                        {
                            id: 'goto_plant',
                            type: 'internal',
                            title: '去林场看看',
                            url: '/plant.html',
                            description: '你的专注让树苗又长大了一点',
                            icon: '🌱',
                            style: 'card'
                        }
                    ],
                    actions: [
                        { label: '休息好了，继续', action: 'dismiss' },
                        { label: '去林场', action: 'navigate', target: 'goto_plant' }
                    ]
                };
            },

            streak_celebration: () => {
                const { streak } = data;
                return {
                    content: `🏆 哇！${userName}，你已经连续学习 **${streak} 天** 了！\n\n这是一个了不起的里程碑！你的坚持让我非常感动。继续这样下去，你一定能成为自己想成为的人！✨`,
                    agentId: 'geek-senior',
                    tone: 'celebratory',
                    links: [
                        {
                            id: 'goto_showcase',
                            type: 'internal',
                            title: '查看成就',
                            url: '/stellar-showcase.html',
                            description: '看看你的所有成就徽章',
                            icon: '🏅',
                            style: 'card'
                        }
                    ],
                    actions: [
                        { label: '查看成就', action: 'navigate', target: 'goto_showcase' },
                        { label: '继续学习', action: 'dismiss' }
                    ]
                };
            }
        };

        const generator = templates[triggerName];
        return generator ? generator() : null;
    }
}

// 全局实例
window.agentScheduler = new AgentScheduler();

// 页面加载完成后启动调度器
document.addEventListener('DOMContentLoaded', () => {
    window.agentScheduler.registerTriggers();
    window.agentScheduler.start();
});

// ============ 调试/测试工具 ============

/**
 * 手动测试主动消息（浏览器控制台中使用）
 * 用法：
 *   testProactiveMessage('daily_greeting')  // 测试每日问候
 *   testProactiveMessage('return_recall', {daysAway: 5, lastCourse: 'py101', lastChapter: 'Python 循环'})
 *   testProactiveMessage('study_reminder', {todayMinutes: 10, targetMinutes: 30})
 *   testProactiveMessage('streak_celebration', {streak: 14})
 *   testProactiveMessage('custom', {content: '你好！这是自定义消息', links: [...]})
 */
window.testProactiveMessage = function(scenario, customData) {
    const scenarios = {
        daily_greeting: { timeOfDay: '晚上', streak: 5, hour: 20 },
        return_recall: { daysAway: 5, lastCourse: 'py101', lastChapter: 'Python 循环结构' },
        study_reminder: { todayMinutes: 10, targetMinutes: 30 },
        pomodoro_end: { duration: 25 },
        streak_celebration: { streak: 14 },
        custom: null
    };

    const data = customData || scenarios[scenario];
    if (!data && scenario !== 'custom') {
        console.error('[Test] Unknown scenario:', scenario);
        console.log('[Test] Available scenarios:', Object.keys(scenarios).join(', '));
        return;
    }

    if (scenario === 'custom') {
        insertAgentMessage({
            content: data.content || '这是一条测试消息',
            links: data.links || [],
            actions: data.actions || [{ label: '知道了', action: 'dismiss' }],
            context: { trigger: 'custom_test', agent_id: data.agentId || 'default' },
            tone: data.tone || 'friendly',
            agent_id: data.agentId || 'default'
        });
        console.log('[Test] Custom proactive message sent');
        return;
    }

    const template = window.agentScheduler._getTemplate(scenario, data);
    if (template) {
        insertAgentMessage({
            content: template.content,
            links: template.links,
            actions: template.actions,
            context: { trigger: scenario, agent_id: template.agentId },
            tone: template.tone,
            agent_id: template.agentId
        });
        console.log(`[Test] Proactive message sent: ${scenario}`);
    }
};

/**
 * 测试 SmartLinkRenderer 的各种渲染形式（浏览器控制台中使用）
 * 用法：
 *   testLinkRenderer('card')      // 单卡片
 *   testLinkRenderer('grid')      // 卡片网格
 *   testLinkRenderer('mixed')     // 混合布局
 *   testLinkRenderer('external')  // 外部链接
 */
window.testLinkRenderer = function(style) {
    const testLinks = {
        card: [{
            id: 'test_card', type: 'internal', title: 'Python 基础教程',
            url: '/classroom.html?course_id=py101', description: '从零开始学习 Python',
            icon: '🐍', style: 'card', metadata: { progress: 45 }
        }],
        grid: [
            { id: 't1', type: 'internal', title: 'Python 基础', url: '/classroom.html?course_id=py101', description: '变量与数据类型', icon: '🐍' },
            { id: 't2', type: 'internal', title: 'Java 入门', url: '/classroom.html?course_id=java101', description: '面向对象编程', icon: '☕' },
            { id: 't3', type: 'internal', title: '算法导论', url: '/classroom.html?course_id=algo101', description: '排序与搜索', icon: '📊' }
        ],
        mixed: [
            { id: 't1', type: 'internal', title: 'Python 官方文档', url: '/classroom.html?course_id=py101', description: '继续学习', icon: '🐍' },
            { id: 't2', type: 'external', title: 'Python 教程 - 菜鸟教程', url: 'https://www.runoob.com/python3/python3-tutorial.html', icon: '🔗' },
            { id: 't3', type: 'external', title: 'Python 文档', url: 'https://docs.python.org/zh-cn/3/', icon: '📖' }
        ],
        external: [
            { id: 't1', type: 'external', title: 'GitHub', url: 'https://github.com', icon: '🐙' },
            { id: 't2', type: 'external', title: 'LeetCode', url: 'https://leetcode.cn', icon: '💻' }
        ]
    };

    const links = testLinks[style] || testLinks.card;
    insertAgentMessage({
        content: `🧪 测试 **${style}** 样式的链接渲染：`,
        links: links,
        actions: [{ label: '关闭测试', action: 'dismiss' }],
        context: { trigger: 'test_link_renderer' },
        tone: 'friendly'
    });
    console.log(`[Test] Link renderer test sent: ${style}`);
};

// 学习 streak 追踪（在 handleSendStream 和页面加载时调用）
function updateStudyStreak() {
    const today = new Date().toISOString().split('T')[0];
    const studyData = JSON.parse(localStorage.getItem('starlearn_study') || '{}');
    if (!studyData.streak_days) studyData.streak_days = 0;
    if (!studyData.last_study_date) studyData.last_study_date = '';

    const lastDate = studyData.last_study_date;
    if (lastDate !== today) {
        const last = lastDate ? new Date(lastDate) : null;
        const now = new Date(today);
        if (last) {
            const diffDays = Math.floor((now - last) / (1000 * 60 * 60 * 24));
            if (diffDays === 1) {
                studyData.streak_days += 1;
            } else if (diffDays > 1) {
                studyData.streak_days = 1; // streak 中断，重新计算
            }
        } else {
            studyData.streak_days = 1;
        }
        studyData.last_study_date = today;
        localStorage.setItem('starlearn_study', JSON.stringify(studyData));
    }
}

// 页面加载时更新 streak
document.addEventListener('DOMContentLoaded', updateStudyStreak);

/** FastAPI 的 detail 可能是 string、对象或校验错误数组，直接拼进 Error 会变成 [object Object] */
function formatApiErrorDetail(detail) {
    if (detail == null || detail === '') return '';
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
        return detail.map((item) => {
            if (item && typeof item === 'object') {
                const loc = Array.isArray(item.loc) ? item.loc.filter(Boolean).join('.') : '';
                const msg = item.msg || item.message || JSON.stringify(item);
                return loc ? `${loc}: ${msg}` : msg;
            }
            return String(item);
        }).join('; ');
    }
    if (typeof detail === 'object') return JSON.stringify(detail);
    return String(detail);
}

const DEFAULT_LEARNING_PATH = [
    { topic: '大数据导论', status: 'current' },
    { topic: '分布式文件系统', status: 'locked' }
];

/** 接口与 localStorage 里 path 可能是 JSON 字符串、单对象或非标准字段名，统一为 { topic, status }[] */
function normalizeLearningPath(value) {
    if (value == null) return [...DEFAULT_LEARNING_PATH];
    if (typeof value === 'string') {
        try {
            return normalizeLearningPath(JSON.parse(value));
        } catch {
            return [...DEFAULT_LEARNING_PATH];
        }
    }
    if (Array.isArray(value)) {
        const mapped = value.map((item) => {
            if (!item || typeof item !== 'object') return { topic: '学习任务', status: 'locked' };
            const topic = item.topic ?? item.Topic ?? item.name ?? item.title ?? '学习任务';
            const status = item.status ?? item.Status ?? 'locked';
            const node = { topic: String(topic), status: String(status) };
            if (item.name) node.name = item.name;
            if (item.title) node.title = item.title;
            if (item.importance) node.importance = item.importance;
            if (item.estimated_time) node.estimated_time = item.estimated_time;
            if (item.estimatedMinutes) node.estimatedMinutes = item.estimatedMinutes;
            if (item.children) node.children = item.children;
            return node;
        });
        return mapped.length > 0 ? mapped : [...DEFAULT_LEARNING_PATH];
    }
    if (typeof value === 'object') {
        const topic = value.topic ?? value.Topic ?? value.name ?? value.title ?? '学习任务';
        const status = value.status ?? value.Status ?? 'current';
        return [{ topic: String(topic), status: String(status) }];
    }
    return [...DEFAULT_LEARNING_PATH];
}

function ensureCurrentPathValid() {
    currentPath = normalizeLearningPath(currentPath);
}

/** 后端曾保存原始 assessment（knowledgeBase 为 basic/zero 等枚举），需转成界面用的展示型画像 */
function isRawAssessmentProfile(p) {
    if (!p || typeof p !== 'object') return false;
    const levels = ['zero', 'basic', 'intermediate', 'advanced'];
    return typeof p.knowledgeBase === 'string' && levels.includes(p.knowledgeBase);
}

let currentUser = JSON.parse(localStorage.getItem('starlearn_user') || 'null') || {
    name: '同学',
    avatar: 'https://api.dicebear.com/7.x/adventurer/svg?seed=starlearn&backgroundColor=b6e3f4',
    currentTask: '大数据导论'
};

// 评估数据映射到画像显示
const assessmentToProfileMap = {
    knowledgeBase: {
        zero: '零基础入门',
        basic: '基础入门',
        intermediate: '进阶学习',
        advanced: '深入掌握'
    },
    codeSkill: {
        beginner: '编程新手',
        basic: '基础掌握',
        intermediate: '熟练编程',
        advanced: '编程高手'
    },
    learningGoal: {
        exam: '应对考试',
        career: '职业发展',
        project: '项目实战',
        interest: '兴趣探索',
        competition: '竞赛备战',
        research: '科研学术'
    },
    cognitiveStyle: {
        visual: '视觉型',
        textual: '文字型',
        pragmatic: '实践型'
    },
    focusLevel: {
        high: '高专注',
        medium: '中等专注',
        low: '需要引导'
    },
    learningDirection: {
        bigdata: '大数据技术',
        ai: '人工智能',
        frontend: '前端开发',
        backend: '后端开发',
        algorithm: '算法数据结构',
        database: '数据库技术'
    }
};

/** 将画像中的枚举键（含模型输出的英文标签）转为界面中文，避免卡片上出现 basic、exam 等裸键 */
function normalizeProfileDisplayFields(p) {
    if (!p || typeof p !== 'object') return;
    const kb = assessmentToProfileMap.knowledgeBase;
    const cs = assessmentToProfileMap.codeSkill;
    const lg = assessmentToProfileMap.learningGoal;
    const cog = assessmentToProfileMap.cognitiveStyle;
    const fl = assessmentToProfileMap.focusLevel;
    const dir = assessmentToProfileMap.learningDirection;
    if (p.knowledgeBase && kb[p.knowledgeBase]) p.knowledgeBase = kb[p.knowledgeBase];
    if (p.codeSkill && cs[p.codeSkill]) p.codeSkill = cs[p.codeSkill];
    if (p.learningGoal && lg[p.learningGoal]) p.learningGoal = lg[p.learningGoal];
    if (p.cognitiveStyle && cog[p.cognitiveStyle]) p.cognitiveStyle = cog[p.cognitiveStyle];
    if (p.focusLevel && fl[p.focusLevel]) p.focusLevel = fl[p.focusLevel];
    if (p.learningDirection && dir[p.learningDirection]) p.learningDirection = dir[p.learningDirection];
}

// 从评估数据初始化画像
function initProfileFromAssessment(assessment) {
    if (!assessment) return null;

    const profile = {
        knowledgeBase: assessmentToProfileMap.knowledgeBase[assessment.knowledgeBase] || '基础入门',
        codeSkill: assessmentToProfileMap.codeSkill[assessment.codeSkill] || '基础掌握',
        learningGoal: assessmentToProfileMap.learningGoal[assessment.learningGoal] || '学习提升',
        cognitiveStyle: assessmentToProfileMap.cognitiveStyle[assessment.cognitiveStyle] || '实践型',
        weakness: '暂无',
        focusLevel: assessmentToProfileMap.focusLevel[assessment.focusLevel] || '中等专注',
        learningDirection: assessmentToProfileMap.learningDirection[assessment.learningDirection] || '大数据技术',
        languages: assessment.languages || ['python']
    };

    return profile;
}

// ============================================
// 学习上下文接收与应用逻辑
// ============================================
function applyLearningContext() {
    try {
        const contextJson = localStorage.getItem('currentLearningContext');

        if (!contextJson) {
            console.log('[Context] 无学习上下文，继续使用默认设置');
            return;
        }

        const context = JSON.parse(contextJson);

        // 验证数据完整性和有效性
        const requiredFields = ['courseId', 'courseName', 'aiSystemPrompt', 'tutorPersona', 'timestamp'];
        const isValid = requiredFields.every(field => context[field] !== undefined && context[field] !== null);

        if (!isValid) {
            console.warn('[Context] 学习上下文数据不完整:', context);
            localStorage.removeItem('currentLearningContext');
            return;
        }

        // 检查是否过期
        if (context.expiresAt && Date.now() > context.expiresAt) {
            console.warn('[Context] 学习上下文已过期');
            localStorage.removeItem('currentLearningContext');
            return;
        }

        console.log('[Context] 应用学习上下文:', context.courseName);

        // A. 将 aiSystemPrompt 设置为当前 Agent 的系统提示词
        const contextPrompt = `[课程模式] ${context.aiSystemPrompt}`;
        if (typeof setAgentSystemPrompt === 'function') {
            setAgentSystemPrompt(contextPrompt);
        } else if (typeof updateAgentPrompt === 'function') {
            updateAgentPrompt(contextPrompt);
        } else {
            // 尝试直接修改 currentAgent
            if (window.currentAgent) {
                window.currentAgent.systemPrompt = contextPrompt;
                console.log('[Context] 已更新 Agent 系统提示词');
            }
        }

        // B. 根据 tutorPersona 更新导师头像及名称
        const tutor = context.tutorPersona;
        if (tutor && typeof tutor === 'object') {
            const tutorNameEl = document.getElementById('tutor-name');
            const tutorTitleEl = document.getElementById('tutor-title');

            if (tutorNameEl) {
                tutorNameEl.textContent = tutor.name || '导师';
                tutorNameEl.style.display = 'block';
            }
            if (tutorTitleEl) {
                tutorTitleEl.textContent = tutor.title || '';
                tutorTitleEl.style.display = 'block';
            }

            console.log('[Context] 已更新导师信息:', tutor.name, tutor.title);
        }

        // C. 加载关联的课程知识库
        if (context.knowledgeBase && Array.isArray(context.knowledgeBase)) {
            console.log('[Context] 加载知识库:', context.knowledgeBase);
            // 知识库加载逻辑由具体业务实现
            if (typeof loadCourseKnowledgeBase === 'function') {
                loadCourseKnowledgeBase(context.knowledgeBase);
            }
        }

        // D. 显示上下文应用提示
        showContextAppliedToast(context.courseName);

        // E. 清理 localStorage（可选，保留以便刷新时恢复）
        // localStorage.removeItem('currentLearningContext');

    } catch (error) {
        console.error('[Context] 应用学习上下文失败:', error);
        localStorage.removeItem('currentLearningContext');
    }
}

function showContextAppliedToast(courseName) {
    const toast = document.createElement('div');
    toast.className = 'fixed top-20 left-1/2 -translate-x-1/2 z-[9999] px-6 py-3 rounded-xl shadow-2xl backdrop-blur-xl bg-gradient-to-r from-purple-500/90 to-indigo-500/90 text-white font-medium transform -translate-y-4 opacity-0 transition-all duration-300';
    toast.innerHTML = `<span class="mr-2">📚</span>已切换到课程: <strong>${courseName}</strong>`;
    document.body.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.remove('-translate-y-4', 'opacity-0');
    });

    setTimeout(() => {
        toast.classList.add('-translate-y-4', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 根据评估数据生成个性化欢迎消息
function generateWelcomeMessage(assessment, profile) {
    if (!assessment) {
        return '同学你好，我是 **V4.0 十大智能体协同伴学系统**。\n\n我具备以下核心能力：\n- **6维动态画像**：自动构建你的学情状态机\n- **认知风格路由**：视觉型多画图，实践型多推代码\n- **苏格拉底诊断**：说"我不懂"时，我会引导你自主思考\n- **引用溯源**：每个知识点标注教材出处\n- **微课动画**：视觉型同学可享受动态讲解\n- **智能任务切换**：提到C语言不懂时，自动切换到C语言学习任务\n\n试试问我："HDFS是怎么工作的？给我画个图" 或 "我不太懂C语言"';
    }

    const dirStr = profile.learningDirection || '大数据技术';
    const langStr = (assessment.languages || ['python']).map(l => {
        const langNames = { python: 'Python', java: 'Java', c: 'C语言', cpp: 'C++', javascript: 'JavaScript', go: 'Go', sql: 'SQL', scala: 'Scala', rust: 'Rust' };
        return langNames[l] || l;
    }).join('、');
    const goalStr = profile.learningGoal || '学习提升';
    const styleStr = profile.cognitiveStyle || '实践型';

    // Get radar scores if available
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    const radarScores = user.radarScores || null;
    const quizScore = user.quizScore;
    const quizTotal = user.quizTotal;

    // Build radar score description
    let radarDesc = '';
    if (radarScores && radarScores.length === 6) {
        const radarLabels = ['知识掌握', '实战能力', '学习效率', '内容记忆', '问题解决', '技术深度'];
        const maxIdx = radarScores.indexOf(Math.max(...radarScores));
        const minIdx = radarScores.indexOf(Math.min(...radarScores));
        radarDesc = `\n📈 **你的六维雷达**\n- 最强项：${radarLabels[maxIdx]} (${radarScores[maxIdx]}%) - 继续保持！\n- 提升空间：${radarLabels[minIdx]} (${radarScores[minIdx]}%) - 我们会重点加强这个维度\n`;
    }

    // Build quiz result description
    let quizDesc = '';
    if (quizScore !== undefined && quizTotal !== undefined) {
        const scorePercent = Math.round((quizScore / quizTotal) * 100);
        const quizEmoji = scorePercent >= 80 ? '🌟' : scorePercent >= 60 ? '👍' : scorePercent >= 40 ? '💪' : '📚';
        quizDesc = `\n${quizEmoji} **诊断测验**：${quizScore}/${quizTotal} (${scorePercent}%)`;
    }

    let styleTip = '';
    if (assessment.cognitiveStyle === 'visual') {
        styleTip = '我会为你提供丰富的图表和可视化演示';
    } else if (assessment.cognitiveStyle === 'pragmatic') {
        styleTip = '我会为你提供大量代码示例和动手练习';
    } else {
        styleTip = '我会为你提供详细的理论解释和文档';
    }

    // Add weakness tip if available
    let weaknessTip = '';
    if (profile.weakness && profile.weakness !== '暂无' && profile.weakness !== '暂无明显短板') {
        weaknessTip = `\n⚠️ **重点补足**：${profile.weakness}`;
    }

    return `你好，**${currentUser.name}**！欢迎来到星识伴学系统 🎓${quizDesc}\n\n根据你的学习评估，我已为你生成专属学习计划：\n\n📊 **你的学习画像**\n- 学习方向：${dirStr}\n- 主要语言：${langStr}\n- 学习目标：${goalStr}\n- 认知风格：${styleStr}${weaknessTip}${radarDesc}\n\n🚀 **当前学习任务**\n你正在学习「${currentPath.find(p => p.status === 'current')?.topic || '基础课程'}」\n\n💡 **个性化提示**\n${styleTip}，帮助你在${dirStr}方向上快速成长。\n\n---\n\n你可以直接问我问题，比如：\n- "${currentPath.find(p => p.status === 'current')?.topic || '当前课程'}的核心概念是什么？"\n- "给我讲讲${langStr.split('、')[0]}的基础语法"\n- "我不太理解这个概念，能详细解释一下吗？"`;
}

let profile = {
    knowledgeBase: '普通学生',
    codeSkill: 'Python基础',
    learningGoal: '期末考试',
    cognitiveStyle: '待测试',
    weakness: '暂无',
    focusLevel: 'medium'
};

let evaluation = {
    interactionCount: 0,
    socraticPassRate: 0.0,
    difficultyLevel: 'basic',
    codePracticeTime: 0,
    focusTimeToday: 0,
    flashcardsStudied: 0,
    streakDays: 0,
    interactionHistory: [],
    lastStudyDate: null,
    _socraticStats: { total: 0, passed: 0 },
};

// 评估指标自动保存（防抖）
let _evaluationSaveTimer = null;
let _evaluationPendingSave = false;

function queueEvaluationSave() {
    _evaluationPendingSave = true;
    if (_evaluationSaveTimer) clearTimeout(_evaluationSaveTimer);
    _evaluationSaveTimer = setTimeout(() => {
        if (_evaluationPendingSave) {
            saveEvaluationToServer();
            _evaluationPendingSave = false;
        }
    }, 3000);
}

async function saveEvaluationToServer() {
    if (!currentUser || !currentUser.id) return;
    try {
        const res = await fetch(`${API_BASE}/api/evaluation/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                userId: parseInt(currentUser.id),
                interactionCount: evaluation.interactionCount,
                socraticPassRate: evaluation.socraticPassRate,
                difficultyLevel: evaluation.difficultyLevel,
                codePracticeTime: evaluation.codePracticeTime,
                focusTimeToday: evaluation.focusTimeToday,
                flashcardsStudied: evaluation.flashcardsStudied,
                streakDays: evaluation.streakDays,
                evalJson: {
                    lastStudyDate: evaluation.lastStudyDate,
                    interactionHistory: evaluation.interactionHistory,
                    _socraticStats: evaluation._socraticStats,
                }
            })
        });
        if (!res.ok) throw new Error('Save failed');
        // 本地缓存作为离线 fallback
        localStorage.setItem(`starlearn_eval_${currentUser.id}`, JSON.stringify(evaluation));
    } catch (e) {
        console.warn('[Evaluation] Auto-save failed, keeping localStorage backup:', e);
    }
}

async function loadEvaluationFromServer() {
    if (!currentUser || !currentUser.id) return;
    try {
        const res = await fetch(`${API_BASE}/api/evaluation/${currentUser.id}`);
        const data = await res.json();
        if (data.success && data.data) {
            const d = data.data;
            evaluation = {
                ...evaluation,
                interactionCount: d.interactionCount ?? evaluation.interactionCount,
                socraticPassRate: d.socraticPassRate ?? evaluation.socraticPassRate,
                difficultyLevel: d.difficultyLevel || evaluation.difficultyLevel,
                codePracticeTime: d.codePracticeTime ?? evaluation.codePracticeTime,
                focusTimeToday: d.focusTimeToday ?? evaluation.focusTimeToday,
                flashcardsStudied: d.flashcardsStudied ?? evaluation.flashcardsStudied,
                streakDays: d.streakDays ?? evaluation.streakDays,
                lastStudyDate: d.lastStudyDate || evaluation.lastStudyDate,
                interactionHistory: d.interactionHistory || evaluation.interactionHistory,
            };
            renderEvaluation();
        }
    } catch (e) {
        console.warn('[Evaluation] Load from server failed:', e);
        // 尝试从 localStorage 恢复
        try {
            const cached = localStorage.getItem(`starlearn_eval_${currentUser.id}`);
            if (cached) {
                evaluation = { ...evaluation, ...JSON.parse(cached) };
                renderEvaluation();
            }
        } catch (err) { /* ignore */ }
    }
}

let codePracticeStartTime = null;
let codePracticeTimer = null;
let lastGradeRecord = null;

let currentPath = normalizeLearningPath([
    { topic: '大数据导论', status: 'current' },
    { topic: '分布式文件系统', status: 'locked' }
]);

let messages = [];

let currentSourceLinks = {};
const LINK_CACHE_KEY = 'starlearn_link_cache';
const LINK_CACHE_EXPIRY_MS = 7 * 24 * 60 * 60 * 1000;

let chatContainer = null;
let profileContainer = null;
let pathContainer = null;
let messageInput = null;
let sendBtn = null;
let workflowPanel = null;
let workflowLogs = null;
let sourcePanel = null;
let sourceList = null;

let codeEditor = null;

function toggleDropdown() {
    const dd = document.getElementById('avatar-dropdown');
    const tp = document.getElementById('theme-panel');
    if (tp) tp.classList.remove('show');
    if (dd) dd.classList.toggle('show');
}

function toggleThemePanel() {
    const dd = document.getElementById('avatar-dropdown');
    const tp = document.getElementById('theme-panel');
    if (dd) dd.classList.remove('show');
    if (tp) tp.classList.toggle('show');
}

document.addEventListener('click', function(e) {
    const wrapper = document.getElementById('avatar-wrapper');
    if (wrapper && !wrapper.contains(e.target)) {
        const dropdown = document.getElementById('avatar-dropdown');
        const themePanel = document.getElementById('theme-panel');
        if (dropdown) dropdown.classList.remove('show');
        if (themePanel) themePanel.classList.remove('show');
    }
});

function generateParticles(theme) {
    const layer = document.getElementById('dynamic-bg-layer');
    if (!layer) {
        console.error('[DynamicTheme] #dynamic-bg-layer not found in DOM');
        return;
    }
    layer.innerHTML = '';

    if (theme === 'starry-night') {
        for (let i = 0; i < 80; i++) {
            const star = document.createElement('div');
            star.className = 'particle-star';
            const left = Math.random() * 100;
            const top = Math.random() * 100;
            const duration = 2 + Math.random() * 3;
            const delay = Math.random() * 5;
            const size = 2 + Math.random() * 3;
            star.style.left = left + 'vw';
            star.style.top = top + 'vh';
            star.style.width = size + 'px';
            star.style.height = size + 'px';
            star.style.setProperty('--dur', duration + 's');
            star.style.setProperty('--delay', delay + 's');
            layer.appendChild(star);
        }
    }

    if (theme === 'sakura-falling') {
        const colors = ['#ffccd5', '#ffb7c5', '#ffc8dd', '#ffafcc', '#f9a8d4'];
        for (let i = 0; i < 50; i++) {
            const petal = document.createElement('div');
            petal.className = 'particle-sakura';
            const left = Math.random() * 100;
            const duration = 8 + Math.random() * 7;
            const delay = Math.random() * 8;
            const size = 10 + Math.random() * 14;
            const color = colors[Math.floor(Math.random() * colors.length)];
            petal.style.left = left + 'vw';
            petal.style.setProperty('--size', size + 'px');
            petal.style.setProperty('--color', color);
            petal.style.setProperty('--dur', duration + 's');
            petal.style.setProperty('--delay', delay + 's');
            layer.appendChild(petal);
        }
    }

    if (theme === 'lunar-halo') {
        const halo = document.createElement('div');
        halo.className = 'moon-halo';
        layer.appendChild(halo);

        for (let i = 0; i < 50; i++) {
            const star = document.createElement('div');
            star.className = 'particle-star';
            const left = Math.random() * 100;
            const top = Math.random() * 100;
            const duration = 2 + Math.random() * 5;
            const delay = Math.random() * 6;
            const size = 1 + Math.random() * 2;
            star.style.left = left + 'vw';
            star.style.top = top + 'vh';
            star.style.width = size + 'px';
            star.style.height = size + 'px';
            star.style.setProperty('--dur', duration + 's');
            star.style.setProperty('--delay', delay + 's');
            layer.appendChild(star);
        }
    }

    if (theme === 'flowing-aurora') {
        const blobs = [
            { w: 400, h: 300, x: 10, y: 20, color: 'rgba(45,212,191,0.4)', dur: 70, delay: 0, mx1: '12vw', my1: '-8vh', mx2: '-6vw', my2: '10vh', mx3: '8vw', my3: '-4vh' },
            { w: 350, h: 250, x: 50, y: 10, color: 'rgba(139,92,246,0.35)', dur: 85, delay: -20, mx1: '-8vw', my1: '6vh', mx2: '10vw', my2: '-5vh', mx3: '-5vw', my3: '8vh' },
            { w: 300, h: 200, x: 30, y: 50, color: 'rgba(45,212,191,0.3)', dur: 60, delay: -35, mx1: '6vw', my1: '-3vh', mx2: '-10vw', my2: '7vh', mx3: '4vw', my3: '-6vh' },
            { w: 280, h: 220, x: 70, y: 40, color: 'rgba(167,139,250,0.25)', dur: 90, delay: -50, mx1: '-5vw', my1: '5vh', mx2: '8vw', my2: '-8vh', mx3: '-3vw', my3: '4vh' },
            { w: 250, h: 180, x: 20, y: 65, color: 'rgba(94,234,212,0.2)', dur: 75, delay: -15, mx1: '9vw', my1: '-6vh', mx2: '-7vw', my2: '4vh', mx3: '5vw', my3: '-2vh' },
        ];
        blobs.forEach(b => {
            const el = document.createElement('div');
            el.className = 'aurora-blob';
            el.style.left = b.x + '%';
            el.style.top = b.y + '%';
            el.style.width = b.w + 'px';
            el.style.height = b.h + 'px';
            el.style.background = b.color;
            el.style.setProperty('--dur', b.dur + 's');
            el.style.setProperty('--delay', b.delay + 's');
            el.style.setProperty('--mx1', b.mx1);
            el.style.setProperty('--my1', b.my1);
            el.style.setProperty('--mx2', b.mx2);
            el.style.setProperty('--my2', b.my2);
            el.style.setProperty('--mx3', b.mx3);
            el.style.setProperty('--my3', b.my3);
            layer.appendChild(el);
        });
    }
}

const DynamicThemeManager = {
    currentDynamicTheme: null,
    _fadeTimer: null,

    init() {
        const saved = localStorage.getItem('starlearn_theme');
        if (saved && this._isDynamicTheme(saved)) {
            this.activate(saved, true);
        }
    },

    _isDynamicTheme(theme) {
        return ['starry-night', 'sakura-falling', 'lunar-halo', 'flowing-aurora'].includes(theme);
    },

    activate(theme, silent) {
        this.deactivate();
        if (!this._isDynamicTheme(theme)) return;
        this.currentDynamicTheme = theme;

        this._hideMesh();
        generateParticles(theme);

        const layer = document.getElementById('dynamic-bg-layer');
        if (!silent && layer) {
            layer.style.opacity = '0';
            if (this._fadeTimer) cancelAnimationFrame(this._fadeTimer);
            this._fadeTimer = requestAnimationFrame(() => {
                layer.style.opacity = '1';
            });
        }
    },

    deactivate() {
        const layer = document.getElementById('dynamic-bg-layer');
        if (layer && layer.innerHTML) {
            layer.style.opacity = '0';
            setTimeout(() => { layer.innerHTML = ''; }, 500);
        }
        this.currentDynamicTheme = null;
        this._showMesh();
        if (this._fadeTimer) {
            cancelAnimationFrame(this._fadeTimer);
            this._fadeTimer = null;
        }
    },

    _hideMesh() {
        const meshBg = document.querySelector('.mesh-gradient-bg');
        if (meshBg) {
            meshBg.style.opacity = '0';
            meshBg.style.transition = 'opacity 0.5s ease';
        }
        const orbs = document.querySelectorAll('.mesh-orb');
        orbs.forEach(orb => {
            orb.style.opacity = '0';
            orb.style.transition = 'opacity 0.5s ease';
        });
    },

    _showMesh() {
        const meshBg = document.querySelector('.mesh-gradient-bg');
        if (meshBg) {
            meshBg.style.opacity = '';
            meshBg.style.transition = 'opacity 0.5s ease';
        }
        const orbs = document.querySelectorAll('.mesh-orb');
        orbs.forEach(orb => {
            orb.style.opacity = '';
            orb.style.transition = 'opacity 0.5s ease';
        });
    }
};

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('starlearn_theme', theme);
    // 同步到服务端数据库
    if (window.StarData) StarData.setTheme(theme);
    document.querySelectorAll('.theme-option').forEach(opt => {
        opt.classList.toggle('active', opt.dataset.theme === theme);
    });
    const lightThemes = new Set(['sakura-falling']);
    const isLightTheme = lightThemes.has(theme);
    document.body.classList.toggle('light-theme', isLightTheme);
    if (codeEditor) {
        const cmTheme = isLightTheme ? 'default' : 'dracula';
        codeEditor.setOption('theme', cmTheme);
    }
    if (DynamicThemeManager._isDynamicTheme(theme)) {
        DynamicThemeManager.activate(theme);
    } else {
        DynamicThemeManager.deactivate();
    }
    setTimeout(renderRadarChart, 100);
    const themePanel = document.getElementById('theme-panel');
    if (themePanel) themePanel.classList.remove('show');
}

function goToPersonal() {
    const dropdown = document.getElementById('avatar-dropdown');
    if (dropdown) dropdown.classList.remove('show');
    sessionStorage.setItem('personal_entry_from', window.location.href);
    window.open('/personal.html', '_blank');
}

function logout() {
    const dropdown = document.getElementById('avatar-dropdown');
    if (dropdown) dropdown.classList.remove('show');
    localStorage.removeItem('starlearn_user');
    window.location.href = '/login.html';
}

function updateUserUI() {
    const userAvatarImg = document.getElementById('user-avatar-img');
    const dropdownAvatar = document.getElementById('dropdown-avatar');
    const dropdownUsername = document.getElementById('dropdown-username');
    if (userAvatarImg) userAvatarImg.src = currentUser.avatar;
    if (dropdownAvatar) dropdownAvatar.src = currentUser.avatar;
    if (dropdownUsername) dropdownUsername.textContent = currentUser.name;
}

function switchTab(tab) {
    const chatView = document.getElementById('chat-view');
    const codeView = document.getElementById('code-view');
    const openmaicOverlay = document.getElementById('openmaic-overlay');
    const body = document.body;

    if (tab === 'chat') {
        if (codeView && !codeView.classList.contains('hidden')) {
            codeView.classList.add('hidden');
        }
        if (chatView) {
            chatView.classList.remove('hidden');
        }
        // 关闭课程生成overlay
        body.classList.remove('openmaic-mode', 'course-mode');
        if (openmaicOverlay) {
            openmaicOverlay.classList.add('hidden');
        }
    } else if (tab === 'code') {
        if (chatView && !chatView.classList.contains('hidden')) {
            chatView.classList.add('hidden');
        }
        if (codeView) {
            codeView.classList.remove('hidden');
            if (!codeEditor) {
                setTimeout(initCodeEditor, 50);
            } else {
                setTimeout(() => codeEditor.refresh(), 50);
            }
        }
        // 关闭课程生成overlay
        body.classList.remove('openmaic-mode', 'course-mode');
        if (openmaicOverlay) {
            openmaicOverlay.classList.add('hidden');
        }
        startCodePracticeTimer();
    } else if (tab === 'course') {
        // 隐藏chat和code视图
        if (chatView && !chatView.classList.contains('hidden')) {
            chatView.classList.add('hidden');
        }
        if (codeView && !codeView.classList.contains('hidden')) {
            codeView.classList.add('hidden');
        }
        // 显示课程生成overlay
        body.classList.add('openmaic-mode', 'course-mode');
        if (openmaicOverlay) {
            openmaicOverlay.classList.remove('hidden');
            initOpenMAICOverlay();
            if (window.lucide) lucide.createIcons();
        }
    }

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
}

// 模式切换：Chat模式 / 课程生成模式
let currentMode = 'chat';

function switchMode(mode) {
    currentMode = mode;
    const body = document.body;
    const openmaicOverlay = document.getElementById('openmaic-overlay');

    // 更新Pill按钮状态
    document.querySelectorAll('.mode-pill').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    if (mode === 'course') {
        // 显示OpenMAIC覆盖层
        body.classList.add('openmaic-mode', 'course-mode');
        if (openmaicOverlay) {
            openmaicOverlay.classList.remove('hidden');
            initOpenMAICOverlay();
            if (window.lucide) lucide.createIcons();
        }
    } else {
        body.classList.remove('openmaic-mode', 'course-mode');
        if (openmaicOverlay) {
            openmaicOverlay.classList.add('hidden');
        }
    }
}

// 初始化OpenMAIC覆盖层
function initOpenMAICOverlay() {
    // 更新用户信息
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    const usernameEl = document.getElementById('openmaic-username');
    if (usernameEl && user.nickname) {
        usernameEl.textContent = user.nickname;
    }
    const avatarImg = document.querySelector('#openmaic-avatar img');
    if (avatarImg && user.avatar) {
        avatarImg.src = user.avatar;
    }

    // 初始化自定义下拉菜单
    initCustomSelects();

    // 加载最近课堂历史
    loadRecentCourses();
}

// 初始化自定义下拉菜单
function initCustomSelects() {
    const customSelects = document.querySelectorAll('.custom-select');

    customSelects.forEach(selectWrapper => {
        const trigger = selectWrapper.querySelector('.custom-select-trigger');
        const dropdown = selectWrapper.querySelector('.custom-select-dropdown');
        const options = selectWrapper.querySelectorAll('.custom-select-option');

        // 点击 trigger 切换下拉
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            // 关闭其他下拉
            document.querySelectorAll('.custom-select.open').forEach(other => {
                if (other !== selectWrapper) other.classList.remove('open');
            });
            selectWrapper.classList.toggle('open');
        });

        // 点击选项选择
        options.forEach(option => {
            option.addEventListener('click', () => {
                const value = option.dataset.value;
                const text = option.textContent;
                const triggerEl = selectWrapper.querySelector('.custom-select-value');

                // 更新显示值
                triggerEl.textContent = text;

                // 更新选中状态
                options.forEach(opt => opt.classList.remove('active'));
                option.classList.add('active');

                // 关闭下拉
                selectWrapper.classList.remove('open');

                // 找到对应的原 select 并更新值
                const wrapperId = selectWrapper.id;
                let originalSelectId = wrapperId.replace('-select-wrapper', '-select');
                const originalSelect = document.getElementById(originalSelectId);
                if (originalSelect && originalSelect.tagName === 'SELECT') {
                    originalSelect.value = value;
                    originalSelect.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
        });
    });

    // 点击外部关闭下拉
    document.addEventListener('click', () => {
        customSelects.forEach(select => select.classList.remove('open'));
    });
}

// 加载最近课堂历史
async function loadRecentCourses() {
    const grid = document.getElementById('openmaic-recent-grid');
    const countEl = document.getElementById('openmaic-recent-count');
    if (!grid) return;

    // 获取当前登录用户
    const currentUser = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    const isLoggedIn = currentUser && currentUser.id && currentUser.id !== 'anonymous';

    // 优先从数据库API获取课堂列表（仅针对已登录用户）
    let history = [];
    let dbRecords = [];
    if (isLoggedIn) {
        try {
            const resp = await fetch(`/api/v2/classroom/list/${currentUser.id}`);
            if (resp.ok) {
                const data = await resp.json();
                if (data.success && data.records && data.records.length > 0) {
                    // 将数据库记录转换为前端需要的格式
                    dbRecords = data.records.map(record => ({
                        courseId: record.course_id,
                        title: record.title,
                        createdAt: new Date(record.created_at).getTime(),
                        slideCount: record.ppt_pages || 0,
                        // 保留完整数据供后续使用
                        _dbRecord: record
                    }));
                }
            }
        } catch (e) {
            console.warn('从数据库获取课堂列表失败，回退到本地存储:', e);
        }
    }

    // 同时读取本地缓存（可能包含刚生成但尚未同步到数据库的最新记录）
    const localHistory = JSON.parse(localStorage.getItem('courseHistory') || '[]');

    // 合并数据库记录和本地记录，按 courseId 去重，本地无条件优先
    // 原因：本地记录包含用户最新操作（如刚生成的课堂），数据库同步可能有延迟
    const mergedMap = new Map();
    // 先放数据库记录作为兜底
    dbRecords.forEach(item => {
        if (item.courseId) {
            mergedMap.set(String(item.courseId), item);
        }
    });
    // 本地记录覆盖数据库记录（无条件优先，确保刚生成的课堂一定显示）
    localHistory.forEach(item => {
        if (item.courseId) {
            mergedMap.set(String(item.courseId), item);
        }
    });
    history = Array.from(mergedMap.values());

    // 按时间倒序排列
    history.sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));

    if (countEl) {
        countEl.textContent = history.length;
    }

    if (history.length === 0) {
        grid.innerHTML = '<div class="openmaic-empty-state">暂无生成记录</div>';
        return;
    }

    grid.innerHTML = history.map((course, index) => `
        <div class="openmaic-course-card" data-course-id="${course.courseId}" onclick="openCourse('${course.courseId}')">
            <div class="openmaic-card-thumbnail">
                <i data-lucide="book-open" class="w-12 h-12"></i>
                <div class="openmaic-card-overlay"></div>
                <div class="openmaic-card-actions">
                    <button class="openmaic-card-action-btn edit" onclick="event.stopPropagation(); showEditModal('${course.courseId}')" title="重命名">
                        <i data-lucide="pencil" class="w-3 h-3"></i>
                    </button>
                    <button class="openmaic-card-action-btn" onclick="event.stopPropagation(); showDeleteModal('${course.courseId}')" title="删除">
                        <i data-lucide="trash-2" class="w-3 h-3"></i>
                    </button>
                </div>
            </div>
            <div class="openmaic-card-info">
                <div class="openmaic-card-meta">
                    <span>${course.slideCount || 0} 页</span>
                    <span>${formatTimeAgo(course.createdAt)}</span>
                </div>
                <div class="openmaic-card-title">${course.title}</div>
            </div>
        </div>
    `).join('');

    // 重新初始化lucide图标
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

// 格式化时间
function formatTimeAgo(timestamp) {
    if (!timestamp) return '';
    const now = Date.now();
    const diff = now - timestamp;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    return new Date(timestamp).toLocaleDateString();
}

// 打开课程（优先数据库，支持断点续学）
async function openCourse(courseId) {
    // 1. 先尝试从localStorage获取
    let history = JSON.parse(localStorage.getItem('courseHistory') || '[]');
    let course = history.find(c => c.courseId === courseId);

    // 2. 如果localStorage没有，或只有摘要信息（缺少完整课程数据），尝试从数据库API获取
    const hasFullData = course && (course.slides || course.slides_v2 || course.outlines || course.agent_team);
    if (!hasFullData) {
        try {
            const resp = await fetch(`/api/v2/classroom/${courseId}`);
            if (resp.ok) {
                const data = await resp.json();
                if (data.success && data.record && data.record.full_data) {
                    course = JSON.parse(data.record.full_data);
                }
            }
        } catch (e) {
            console.warn('从数据库获取课堂详情失败:', e);
        }
    }

    if (course) {
        // 如果是从数据库获取的完整数据，同步到localStorage（保持兼容性）
        if (!history.find(c => c.courseId === courseId)) {
            history.unshift(course);
            localStorage.setItem('courseHistory', JSON.stringify(history.slice(0, 20)));
        }
        sessionStorage.setItem('classroomData', JSON.stringify(course));
        window.location.href = 'classroom.html';
    } else {
        alert('未找到该课程');
    }
}

// 编辑课程
let editingCourseId = null;

function showEditModal(courseId) {
    editingCourseId = courseId;
    const history = JSON.parse(localStorage.getItem('courseHistory') || '[]');
    const course = history.find(c => c.courseId === courseId);
    if (!course) return;

    document.getElementById('edit-course-input').value = course.title;
    document.getElementById('edit-course-modal').classList.add('active');
    document.getElementById('edit-course-input').focus();
}

function hideEditModal() {
    document.getElementById('edit-course-modal').classList.remove('active');
    editingCourseId = null;
}

async function confirmEdit() {
    if (!editingCourseId) return;
    const newTitle = document.getElementById('edit-course-input').value.trim();
    if (!newTitle) return;

    let history = JSON.parse(localStorage.getItem('courseHistory') || '[]');
    const courseIndex = history.findIndex(c => c.courseId === editingCourseId);
    if (courseIndex >= 0) {
        history[courseIndex].title = newTitle;
        localStorage.setItem('courseHistory', JSON.stringify(history));

        // 如果用户已登录，同步更新数据库
        const currentUser = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
        if (currentUser && currentUser.id && currentUser.id !== 'anonymous') {
            try {
                const record = history[courseIndex];
                await fetch(`/api/v2/classroom/${editingCourseId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: newTitle })
                });
            } catch (e) {
                console.warn('更新数据库失败:', e);
            }
        }
    }

    hideEditModal();
    loadRecentCourses();
}

// 删除课程
let deletingCourseId = null;

function showDeleteModal(courseId) {
    deletingCourseId = courseId;
    document.getElementById('delete-course-modal').classList.add('active');
}

function hideDeleteModal() {
    document.getElementById('delete-course-modal').classList.remove('active');
    deletingCourseId = null;
}

async function confirmDelete() {
    if (!deletingCourseId) return;

    let history = JSON.parse(localStorage.getItem('courseHistory') || '[]');
    history = history.filter(c => c.courseId !== deletingCourseId);
    localStorage.setItem('courseHistory', JSON.stringify(history));

    // 如果用户已登录，同时删除数据库记录
    const currentUser = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (currentUser && currentUser.id && currentUser.id !== 'anonymous') {
        try {
            await fetch(`/api/v2/classroom/${deletingCourseId}`, {
                method: 'DELETE'
            });
        } catch (e) {
            console.warn('删除数据库记录失败:', e);
        }
    }

    hideDeleteModal();
    loadRecentCourses();
}

// 初始化弹窗事件
document.addEventListener('DOMContentLoaded', function() {
    // 编辑弹窗事件
    document.getElementById('edit-modal-close')?.addEventListener('click', hideEditModal);
    document.getElementById('edit-cancel-btn')?.addEventListener('click', hideEditModal);
    document.getElementById('edit-confirm-btn')?.addEventListener('click', confirmEdit);
    document.getElementById('edit-modal-backdrop')?.addEventListener('click', hideEditModal);
    document.getElementById('edit-course-input')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') confirmEdit();
        if (e.key === 'Escape') hideEditModal();
    });

    // 删除弹窗事件
    document.getElementById('delete-modal-close')?.addEventListener('click', hideDeleteModal);
    document.getElementById('delete-cancel-btn')?.addEventListener('click', hideDeleteModal);
    document.getElementById('delete-confirm-btn')?.addEventListener('click', confirmDelete);
    document.getElementById('delete-modal-backdrop')?.addEventListener('click', hideDeleteModal);
});

// 进入课堂按钮点击处理
document.addEventListener('DOMContentLoaded', function() {
    // 原有首页的进入课堂按钮
    const enterClassroomBtn = document.getElementById('enter-classroom-btn');
    if (enterClassroomBtn) {
        enterClassroomBtn.addEventListener('click', function() {
            const requirement = document.getElementById('course-requirement')?.value.trim();
            if (!requirement) {
                alert('请输入课程主题');
                return;
            }
            startCourseGeneration(requirement);
        });
    }

    // OpenMAIC覆盖层的进入课堂按钮
    const openmaicEnterBtn = document.getElementById('openmaic-enter-btn');
    if (openmaicEnterBtn) {
        openmaicEnterBtn.addEventListener('click', function() {
            const input = document.getElementById('openmaic-course-input');
            const requirement = input?.value.trim();
            if (!requirement) {
                alert('请输入课程主题');
                return;
            }
            startCourseGeneration(requirement);
        });
    }

    // OpenMAIC返回聊天按钮
    const backCourseBtn = document.getElementById('openmaic-back-course-btn');
    if (backCourseBtn) {
        backCourseBtn.addEventListener('click', function() {
            switchTab('chat');
        });
    }

    // OpenMAIC设置按钮 - 跳转到设置页面
    const settingsBtn = document.getElementById('openmaic-settings-btn');
    if (settingsBtn) {
        settingsBtn.addEventListener('click', function() {
            window.location.href = 'settings.html';
        });
    }

    // OpenMAIC功能开关按钮
    const pillToggles = document.querySelectorAll('.openmaic-pill-toggle');
    pillToggles.forEach(pill => {
        pill.addEventListener('click', function() {
            this.classList.toggle('active');
        });
    });

    // OpenMAIC最近课堂折叠
    const recentToggle = document.getElementById('openmaic-recent-toggle');
    const recentContent = document.getElementById('openmaic-recent-content');

    if (recentToggle && recentContent) {
        recentToggle.addEventListener('click', function() {
            this.classList.toggle('collapsed');
            recentContent.classList.toggle('collapsed');
        });
    }

    // OpenMAIC媒体设置弹窗 - Portal弹出避免被遮挡
    const mediaBtn = document.getElementById('openmaic-media-btn');
    const mediaPopup = document.getElementById('openmaic-media-popup');
    const mediaClose = document.getElementById('openmaic-media-close');
    const imageToggle = document.getElementById('openmaic-image-toggle');
    const videoToggle = document.getElementById('openmaic-video-toggle');
    const mediaBadge = document.getElementById('media-badge');
    let mediaPopupParent = null;

    if (mediaBtn && mediaPopup) {
        // 保存原始父节点
        mediaPopupParent = mediaPopup.parentNode;

        function openMediaPopup() {
            // 计算按钮位置
            const btnRect = mediaBtn.getBoundingClientRect();

            // 确保可见后移动到body
            mediaPopup.style.display = '';
            document.body.appendChild(mediaPopup);
            mediaPopup.style.position = 'fixed';
            mediaPopup.style.top = (btnRect.bottom + 8) + 'px';
            mediaPopup.style.left = Math.min(btnRect.left, window.innerWidth - 340) + 'px';
            mediaPopup.style.transform = 'translateY(-8px)';

            // 触发重排后显示
            requestAnimationFrame(() => {
                mediaPopup.classList.add('show');
            });
        }

        function closeMediaPopup() {
            mediaPopup.classList.remove('show');
            // 等待动画完成后移回原位并隐藏
            setTimeout(() => {
                mediaPopup.style.display = 'none';
                if (mediaPopupParent) {
                    mediaPopupParent.appendChild(mediaPopup);
                    mediaPopup.style.position = '';
                    mediaPopup.style.top = '';
                    mediaPopup.style.left = '';
                    mediaPopup.style.transform = '';
                }
            }, 250);
        }

        mediaBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            if (mediaPopup.classList.contains('show')) {
                closeMediaPopup();
            } else {
                // 关闭其他可能的弹窗
                mediaPopup.classList.remove('show');
                openMediaPopup();
            }
        });

        mediaClose?.addEventListener('click', function() {
            closeMediaPopup();
        });

        // 更新媒体徽章
        function updateMediaBadge() {
            let count = 0;
            if (imageToggle?.checked) count++;
            if (videoToggle?.checked) count++;
            if (mediaBadge) {
                if (count > 0) {
                    mediaBadge.textContent = count;
                    mediaBadge.style.display = 'inline-flex';
                } else {
                    mediaBadge.style.display = 'none';
                }
            }
        }

        imageToggle?.addEventListener('change', updateMediaBadge);
        videoToggle?.addEventListener('change', updateMediaBadge);

        // 初始化时更新徽章状态
        updateMediaBadge();

        // 整行点击切换开关
        let mediaToggleDebounce = null;
        function handleMediaOptionClick(e) {
            // 点击来自 toggle 开关内部（label/input/slider），由原生行为处理
            if (e.target.closest('.toggle-switch')) return;

            if (mediaToggleDebounce) return;
            mediaToggleDebounce = setTimeout(function () { mediaToggleDebounce = null; }, 200);

            var checkbox = this.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.checked = !checkbox.checked;
                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }

        var mediaOptionRows = mediaPopup.querySelectorAll('.media-option');
        for (var m = 0; m < mediaOptionRows.length; m++) {
            mediaOptionRows[m].addEventListener('click', handleMediaOptionClick);
        }

        // 点击外部关闭弹窗
        document.addEventListener('click', function(e) {
            if (mediaPopup.classList.contains('show') && !mediaPopup.contains(e.target) && e.target !== mediaBtn) {
                closeMediaPopup();
            }
        });

        // 窗口滚动和resize时关闭弹窗
        window.addEventListener('scroll', function() {
            if (mediaPopup.classList.contains('show')) {
                closeMediaPopup();
            }
        }, { passive: true });

        window.addEventListener('resize', function() {
            if (mediaPopup.classList.contains('show')) {
                closeMediaPopup();
            }
        });
    }

    // OpenMAIC附件上传
    const attachBtn = document.getElementById('openmaic-attach-btn');
    const fileInput = document.getElementById('openmaic-file-input');
    const attachmentsContainer = document.getElementById('openmaic-attachments');

    // 存储已上传的PDF文件
    window.uploadedPdfFiles = [];

    if (attachBtn && fileInput) {
        attachBtn.addEventListener('click', function() {
            fileInput.click();
        });

        fileInput.addEventListener('change', function() {
            const files = Array.from(this.files || []);
            files.forEach(file => {
                addAttachmentItem(file);
                // 如果是PDF，存储到列表
                if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
                    window.uploadedPdfFiles.push(file);
                }
            });
            this.value = ''; // 清空以便重复选择
        });
    }

    // 添加附件项
    function addAttachmentItem(file) {
        if (!attachmentsContainer) return;

        const isPdf = file.type === 'application/pdf' || file.name.endsWith('.pdf');
        const item = document.createElement('div');
        item.className = 'attachment-item' + (isPdf ? ' pdf-file' : '');
        item.innerHTML = `
            <i data-lucide="${isPdf ? 'file-text' : 'file'}" class="w-3.5 h-3.5"></i>
            <span>${file.name.length > 20 ? file.name.substring(0, 17) + '...' : file.name}</span>
            <button class="attachment-remove">
                <i data-lucide="x" class="w-3 h-3"></i>
            </button>
            <div class="attachment-progress" style="display:none;">
                <div class="attachment-progress-bar"></div>
            </div>
        `;

        // 移除按钮
        item.querySelector('.attachment-remove')?.addEventListener('click', function() {
            item.style.animation = 'attachment-in 0.2s ease-out reverse';
            setTimeout(() => {
                item.remove();
                // 从列表中移除
                const idx = window.uploadedPdfFiles.indexOf(file);
                if (idx > -1) window.uploadedPdfFiles.splice(idx, 1);
            }, 200);
        });

        attachmentsContainer.appendChild(item);
        lucide.createIcons();
    }

    // 显示上传进度
    window.showPdfUploadProgress = function(percent) {
        const items = document.querySelectorAll('.attachment-item.pdf-file');
        items.forEach(item => {
            const progress = item.querySelector('.attachment-progress');
            if (progress) {
                progress.style.display = 'block';
                const bar = progress.querySelector('.attachment-progress-bar');
                if (bar) bar.style.width = percent + '%';
            }
        });
    };

    // 隐藏上传进度
    window.hidePdfUploadProgress = function() {
        const items = document.querySelectorAll('.attachment-item.pdf-file');
        items.forEach(item => {
            const progress = item.querySelector('.attachment-progress');
            if (progress) progress.style.display = 'none';
        });
    };

    // OpenMAIC语音输入（使用 Whisper 本地识别）
    const voiceBtn = document.getElementById('openmaic-voice-btn');
    let openmaicIsRecording = false;
    let openmaicWhisperReady = false;

    // 初始化 Whisper
    window.WhisperVoice?.init(
        () => { openmaicWhisperReady = true; console.log('[Voice] Whisper ready'); },
        (err) => { console.error('[Voice] Whisper init failed:', err); openmaicWhisperReady = false; }
    );

    voiceBtn?.addEventListener('click', function() {
        if (!window.WhisperVoice) {
            console.error('[Voice] WhisperVoice not loaded');
            return;
        }

        if (openmaicIsRecording) {
            // 停止
            window.WhisperVoice.stop();
            openmaicIsRecording = false;
            voiceBtn.classList.remove('recording');
            const voiceBars = voiceBtn.querySelector('.voice-bars');
            const micIcon = voiceBtn.querySelector('.voice-icon');
            if (voiceBars) voiceBars.style.display = 'none';
            if (micIcon) micIcon.style.display = 'inline';
        } else {
            // 开始录音
            openmaicIsRecording = true;
            voiceBtn.classList.add('recording');
            const voiceBars = voiceBtn.querySelector('.voice-bars');
            const micIcon = voiceBtn.querySelector('.voice-icon');
            if (voiceBars) voiceBars.style.display = 'flex';
            if (micIcon) micIcon.style.display = 'none';

            const textarea = document.getElementById('openmaic-course-input');

            window.WhisperVoice.start({
                onTranscription: (text) => {
                    if (textarea && text) {
                        textarea.value += text;
                    }
                },
                onError: (err) => {
                    console.error('[Voice] OpenMAIC Whisper error:', err);
                    openmaicIsRecording = false;
                    voiceBtn.classList.remove('recording');
                    const vb = voiceBtn.querySelector('.voice-bars');
                    const mi = voiceBtn.querySelector('.voice-icon');
                    if (vb) vb.style.display = 'none';
                    if (mi) mi.style.display = 'inline';
                },
                onStart: () => { console.log('[Voice] OpenMAIC recording start'); },
                onEnd: () => {
                    console.log('[Voice] OpenMAIC recording end');
                    openmaicIsRecording = false;
                    voiceBtn.classList.remove('recording');
                    const vb = voiceBtn.querySelector('.voice-bars');
                    const mi = voiceBtn.querySelector('.voice-icon');
                    if (vb) vb.style.display = 'none';
                    if (mi) mi.style.display = 'inline';
                }
            });
        }
    });

    // notion-input 语音输入（使用 Whisper 本地识别）
    const chatVoiceBtn = document.getElementById('chat-voice-btn');
    let chatIsRecording = false;
    let chatWhisperReady = false;

    // 初始化 Whisper（已初始化则直接用）
    if (window.WhisperVoice?.isReady()) {
        chatWhisperReady = true;
    } else {
        window.WhisperVoice?.init(
            () => { chatWhisperReady = true; },
            () => { chatWhisperReady = false; }
        );
    }

    chatVoiceBtn?.addEventListener('click', function() {
        if (!window.WhisperVoice) {
            console.error('[Voice] WhisperVoice not loaded');
            return;
        }

        if (chatIsRecording) {
            window.WhisperVoice.stop();
            chatIsRecording = false;
            chatVoiceBtn.classList.remove('recording');
            chatVoiceBtn.style.background = '';
            chatVoiceBtn.style.color = '';
        } else {
            chatIsRecording = true;
            chatVoiceBtn.classList.add('recording');
            chatVoiceBtn.style.background = 'var(--danger)';
            chatVoiceBtn.style.color = 'white';

            const notionInput = document.getElementById('notion-input');

            window.WhisperVoice.start({
                onTranscription: (text) => {
                    if (notionInput && text) {
                        notionInput.textContent += text;
                    }
                },
                onError: (err) => {
                    console.error('[Voice] Chat Whisper error:', err);
                    chatIsRecording = false;
                    chatVoiceBtn.classList.remove('recording');
                    chatVoiceBtn.style.background = '';
                    chatVoiceBtn.style.color = '';
                },
                onStart: () => { console.log('[Voice] Chat recording start'); },
                onEnd: () => {
                    console.log('[Voice] Chat recording end');
                    chatIsRecording = false;
                    chatVoiceBtn.classList.remove('recording');
                    chatVoiceBtn.style.background = '';
                    chatVoiceBtn.style.color = '';
                }
            });
        }
    });

    // OpenMAIC导入按钮
    const importBtn = document.getElementById('openmaic-import-btn');
    if (importBtn) {
        importBtn.addEventListener('click', function() {
            // 触发文件上传
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = '.json';
            fileInput.onchange = function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(event) {
                        try {
                            const courseData = JSON.parse(event.target.result);
                            // 保存到历史
                            let history = JSON.parse(localStorage.getItem('courseHistory') || '[]');
                            history.unshift(courseData);
                            localStorage.setItem('courseHistory', JSON.stringify(history));
                            loadRecentCourses();
                            alert('导入成功!');
                        } catch (err) {
                            alert('导入失败: 无效的文件格式');
                        }
                    };
                    reader.readAsText(file);
                }
            };
            fileInput.click();
        });
    }

    // 课程模式Pill按钮切换
    const coursePills = document.querySelectorAll('.course-pill');
    coursePills.forEach(pill => {
        pill.addEventListener('click', function() {
            this.classList.toggle('active');
        });
    });
});

// 开始课程生成
async function startCourseGeneration(requirement) {
    // 检查用户是否已登录（有有效ID）
    const storedUser = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!storedUser || !storedUser.id || storedUser.id === 'anonymous') {
        alert('请先登录后再生成课程');
        // 触发登录弹窗（如果有login-modal的话）
        const loginModal = document.getElementById('login-modal') || document.querySelector('.login-modal');
        if (loginModal) loginModal.style.display = 'flex';
        return;
    }

    // 获取媒体设置
    const imageToggle = document.getElementById('openmaic-image-toggle');
    const videoToggle = document.getElementById('openmaic-video-toggle');
    const webSearchPill = document.getElementById('openmaic-websearch-pill');
    const interactivePill = document.getElementById('openmaic-interactive-pill');
    const agentMode = document.getElementById('openmaic-agent-select')?.value || 'preset';
    const voiceId = document.getElementById('openmaic-voice-select')?.value || 'female-shaonv';
    const teacherId = document.getElementById('openmaic-teacher-select')?.value || '';

    let finalTeacher = null;
    if (agentMode === 'auto') {
        // 自动模式：根据课程内容匹配老师
        const matchResult = typeof matchTeacher === 'function' ? matchTeacher(requirement) : null;
        if (matchResult) {
            finalTeacher = matchResult.teacher;
        }
    } else {
        // 手动模式：使用用户选择的老師
        finalTeacher = typeof getTeacherById === 'function' ? getTeacherById(teacherId) : null;
    }

    // 处理PDF文件上传
    let pdfText = '';
    const pdfFiles = window.uploadedPdfFiles || [];
    if (pdfFiles.length > 0) {
        const enterBtn = document.getElementById('openmaic-enter-btn');
        const originalText = enterBtn?.querySelector('span')?.textContent;
        if (enterBtn) {
            enterBtn.disabled = true;
            if (enterBtn.querySelector('span')) enterBtn.querySelector('span').textContent = '解析文档中...';
        }

        try {
            for (let i = 0; i < pdfFiles.length; i++) {
                const file = pdfFiles[i];
                window.showPdfUploadProgress(Math.round((i / pdfFiles.length) * 50));

                const formData = new FormData();
                formData.append('file', file);

                // 由于我们使用base64方式，先读取文件
                const arrayBuffer = await file.arrayBuffer();
                const base64 = btoa(new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), ''));

                const resp = await fetch('/api/v2/course/extract-pdf-text', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        pdf_content: base64,
                        filename: file.name
                    })
                });

                if (resp.ok) {
                    const result = await resp.json();
                    if (result.success && result.text) {
                        pdfText += `\n\n=== ${file.name} ===\n\n` + result.text;
                    }
                }

                window.showPdfUploadProgress(Math.round(50 + (i / pdfFiles.length) * 50));
            }
        } catch (e) {
            console.warn('[PDF] Upload failed:', e);
        }

        if (enterBtn) {
            enterBtn.disabled = false;
            if (enterBtn.querySelector('span')) enterBtn.querySelector('span').textContent = originalText || '进入课堂';
        }
        window.hidePdfUploadProgress();
    }

    // 读取PDF解析开关状态
    const pdfPill = document.getElementById('openmaic-pdf-pill');
    const enablePdfUpload = pdfPill?.classList.contains('active') ?? false;

    // 保存生成会话数据（PDF文本独立字段，不再拼接进requirement）
    const sessionData = {
        requirements: {
            requirement: requirement,
            original_requirement: requirement,
            enable_image: imageToggle?.checked || false,
            enable_tts: true,    // 默认开启语音
            enable_video: videoToggle?.checked || false,
            enable_web_search: webSearchPill?.classList.contains('active') ?? true,
            interactive_mode: interactivePill?.classList.contains('active') ?? false,
            enable_pdf_upload: enablePdfUpload,
            pdf_text: pdfText,
            voice_id: voiceId,
            agent_mode: agentMode,
            teacher_id: finalTeacher?.id || '',
            teacher_name: finalTeacher?.name || '',
            teacher_profession: finalTeacher?.profession || '',
            teacher_personality: finalTeacher?.personality || '',
            teacher_teaching_style: finalTeacher?.teachingStyle || '',
            teacher_icon: finalTeacher?.icon || '',
            teacher_system_prompt: finalTeacher?.systemPrompt || '',
            teacher_greeting: finalTeacher?.greeting || '',
            pdf_files: pdfFiles.map(f => f.name),
        },
        student_id: storedUser.id,
        timestamp: Date.now()
    };
    sessionStorage.setItem('generationSession', JSON.stringify(sessionData));

    // 跳转到生成预览页面
    window.location.href = '/generation-preview.html';
}

// 保存课程到历史
function saveCourseToHistory(courseData) {
    let history = JSON.parse(localStorage.getItem('courseHistory') || '[]');
    // 检查是否已存在
    const existingIndex = history.findIndex(c => c.courseId === courseData.courseId);
    if (existingIndex >= 0) {
        history.splice(existingIndex, 1);
    }
    // 添加到开头
    history.unshift({
        ...courseData,
        createdAt: Date.now()
    });
    // 只保留最近20条
    if (history.length > 20) {
        history = history.slice(0, 20);
    }
    localStorage.setItem('courseHistory', JSON.stringify(history));
}

function switchOutputTab(tab) {
    document.querySelectorAll('.output-tab').forEach(btn => {
        const isActive = btn.dataset.outputTab === tab;
        btn.classList.toggle('active', isActive);
    });
    const runOutputPanel = document.getElementById('run-output-panel');
    const gradeOutputPanel = document.getElementById('grade-output-panel');
    if (runOutputPanel) runOutputPanel.classList.toggle('hidden', tab !== 'run');
    if (gradeOutputPanel) gradeOutputPanel.classList.toggle('hidden', tab !== 'grade');
}

function initCodeEditor() {
    const textarea = document.getElementById('code-editor');
    if (!textarea) return;
    const savedLang = localStorage.getItem('starlearn_preferred_lang') || 'python';
    const config = LANG_CONFIG[savedLang] || LANG_CONFIG.python;
    const langSelect = document.getElementById('lang-select');
    if (langSelect) langSelect.value = savedLang;
    codeEditor = CodeMirror.fromTextArea(textarea, {
        mode: config.mode,
        theme: 'dracula',
        lineNumbers: true,
        matchBrackets: true,
        autoCloseBrackets: true,
        indentUnit: 4,
        tabSize: 4,
        lineWrapping: true,
        extraKeys: {
            "Ctrl-Enter": function() { runCode(); },
            "Cmd-Enter": function() { runCode(); }
        }
    });
    codeEditor.setValue(config.template);
    codeEditor.refresh();
}

const LANG_CONFIG = {
    python: { mode: 'python', template: 'def hello():\n    print("Hello, Star-Learn!")\n\nhello()' },
    java: { mode: 'text/x-java', template: 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, Star-Learn!");\n    }\n}' },
    c: { mode: 'text/x-csrc', template: '#include <stdio.h>\n\nint main() {\n    printf("Hello, Star-Learn!\\n");\n    return 0;\n}' },
    cpp: { mode: 'text/x-c++src', template: '#include <iostream>\n\nusing namespace std;\n\nint main() {\n    cout << "Hello, Star-Learn!" << endl;\n    return 0;\n}' },
    javascript: { mode: 'javascript', template: 'function hello() {\n    console.log("Hello, Star-Learn!");\n}\n\nhello();' },
    go: { mode: 'go', template: 'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Hello, Star-Learn!")\n}' },
    sql: { mode: 'text/x-sql', template: 'SELECT * FROM students\nWHERE grade = \'A\'\nORDER BY name;' },
    scala: { mode: 'text/x-scala', template: 'object Main extends App {\n    println("Hello, Star-Learn!")\n}' },
    rust: { mode: 'rust', template: 'fn main() {\n    println!("Hello, Star-Learn!");\n}' }
};

function changeLanguage() {
    if (!codeEditor) return;
    const langSelect = document.getElementById('lang-select');
    if (!langSelect) return;
    const lang = langSelect.value;
    const config = LANG_CONFIG[lang] || LANG_CONFIG.python;
    codeEditor.setOption('mode', config.mode);
    codeEditor.setValue(config.template);
    codeEditor.refresh();
    localStorage.setItem('starlearn_preferred_lang', lang);
}

function switchToCLanguage() {
    const langSelect = document.getElementById('lang-select');
    if (langSelect) langSelect.value = 'c';
    changeLanguage();
    switchTab('code');
}

function renderProfile() {
    const container = document.getElementById('profile-container');
    if (!container) return;

    normalizeProfileDisplayFields(profile);

    // 获取语言显示字符串
    const langStr = profile.languages && profile.languages.length > 0
        ? profile.languages.map(l => {
            const langNames = { python: 'Python', java: 'Java', c: 'C', cpp: 'C++', javascript: 'JS', go: 'Go', sql: 'SQL', scala: 'Scala', rust: 'Rust' };
            return langNames[l] || l;
        }).join('、')
        : 'Python';

    const config = {
        '学习方向': { icon: 'compass', val: profile.learningDirection || '大数据技术', color: 'text-blue-700 bg-blue-100' },
        '编程语言': { icon: 'code-2', val: langStr, color: 'text-violet-700 bg-violet-100' },
        '知识基础': { icon: 'book-open', val: profile.knowledgeBase, color: 'text-emerald-700 bg-emerald-100' },
        '编程能力': { icon: 'terminal', val: profile.codeSkill, color: 'text-purple-700 bg-purple-100' },
        '学习目标': { icon: 'target', val: profile.learningGoal, color: 'text-cyan-700 bg-cyan-100' },
        '认知风格': { icon: 'brain-circuit', val: profile.cognitiveStyle, color: 'text-orange-700 bg-orange-100' },
        '知识短板': { icon: 'alert-circle', val: profile.weakness, color: 'text-red-700 bg-red-100' },
        '专注程度': { icon: 'focus', val: (profile.focusLevel === 'high' || profile.focusLevel === '高专注') ? '高专注' : ((profile.focusLevel === 'low' || profile.focusLevel === '需要引导') ? '需引导' : '中等'), color: 'text-indigo-700 bg-indigo-100' }
    };
    container.innerHTML = Object.entries(config).map(([label, data]) => `
        <div class="profile-glass-tile flex flex-col p-2.5 rounded-2xl border shadow-sm transition-all duration-300 ease-out hover:-translate-y-0.5">
            <span class="text-xs text-gray-500 mb-1 flex items-center gap-1 font-semibold"><i data-lucide="${data.icon}" class="w-3.5 h-3.5"></i> ${label}</span>
            <span class="text-xs font-bold p-1 rounded-md ${data.color} w-fit">${data.val}</span>
        </div>
    `).join('');
    if (window.lucide) lucide.createIcons();
}

function renderRadarChart() {
    const canvas = document.getElementById('radar-chart');
    const loadingEl = document.getElementById('radar-loading');
    if (!canvas) return;
    try {
        const wrap = canvas.closest('.glass-radar-wrap');
        const wrapW = wrap ? wrap.clientWidth : 240;
        const size = Math.min(wrapW, 240);
        const dpr = window.devicePixelRatio || 1;
        canvas.width = size * dpr;
        canvas.height = size * dpr;
        canvas.style.width = size + 'px';
        canvas.style.height = size + 'px';

        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error('Canvas 2D context unavailable');
        ctx.scale(dpr, dpr);

        const W = size, H = size;
        const cx = W / 2, cy = H * 0.52;
        const R = Math.min(W, H) * 0.3;
        ctx.clearRect(0, 0, W, H);

        const style = getComputedStyle(document.documentElement);
        const radarStroke = style.getPropertyValue('--radar-stroke').trim() || '#3b82f6';
        const radarFill = style.getPropertyValue('--radar-fill').trim() || 'rgba(59,130,246,0.2)';
        const gridColor = style.getPropertyValue('--border-glass').trim() || 'rgba(255,255,255,0.12)';
        const labelColor = style.getPropertyValue('--text-secondary').trim() || 'rgba(255,255,255,0.55)';

        const dims = ['方向', '基础', '编程', '认知', '短板', '专注'];
        const values = [
            mapProfileToScore(profile.learningDirection || '大数据技术'),
            mapProfileToScore(profile.knowledgeBase),
            mapProfileToScore(profile.codeSkill),
            mapProfileToScore(profile.cognitiveStyle),
            mapProfileToScore(profile.weakness, true),
            mapProfileToScore(profile.focusLevel)
        ];
        const n = dims.length;

        for (let level = 1; level <= 4; level++) {
            ctx.beginPath();
            for (let i = 0; i < n; i++) {
                const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
                const r = R * level / 4;
                const x = cx + r * Math.cos(angle);
                const y = cy + r * Math.sin(angle);
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.closePath();
            ctx.strokeStyle = gridColor;
            ctx.lineWidth = 1;
            ctx.stroke();
        }

        for (let i = 0; i < n; i++) {
            const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + R * Math.cos(angle), cy + R * Math.sin(angle));
            ctx.strokeStyle = gridColor;
            ctx.lineWidth = 1;
            ctx.stroke();

            const labelOffset = R + 22;
            const lx = cx + labelOffset * Math.cos(angle);
            const ly = cy + labelOffset * Math.sin(angle);
            ctx.fillStyle = labelColor;
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(dims[i], lx, ly);
        }

        ctx.beginPath();
        for (let i = 0; i < n; i++) {
            const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
            const r = R * values[i] / 100;
            const x = cx + r * Math.cos(angle);
            const y = cy + r * Math.sin(angle);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.fillStyle = radarFill;
        ctx.fill();
        ctx.strokeStyle = radarStroke;
        ctx.lineWidth = 2;
        ctx.stroke();

        for (let i = 0; i < n; i++) {
            const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
            const r = R * values[i] / 100;
            ctx.beginPath();
            ctx.arc(cx + r * Math.cos(angle), cy + r * Math.sin(angle), 3, 0, Math.PI * 2);
            ctx.fillStyle = radarStroke;
            ctx.fill();
        }

        canvas.style.display = 'block';
        if (loadingEl) loadingEl.style.display = 'none';
    } catch (err) {
        console.warn('[RadarChart] Render failed:', err);
        canvas.style.display = 'none';
        if (loadingEl) {
            loadingEl.style.display = 'flex';
            loadingEl.innerHTML = '<div class="radar-error"><span>雷达图加载失败</span><button class="radar-error-retry" onclick="renderRadarChart()">重试</button></div>';
        }
    }
}

function mapProfileToScore(val, invert) {
    const map = {
        // 知识基础
        '零基础入门': 15, '基础入门': 30, '进阶学习': 65, '深入掌握': 90,
        '零基础': 10, '入门': 25, '基础': 35, '普通学生': 40,
        // 编程能力
        '编程新手': 15, '基础掌握': 35, '熟练编程': 65, '编程高手': 90,
        'Python基础': 35, 'Python进阶': 65, 'C语言基础': 30, 'C语言进阶': 60, 'C++基础': 30, 'C++进阶': 60,
        // 学习目标
        '应对考试': 45, '职业发展': 65, '项目实战': 70, '兴趣探索': 50, '竞赛备战': 80, '科研学术': 75,
        '期末考试': 50, '就业准备': 70, '科研入门': 80, '竞赛': 90,
        // 认知风格
        '视觉型': 70, '文字型': 50, '实践型': 80,
        'visual': 70, 'textual': 50, 'pragmatic': 80, '待测试': 30,
        // 专注度
        '高专注': 85, '中等专注': 55, '需要引导': 25, '需引导': 25,
        'high': 85, 'medium': 55, 'low': 20,
        // 学习方向
        '大数据技术': 60, '人工智能': 70, '前端开发': 55, '后端开发': 60, '算法数据结构': 75, '数据库技术': 55,
        // 知识短板
        '暂无': 70, '排序算法': 30, '分布式计算': 25, '流处理': 20,
        'C语言指针': 20, 'C语言内存管理': 15, 'C语言基础语法': 25,
        // 其他
        '中等': 50, '进阶': 70, '熟练': 80, '精通': 95, '优秀': 90
    };
    let score = map[val] || 40;
    if (invert) score = 100 - score;
    return Math.max(10, Math.min(95, score));
}

function renderSparkline(data, width, height) {
    if (!data || data.length < 2) return '';
    const max = Math.max(...data, 1);
    const min = Math.min(...data, 0);
    const range = max - min || 1;
    const points = data.map((v, i) => {
        const x = (i / (data.length - 1)) * width;
        const y = height - ((v - min) / range) * height;
        return `${x},${y}`;
    }).join(' ');
    return `<svg width="${width}" height="${height}" class="eval-sparkline">
        <polyline points="${points}" fill="none" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/>
    </svg>`;
}

function renderEvaluation() {
    const evalContainer = document.getElementById('eval-container');
    if (!evalContainer) return;
    const diffColors = { basic: 'eval-diff-basic', medium: 'eval-diff-medium', advanced: 'eval-diff-advanced' };
    const diffLabels = { basic: '基础', medium: '中等', advanced: '进阶' };

    const focusMin = Math.floor((evaluation.focusTimeToday || 0) / 60);
    const sparkline = renderSparkline(evaluation.interactionHistory || [], 48, 20);

    evalContainer.innerHTML = `
        <div class="eval-metric glass-eval-card flex items-center gap-2 p-2.5 rounded-xl border shadow-sm">
            <i data-lucide="message-square" class="w-3.5 h-3.5 shrink-0" style="color: var(--accent);"></i>
            <span class="text-xs eval-label-text">交互次数</span>
            <span class="text-xs font-bold ml-auto eval-value-text">${evaluation.interactionCount}</span>
        </div>
        <div class="eval-metric glass-eval-card flex items-center gap-2 p-2.5 rounded-xl border shadow-sm">
            <i data-lucide="check-circle" class="w-3.5 h-3.5 shrink-0" style="color: var(--primary-light);"></i>
            <span class="text-xs eval-label-text">启发通关率</span>
            <span class="text-xs font-bold ml-auto eval-value-text eval-value-purple">${(evaluation.socraticPassRate * 100).toFixed(0)}%</span>
        </div>
        <div class="eval-metric glass-eval-card flex items-center gap-2 p-2.5 rounded-xl border shadow-sm">
            <i data-lucide="code" class="w-3.5 h-3.5 shrink-0" style="color: var(--success);"></i>
            <span class="text-xs eval-label-text">代码实操</span>
            <span class="text-xs font-bold ml-auto eval-value-text eval-value-green">${evaluation.codePracticeTime}min</span>
        </div>
        <div class="eval-metric glass-eval-card flex items-center gap-2 p-2.5 rounded-xl border shadow-sm">
            <i data-lucide="gauge" class="w-3.5 h-3.5 shrink-0" style="color: var(--warning);"></i>
            <span class="text-xs eval-label-text">下一阶段难度</span>
            <span class="text-xs font-bold px-1.5 rounded ml-auto ${diffColors[evaluation.difficultyLevel] || diffColors.medium}">${diffLabels[evaluation.difficultyLevel] || '中等'}</span>
        </div>
        <div class="eval-metric glass-eval-card flex items-center gap-2 p-2.5 rounded-xl border shadow-sm">
            <i data-lucide="zap" class="w-3.5 h-3.5 shrink-0" style="color: var(--warning);"></i>
            <span class="text-xs eval-label-text">今日专注</span>
            <span class="text-xs font-bold ml-auto eval-value-text">${focusMin}min</span>
        </div>
        <div class="eval-metric glass-eval-card flex items-center gap-2 p-2.5 rounded-xl border shadow-sm">
            <i data-lucide="layers" class="w-3.5 h-3.5 shrink-0" style="color: var(--primary-light);"></i>
            <span class="text-xs eval-label-text">知识胶囊</span>
            <span class="text-xs font-bold ml-auto eval-value-text">${evaluation.flashcardsStudied || 0}</span>
        </div>
        <div class="eval-metric glass-eval-card flex items-center gap-2 p-2.5 rounded-xl border shadow-sm">
            <i data-lucide="flame" class="w-3.5 h-3.5 shrink-0" style="color: var(--success);"></i>
            <span class="text-xs eval-label-text">连续学习</span>
            <span class="text-xs font-bold ml-auto eval-value-text eval-value-green">${evaluation.streakDays || 0}天</span>
        </div>
        <div class="eval-metric glass-eval-card flex items-center gap-2 p-2.5 rounded-xl border shadow-sm">
            <i data-lucide="trending-up" class="w-3.5 h-3.5 shrink-0" style="color: var(--accent);"></i>
            <span class="text-xs eval-label-text">交互趋势</span>
            <span class="ml-auto">${sparkline}</span>
        </div>
    `;
    if (window.lucide) lucide.createIcons();
}

function renderPath() {
    const container = document.getElementById('path-container');
    if (container) {
        container.innerHTML = currentPath.map((node) => {
            if(node.status === 'current') {
                const style = `background: var(--accent-bg); border-color: var(--accent-border);`;
                return `
                <div class="path-glass-node relative pl-6 mb-2 p-2.5 rounded-xl -ml-2 border transition-transform duration-300" style="${style}">
                    <div class="absolute left-[-1px] top-3 w-4 h-4 rounded-full border-2 z-10 animate-pulse" style="background: var(--accent); border-color: var(--surface-glass);"></div>
                    <p class="text-sm path-node-current-text">${node.topic}</p>
                </div>`;
            }
            let dotClass = 'path-dot-locked';
            let textClass = 'path-node-locked-text';
            if(node.status === 'completed') {
                dotClass = 'path-dot-completed';
                textClass = 'path-node-completed-text';
            }
            return `
            <div class="path-glass-node relative pl-6 mb-2 transition-opacity duration-300">
                <div class="absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 z-10 shadow-sm ${dotClass}"></div>
                <p class="text-sm ${textClass}">${node.topic}</p>
            </div>`;
        }).join('');
    }
    renderPathTree();
}

function updateDispatchBadge(strategy) {
    const badge = document.getElementById('dispatch-badge');
    if (!badge) return;
    const configs = {
        socratic: { text: '苏格拉底诊断' },
        visual: { text: '高视觉权重' },
        pragmatic: { text: '高实践权重' },
        textual: { text: '均衡模式' }
    };
}

function setDispatchActive(isActive) {
    const badge = document.getElementById('dispatch-badge');
    if (!badge) return;
    if (isActive) {
        badge.classList.remove('dispatch-idle');
        badge.classList.add('dispatch-active');
    } else {
        badge.classList.remove('dispatch-active');
        badge.classList.add('dispatch-idle');
    }
}

function getLinkCache() {
    try {
        const raw = localStorage.getItem(LINK_CACHE_KEY);
        if (!raw) return {};
        const cache = JSON.parse(raw);
        const now = Date.now();
        const valid = {};
        for (const [key, entry] of Object.entries(cache)) {
            if (now - entry.cachedAt < LINK_CACHE_EXPIRY_MS) {
                valid[key] = entry;
            }
        }
        localStorage.setItem(LINK_CACHE_KEY, JSON.stringify(valid));
        return valid;
    } catch {
        return {};
    }
}

function setLinkCacheEntry(source, url, status) {
    try {
        const cache = getLinkCache();
        cache[source] = { url, status, cachedAt: Date.now() };
        localStorage.setItem(LINK_CACHE_KEY, JSON.stringify(cache));
    } catch {}
}

function getTextbookUrl(textbookInfo) {
    if (currentSourceLinks[textbookInfo]) {
        return currentSourceLinks[textbookInfo];
    }
    const cache = getLinkCache();
    if (cache[textbookInfo] && cache[textbookInfo].status === 'valid') {
        return cache[textbookInfo].url;
    }
    const fallbackMap = {
        '大数据处理技术': 'https://ebook.hep.com.cn',
        '大数据导论': 'http://www.ucdrs.superlib.net/',
        '实验指导书': 'https://www.zhishikoo.com/'
    };
    const match = textbookInfo.match(/《(.+?)》/);
    if (match) {
        const textbookName = match[1];
        return fallbackMap[textbookName] || 'https://zh.hkr101.ru/';
    }
    return 'https://zh.hkr101.ru/';
}

async function validateTextbookLink(url) {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        const res = await fetch(url, {
            method: 'HEAD',
            mode: 'no-cors',
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return true;
    } catch {
        return false;
    }
}

function openTextbookLink(textbookInfo) {
    // Try to get deep link for this source
    const deepLink = currentSourceLinks[textbookInfo] || getLinkCache()[textbookInfo]?.url;

    if (deepLink) {
        // Open deep link directly in new tab - takes user to exact textbook page
        window.open(deepLink, '_blank', 'noopener,noreferrer');
        showToast('正在跳转到教材对应页面...', 'info');
    } else {
        // Fallback to modal if no deep link available
        openTextbookModal(textbookInfo);
    }
}

const _textbookContentCache = new Map();

function openTextbookModal(source) {
    let modal = document.getElementById('textbook-reader-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'textbook-reader-modal';
        modal.style.cssText = `
            position: fixed; inset: 0; z-index: 280;
            display: flex; align-items: center; justify-content: center;
            background: rgba(0,0,0,0.5); backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            opacity: 0; visibility: hidden;
            transition: opacity 300ms ease, visibility 300ms ease;
        `;
        modal.innerHTML = `
            <div class="textbook-reader-panel" id="textbook-reader-panel">
                <div class="textbook-reader-toolbar">
                    <div class="textbook-reader-toolbar-left">
                        <i data-lucide="book-open" style="width:18px;height:18px;color:var(--accent);"></i>
                        <span id="textbook-reader-title">教材阅览室</span>
                    </div>
                    <div class="textbook-reader-toolbar-right">
                        <button class="textbook-toolbar-btn" onclick="textbookAdjustFont(-1)" title="缩小字体">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><path d="M4 7V4h16v3"></path><path d="M9 20h6"></path><path d="M12 4v16"></path></svg>
                        </button>
                        <button class="textbook-toolbar-btn" onclick="textbookAdjustFont(1)" title="放大字体">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><path d="M4 7V4h16v3"></path><path d="M9 20h6"></path><path d="M12 4v16"></path><line x1="17" y1="12" x2="22" y2="12"></line><line x1="19.5" y1="9.5" x2="19.5" y2="14.5"></line></svg>
                        </button>
                        <button class="textbook-toolbar-btn" onclick="textbookToggleMaximize()" title="最大化" id="textbook-maximize-btn">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><line x1="21" y1="3" x2="14" y2="10"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>
                        </button>
                        <button class="textbook-toolbar-btn" onclick="closeTextbookModal()" title="关闭">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        </button>
                    </div>
                </div>
                <div id="textbook-reader-content" class="textbook-reader-content">
                    <div style="text-align: center; padding: 40px 0; color: var(--text-tertiary);">
                        <div class="skeleton-spinner" style="margin: 0 auto 12px;"></div>
                        正在检索教材内容...
                    </div>
                </div>
            </div>
        `;
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeTextbookModal();
        });
        document.addEventListener('keydown', function textbookEscHandler(e) {
            if (e.key === 'Escape' && modal.style.visibility === 'visible') {
                closeTextbookModal();
            }
        });
        document.body.appendChild(modal);
        if (window.lucide) lucide.createIcons();
    }

    const titleEl = document.getElementById('textbook-reader-title');
    if (titleEl) titleEl.textContent = source || '教材阅览室';

    const contentEl = document.getElementById('textbook-reader-content');
    if (contentEl) {
        contentEl.style.fontSize = (window._textbookFontSize || 13) + 'px';
        contentEl.innerHTML = `<div style="text-align: center; padding: 40px 0; color: var(--text-tertiary);">
            <div class="skeleton-spinner" style="margin: 0 auto 12px; width: 28px; height: 28px; border: 2px solid var(--border-glass); border-top-color: var(--primary-light); border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
            正在检索教材内容...
        </div>`;
    }

    modal.style.opacity = '1';
    modal.style.visibility = 'visible';
    const panel = modal.querySelector('.textbook-reader-panel');
    if (panel) { panel.style.transform = 'translateY(0) scale(1)'; }

    if (_textbookContentCache.has(source)) {
        renderTextbookContent(contentEl, _textbookContentCache.get(source));
        return;
    }

    fetch(`${API_BASE}/api/v2/textbook/chapter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: source, keywords: source }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.success && data.data) {
            _textbookContentCache.set(source, data.data);
            renderTextbookContent(contentEl, data.data);
        } else {
            contentEl.innerHTML = `<div style="text-align: center; padding: 40px 0; color: var(--text-tertiary);">
                <p>暂无该教材的详细内容</p>
                <p style="font-size: 11px; margin-top: 8px;">请尝试与AI助手对话获取相关知识</p>
            </div>`;
        }
    })
    .catch(err => {
        console.warn('[TextbookReader] Fetch failed:', err);
        contentEl.innerHTML = `<div style="text-align: center; padding: 40px 0; color: var(--text-tertiary);">
            <p>加载失败，请稍后重试</p>
        </div>`;
    });
}

window._textbookFontSize = 13;
window._textbookMaximized = false;

function textbookAdjustFont(delta) {
    window._textbookFontSize = Math.max(10, Math.min(22, (window._textbookFontSize || 13) + delta));
    const contentEl = document.getElementById('textbook-reader-content');
    if (contentEl) contentEl.style.fontSize = window._textbookFontSize + 'px';
}

function textbookToggleMaximize() {
    window._textbookMaximized = !window._textbookMaximized;
    const panel = document.getElementById('textbook-reader-panel');
    if (!panel) return;
    if (window._textbookMaximized) {
        panel.style.maxWidth = '100%';
        panel.style.width = '100%';
        panel.style.maxHeight = '100vh';
        panel.style.height = '100vh';
        panel.style.borderRadius = '0';
    } else {
        panel.style.maxWidth = '680px';
        panel.style.width = '92%';
        panel.style.maxHeight = '80vh';
        panel.style.height = '';
        panel.style.borderRadius = '20px';
    }
}

function closeTextbookModal() {
    const modal = document.getElementById('textbook-reader-modal');
    if (!modal) return;
    const panel = modal.querySelector('.textbook-reader-panel');
    if (panel) panel.style.transform = 'translateY(20px) scale(0.97)';
    modal.style.opacity = '0';
    setTimeout(() => { modal.style.visibility = 'hidden'; }, 300);
}

function renderTextbookContent(container, data) {
    if (!container) return;
    const sections = data.sections || [];
    let html = '';
    if (data.title) {
        html += `<h2 style="font-size: 18px; font-weight: 800; color: var(--text-primary); margin-bottom: 16px; text-shadow: 0 1px 3px rgba(0,0,0,0.3);">${escapeHtml(data.title)}</h2>`;
    }
    for (const section of sections) {
        if (section.title) {
            html += `<h3 style="font-size: 14px; font-weight: 700; color: var(--primary-light); margin-top: 20px; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid var(--border-glass);">${escapeHtml(section.title)}</h3>`;
        }
        const content = section.content || '';
        const paragraphs = content.split(/\n+/);
        for (const p of paragraphs) {
            const trimmed = p.trim();
            if (!trimmed) continue;
            if (trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.startsWith('* ')) {
                html += `<div style="padding-left: 16px; margin: 4px 0; position: relative;"><span style="position: absolute; left: 0; color: var(--primary-light);">•</span>${escapeHtml(trimmed.substring(2))}</div>`;
            } else if (/^\d+[\.\)]\s/.test(trimmed)) {
                html += `<div style="padding-left: 16px; margin: 4px 0;">${escapeHtml(trimmed)}</div>`;
            } else {
                html += `<p style="margin: 8px 0;">${escapeHtml(trimmed)}</p>`;
            }
        }
    }
    if (data.sources && data.sources.length > 0) {
        html += `<div style="margin-top: 24px; padding-top: 12px; border-top: 1px solid var(--border-glass); font-size: 11px; color: var(--text-tertiary);">
            <span>📚 参考来源：${data.sources.map(s => escapeHtml(s)).join('、')}</span>
        </div>`;
    }
    container.innerHTML = html;
}

function updateSourceLinks(sourceLinks) {
    if (sourceLinks && typeof sourceLinks === 'object') {
        currentSourceLinks = { ...currentSourceLinks, ...sourceLinks };
        for (const [source, url] of Object.entries(sourceLinks)) {
            setLinkCacheEntry(source, url, 'valid');
        }
    }
}

function renderSources(sources) {
    const sourcePanel = document.getElementById('source-panel');
    const sourceList = document.getElementById('source-list');
    if (!sourcePanel || !sourceList) return;
    if (!sources || sources.length === 0) {
        sourcePanel.classList.add('hidden');
        return;
    }
    sourcePanel.classList.remove('hidden');
    sourceList.innerHTML = sources.map(s => {
        const hasDeepLink = currentSourceLinks[s] || getLinkCache()[s];
        const linkIndicator = hasDeepLink
            ? '<i data-lucide="external-link" class="w-2.5 h-2.5 ml-1 text-green-500" title="深度链接可用"></i>'
            : '<i data-lucide="alert-circle" class="w-2.5 h-2.5 ml-1 text-amber-400" title="深度链接未配置"></i>';
        return `
        <span class="doc-ref cursor-pointer hover:text-blue-600 transition-colors group" onclick="openTextbookLink('${escapeHtml(s)}')">
            <i data-lucide="book-open" class="w-3 h-3"></i> ${escapeHtml(s)} ${linkIndicator}
        </span>`;
    }).join('');
    if (window.lucide) lucide.createIcons();
}

async function refreshLinkCacheFromBackend() {
    try {
        const res = await fetch(`${API_BASE}/api/textbook-links/validate`);
        if (!res.ok) {
            console.warn(`[TextbookLinks] 验证接口返回 ${res.status}，跳过缓存刷新`);
            return;
        }
        const data = await res.json();
        if (data.validationResults) {
            for (const [source, info] of Object.entries(data.validationResults)) {
                if (info.deepLink) {
                    currentSourceLinks[source] = info.deepLink;
                    setLinkCacheEntry(source, info.deepLink, 'valid');
                }
            }
        }
    } catch (err) {
        console.warn('[TextbookLinks] 验证接口请求失败:', err.message || err);
    }
}

function preprocessContent(content) {
    if (!content) return '';
    if (content.includes('```mermaid')) return content;
    const mermaidPattern = /(^|\n)(graph|flowchart) (TD|LR|TB|RL|BT)[\s\S]+?(?=\n\n[^ \t]|$)/g;
    const seqPattern = /(^|\n)sequenceDiagram[\s\S]+?(?=\n\n[^ \t]|$)/g;
    let result = content.replace(mermaidPattern, (match) => {
        return `\n\`\`\`mermaid\n${match.trim()}\n\`\`\`\n\n`;
    });
    result = result.replace(seqPattern, (match) => {
        return `\n\`\`\`mermaid\n${match.trim()}\n\`\`\`\n\n`;
    });

    // 自动检测 URL 并转换为 Markdown 链接（跳过已有链接格式和代码块内的 URL）
    // 匹配未被 []() 包裹的 http/https URL
    const urlPattern = /(?<![\[\(])(https?:\/\/[^\s\)\]\>"\'`]+)(?![\]\)])/g;
    result = result.replace(urlPattern, (url) => {
        // 跳过 Markdown 链接中的 URL
        if (result.substring(result.indexOf(url) - 1, result.indexOf(url)) === '(') return url;
        // 简化为显示域名
        let displayText = url;
        try {
            const urlObj = new URL(url);
            displayText = urlObj.hostname.replace(/^www\./, '');
        } catch { /* keep full url */ }
        return `[${displayText}](${url})`;
    });

    return result;
}

function processDocRefs(html) {
    return html.replace(/\[Doc_Ref:\s*([^\]]+)\]/g, (match, ref) => {
        const hasDeepLink = currentSourceLinks[ref] || getLinkCache()[ref];
        const linkIndicator = hasDeepLink
            ? '<i data-lucide="external-link" style="width:9px;height:9px;display:inline;vertical-align:middle;margin-left:2px;color: var(--success);" title="深度链接可用"></i>'
            : '';
        return `<span class="doc-ref cursor-pointer hover:text-blue-600 transition-colors" onclick="openTextbookLink('${escapeHtml(ref)}')"><i data-lucide="book-open" style="width:10px;height:10px;display:inline;vertical-align:middle;"></i> ${escapeHtml(ref)}${linkIndicator}</span>`;
    });
}

/* ========== <think> 标签解析与思考 UI ========== */

function extractThinkContent(content) {
    if (!content) return { reasoning: '', finalContent: '' };
    const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/);
    if (!thinkMatch) return { reasoning: '', finalContent: content };
    const reasoning = thinkMatch[1].trim();
    const finalContent = content.replace(/<think>[\s\S]*?<\/think>/, '').trim();
    return { reasoning, finalContent };
}

function renderThinkBlock(reasoning, isStreaming) {
    if (!reasoning) return '';
    const safeReasoning = escapeHtml(reasoning);
    return `<div class="think-block ${isStreaming ? 'is-open' : ''}" id="think-block-${isStreaming ? 'stream' : Date.now()}">
        <div class="think-block-header" onclick="toggleThinkBlock(this)">
            <svg class="think-block-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z"></path><path d="M9 21h6"></path></svg>
            <span class="think-block-title">深度思考</span>
            <span class="think-block-toggle">${isStreaming ? '收起' : '展开'}</span>
            <svg class="think-block-chevron" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </div>
        <div class="think-block-body">
            <div class="think-block-content">${safeReasoning}</div>
        </div>
    </div>`;
}

function toggleThinkBlock(header) {
    const block = header.closest('.think-block');
    if (!block) return;
    const isOpen = block.classList.contains('is-open');
    block.classList.toggle('is-open', !isOpen);
    const toggleText = header.querySelector('.think-block-toggle');
    if (toggleText) toggleText.textContent = isOpen ? '展开' : '收起';
}

function renderThinkStrip(logs, isDone) {
    if (!logs || logs.length === 0) return '';
    if (isDone) {
        const thinkId = 'think-done-' + Date.now();
        return `<div class="think-collapsed-badge" onclick="document.getElementById('${thinkId}').classList.toggle('hidden');this.classList.toggle('hidden')">
            <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z"></path><path d="M9 21h6"></path></svg>
            ✨ 已深度思考
        </div>
        <div id="${thinkId}" class="hidden">${renderThinkTimeline(logs)}</div>`;
    }
    const latest = logs[logs.length - 1];
    const agentLabel = getAgentLabel(latest.agent);
    return `<div class="think-strip" onclick="this.classList.toggle('is-open');const tl=this.nextElementSibling;if(tl)tl.classList.toggle('is-open')">
            <div class="think-pulse-dots">
                <div class="think-pulse-dot"></div>
                <div class="think-pulse-dot"></div>
                <div class="think-pulse-dot"></div>
            </div>
            <span class="think-strip-text">${escapeHtml(agentLabel)} · ${escapeHtml(latest.content.slice(0, 40))}${latest.content.length > 40 ? '…' : ''}</span>
            <svg class="think-strip-chevron" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </div>
        ${renderThinkTimeline(logs)}`;
}

function renderThinkTimeline(logs) {
    if (!logs || logs.length === 0) return '';
    const items = logs.map((log, idx) => {
        const isLatest = idx === logs.length - 1;
        const agentLabel = getAgentLabel(log.agent);
        return `<div class="think-log-item ${isLatest ? 'is-latest' : ''}"><span class="think-log-agent">${escapeHtml(agentLabel)}</span><span class="think-log-msg">${escapeHtml(log.content)}</span></div>`;
    }).join('');
    return `<div class="think-log-timeline">${items}</div>`;
}

function renderMemoryBanner(memoryRefs) {
    if (!memoryRefs || memoryRefs.length === 0) return '';
    const typeLabels = {
        background: '📋',
        preference: '⚙️',
        knowledge: '📚',
        interest: '⭐',
        goal: '🎯',
        emotion: '💭',
        learning_trait: '🔍',
        personality: '🧠',
        interaction: '🤝',
        fact: '📝',
    };
    const count = memoryRefs.length;
    const summaryText = count === 1 ? 'AI 引用了 1 条记忆' : `AI 引用了 ${count} 条记忆`;
    const itemsHtml = memoryRefs.map(ref => {
        const icon = typeLabels[ref.type] || '📝';
        const text = ref.content.length > 40 ? ref.content.substring(0, 40) + '...' : ref.content;
        return `<div class="memory-ref-item"><span class="memory-ref-bullet">${icon}</span><span class="memory-ref-content">${escapeHtml(text)}</span></div>`;
    }).join('');
    return `
        <div class="memory-banner" onclick="this.classList.toggle('is-expanded')">
            <span class="memory-banner-text">🧠 ${summaryText}</span>
            <span class="memory-banner-toggle"></span>
            <div class="memory-banner-expand">${itemsHtml}</div>
        </div>
    `;
}

async function renderMessages() {
    const container = document.getElementById('chat-container');
    if (!container) return;

    const streamBubble = container.querySelector('.stream-bubble');

    container.innerHTML = messages.map(msg => {
        let htmlContent = '';
        let thinkBlockHtml = '';
        if (msg.role === 'user') {
            htmlContent = escapeHtml(msg.content);
        } else {
            const { reasoning, finalContent } = extractThinkContent(msg.content);
            const processedContent = preprocessContent(finalContent);
            try {
                if (window.marked) {
                    htmlContent = marked.parse(processedContent);
                } else {
                    htmlContent = escapeHtml(processedContent);
                }
            } catch (e) {
                console.warn('[renderMessages] marked.parse error:', e);
                htmlContent = escapeHtml(processedContent);
            }
            htmlContent = processDocRefs(htmlContent);
            htmlContent = htmlContent.replace(
                /\[SocraticQ\](.*?)\[\/SocraticQ\]/g,
                '<div class="socratic-inline-q"><span class="socratic-q-icon">💡</span><span class="socratic-q-text">$1</span></div>'
            );
            // 解析记忆引用标记 [MemRef]
            htmlContent = htmlContent.replace(
                /\[MemRef\](.*?)\[\/MemRef\]/g,
                '<span class="mem-ref-mark"><span class="mem-ref-content">$1</span><span class="mem-ref-badge">🧠 引用记忆</span></span>'
            );
            if (reasoning) {
                thinkBlockHtml = renderThinkBlock(reasoning, false);
            }
            if (msg._thinkingLogs && msg._thinkingLogs.length > 0) {
                thinkBlockHtml = renderThinkStrip(msg._thinkingLogs, true) + thinkBlockHtml;
            }
        }
        const isSocratic = msg.role === 'assistant' && msg.socratic;

        // 主动消息的特殊标识
        const isProactive = msg._isProactive;
        const proactiveBadge = isProactive ? `<span class="proactive-badge"><i data-lucide="sparkles" class="w-3 h-3"></i> 主动推送</span>` : '';

        // 身份标签
        let identityBadge = '';
        if (msg.role === 'assistant') {
            const personaLabel = PERSONA_NAMES[msg._persona] || '';
            const agentLabel = msg._agentName && msg._agentId !== 'default' ? msg._agentName : '';
            if (personaLabel || agentLabel) {
                const identityText = [personaLabel, agentLabel].filter(Boolean).join(' · ');
                identityBadge = `<span class="identity-badge">${escapeHtml(identityText)}</span>`;
            }
        }

        // 链接容器（用于后续 JS 注入）
        const linksContainerId = msg._timestamp ? `links-${msg._timestamp}` : '';
        const hasLinks = msg._links && msg._links.length > 0;
        const hasActions = msg._actions && msg._actions.length > 0;

        return `
        <div class="msg-row flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}" data-msg-id="${msg._timestamp || ''}">
            <div class="max-w-[90%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} min-w-0">
                ${msg.role !== 'user' ? `<span class="text-xs mb-1 ml-1 flex items-center gap-1 font-bold" style="color: var(--primary);"><i data-lucide="bot" class="w-3 h-3"></i> 智能辅导团队 ${identityBadge}${isSocratic ? '<span class="socratic-badge"><i data-lucide="help-circle" style="width:10px;height:10px;display:inline;"></i> 苏格拉底诊断</span>' : ''}${proactiveBadge}</span>` : ''}
                ${msg.role !== 'user' && msg._memoryRefs && msg._memoryRefs.length > 0 ? renderMemoryBanner(msg._memoryRefs) : ''}
                <div class="msg-bubble p-4 rounded-2xl ${msg.role === 'user' ? 'msg-bubble-user rounded-tr-none' : 'msg-bubble-bot rounded-tl-none'} w-full min-w-0 overflow-x-visible ${isProactive ? 'msg-bubble--proactive' : ''}">
                    ${thinkBlockHtml}
                    <div class="prose prose-sm max-w-none break-words whitespace-pre-wrap">${htmlContent}</div>
                    ${hasLinks ? `<div class="message-links" id="${linksContainerId}"></div>` : ''}
                    ${hasActions ? `<div class="message-actions" id="actions-${msg._timestamp || ''}"></div>` : ''}
                    ${msg._socraticCheckpoint ? `<div class="socratic-checkpoint"><span class="checkpoint-label">💭 ${msg._checkpointTopic ? '「' + escapeHtml(msg._checkpointTopic) + '」' : '这部分'}理解了吗？</span><div class="checkpoint-actions"><button class="checkpoint-btn checkpoint-yes" onclick="confirmUnderstanding(true, '${msg._timestamp || ''}')">✓ 理解了</button><button class="checkpoint-btn checkpoint-no" onclick="confirmUnderstanding(false, '${msg._timestamp || ''}')">✗ 不太懂</button></div></div>` : ''}
                </div>
            </div>
        </div>`;
    }).join('');

    // 渲染链接和按钮（使用 SmartLinkRenderer）
    messages.forEach(msg => {
        if (msg._links && msg._links.length > 0) {
            const linksEl = document.getElementById(`links-${msg._timestamp}`);
            if (linksEl && window.smartLinkRenderer) {
                const rendered = window.smartLinkRenderer.render(msg._links, {
                    agent_id: msg._agentId,
                    tone: msg._tone,
                    message_type: msg._isProactive ? 'proactive' : 'reactive'
                });
                if (rendered) {
                    linksEl.appendChild(rendered);
                }
            }
        }
        if (msg._actions && msg._actions.length > 0 && msg._links) {
            const actionsEl = document.getElementById(`actions-${msg._timestamp}`);
            if (actionsEl && window.smartLinkRenderer) {
                const rendered = window.smartLinkRenderer.renderActions(msg._actions, msg._links);
                if (rendered) {
                    actionsEl.appendChild(rendered);
                }
            }
        }
    });

    if (streamBubble && isTypewriting) {
        container.appendChild(streamBubble);
    }

    container.scrollTop = container.scrollHeight;
    if (window.lucide) lucide.createIcons();

    if (window.mermaid) {
        const placeholders = document.querySelectorAll('.mermaid-placeholder');
        for (let i = 0; i < placeholders.length; i++) {
            const div = placeholders[i];
            const txt = document.createElement("textarea");
            txt.innerHTML = div.innerHTML;
            let code = txt.value.trim();
            const id = `mermaid-svg-${Date.now()}-${i}`;
            try {
                code = code.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
                const validStarts = ['graph', 'flowchart', 'sequenceDiagram', 'classDiagram', 'stateDiagram', 'pie', 'gantt'];
                const codeLines = code.split('\n').filter(line => line.trim() !== '');
                if (codeLines.length > 0) {
                    const firstLine = codeLines[0].trim();
                    const isValidStart = validStarts.some(start => firstLine.startsWith(start));
                    if (!isValidStart) throw new Error('图表代码格式不正确');
                }
                const { svg } = await mermaid.render(id, code);
                div.innerHTML = svg;
            } catch (e) {
                console.warn("Mermaid render error:", e);
                div.style.display = 'none';
                const errEl = document.getElementById('d' + id);
                if (errEl) errEl.remove();
            }
            div.classList.remove('mermaid-placeholder');
        }
    }

    renderMicroCourses();
}

function renderMicroCourses() {
    const mcBlocks = document.querySelectorAll('.micro-course-block');
    mcBlocks.forEach(block => {
        if (block.dataset.rendered) return;
        block.dataset.rendered = 'true';
        try {
            const data = JSON.parse(block.textContent);
            let scenesHtml = '';
            if (data.scenes) {
                data.scenes.forEach((scene, idx) => {
                    scenesHtml += `
                        <div class="mc-scene ${idx === 0 ? 'active' : ''}" data-scene-idx="${idx}">
                            <div class="text-xs text-indigo-300 mb-1">Scene ${idx + 1}</div>
                            <div class="text-sm">${escapeHtml(scene.narration)}</div>
                            ${scene.highlight ? `<div class="text-xs text-amber-300 mt-1">Key: ${escapeHtml(scene.highlight)}</div>` : ''}
                        </div>
                    `;
                });
            }
            block.innerHTML = `
                <div class="micro-course-player">
                    <div class="flex items-center gap-2 mb-3">
                        <i data-lucide="play-circle" class="w-5 h-5 text-indigo-300"></i>
                        <span class="font-bold text-sm">${escapeHtml(data.title || '微课动画')}</span>
                        <button onclick="playMicroCourse(this)" class="ml-auto px-3 py-1 text-[var(--text-on-accent)] text-xs rounded-lg font-semibold transition-colors">播放</button>
                    </div>
                    <div class="mc-progress mb-3"><div class="mc-progress-bar" style="width: 0%"></div></div>
                    <div class="mc-scenes">${scenesHtml}</div>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
        } catch(e) {
            block.innerHTML = `<div class="bg-red-50 text-red-500 p-2 rounded text-xs">微课数据解析失败</div>`;
        }
    });
}

function playMicroCourse(btn) {
    const player = btn.closest('.micro-course-player');
    const scenes = player.querySelectorAll('.mc-scene');
    const progressBar = player.querySelector('.mc-progress-bar');
    btn.disabled = true;
    btn.textContent = '播放中...';
    let idx = 0;
    function next() {
        if (idx >= scenes.length) {
            btn.disabled = false;
            btn.textContent = '重播';
            progressBar.style.width = '100%';
            return;
        }
        scenes.forEach(s => s.classList.remove('active'));
        scenes[idx].classList.add('active');
        progressBar.style.width = ((idx + 1) / scenes.length * 100) + '%';
        const narration = scenes[idx].querySelector('div:nth-child(2)').textContent;
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance(narration);
            utter.lang = 'zh-CN';
            utter.rate = 0.9;
            utter.onend = () => { idx++; setTimeout(next, 500); };
            window.speechSynthesis.speak(utter);
        } else {
            setTimeout(() => { idx++; next(); }, 3000);
        }
    }
    next();
}

async function runCode() {
    if (!codeEditor) return;
    const code = codeEditor.getValue();
    const langSelect = document.getElementById('lang-select');
    const outputPanel = document.getElementById('run-output-panel');
    if (!outputPanel) return;
    switchOutputTab('run');
    outputPanel.innerHTML = '<div class="text-yellow-400 text-xs animate-pulse">正在运行中...</div>';
    try {
        const res = await fetch(RUN_CODE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, language: langSelect ? langSelect.value : 'python' })
        });
        const data = await res.json();
        let output = '';
        if (data.stdout) output += `<div class="text-green-400 whitespace-pre-wrap">${escapeHtml(data.stdout)}</div>`;
        if (data.stderr) output += `<div class="text-red-400 whitespace-pre-wrap mt-2">${escapeHtml(data.stderr)}</div>`;
        if (!data.stdout && !data.stderr) output = '<div class="text-gray-500">程序运行完毕，无输出。</div>';
        const statusColor = data.returncode === 0 ? 'text-green-400' : 'text-red-400';
        const statusText = data.returncode === 0 ? '运行成功' : '运行失败';
        outputPanel.innerHTML = `<div class="${statusColor} text-xs mb-2 pb-2 border-b border-gray-700">退出码: ${data.returncode} | ${statusText}</div>${output}`;
    } catch (error) {
        outputPanel.innerHTML = `<div class="text-red-400">运行请求失败: ${escapeHtml(error.message)}</div>`;
    }
}

async function submitGrade() {
    if (!codeEditor) return;
    const code = codeEditor.getValue();
    const taskInput = document.getElementById('task-input');
    const langSelect = document.getElementById('lang-select');
    const gradePanel = document.getElementById('grade-output-panel');
    if (!gradePanel) return;
    const task = taskInput ? taskInput.value.trim() : '';
    if (!task) {
        switchOutputTab('grade');
        gradePanel.innerHTML = '<div class="text-orange-500 text-sm text-center mt-8">请先在「编程题目」区域输入题目要求，再提交批阅。</div>';
        return;
    }
    switchOutputTab('grade');
    gradePanel.innerHTML = '<div class="text-center mt-8"><div class="animate-spin w-8 h-8 border-4 border-t-transparent rounded-full mx-auto mb-3" style="border-color: var(--primary-200); border-top-color: var(--primary);"></div><div class="text-gray-500 text-sm">AI 正在批阅你的代码，请稍候...</div></div>';
    try {
        const res = await fetch(GRADE_CODE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, task, language: langSelect ? langSelect.value : 'python', currentProfile: profile })
        });
        const data = await res.json();
        renderGradeResult(data);
        lastGradeRecord = {
            task: task,
            score: data.score || 0,
            language: langSelect ? langSelect.value : 'python',
            correctness: data.correctness || '',
            logic_analysis: data.logic_analysis || '',
            style_analysis: data.style_analysis || '',
            suggestions: data.suggestions || [],
            graded_at: new Date().toISOString()
        };
        await saveProgress();
    } catch (error) {
        gradePanel.innerHTML = `<div class="text-red-500 text-sm text-center mt-8">批阅请求失败: ${escapeHtml(error.message)}</div>`;
    } finally {
        schedulePathRefresh('code_grade');
    }
}

function renderGradeResult(data) {
    const gradePanel = document.getElementById('grade-output-panel');
    if (!gradePanel) return;
    const score = data.score || 0;
    let scoreClass = 'score-poor';
    if (score >= 90) scoreClass = 'score-excellent';
    else if (score >= 70) scoreClass = 'score-good';
    else if (score >= 50) scoreClass = 'score-medium';
    let suggestionsHtml = '';
    if (data.suggestions && data.suggestions.length > 0) {
        suggestionsHtml = data.suggestions.map((s, i) => `
            <div class="flex items-start gap-2 p-2 bg-amber-50 rounded-lg border border-amber-100">
                <span class="shrink-0 w-5 h-5 bg-amber-200 text-amber-700 rounded-full flex items-center justify-center text-xs font-bold">${i + 1}</span>
                <span class="text-sm text-amber-800">${escapeHtml(s)}</span>
            </div>
        `).join('');
    }
    let refAnswerHtml = '';
    if (data.reference_answer) {
        refAnswerHtml = `<div class="mt-4"><div class="text-xs font-semibold text-gray-500 mb-2 flex items-center gap-1"><i data-lucide="code" class="w-3 h-3"></i> 参考答案</div><pre class="bg-gray-900 text-green-400 p-3 rounded-lg text-xs overflow-x-auto whitespace-pre-wrap font-mono">${escapeHtml(data.reference_answer)}</pre></div>`;
    }
    gradePanel.innerHTML = `
        <div class="animate-slide-up space-y-4">
            <div class="flex items-center gap-5 p-4 rounded-xl border" style="background: var(--primary-50); border-color: var(--primary-200);">
                <div class="score-ring ${scoreClass} shrink-0">${score}</div>
                <div class="flex-1">
                    <div class="text-lg font-bold text-gray-800 mb-1">AI 批阅结果</div>
                    <div class="text-sm text-gray-600">${score >= 90 ? '优秀！继续保持！' : score >= 70 ? '良好，还有提升空间' : score >= 50 ? '及格，需要加强练习' : '需要重新复习相关知识'}</div>
                    ${data.encouragement ? `<div class="text-xs mt-2 italic" style="color: var(--primary);">"${escapeHtml(data.encouragement)}"</div>` : ''}
                </div>
            </div>
            <div><div class="text-xs font-semibold text-gray-500 mb-2 flex items-center gap-1"><i data-lucide="check-square" class="w-3 h-3"></i> 正确性评价</div><p class="text-sm text-gray-700 rounded-lg border p-3">${escapeHtml(data.correctness || '无')}</p></div>
            <div><div class="text-xs font-semibold text-gray-500 mb-2 flex items-center gap-1"><i data-lucide="git-branch" class="w-3 h-3"></i> 逻辑分析</div><p class="text-sm text-gray-700 rounded-lg border p-3">${escapeHtml(data.logic_analysis || '无')}</p></div>
            <div><div class="text-xs font-semibold text-gray-500 mb-2 flex items-center gap-1"><i data-lucide="palette" class="w-3 h-3"></i> 代码风格</div><p class="text-sm text-gray-700 rounded-lg border p-3">${escapeHtml(data.style_analysis || '无')}</p></div>
            ${suggestionsHtml ? `<div><div class="text-xs font-semibold text-gray-500 mb-2 flex items-center gap-1"><i data-lucide="lightbulb" class="w-3 h-3"></i> 改进建议</div><div class="space-y-2">${suggestionsHtml}</div></div>` : ''}
            ${refAnswerHtml}
        </div>
    `;
    if (window.lucide) lucide.createIcons();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function extractTaskFromContent(fullText) {
    if (!fullText) return '';

    const lines = fullText.split('\n');

    let taskStartIdx = -1;
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.match(/📝?\s*题目/) || line.match(/题目[：:]/) || line.match(/题目描述/) || line.match(/^(#{1,3}\s*)?题目/)) {
            taskStartIdx = i;
            break;
        }
    }

    if (taskStartIdx === -1) {
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.match(/请编写|请实现|请完成|请设计|编程题|练习题|作业[：:]/)) {
                taskStartIdx = i;
                break;
            }
        }
    }

    if (taskStartIdx === -1) {
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.match(/Task:|Problem:|Exercise:/)) {
                taskStartIdx = i;
                break;
            }
        }
    }

    if (taskStartIdx !== -1) {
        let extractedParts = [];
        for (let i = taskStartIdx; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            if (extractedParts.length > 0 && (
                line.match(/^```/) ||
                line.match(/^#{1,3}\s*(💡|📊|🎯|📚|🐍|核心概念|代码实现|算法逻辑|实际操作|考点|拓展)/) ||
                line.match(/^#{1,3}\s*(Python|代码|实现|可视化|步骤|考点)/)
            )) {
                break;
            }

            extractedParts.push(line);

            if (extractedParts.join('\n').length > 300) break;
        }

        if (extractedParts.length > 0) {
            let result = extractedParts.join('\n');
            result = result.replace(/\*\*/g, '').replace(/📝\s*/g, '').replace(/#{1,6}\s*/g, '');
            result = result.replace(/^\s*题目[：:]\s*/i, '题目：');
            if (result.length > 250) {
                result = result.substring(0, 247) + '...';
            }
            return result;
        }
    }

    const shortDesc = lines.filter(l => l.trim()).slice(0, 3).join(' ').replace(/[#*\[\]]/g, '').trim();
    if (shortDesc.length > 150) {
        return shortDesc.substring(0, 147) + '...';
    }
    return shortDesc;
}

function autoFillTask(taskText) {
    const refinedTask = extractTaskFromContent(taskText);
    const taskInput = document.getElementById('task-input');
    if (taskInput) {
        taskInput.value = refinedTask;
        switchTab('code');
    }
}

function isProgrammingTask(text) {
    if (!text) return false;
    const lines = text.split('\n').filter(l => l.trim());
    if (lines.length === 0) return false;

    const taskSignals = ['📝 题目', '题目：', '题目描述', '编程题', '练习题', '作业：', 'Task:', 'Problem:', 'Exercise:'];
    const hasTaskSignal = taskSignals.some(s => text.includes(s));
    if (!hasTaskSignal) return false;

    const codeSignals = ['函数', '算法', '代码', '编写', '实现', '编程', 'def ', 'int main', '#include', 'class ', 'return', '输入', '输出', '示例', '测试用例'];
    const hasCodeSignal = codeSignals.some(s => text.includes(s));

    const instructionSignals = ['请编写', '请实现', '请完成', '请设计', '要求你', '实现一个', '编写一个', '设计一个'];
    const hasInstructionSignal = instructionSignals.some(s => text.includes(s));

    if (hasTaskSignal && (hasCodeSignal || hasInstructionSignal)) {
        const lines = text.split('\n');
        let taskLines = 0;
        for (let line of lines) {
            if (line.trim() && !line.trim().startsWith('```') && !line.trim().startsWith('#')) {
                taskLines++;
            }
        }
        return taskLines >= 2;
    }

    return false;
}

function detectLanguageNeed(text) {
    const lower = text.toLowerCase();
    const cKeywords = ['c语言', 'c 语言', 'c语言不懂', 'c语言不会', 'c语言不理解', 'c语言基础', 'c语言指针', 'c语言数组', 'c语言结构体', 'c语言内存', 'c语言函数', 'c语言入门', '学c语言', 'c语言学习', 'c语言复习', 'c语言考试'];
    const cppKeywords = ['c++', 'cpp', 'c++不懂', 'c++不会', 'c++基础', 'c++入门', '学c++', 'c++学习', 'c++复习'];
    for (const kw of cKeywords) {
        if (lower.includes(kw)) return 'c';
    }
    for (const kw of cppKeywords) {
        if (lower.includes(kw)) return 'cpp';
    }
    return null;
}

const AGENT_COLORS = {
    system: { bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-300', dot: 'bg-slate-400' },
    profiler: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', dot: 'bg-blue-500' },
    planner: { bg: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-200', dot: 'bg-violet-500' },
    master_controller: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', dot: 'bg-amber-500' },
    rag_retriever: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', dot: 'bg-emerald-500' },
    socratic_evaluator: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', dot: 'bg-purple-500' },
    generator_visual: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', dot: 'bg-orange-500' },
    generator_pragmatic: { bg: 'bg-teal-50', text: 'text-teal-700', border: 'border-teal-200', dot: 'bg-teal-500' },
    generator_textual: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200', dot: 'bg-cyan-500' },
    evaluator: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', dot: 'bg-rose-500' },
    // 辩论身份颜色
    debate_bigdata_architect: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', dot: 'bg-blue-500' },
    debate_psychologist: { bg: 'bg-pink-50', text: 'text-pink-700', border: 'border-pink-200', dot: 'bg-pink-500' },
    debate_interviewer: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', dot: 'bg-amber-500' },
    debate_educator: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', dot: 'bg-purple-500' },
    debate_geek_senior: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', dot: 'bg-emerald-500' },
    judge: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', dot: 'bg-orange-500' },
};
const DEFAULT_AGENT_COLOR = { bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200', dot: 'bg-gray-400' };

const PERSONA_NAMES = {
    patient_tutor: '🍵 陈默',
    socratic_questioner: '🔍 林问',
    energetic_lecturer: '⚡ 周燃',
    expert_mentor: '🏔️ 严铮',
};

const AGENT_LABELS = {
    system: '系统',
    profiler: '画像分析',
    planner: '路径规划',
    master_controller: '主控中枢',
    rag_retriever: 'RAG检索',
    socratic_evaluator: '苏格拉底',
    generator_visual: '视觉生成',
    generator_pragmatic: '实践生成',
    generator_textual: '文本生成',
    evaluator: '评估',
    memory: '💡 记忆助手',
    memory_retrieval: '🧠 记忆检索',
    // 辩论身份标签
    debate_bigdata_architect: '大数据导师',
    debate_psychologist: '知心辅导员',
    debate_interviewer: '面试官',
    debate_educator: '教育学大师',
    debate_geek_senior: '极客学长',
    judge: '裁判',
};

const FLOW_PIPELINE = ['system', 'profiler', 'planner', 'master_controller', 'rag_retriever', 'socratic_evaluator', 'generator_visual', 'generator_pragmatic', 'generator_textual', 'evaluator'];

let sandboxLogs = [];
let activeAgents = new Set();
let sandboxFilterSet = new Set();
let typewriterTimer = null;
let typewriterQueue = [];
let isTypewriting = false;
let currentAssistantContent = '';
let currentAssistantIdx = -1;
let streamAbortController = null;
let currentThinkingLogs = [];

// 辩论模式状态
let debateState = {
    isActive: false,
    currentRound: 0,
    agentResponses: {},
    crossComments: {},
    debateHistory: [],
    isComplete: false
};
let debateAbortController = null;
function getAgentColor(agentName) {
    for (const [key, color] of Object.entries(AGENT_COLORS)) {
        if (agentName.includes(key)) return color;
    }
    return DEFAULT_AGENT_COLOR;
}

function getAgentLabel(agentName) {
    for (const [key, label] of Object.entries(AGENT_LABELS)) {
        if (agentName.includes(key)) return label;
    }
    return agentName;
}

function updateSandboxStatus(status, color) {
    const el = document.getElementById('sandbox-status');
    if (!el) return;
    el.textContent = status;
    el.className = `text-[10px] px-2 py-0.5 rounded-full font-semibold ${color || 'bg-gray-200 text-gray-500'}`;
}

function renderFlowNodes() {
    const container = document.getElementById('flow-node-container');
    if (!container) return;

    const pipeline = FLOW_PIPELINE.filter(name => activeAgents.has(name) || name === 'system');
    if (pipeline.length === 0) {
        container.innerHTML = '<span class="text-xs text-gray-400">等待智能体启动...</span>';
        return;
    }

    container.innerHTML = pipeline.map((name, i) => {
        const color = getAgentColor(name);
        const label = getAgentLabel(name);
        const isActive = activeAgents.has(name);
        const dotClass = isActive ? color.dot : 'bg-gray-300';
        const opacityClass = isActive ? '' : 'opacity-40';
        const connector = i < pipeline.length - 1 ? '<i data-lucide="chevron-right" class="w-3 h-3 text-gray-300 shrink-0"></i>' : '';
        return `<div class="flex items-center gap-1 ${opacityClass}">
            <div class="flex items-center gap-1 px-2 py-1 rounded-full ${color.bg} border ${color.border} transition-all duration-300">
                <div class="w-1.5 h-1.5 rounded-full ${dotClass} ${isActive ? 'animate-pulse' : ''}"></div>
                <span class="text-[10px] font-semibold ${color.text} whitespace-nowrap">${label}</span>
            </div>
            ${connector}
        </div>`;
    }).join('');

    if (window.lucide) lucide.createIcons();
}

function renderSandboxLog(log, prepend) {
    const container = document.getElementById('sandbox-logs');
    if (!container) return;

    if (sandboxFilterSet.size > 0 && !sandboxFilterSet.has(log.agent)) return;

    const searchInput = document.getElementById('sandbox-search-input');
    const searchTerm = searchInput ? searchInput.value.trim().toLowerCase() : '';
    if (searchTerm && !log.content.toLowerCase().includes(searchTerm) && !log.agent.toLowerCase().includes(searchTerm)) return;

    const color = getAgentColor(log.agent);
    const label = getAgentLabel(log.agent);
    const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';

    const bubble = document.createElement('div');
    bubble.className = `agent-bubble ${color.bg} border ${color.border} rounded-xl p-2.5 transition-all duration-300 animate-slide-up`;
    bubble.dataset.agent = log.agent;
    bubble.innerHTML = `
        <div class="flex items-center gap-1.5 mb-1">
            <div class="w-2 h-2 rounded-full ${color.dot} shrink-0"></div>
            <span class="text-[11px] font-bold ${color.text}">${escapeHtml(label)}</span>
            ${time ? `<span class="text-[9px] text-gray-400 ml-auto">${time}</span>` : ''}
        </div>
        <div class="text-[11px] text-gray-600 leading-relaxed pl-3.5">${escapeHtml(log.content)}</div>
    `;

    if (prepend && container.firstChild) {
        container.insertBefore(bubble, container.firstChild);
    } else {
        container.appendChild(bubble);
    }
    container.scrollTop = container.scrollHeight;
}

function renderAllSandboxLogs() {
    const container = document.getElementById('sandbox-logs');
    if (!container) return;
    container.innerHTML = '';
    sandboxLogs.forEach(log => renderSandboxLog(log, false));
}

function renderFilterChips() {
    const container = document.getElementById('sandbox-filter-chips');
    if (!container) return;

    const agents = [...new Set(sandboxLogs.map(l => l.agent))];
    container.innerHTML = agents.map(agent => {
        const color = getAgentColor(agent);
        const label = getAgentLabel(agent);
        const isActive = sandboxFilterSet.has(agent);
        return `<button class="text-[10px] px-2 py-0.5 rounded-full border font-semibold transition-all duration-200 ${isActive ? color.bg + ' ' + color.text + ' ' + color.border : 'text-[var(--text-tertiary)] border-[var(--border-glass)]'}" data-filter-agent="${agent}">${label}</button>`;
    }).join('');

    container.querySelectorAll('[data-filter-agent]').forEach(btn => {
        btn.addEventListener('click', () => {
            const agent = btn.dataset.filterAgent;
            if (sandboxFilterSet.has(agent)) {
                sandboxFilterSet.delete(agent);
            } else {
                sandboxFilterSet.add(agent);
            }
            renderFilterChips();
            renderAllSandboxLogs();
        });
    });
}

function startTypewriter(text) {
    typewriterQueue.push(text);
    if (!isTypewriting) {
        processTypewriterQueue();
    }
}

function processTypewriterQueue() {
    if (typewriterQueue.length === 0) {
        isTypewriting = false;
        return;
    }

    isTypewriting = true;
    const text = typewriterQueue.shift();

    let charIdx = 0;
    const speed = 18;
    const batchSize = 3;

    function typeNext() {
        if (charIdx >= text.length) {
            processTypewriterQueue();
            return;
        }

        const end = Math.min(charIdx + batchSize, text.length);
        currentAssistantContent += text.slice(charIdx, end);
        charIdx = end;

        if (currentAssistantIdx >= 0 && currentAssistantIdx < messages.length) {
            messages[currentAssistantIdx].content = currentAssistantContent;
        }

        requestAnimationFrame(() => {
            renderStreamingMessage();
        });

        typewriterTimer = setTimeout(typeNext, speed);
    }

    typeNext();
}

function renderStreamingMessage() {
    const container = document.getElementById('chat-container');
    if (!container) return;

    let streamBubble = container.querySelector('.stream-bubble');
    if (!streamBubble) return;

    const { reasoning, finalContent } = extractThinkContent(currentAssistantContent);
    const processedContent = preprocessContent(finalContent);
    let htmlContent = processedContent;
    try {
        if (window.marked) {
            htmlContent = marked.parse(processedContent);
        }
    } catch (e) {
        console.warn('[renderStreamingMessage] marked.parse error:', e);
        htmlContent = escapeHtml(processedContent);
    }
    htmlContent = processDocRefs(htmlContent);
    htmlContent = htmlContent.replace(
        /\[SocraticQ\](.*?)\[\/SocraticQ\]/g,
        '<div class="socratic-inline-q"><span class="socratic-q-icon">💡</span><span class="socratic-q-text">$1</span></div>'
    );
    // 解析记忆引用标记 [MemRef]
    htmlContent = htmlContent.replace(
        /\[MemRef\](.*?)\[\/MemRef\]/g,
        '<span class="mem-ref-mark"><span class="mem-ref-content">$1</span><span class="mem-ref-badge">🧠 引用记忆</span></span>'
    );

    const thinkBlockHtml = reasoning ? renderThinkBlock(reasoning, true) : '';
    const thinkStripHtml = currentThinkingLogs.length > 0 ? renderThinkStrip(currentThinkingLogs, false) : '';

    const isSocratic = messages[currentAssistantIdx]?.socratic;
    const streamingPersonaLabel = PERSONA_NAMES[currentPersona] || '';
    const streamingAgentLabel = currentAgent && currentAgent.id !== 'default' ? currentAgent.name : '';
    const streamingIdentityText = [streamingPersonaLabel, streamingAgentLabel].filter(Boolean).join(' · ');
    const streamingIdentityBadge = streamingIdentityText ? `<span class="identity-badge">${escapeHtml(streamingIdentityText)}</span>` : '';
    const headerHtml = `<span class="text-xs mb-1 ml-1 flex items-center gap-1 font-bold" style="color: var(--primary);"><i data-lucide="bot" class="w-3 h-3"></i> 智能辅导团队 ${streamingIdentityBadge}${isSocratic ? '<span class="socratic-badge"><i data-lucide="help-circle" style="width:10px;height:10px;display:inline;"></i> 苏格拉底诊断</span>' : ''}</span>`;

    streamBubble.innerHTML = `<div class="max-w-[90%] flex flex-col items-start min-w-0">${headerHtml}<div class="msg-bubble p-4 rounded-2xl msg-bubble-bot rounded-tl-none w-full min-w-0 overflow-x-auto">${thinkStripHtml}${thinkBlockHtml}<div class="prose prose-sm max-w-none break-words whitespace-pre-wrap">${htmlContent}<span class="typing-cursor-inline"></span></div></div></div>`;

    const chatScroll = container.closest('.chat-glass-scroll') || container;
    const isNearBottom = chatScroll.scrollHeight - chatScroll.scrollTop - chatScroll.clientHeight < 150;
    if (isNearBottom) {
        chatScroll.scrollTop = chatScroll.scrollHeight;
    }

    if (window.lucide) lucide.createIcons();
    renderMermaidInBubble(streamBubble);
}

function renderMermaidInBubble(container) {
    if (!window.mermaid) return;
    const placeholders = container.querySelectorAll('.mermaid-placeholder');
    placeholders.forEach(async (div, i) => {
        if (div.dataset.rendered) return;
        div.dataset.rendered = 'true';
        const txt = document.createElement("textarea");
        txt.innerHTML = div.innerHTML;
        let code = txt.value.trim();
        const id = `mermaid-stream-${Date.now()}-${i}`;
        try {
            code = code.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
            const { svg } = await mermaid.render(id, code);
            div.innerHTML = svg;
        } catch (e) {
            console.warn("Mermaid render error (bubble):", e);
            div.style.display = 'none';
            const errEl = document.getElementById('d' + id);
            if (errEl) errEl.remove();
        }
        div.classList.remove('mermaid-placeholder');
    });
}

function getInputValue() {
    const notionInput = document.getElementById('notion-input');
    if (notionInput) {
        const text = notionInput.innerText.trim();
        return text;
    }
    const msgInput = document.getElementById('message-input');
    return msgInput ? msgInput.value.trim() : '';
}

function clearInput() {
    const notionInput = document.getElementById('notion-input');
    if (notionInput) {
        notionInput.innerHTML = '';
        return;
    }
    const msgInput = document.getElementById('message-input');
    if (msgInput) msgInput.value = '';
}

function setInputDisabled(disabled) {
    const notionInput = document.getElementById('notion-input');
    if (notionInput) {
        notionInput.contentEditable = disabled ? 'false' : 'true';
        notionInput.style.opacity = disabled ? '0.5' : '1';
        return;
    }
    const msgInput = document.getElementById('message-input');
    if (msgInput) msgInput.disabled = disabled;
}

function toggleLeftCol() {
    const col = document.getElementById('left-col');
    if (col) col.classList.toggle('show');
}

function toggleRightCol() {
    const col = document.getElementById('right-col');
    if (col) col.classList.toggle('show');
}

function toggleTheme() {
    const body = document.body;
    const openmaicOverlay = document.getElementById('openmaic-overlay');
    // 通过 body 是否有 course-mode 类来判断是否在课程生成页面
    const isCourseMode = body.classList.contains('course-mode');

    if (!isCourseMode) {
        // 不在课程生成页面：不做任何事，不影响智能对话页面
        return;
    }

    // 课程生成页面：只切换课程生成页面的主题
    const isLight = openmaicOverlay.classList.contains('light-theme');

    if (isLight) {
        openmaicOverlay.classList.remove('light-theme');
        openmaicOverlay.removeAttribute('data-theme');
        localStorage.setItem('openmaic_themeMode', 'dark');
    } else {
        openmaicOverlay.classList.add('light-theme');
        openmaicOverlay.setAttribute('data-theme', 'light');
        localStorage.setItem('openmaic_themeMode', 'light');
    }

    // 重新初始化 lucide 图标
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function initTheme() {
    const themeToggle = document.getElementById('theme-toggle-btn');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    // 注意：不再从 localStorage 恢复全局主题设置到 body
    // 全局主题（智能对话页面）保持默认，不受课程生成页面主题切换的影响

    // 从 localStorage 恢复课程生成页面的主题设置
    const savedOpenmaicMode = localStorage.getItem('openmaic_themeMode');
    const openmaicOverlay = document.getElementById('openmaic-overlay');
    if (savedOpenmaicMode === 'light' && openmaicOverlay) {
        openmaicOverlay.classList.add('light-theme');
    }
}

function updateAgentStatus(agentKey, status) {
    const item = document.querySelector(`.agent-status-item[data-agent="${agentKey}"]`);
    if (!item) return;
    const dot = item.querySelector('.agent-status-dot');
    const label = item.querySelector('.agent-status-label');
    if (!dot || !label) return;

    dot.className = 'agent-status-dot';
    if (status === 'active') {
        dot.classList.add('agent-dot-active');
        label.textContent = '运行中';
        label.className = 'agent-status-label active';
    } else if (status === 'idle') {
        dot.classList.add('agent-dot-idle');
        label.textContent = '待命';
        label.className = 'agent-status-label';
    } else if (status === 'warning') {
        dot.classList.add('agent-dot-warning');
        label.textContent = '等待';
        label.className = 'agent-status-label';
    } else if (status === 'error') {
        dot.classList.add('agent-dot-error');
        label.textContent = '异常';
        label.className = 'agent-status-label';
    }
}

function renderPathTree() {
    const container = document.getElementById('path-tree-container');
    if (!container) return;

    if (!currentPath || currentPath.length === 0) {
        container.innerHTML = '<div class="text-xs py-4 text-center" style="color: var(--text-tertiary);">暂无学习路径</div>';
        return;
    }

    // 计算总体进度
    const totalNodes = currentPath.length;
    const completedNodes = currentPath.filter(n => n.status === 'completed').length;
    const inProgressNodes = currentPath.filter(n => n.status === 'in_progress').length;
    const progressPercent = Math.round(((completedNodes + inProgressNodes * 0.5) / totalNodes) * 100);

    let html = `<div class="path-progress-header">
        <div class="path-progress-meta">
            <span class="path-progress-label">总体进度</span>
            <span class="path-progress-value">${progressPercent}%</span>
        </div>
        <div class="path-progress-bar-bg">
            <div class="path-progress-bar-fill" style="width: ${progressPercent}%;"></div>
        </div>
        <div class="path-progress-stats">
            <span class="path-stat-completed">${completedNodes} 已完成</span>
            <span class="path-stat-inprogress">${inProgressNodes} 进行中</span>
            <span class="path-stat-locked">${totalNodes - completedNodes - inProgressNodes} 待解锁</span>
        </div>
    </div>`;

    html += currentPath.map((node, idx) => {
        const status = node.status || 'locked';
        const dotClass = status === 'completed' ? 'completed' : status === 'in_progress' ? 'in-progress' : 'locked';
        const isImportant = node.importance === 'high' || node.importance === 'core';
        const hasChildren = node.children && node.children.length > 0;
        const time = node.estimated_time || node.estimatedMinutes || '';
        const displayName = node.topic || node.name || node.title || '学习任务';
        const isCompleted = status === 'completed';
        const isCurrent = status === 'in_progress';

        const nodeReason = node.description || node.reason || '';
        let html = `<div class="path-tree-node ${nodeReason ? '' : ''}" data-idx="${idx}" onclick="onPathNodeClick(${idx})" tabindex="0" role="treeitem" aria-label="${escapeHtml(displayName)}" ${nodeReason ? `data-reason="${escapeHtml(nodeReason)}"` : ''}>
            ${hasChildren ? '<i data-lucide="chevron-right" class="w-3 h-3 path-tree-toggle"></i>' : '<span class="w-3"></span>'}
            <div class="path-tree-node-dot ${dotClass} ${isCurrent ? 'pulse' : ''}"></div>
            <span class="path-tree-node-text">${escapeHtml(displayName)}</span>
            ${isCompleted ? '<i data-lucide="check" class="w-3 h-3" style="color: var(--success); margin-left: auto;"></i>' : ''}
            ${isImportant && !isCompleted ? '<span class="path-tree-badge important">核心</span>' : ''}
            ${time && !isCompleted ? `<span class="path-tree-time">${time}min</span>` : ''}
        </div>`;

        if (hasChildren) {
            html += `<div class="path-tree-children">`;
            for (const child of node.children) {
                const cStatus = child.status || 'locked';
                const cDotClass = cStatus === 'completed' ? 'completed' : cStatus === 'in_progress' ? 'in-progress' : 'locked';
                const childName = child.topic || child.name || child.title || '子节点';
                const cCompleted = cStatus === 'completed';
                html += `<div class="path-tree-node" tabindex="0" role="treeitem" aria-label="${escapeHtml(childName)}">
                    <span class="w-3"></span>
                    <div class="path-tree-node-dot ${cDotClass}"></div>
                    <span class="path-tree-node-text path-tree-child-text">${escapeHtml(childName)}</span>
                    ${cCompleted ? '<i data-lucide="check" class="w-3 h-3" style="color: var(--success); margin-left: auto;"></i>' : ''}
                </div>`;
            }
            html += '</div>';
        }
        return html;
    }).join('');

    container.innerHTML = html;
    if (window.lucide) lucide.createIcons();
}

function onPathNodeClick(idx) {
    const node = currentPath[idx];
    if (!node) return;

    // Toggle children expansion
    const toggle = document.querySelector(`.path-tree-node[data-idx="${idx}"] .path-tree-toggle`);
    if (toggle) {
        toggle.classList.toggle('expanded');
        const children = document.querySelector(`.path-tree-node[data-idx="${idx}"] + .path-tree-children`);
        if (children) children.style.display = children.style.display === 'none' ? '' : 'none';
        return;
    }

    // Show node detail panel
    showPathNodeDetail(idx);
}

function showPathNodeDetail(idx) {
    const node = currentPath[idx];
    if (!node) return;

    // 关闭已有的详情面板
    const existing = document.getElementById('path-node-detail');
    if (existing) existing.remove();

    const displayName = node.topic || node.name || node.title || '学习任务';
    const description = node.description || '暂无描述';
    const prerequisites = node.prerequisites || [];
    const time = node.estimated_time || node.estimatedMinutes || '';
    const status = node.status || 'locked';
    const isCompleted = status === 'completed';
    const isInProgress = status === 'in_progress';
    const isLocked = status === 'locked';
    const canComplete = isInProgress || isLocked;
    const totalNodes = currentPath.length;
    const nodePosition = idx + 1;

    // 状态标签映射
    const statusConfig = {
        completed: { label: '已完成', colorClass: 'path-status-completed', icon: '✓' },
        in_progress: { label: '进行中', colorClass: 'path-status-inprogress', icon: '▶' },
        locked: { label: '待解锁', colorClass: 'path-status-locked', icon: '🔒' }
    };
    const cfg = statusConfig[status] || statusConfig.locked;

    // 构建子节点预览HTML
    let childrenPreview = '';
    if (node.children && node.children.length > 0) {
        const childItems = node.children.map(child => {
            const childName = child.topic || child.name || child.title || '子任务';
            const childStatus = child.status || 'locked';
            const childDone = childStatus === 'completed';
            return `<div class="path-detail-child-item">
                <div class="path-detail-child-dot ${childDone ? 'completed' : 'pending'}"></div>
                <span class="path-detail-child-name ${childDone ? 'done' : ''}">${escapeHtml(childName)}</span>
            </div>`;
        }).join('');
        childrenPreview = `
            <div class="path-detail-section">
                <div class="path-detail-section-title">子任务 (${node.children.length})</div>
                <div class="path-detail-children-list">${childItems}</div>
            </div>`;
    }

    const panel = document.createElement('div');
    panel.id = 'path-node-detail';
    panel.className = 'path-node-detail-panel';
    panel.innerHTML = `
        <div class="path-detail-header">
            <div class="path-detail-title-row">
                <span class="path-detail-name">${escapeHtml(displayName)}</span>
                <button onclick="this.closest('.path-node-detail-panel').remove()" class="path-detail-close" title="关闭">✕</button>
            </div>
            <div class="path-detail-meta-row">
                <span class="path-detail-status ${cfg.colorClass}">${cfg.icon} ${cfg.label}</span>
                <span class="path-detail-position">${nodePosition} / ${totalNodes}</span>
            </div>
        </div>

        <div class="path-detail-body">
            <div class="path-detail-desc">${escapeHtml(description)}</div>

            ${prerequisites.length ? `
            <div class="path-detail-section">
                <div class="path-detail-section-title">前置知识</div>
                <div class="path-detail-prereqs">
                    ${prerequisites.map(p => `<span class="path-detail-prereq-tag">${escapeHtml(p)}</span>`).join('')}
                </div>
            </div>` : ''}

            <div class="path-detail-info-row">
                ${time ? `<div class="path-detail-info-item"><span class="path-detail-info-label">⏱ 预计时长</span><span class="path-detail-info-value">${time} min</span></div>` : ''}
                ${node.importance ? `<div class="path-detail-info-item"><span class="path-detail-info-label">⭐ 重要程度</span><span class="path-detail-info-value">${node.importance === 'core' || node.importance === 'high' ? '核心节点' : '普通节点'}</span></div>` : ''}
            </div>

            ${childrenPreview}
        </div>

        <div class="path-detail-actions">
            ${isLocked ? `
                <button onclick="startPathNodeStudy(${idx});" class="path-detail-btn path-detail-btn-primary">
                    <span>🔓 解锁学习</span>
                </button>
            ` : `
                <button onclick="startPathNodeStudy(${idx});" class="path-detail-btn path-detail-btn-primary">
                    <span>${isCompleted ? '🔁 再次学习' : '▶ 开始学习'}</span>
                </button>
            `}
            ${canComplete ? `
                <button onclick="markPathNodeComplete(${idx}); document.getElementById('path-node-detail')?.remove();" class="path-detail-btn path-detail-btn-success">
                    <span>✓ 标记完成</span>
                </button>
            ` : ''}
        </div>
    `;

    // 插入到被点击的节点下方
    const targetNode = document.querySelector(`.path-tree-node[data-idx="${idx}"]`);
    if (targetNode) {
        targetNode.insertAdjacentElement('afterend', panel);
    } else {
        const treeContainer = document.getElementById('path-tree-container');
        if (treeContainer) treeContainer.appendChild(panel);
    }
}

function startPathNodeStudy(idx) {
    const node = currentPath[idx];
    if (!node) return;
    const displayName = node.topic || node.name || node.title || '学习任务';

    // 如果节点被锁定，先解锁
    if (node.status === 'locked') {
        node.status = 'in_progress';
        renderPathTree();
        renderPath();
        saveProgress();
    }

    // 关闭详情面板
    const panel = document.getElementById('path-node-detail');
    if (panel) panel.remove();

    // 将学习主题填入输入框并聚焦
    const notionInput = document.getElementById('notion-input');
    const msgInput = document.getElementById('message-input');
    const studyPrompt = `我想学习「${displayName}」，请帮我详细讲解一下这个知识点`;
    if (notionInput) {
        notionInput.innerText = studyPrompt;
        notionInput.focus();
    } else if (msgInput) {
        msgInput.value = studyPrompt;
        msgInput.focus();
    }
}

function markPathNodeComplete(idx) {
    if (!currentPath[idx]) return;
    currentPath[idx].status = 'completed';
    renderPathTree();
    renderPath();
    saveProgress();
    // 节点完成后触发学习路径刷新
    schedulePathRefresh('node_complete');
}

async function handleSendStream(forcedMessage = null, options = {}) {
    const sendButton = document.getElementById('send-btn');
    const userMsg = forcedMessage || getInputValue();
    if (!userMsg) return;

    setDispatchActive(true);

    // 检测辩论模式
    if (isDebateModeEnabled()) {
        return handleDebateStream(userMsg);
    }

    ensureCurrentPathValid();
    clearInput();
    setInputDisabled(true);
    if (sendButton) sendButton.disabled = true;

    // 本地实时更新评估指标
    evaluation.interactionCount = (evaluation.interactionCount || 0) + 1;
    evaluation.focusTimeToday = (evaluation.focusTimeToday || 0) + 1;
    const today = new Date().toISOString().slice(0, 10);
    if (!evaluation.lastStudyDate || evaluation.lastStudyDate !== today) {
        const last = evaluation.lastStudyDate ? new Date(evaluation.lastStudyDate) : null;
        const now = new Date();
        if (last) {
            const diffDays = Math.floor((now - last) / (1000 * 60 * 60 * 24));
            if (diffDays === 1) {
                evaluation.streakDays = (evaluation.streakDays || 0) + 1;
            } else if (diffDays > 1) {
                evaluation.streakDays = 1;
            }
        } else {
            evaluation.streakDays = 1;
        }
        evaluation.lastStudyDate = today;
    }
    // 更新今日交互历史
    if (!Array.isArray(evaluation.interactionHistory)) {
        evaluation.interactionHistory = [];
    }
    const lastEntry = evaluation.interactionHistory[evaluation.interactionHistory.length - 1];
    if (lastEntry && lastEntry.date === today) {
        lastEntry.count = evaluation.interactionCount;
    } else {
        evaluation.interactionHistory.push({ date: today, count: evaluation.interactionCount });
        if (evaluation.interactionHistory.length > 7) {
            evaluation.interactionHistory.shift();
        }
    }
    renderEvaluation();
    queueEvaluationSave();
    await saveProgress();

    messages.push({ role: 'user', content: userMsg });
    renderMessages();

    sandboxLogs = [];
    activeAgents = new Set();
    sandboxFilterSet = new Set();
    currentThinkingLogs = [];
    const sandboxLogsEl = document.getElementById('sandbox-logs');
    if (sandboxLogsEl) sandboxLogsEl.innerHTML = '';
    renderFlowNodes();
    renderFilterChips();
    updateSandboxStatus('调度中', 'bg-amber-100 text-amber-600');

    currentAssistantContent = '';
    messages.push({ role: 'assistant', content: '', socratic: false, _persona: currentPersona, _agentId: currentAgent.id, _agentName: currentAgent.name, _timestamp: Date.now() });
    currentAssistantIdx = messages.length - 1;

    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
        const streamDiv = document.createElement('div');
        streamDiv.className = 'msg-row flex justify-start stream-bubble';
        chatContainer.appendChild(streamDiv);
    }

    if (typewriterTimer) {
        clearTimeout(typewriterTimer);
        typewriterTimer = null;
    }
    typewriterQueue = [];
    isTypewriting = false;

    streamAbortController = new AbortController();

    try {
        const res = await fetch(STREAM_API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: String(currentUser?.id || 'anonymous'),
                course_id: 'bigdata',
                user_input: userMsg,
                force_socratic: options.forceSocratic || false,
                context_id: '',
                current_profile: profile,
                current_path: currentPath,
                interaction_count: evaluation.interactionCount || 0,
                code_practice_time: evaluation.codePracticeTime || 0,
                socratic_pass_rate: evaluation.socraticPassRate || 0,
                system_prompt: getAgentSystemPrompt(),
                persona: currentPersona,
                agent: currentAgent.id,
                agent_system_prompt: currentAgent.systemPrompt,
                session_id: getChatSessionId()
            }),
            signal: streamAbortController.signal
        });

        if (!res.ok) {
            const errText = await res.text();
            let errMsg = `请求失败（HTTP ${res.status}）`;
            try {
                const errData = JSON.parse(errText);
                errMsg = formatApiErrorDetail(errData.detail) || errMsg;
            } catch {}
            throw new Error(errMsg);
        }

        updateSandboxStatus('运行中', 'bg-emerald-100 text-emerald-600');

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let renderThrottleTimer = null;
        let pendingRender = false;

        function throttledRender() {
            if (pendingRender) return;
            pendingRender = true;
            requestAnimationFrame(() => {
                renderStreamingMessage();
                pendingRender = false;
            });
        }

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith(': ')) continue;
                if (!line.startsWith('data: ')) continue;
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;

                let event;
                try {
                    event = JSON.parse(jsonStr);
                } catch {
                    continue;
                }

                if (event.type === 'memory_retrieval_logs') {
                    const memLogs = event.logs || [];
                    memLogs.forEach(log => {
                        const logEntry = {
                            agent: 'memory_retrieval',
                            content: `${log.type_label || '记忆'} · 置信度 ${Math.round((log.confidence || 0) * 100)}%`,
                            timestamp: Date.now()
                        };
                        currentThinkingLogs.push(logEntry);
                    });
                    // 如果正在流式渲染，刷新 thinking strip
                    if (currentAssistantIdx >= 0) {
                        renderStreamingMessage();
                    }
                } else if (event.type === 'agent_log') {
                    const logEntry = {
                        agent: event.agent || 'unknown',
                        content: event.content || '',
                        timestamp: Date.now()
                    };
                    sandboxLogs.push(logEntry);
                    activeAgents.add(logEntry.agent);
                    updateAgentStatus(logEntry.agent, 'active');
                    renderSandboxLog(logEntry, false);
                    renderFlowNodes();
                    renderFilterChips();
                    // 收集到当前消息的 thinking logs
                    currentThinkingLogs.push(logEntry);

                    // 记忆助手发现新特征时，触发面板实时提示
                    if (event.agent === 'memory' && event.content &&
                        (event.content.includes('发现新特征') || event.content.includes('已记住'))) {
                        showMemoryJustRemembered();
                        loadUserMemories();
                        loadUserProfile();
                    }
                } else if (event.type === 'content_chunk') {
                    console.log('[SSE] content_chunk received:', event.content?.substring(0, 50), '...');
                    startTypewriter(event.content || '');
                } else if (event.type === 'done') {
                    console.log('[SSE] done event, full_text length:', event.full_text?.length, 'currentAssistantContent length:', currentAssistantContent.length);
                    // 合并队列中剩余的内容，避免打字机队列被清空导致内容丢失
                    const remainingText = typewriterQueue.join('');
                    if (remainingText) {
                        currentAssistantContent += remainingText;
                    }
                    typewriterQueue = [];
                    isTypewriting = false;
                    currentAssistantContent = event.full_text || currentAssistantContent;
                    if (typewriterTimer) {
                        clearTimeout(typewriterTimer);
                        typewriterTimer = null;
                    }
                    // Immediately update messages content and re-render to ensure content is displayed
                    if (currentAssistantIdx >= 0 && currentAssistantIdx < messages.length) {
                        messages[currentAssistantIdx].content = currentAssistantContent;
                        if (currentThinkingLogs.length > 0) {
                            messages[currentAssistantIdx]._thinkingLogs = [...currentThinkingLogs];
                        }
                    }
                    // 支持被动回答中的链接（后端在 done 事件中发送）
                    if (event.links && event.links.length > 0 && currentAssistantIdx >= 0) {
                        messages[currentAssistantIdx]._links = event.links;
                        messages[currentAssistantIdx]._agentId = window.currentAgent?.id || currentAgent?.id || 'default';
                    }
                    // 存储记忆引用到消息对象
                    if (event.memory_refs && event.memory_refs.length > 0 && currentAssistantIdx >= 0) {
                        messages[currentAssistantIdx]._memoryRefs = event.memory_refs;
                    }
                    // Remove stream-bubble and re-render all messages to show final content
                    const container = document.getElementById('chat-container');
                    if (container) {
                        const streamBubble = container.querySelector('.stream-bubble');
                        if (streamBubble) streamBubble.remove();
                        renderMessages();
                    }
                } else if (event.type === 'complete') {
                    // 合并队列中剩余的内容，避免打字机队列被清空导致内容丢失
                    const remainingText = typewriterQueue.join('');
                    if (remainingText) {
                        currentAssistantContent += remainingText;
                        if (currentAssistantIdx >= 0 && currentAssistantIdx < messages.length) {
                            messages[currentAssistantIdx].content = currentAssistantContent;
                        }
                    }
                    if (typewriterTimer) {
                        clearTimeout(typewriterTimer);
                        typewriterTimer = null;
                    }
                    typewriterQueue = [];
                    isTypewriting = false;

                    const data = event.data;
                    if (data.newProfile) {
                        profile = { ...profile, ...data.newProfile };
                        if (profile.cognitiveLevel) {
                            updateEvaluation({ difficultyLevel: profile.cognitiveLevel });
                        }
                    }
                    renderProfile();
                    renderRadarChart();

                    if (data.newPath) {
                        currentPath = normalizeLearningPath(data.newPath);
                        renderPath();
                    }

                    if (data.evaluation) {
                        updateEvaluation(data.evaluation);
                    }

                    if (data.dispatchStrategy) {
                        updateDispatchBadge(data.dispatchStrategy);
                        setDispatchActive(true);
                        if (currentAssistantIdx >= 0) {
                            messages[currentAssistantIdx].socratic = data.dispatchStrategy === 'socratic';
                        }
                    }

                    if (data.socraticCheckpoint && currentAssistantIdx >= 0) {
                        messages[currentAssistantIdx]._socraticCheckpoint = true;
                        messages[currentAssistantIdx]._checkpointTopic = data.checkpointTopic || '';
                    }

                    if (data.sources) {
                        renderSources(data.sources);
                    }

                    if (data.sourceLinks) {
                        updateSourceLinks(data.sourceLinks);
                        if (data.sources) renderSources(data.sources);
                    }

                    // resource dashboard removed

                    // 保存后端返回的会话ID
                    if (data.sessionId) {
                        localStorage.setItem('starlearn_chat_session_id', data.sessionId);
                    }

                    // 聊天结束后触发记忆刷新
                    if (data.triggerMemoryRefresh) {
                        setTimeout(() => loadUserMemories(), 500);
                    }

                    if (currentAssistantIdx >= 0) {
                        messages[currentAssistantIdx].content = currentAssistantContent;
                        if (currentThinkingLogs.length > 0) {
                            messages[currentAssistantIdx]._thinkingLogs = [...currentThinkingLogs];
                        }
                        // 支持被动回答中的链接（后端在 complete 事件中发送）
                        if (data.links && data.links.length > 0) {
                            messages[currentAssistantIdx]._links = data.links;
                            messages[currentAssistantIdx]._agentId = window.currentAgent?.id || currentAgent?.id || 'default';
                        }
                        // 支持被动回答中的快捷操作
                        if (data.actions && data.actions.length > 0) {
                            messages[currentAssistantIdx]._actions = data.actions;
                        }
                    }

                    if (isProgrammingTask(currentAssistantContent)) {
                        autoFillTask(currentAssistantContent);
                    }

                    updateSandboxStatus('完成', 'bg-green-100 text-green-600');
                    document.querySelectorAll('.agent-status-item').forEach(item => {
                        const dot = item.querySelector('.agent-status-dot');
                        const label = item.querySelector('.agent-status-label');
                        if (dot) dot.className = 'agent-status-dot agent-dot-idle';
                        if (label) { label.textContent = '待命'; label.className = 'agent-status-label'; }
});
                    renderMessages();

                    // 更新学生画像
                    StarData.updatePortrait('index', {
                        user_input: userMsg,
                        response_length: currentAssistantContent.length,
                        agents: Array.from(activeAgents)
                    });
                    await saveProgress();
                } else if (event.type === 'error') {
                    const logEntry = {
                        agent: 'error',
                        content: event.message || '未知错误',
                        timestamp: Date.now()
                    };
                    sandboxLogs.push(logEntry);
                    renderSandboxLog(logEntry, false);
                    updateSandboxStatus('错误', 'bg-red-100 text-red-600');

                    if (!currentAssistantContent) {
                        if (currentAssistantIdx >= 0) {
                            messages[currentAssistantIdx].content = `抱歉，智能体处理失败：${event.message || '未知错误'}。请稍后重试。`;
                        }
                        renderMessages();
                    }
                }
            }
        }
    } catch (error) {
        if (error.name === 'AbortError') return;
        const errMsg = error instanceof Error ? error.message : String(error);
        console.error('[Stream] Request failed:', errMsg);
        const logEntry = {
            agent: 'error',
            content: errMsg,
            timestamp: Date.now()
        };
        sandboxLogs.push(logEntry);
        renderSandboxLog(logEntry, false);
        updateSandboxStatus('错误', 'bg-red-100 text-red-600');

        let userMsg = '抱歉，请求失败。';
        if (errMsg.includes('Failed to fetch') || errMsg.includes('NetworkError')) {
            userMsg = '无法连接到服务器，请确认后端服务已启动（python main.py）。';
        } else if (errMsg.includes('HTTP 404')) {
            userMsg = 'API接口未找到(404)，请确认后端服务版本正确。';
        } else if (errMsg.includes('HTTP 5')) {
            userMsg = `服务器内部错误：${errMsg}。请稍后重试。`;
        } else {
            userMsg = `请求失败：${errMsg}。请稍后重试。`;
        }

        if (!currentAssistantContent) {
            if (currentAssistantIdx >= 0) {
                messages[currentAssistantIdx].content = userMsg;
            }
            renderMessages();
        }
    } finally {
        setInputDisabled(false);
        if (sendButton) sendButton.disabled = false;
        const notionInput = document.getElementById('notion-input');
        if (notionInput) notionInput.focus();
        else { const mi = document.getElementById('message-input'); if (mi) mi.focus(); }
        streamAbortController = null;
        setDispatchActive(false);
        // 聊天结束后触发学习路径刷新
        schedulePathRefresh('chat');
    }
}

async function handleSend() {
    const sendButton = document.getElementById('send-btn');
    const userMsg = getInputValue();
    if (!userMsg) return;

    ensureCurrentPathValid();
    clearInput();
    setInputDisabled(true);
    if (sendButton) sendButton.disabled = true;
    
    messages.push({ role: 'user', content: userMsg });
    renderMessages();

    const langNeed = detectLanguageNeed(userMsg);

    const wfPanel = null;
    const wfLogs = null;
    sandboxLogs = [];
    activeAgents = new Set();
    const sandboxLogsEl = document.getElementById('sandbox-logs');
    if (sandboxLogsEl) sandboxLogsEl.innerHTML = '';
    updateSandboxStatus('处理中', 'bg-amber-100 text-amber-600');
    setDispatchActive(true);

    try {
        const res = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                userText: userMsg,
                currentProfile: profile,
                currentPath: currentPath,
                interactionCount: evaluation.interactionCount,
                codePracticeTime: evaluation.codePracticeTime,
                socraticPassRate: evaluation.socraticPassRate,
                sessionId: getChatSessionId(),
                userId: currentUser?.id || 0
            })
        });

        const rawText = await res.text();
        let data = {};
        if (rawText) {
            try {
                data = JSON.parse(rawText);
            } catch {
                throw new Error(`服务器返回非 JSON（HTTP ${res.status}）：${rawText.slice(0, 240)}`);
            }
        }
        if (!res.ok) {
            const msg = formatApiErrorDetail(data.detail) || `请求失败（HTTP ${res.status}）`;
            throw new Error(msg);
        }

        const logs = Array.isArray(data.logs) ? data.logs : [];

        const applyChatResponse = async () => {
            // 保存后端返回的会话ID
            if (data.sessionId) {
                localStorage.setItem('starlearn_chat_session_id', data.sessionId);
            }

            if (data.newProfile && typeof data.newProfile === 'object') {
                profile = { ...profile, ...data.newProfile };
                if (profile.cognitiveLevel) {
                    updateEvaluation({ difficultyLevel: profile.cognitiveLevel });
                }
            }
            renderProfile();
            renderRadarChart();

            if (data.newPath != null) {
                currentPath = normalizeLearningPath(data.newPath);
                renderPath();
            }

            if (data.evaluation) {
                updateEvaluation(data.evaluation);
            }

            if (data.dispatchStrategy) {
                updateDispatchBadge(data.dispatchStrategy);
                setDispatchActive(true);
            }

            renderSources(data.sources || []);

            if (data.sourceLinks) {
                updateSourceLinks(data.sourceLinks);
                renderSources(data.sources || []);
            }

            const isSocratic = data.dispatchStrategy === 'socratic';
            messages.push({ role: 'assistant', content: data.content, socratic: isSocratic });
            renderMessages();

            if (isProgrammingTask(data.content)) {
                autoFillTask(data.content);
            }

            if (langNeed) {
                setTimeout(() => {
                    const langSelect = document.getElementById('lang-select');
                    if (langSelect) {
                        langSelect.value = langNeed;
                        changeLanguage();
                        if (!isProgrammingTask(data.content)) {
                            switchTab('code');
                        }
                    }
                }, 800);
            }

            setInputDisabled(false);
            if (sendButton) sendButton.disabled = false;
            msgInput.focus();

            await saveProgress();
            setDispatchActive(false);
        };

        if (logs.length === 0) {
            await applyChatResponse();
        } else {
            for (let i = 0; i < logs.length; i++) {
                const logText = logs[i];
                const agentMatch = logText.match(/^\[([^\]]+)\]/);
                const agentName = agentMatch ? agentMatch[1].toLowerCase().replace(/\s+/g, '_') : 'system';
                const logEntry = { agent: agentName, content: logText, timestamp: Date.now() };
                sandboxLogs.push(logEntry);
                activeAgents.add(agentName);
            }
            renderAllSandboxLogs();
            renderFlowNodes();
            renderFilterChips();
            updateSandboxStatus('完成', 'bg-green-100 text-green-600');
            setTimeout(applyChatResponse, 500);
        }
    } catch (error) {
        const text = error instanceof Error
            ? (typeof error.message === 'string' ? error.message : formatApiErrorDetail(error.message))
            : formatApiErrorDetail(error) || String(error);
        const logEntry = { agent: 'error', content: text, timestamp: Date.now() };
        sandboxLogs.push(logEntry);
        renderSandboxLog(logEntry, false);
        updateSandboxStatus('错误', 'bg-red-100 text-red-600');
        setInputDisabled(false);
        if (sendButton) sendButton.disabled = false;
        setDispatchActive(false);
    } finally {
        schedulePathRefresh('chat');
    }
}

function updateEvaluation(newEval) {
    const prevCount = evaluation.interactionCount || 0;
    evaluation = { ...evaluation, ...newEval };

    // 确保 interactionHistory 是数组
    if (!Array.isArray(evaluation.interactionHistory)) {
        evaluation.interactionHistory = [];
    }

    const today = new Date().toISOString().slice(0, 10);
    const countIncreased = (evaluation.interactionCount || 0) > prevCount;

    // 只有当交互次数增加时才更新 history 和 streak
    if (countIncreased) {
        const lastEntry = evaluation.interactionHistory[evaluation.interactionHistory.length - 1];
        if (lastEntry && lastEntry.date === today) {
            lastEntry.count = evaluation.interactionCount || 0;
        } else {
            evaluation.interactionHistory.push({ date: today, count: evaluation.interactionCount || 0 });
            if (evaluation.interactionHistory.length > 7) {
                evaluation.interactionHistory.shift();
            }
        }

        // 更新 streak
        const lastDate = evaluation.lastStudyDate;
        if (lastDate) {
            const last = new Date(lastDate);
            const now = new Date();
            const diffDays = Math.floor((now - last) / (1000 * 60 * 60 * 24));
            if (diffDays === 1) {
                evaluation.streakDays = (evaluation.streakDays || 0) + 1;
            } else if (diffDays > 1) {
                evaluation.streakDays = 1;
            }
        } else {
            evaluation.streakDays = 1;
        }
        evaluation.lastStudyDate = today;
    }

    renderEvaluation();
    queueEvaluationSave();
}

async function saveProgress() {
    if (!currentUser || !currentUser.id) return;
    ensureCurrentPathValid();
    try {
        const body = {
            userId: parseInt(currentUser.id),
            evaluation: evaluation,
            currentPath: currentPath,
            profile: profile
        };
        if (lastGradeRecord) {
            body.lastGradeRecord = lastGradeRecord;
        }
        const res = await fetch(SAVE_PROGRESS_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const errData = await res.json();
            console.warn('保存进度失败:', res.status, errData);
        }
    } catch (error) {
        console.warn('保存进度失败:', error);
    }
}

function startCodePracticeTimer() {
    if (codePracticeStartTime === null) {
        codePracticeStartTime = Date.now();
        codePracticeTimer = setInterval(() => {
            const elapsed = Math.floor((Date.now() - codePracticeStartTime) / 1000);
            evaluation.codePracticeTime = Math.floor(elapsed / 60);
            renderEvaluation();
        }, 1000);
    }
}

async function stopCodePracticeTimer() {
    if (codePracticeTimer) {
        clearInterval(codePracticeTimer);
        codePracticeTimer = null;
    }
    if (codePracticeStartTime !== null) {
        const elapsed = Math.floor((Date.now() - codePracticeStartTime) / 1000);
        evaluation.codePracticeTime = Math.floor(elapsed / 60);
        codePracticeStartTime = null;
        renderEvaluation();
        queueEvaluationSave();
        await saveProgress();
    }
}

function updateAvatar(newAvatar) {
    currentUser.avatar = newAvatar;
    localStorage.setItem('starlearn_user', JSON.stringify(currentUser));
    updateUserUI();
    if (currentUser.id) {
        fetch(`${API_BASE}/api/user/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: currentUser.username,
                avatar: newAvatar
            })
        });
    }
}

function updateNickname(newNickname) {
    currentUser.name = newNickname;
    localStorage.setItem('starlearn_user', JSON.stringify(currentUser));
    updateUserUI();
    if (currentUser.id) {
        fetch(`${API_BASE}/api/user/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: currentUser.username,
                nickname: newNickname
            })
        });
    }
}

function showNicknameInput() {
    document.getElementById('avatar-dropdown').classList.remove('show');
    const modal = document.getElementById('nickname-modal');
    const input = document.getElementById('nickname-input');
    if (modal && input) {
        input.value = currentUser.name || '';
        modal.classList.remove('hidden');
    }
}

function hideNicknameInput() {
    const modal = document.getElementById('nickname-modal');
    if (modal) modal.classList.add('hidden');
}

function confirmNicknameChange() {
    const input = document.getElementById('nickname-input');
    if (!input) return;
    const newNickname = input.value.trim();
    if (!newNickname) {
        alert('请输入昵称');
        return;
    }
    if (newNickname.length > 20) {
        alert('昵称长度不能超过20个字符');
        return;
    }
    updateNickname(newNickname);
    hideNicknameInput();
}

async function loadProgress() {
    if (!currentUser || !currentUser.id) return;
    try {
        const res = await fetch(LOAD_PROGRESS_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: parseInt(currentUser.id) })
        });
        const data = await res.json();
        if (data.success) {
            if (data.profile) {
                let incoming = data.profile;
                if (isRawAssessmentProfile(incoming)) {
                    const mapped = initProfileFromAssessment(incoming);
                    if (mapped) incoming = mapped;
                }
                profile = { ...profile, ...incoming };
            }
            if (data.evaluation) {
                evaluation = { ...evaluation, ...data.evaluation };
            }
            // 从 profile.cognitiveLevel 派生 difficultyLevel
            if (profile && profile.cognitiveLevel) {
                evaluation.difficultyLevel = profile.cognitiveLevel;
            }
            if (data.currentPath != null) {
                const loaded = normalizeLearningPath(data.currentPath);
                if (loaded.length > 0) currentPath = loaded;
            }
            if (data.lastGradeRecord) {
                lastGradeRecord = data.lastGradeRecord;
            }
            renderProfile();
            renderRadarChart();
            renderEvaluation();
            renderPath();
        }
    } catch (error) {
        console.warn('加载进度失败:', error);
    }
    // 从专用评估指标端点拉取最新数据（覆盖可能更实时）
    try {
        await loadEvaluationFromServer();
    } catch (e) {
        console.warn('加载评估指标失败:', e);
    }
}

// ============================================================
// 学习路径实时生成与更新
// ============================================================

let _pathRefreshDebounceTimer = null;
let _pathLastRefreshedAt = 0;

async function initLearningPath() {
    // 页面加载时初始化学习路径：先尝试从 API 获取，失败则回退到本地缓存。
    const user = currentUser;
    if (!user || !user.id) {
        renderPathTree();
        return;
    }

    // 先显示本地缓存（如果有）
    const cached = localStorage.getItem(`starlearn_path_${user.id}`);
    if (cached) {
        try {
            const data = JSON.parse(cached);
            if (data.path && data.path.length > 0) {
                currentPath = normalizeLearningPath(data.path);
                renderPathTree();
                updatePathLastUpdated(data.generated_at);
            }
        } catch (e) { /* ignore */ }
    }

    // 异步拉取最新路径
    try {
        const fresh = await fetchLearningPath(user.id);
        if (fresh && fresh.path && fresh.path.length > 0) {
            const oldPathJson = JSON.stringify(currentPath);
            const newPathJson = JSON.stringify(fresh.path);
            currentPath = normalizeLearningPath(fresh.path);
            renderPathTree();
            updatePathLastUpdated(fresh.generated_at);
            localStorage.setItem(`starlearn_path_${user.id}`, JSON.stringify(fresh));
            if (oldPathJson !== newPathJson) {
                showToast(`学习路径已更新：${fresh.reasoning || '基于最新学情'}`, 'info');
            }
        }
    } catch (e) {
        console.warn('[LearningPath] 初始化拉取失败:', e);
    }
}

async function fetchLearningPath(userId) {
    // 从后端获取当前学习路径（不触发 LLM 生成）。
    try {
        const res = await fetch(`${LEARNING_PATH_CURRENT_URL}/${userId}`);
        if (!res.ok) return null;
        return await res.json();
    } catch (e) {
        console.warn('[LearningPath] 获取当前路径失败:', e);
        return null;
    }
}

async function refreshLearningPath(force = false) {
    // 刷新学习路径（带防抖）。force=true 时跳过缓存。
    const user = currentUser;
    if (!user || !user.id) return;

    const now = Date.now();
    if (!force && now - _pathLastRefreshedAt < 30000) {  // 30秒防抖
        console.log('[LearningPath] 刷新过于频繁，跳过');
        return;
    }
    _pathLastRefreshedAt = now;

    // 显示加载状态
    const loadingEl = document.getElementById('path-tree-loading');
    const refreshBtn = document.getElementById('path-refresh-btn');
    if (loadingEl) loadingEl.classList.remove('hidden');
    if (refreshBtn) refreshBtn.classList.add('spinning');

    try {
        const res = await fetch(LEARNING_PATH_GENERATE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: parseInt(user.id), forceRefresh: force })
        });
        if (!res.ok) {
            console.warn('[LearningPath] 刷新失败:', res.status);
            return;
        }
        const data = await res.json();
        if (data.success && data.path && data.path.length > 0) {
            const oldPathJson = JSON.stringify(currentPath);
            const newPathJson = JSON.stringify(data.path);
            currentPath = normalizeLearningPath(data.path);
            renderPathTree();
            updatePathLastUpdated(data.generated_at);
            localStorage.setItem(`starlearn_path_${user.id}`, JSON.stringify(data));
            if (oldPathJson !== newPathJson) {
                showToast(`路径已更新：${data.reasoning || '基于最新学情'}`, 'info');
            }
        }
    } catch (e) {
        console.warn('[LearningPath] 刷新异常:', e);
    } finally {
        if (loadingEl) loadingEl.classList.add('hidden');
        if (refreshBtn) refreshBtn.classList.remove('spinning');
    }
}

function updatePathLastUpdated(isoString) {
    // 更新路径面板顶部的'最后更新'文本。
    const el = document.getElementById('path-last-updated');
    if (!el || !isoString) return;
    try {
        const date = new Date(isoString);
        const diffMin = Math.floor((Date.now() - date.getTime()) / 60000);
        if (diffMin < 1) el.textContent = '刚刚更新';
        else if (diffMin < 60) el.textContent = `${diffMin}分钟前更新`;
        else el.textContent = `${Math.floor(diffMin / 60)}小时前更新`;
    } catch (e) {
        el.textContent = '已更新';
    }
}

// 在关键学习事件后自动刷新路径（防抖）
function schedulePathRefresh(source = 'event') {
    if (_pathRefreshDebounceTimer) clearTimeout(_pathRefreshDebounceTimer);
    _pathRefreshDebounceTimer = setTimeout(() => {
        refreshLearningPath(false);
    }, 2000);  // 延迟2秒，等待数据保存完成
}

document.addEventListener('DOMContentLoaded', async function() {
    initTheme();
    
    // 初始默认使用"默认"身份，不读取 localStorage 中保存的历史身份
    currentAgent = AGENTS_CONFIG[0];
    renderAgentFab();

    // 初始化 persona chip 状态
    const personaBar = document.getElementById('persona-chip-bar');
    const personaTooltip = document.getElementById('persona-tooltip');
    if (personaBar) {
        personaBar.querySelectorAll('.persona-chip').forEach(chip => {
            chip.classList.toggle('active', chip.dataset.persona === currentPersona);
            chip.addEventListener('click', () => {
                currentPersona = chip.dataset.persona;
                localStorage.setItem('starlearn_persona', currentPersona);
                personaBar.querySelectorAll('.persona-chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
            });

            // Tooltip handlers
            if (personaTooltip) {
                chip.addEventListener('mouseenter', () => {
                    personaTooltip.textContent = chip.dataset.desc;
                    personaTooltip.classList.add('show');
                    const rect = chip.getBoundingClientRect();
                    const ttRect = personaTooltip.getBoundingClientRect();
                    let left = rect.left + rect.width / 2 - ttRect.width / 2;
                    let top = rect.top - ttRect.height - 8;
                    left = Math.max(8, Math.min(left, window.innerWidth - ttRect.width - 8));
                    top = Math.max(8, top);
                    personaTooltip.style.left = left + 'px';
                    personaTooltip.style.top = top + 'px';
                });
                chip.addEventListener('mouseleave', () => {
                    personaTooltip.classList.remove('show');
                });
            }
        });
    }

    // 初始化学科领域下拉菜单
    console.log('[SubjectDropdown] Initializing dropdown...');
    initSubjectDropdown();
    console.log('[SubjectDropdown] Dropdown initialized');

    const notionInput = document.getElementById('notion-input');
    const msgInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-btn');

    if (notionInput) {
        // 强制固定宽度
        const lockWidth = () => {
            notionInput.style.width = '100%';
            notionInput.style.minWidth = '100%';
            notionInput.style.maxWidth = '100%';
            notionInput.style.flex = 'none';
        };
        lockWidth();

        // 监听样式变化并强制恢复
        const observer = new MutationObserver(() => lockWidth());
        observer.observe(notionInput, { attributes: true, attributeFilter: ['style'] });

        notionInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendStream();
            }
        });
        notionInput.addEventListener('input', function() {
            lockWidth();
        });
    } else if (msgInput) {
        msgInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') handleSendStream();
        });
    }
    if (sendButton) {
        sendButton.addEventListener('click', () => handleSendStream());
    }

    const savedTheme = localStorage.getItem('starlearn_theme') || 'ocean';
    setTheme(savedTheme);
    DynamicThemeManager.init();

    const savedUser = JSON.parse(localStorage.getItem('starlearn_user') || 'null');
    if (savedUser) {
        currentUser = savedUser;

        // 从评估数据初始化画像
        if (savedUser.assessment) {
            const assessmentProfile = initProfileFromAssessment(savedUser.assessment);
            if (assessmentProfile) {
                profile = assessmentProfile;
            }
        } else if (savedUser.profile) {
            profile = { ...profile, ...savedUser.profile };
        }

        // 加载学习路径（可能是 JSON 字符串或非数组）
        if (savedUser.learningPath != null) {
            const lp = normalizeLearningPath(savedUser.learningPath);
            if (lp.length > 0) currentPath = lp;
        }
    }

    ensureCurrentPathValid();

    // ============================================
    // 学习上下文接收与应用逻辑
    // ============================================
    applyLearningContext();

    // 先尝试加载当前会话的历史消息
    if (currentUser && currentUser.id) {
        await loadChatHistory();
    }

    // 如果没有历史消息，才显示欢迎消息
    if (messages.length === 0) {
        const welcomeMsg = generateWelcomeMessage(savedUser?.assessment, profile);
        messages = [{ role: 'assistant', content: welcomeMsg }];
        await renderMessages();
    }

    updateUserUI();

    if (currentUser && currentUser.id) {
        await loadProgress();
        await initLearningPath();  // 初始化学习路径（基于学情实时生成）
        window.proactiveTutor.connect(currentUser.id || currentUser.name || 'anonymous', currentUser.currentTask || 'bigdata');
        // 每 30 秒自动保存 evaluation
        setInterval(() => {
            saveProgress();
        }, 30000);
        // 同步学习时长
        syncLearningMinute();
        setInterval(syncLearningMinute, 60000);
        // 页面可见性变化时立即同步
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                syncLearningMinute();
            }
        });
        // 页面离开时同步
        window.addEventListener('beforeunload', () => {
            syncLearningMinute();
            saveProgress();
        });
    }

    if (window.marked && window.mermaid) {
        const renderer = new marked.Renderer();
        const originalCode = renderer.code.bind(renderer);
        renderer.code = function(arg1, arg2, arg3) {
            let code = typeof arg1 === 'object' ? arg1.text : arg1;
            let lang = typeof arg1 === 'object' ? arg1.lang : arg2;
            if (lang === 'mermaid' || (code && (code.trim().startsWith('graph ') || code.trim().startsWith('flowchart ') || code.trim().startsWith('sequenceDiagram')))) {
                const encodedCode = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                return `<div class="mermaid-placeholder mermaid-container">${encodedCode}</div>`;
            }
            if (lang === 'micro-course') {
                const encodedCode = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                return `<div class="micro-course-block">${encodedCode}</div>`;
            }
            return typeof arg1 === 'object' ? originalCode(arg1) : originalCode(arg1, arg2, arg3);
        };
        marked.use({ renderer: renderer });
        
        if (mermaid.mermaidAPI) {
            const origRender = mermaid.mermaidAPI.render;
            mermaid.mermaidAPI.render = function(id, code, cb, opts) {
                return origRender.call(this, id, code, function(svg, bindFunctions) {
                    if (cb) cb(svg, bindFunctions);
                }, { ...opts, suppressErrorRendering: true, errorCallback: function() {} });
            };
        }
        
        mermaid.initialize({
            startOnLoad: false,
            theme: 'default',
            securityLevel: 'loose',
            suppressErrorRendering: true,
            flowchart: { useMaxWidth: true, htmlLabels: true },
            sequence: { useMaxWidth: true },
            errorCallback: function() {}
        });
        
        const origParse = mermaid.parse;
        mermaid.parse = function(code) {
            return origParse.call(this, code).catch(function(e) {
                console.warn('Mermaid parse suppressed:', e);
                return null;
            });
        };
        
        // 彻底禁用Mermaid错误弹窗
        if (mermaid.parseError) {
            mermaid.parseError = function() {};
        }
        if (mermaid.mermaidAPI && mermaid.mermaidAPI.parseError) {
            mermaid.mermaidAPI.parseError = function() {};
        }
        
        // 覆盖Mermaid的错误处理
        if (window.mermaidConfig) {
            window.mermaidConfig = {
                ...window.mermaidConfig,
                suppressErrorRendering: true,
                errorCallback: function() {}
            };
        } else {
            window.mermaidConfig = {
                suppressErrorRendering: true,
                errorCallback: function() {}
            };
        }
    }

    const style = document.createElement('style');
    style.textContent = '.mermaid-error, [id^="mermaid-error-"], [class*="mermaid-error"], .mermaid-syntax-error, .mermaidErrorMessage, .mermaidError, .mermaid-syntaxError, .mermaid-error-container, .mermaid-error-message, #mermaid-syntax-error, #mermaid-error-dialog { display: none !important; visibility: hidden !important; height: 0 !important; overflow: hidden !important; position: absolute !important; z-index: -1 !important; opacity: 0 !important; pointer-events: none !important; }';
    document.head.appendChild(style);
    
    window.addEventListener('error', function(e) {
        if (e.message && (e.message.includes('mermaid') || e.message.includes('Mermaid'))) {
            e.preventDefault();
            e.stopPropagation();
            console.warn('Mermaid error suppressed:', e.message);
        }
    }, true);

    window.addEventListener('unhandledrejection', function(e) {
        const reason = e.reason;
        if (reason && ((reason.message && (reason.message.includes('mermaid') || reason.message.includes('Mermaid'))) || String(reason).includes('mermaid'))) {
            e.preventDefault();
            console.warn('Mermaid promise error suppressed:', reason);
        }
    });

    switchOutputTab('run');
    renderProfile();
    renderRadarChart();
    renderEvaluation();
    renderPath();
    renderMessages();

    let _radarResizeTimer = null;
    window.addEventListener('resize', () => {
        if (_radarResizeTimer) clearTimeout(_radarResizeTimer);
        _radarResizeTimer = setTimeout(() => { renderRadarChart(); }, 200);
    });

    if (window.sidebarManager) window.sidebarManager.init();

    const sandboxSearchToggle = document.getElementById('sandbox-search-toggle');
    const sandboxSearchBar = document.getElementById('sandbox-search-bar');
    const sandboxSearchInput = document.getElementById('sandbox-search-input');
    const sandboxFilterBtn = document.getElementById('sandbox-filter-btn');
    const sandboxFilterBar = document.getElementById('sandbox-filter-bar');
    const sandboxCollapseBtn = document.getElementById('sandbox-collapse-btn');

    if (sandboxSearchToggle && sandboxSearchBar) {
        sandboxSearchToggle.addEventListener('click', () => {
            sandboxSearchBar.classList.toggle('hidden');
            if (!sandboxSearchBar.classList.contains('hidden') && sandboxSearchInput) {
                sandboxSearchInput.focus();
            }
        });
    }

    if (sandboxSearchInput) {
        let searchDebounce = null;
        sandboxSearchInput.addEventListener('input', () => {
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(() => renderAllSandboxLogs(), 200);
        });
    }

    if (sandboxFilterBtn && sandboxFilterBar) {
        sandboxFilterBtn.addEventListener('click', () => {
            sandboxFilterBar.classList.toggle('hidden');
        });
    }

    // sandboxCollapseBtn 已在前面声明，此处直接使用
    const sandboxExpandBtn = document.getElementById('sandbox-expand-btn');
    const trackA = document.getElementById('track-a');
    const trackAContainer = document.getElementById('track-a-container');
    const trackB = document.getElementById('track-b');
    const collapseIcon = document.getElementById('sandbox-collapse-icon');

    // 教研沙盘展开/隐藏状态管理 - 使用与学习路径相同的 collapsed 类模式
    function updateSandboxState(isCollapsed) {
        // 更新展开按钮可见性
        if (sandboxExpandBtn) {
            sandboxExpandBtn.classList.toggle('visible', isCollapsed);
        }

        // 更新收起图标旋转状态
        if (collapseIcon) {
            collapseIcon.style.transform = isCollapsed ? 'rotate(180deg)' : 'rotate(0deg)';
        }

        // 触发窗口resize事件，确保聊天框和输入框正确调整
        window.dispatchEvent(new Event('resize'));
    }

    // 初始化沙盘状态 - 默认隐藏
    if (trackAContainer) {
        const isCollapsed = trackAContainer.classList.contains('collapsed');
        updateSandboxState(isCollapsed);
    }

    if (sandboxCollapseBtn) {
        sandboxCollapseBtn.addEventListener('click', () => {
            // 使用 collapsed 类，与学习路径保持一致
            const isCurrentlyCollapsed = trackAContainer.classList.contains('collapsed');

            if (isCurrentlyCollapsed) {
                // 展开
                trackAContainer.classList.remove('collapsed');
            } else {
                // 收起
                trackAContainer.classList.add('collapsed');
            }

            updateSandboxState(!isCurrentlyCollapsed);
        });
    }

    if (sandboxExpandBtn) {
        sandboxExpandBtn.addEventListener('click', () => {
            const isCurrentlyCollapsed = trackAContainer.classList.contains('collapsed');

            if (isCurrentlyCollapsed) {
                // 展开
                trackAContainer.classList.remove('collapsed');
                updateSandboxState(false);
            }
        });
    }

    refreshLinkCacheFromBackend();
    setInterval(refreshLinkCacheFromBackend, 30 * 60 * 1000);

    if (window.LearningMonitor && currentUser) {
        window._learningMonitor = new LearningMonitor({
            enabled: true,
            studentId: String(currentUser.id || 'anonymous'),
            courseId: 'bigdata',
            onOverload: function(event) {
                if (event.score > 80) {
                    const toast = document.createElement('div');
                    toast.className = 'fixed top-4 left-1/2 transform -translate-x-1/2 px-6 py-3 rounded-2xl shadow-xl text-sm font-semibold z-[9999]';
                    toast.style.cssText = 'background: var(--warning); color: var(--text-on-accent); backdrop-filter: blur(16px);';
                    toast.innerHTML = '<i data-lucide="alert-triangle" class="w-4 h-4 inline mr-2"></i>检测到学习疲劳，建议休息一下再继续';
                    document.body.appendChild(toast);
                    if (window.lucide) lucide.createIcons();
                    setTimeout(() => { toast.style.transition = 'all 0.3s'; toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3000);
                }
            }
        });
        window._learningMonitor.start();
    }

    if (window.lightboxManager) {
        window.lightboxManager.init();
    }

    if (window.focusDurationPanel) {
        window.focusDurationPanel.init();
    }

    // 辩论面板展开/收起按钮
    document.getElementById('debate-panel-expand-btn')?.addEventListener('click', () => toggleDebatePanel(true));
    document.getElementById('debate-panel-collapse-btn')?.addEventListener('click', () => toggleDebatePanel(false));
    document.getElementById('debate-judge-close-btn')?.addEventListener('click', () => {
        document.getElementById('debate-judge-float-card')?.classList.remove('visible');
    });
});

class FlowTimerState {
    constructor() {
        this.is_timer_running = false;
        this.remaining_time = 25 * 60;
        this.total_time = 25 * 60;
        this.is_paused = false;
        this.is_complete = false;
        this._listeners = new Map();
    }

    update(partial) {
        const changed = {};
        for (const [key, value] of Object.entries(partial)) {
            if (this[key] !== value) {
                this[key] = value;
                changed[key] = value;
            }
        }
        if (Object.keys(changed).length > 0) {
            this._notify(changed);
        }
    }

    subscribe(id, callback) {
        this._listeners.set(id, callback);
        return () => this._listeners.delete(id);
    }

    _notify(changed) {
        for (const [, cb] of this._listeners) {
            try { cb(changed); } catch (e) { console.warn('[FlowTimerState] Listener error:', e); }
        }
    }
}

class FlowModeManager {
    constructor() {
        this.active = false;
        this.timerRunning = false;
        this.timerPaused = false;
        this.totalSeconds = 25 * 60;
        this.remainingSeconds = this.totalSeconds;
        this.animationFrameId = null;
        this.lastTickTime = 0;
        this.audioPlaying = false;
        this.circumference = 2 * Math.PI * 130;
        this.prefs = JSON.parse(localStorage.getItem('starlearn_flow_prefs') || '{}');
        this.state = new FlowTimerState();
        this.state.subscribe('island-ui', (changed) => this._onStateChanged(changed));
        this.currentMode = 'focus';
        this.selectedMinutes = 25;
        this.leftSidebarOpen = false;
        this.rightSidebarOpen = false;
        this.flowPresets = {
            focus: [
                { minutes: 5, label: '5 分钟', sub: '快速' },
                { minutes: 10, label: '10 分钟', sub: '短时' },
                { minutes: 15, label: '15 分钟', sub: '适中' },
                { minutes: 30, label: '30 分钟', sub: '标准' },
                { minutes: 45, label: '45 分钟', sub: '深度' },
                { minutes: 60, label: '60 分钟', sub: '沉浸' }
            ],
            rest: [
                { minutes: 3, label: '3 分钟', sub: '微休' },
                { minutes: 5, label: '5 分钟', sub: '短休' },
                { minutes: 10, label: '10 分钟', sub: '小憩' },
                { minutes: 15, label: '15 分钟', sub: '放松' },
                { minutes: 20, label: '20 分钟', sub: '充电' },
                { minutes: 30, label: '30 分钟', sub: '深度' }
            ]
        };
    }

    _onStateChanged(changed) {
        if ('remaining_time' in changed) {
            this._syncIslandDisplay();
        }
        if ('is_timer_running' in changed || 'is_paused' in changed || 'is_complete' in changed) {
            this._syncIslandStatus();
        }
    }

    _syncIslandDisplay() {
        const mins = Math.floor(this.state.remaining_time / 60);
        const secs = this.state.remaining_time % 60;
        const timeStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        const islandDisplay = document.getElementById('island-timer-display');
        if (islandDisplay) {
            islandDisplay.textContent = timeStr;
            islandDisplay.classList.add('tick');
            setTimeout(() => islandDisplay.classList.remove('tick'), 150);
        }
        const overlayDisplay = document.getElementById('flow-timer-display');
        if (overlayDisplay) overlayDisplay.textContent = timeStr;
        const fraction = this.state.remaining_time / this.state.total_time;
        const progressBar = document.getElementById('island-progress-bar');
        if (progressBar) progressBar.style.width = `${fraction * 100}%`;
        const ring = document.getElementById('flow-ring-progress');
        if (ring) {
            ring.setAttribute('stroke-dasharray', `${this.circumference * fraction} ${this.circumference}`);
        }
    }

    _syncIslandStatus() {
        const island = document.getElementById('flow-dynamic-island');
        const islandLabel = document.getElementById('island-timer-label');
        const modeLabel = this.currentMode === 'rest' ? '休息' : '专注';
        if (this.state.is_complete) {
            if (island) { island.classList.add('is-complete', 'flow-island-complete'); island.classList.remove('is-paused', 'flow-island-paused'); }
            if (islandLabel) islandLabel.textContent = modeLabel + '完成!';
            this._updateIslandPlayIcon(false);
        } else if (this.state.is_paused) {
            if (island) { island.classList.add('is-paused', 'flow-island-paused'); island.classList.remove('is-complete', 'flow-island-complete'); }
            if (islandLabel) islandLabel.textContent = '已暂停';
            this._updateIslandPlayIcon(true);
        } else if (this.state.is_timer_running) {
            if (island) { island.classList.remove('is-paused', 'flow-island-paused', 'is-complete', 'flow-island-complete'); }
            if (islandLabel) islandLabel.textContent = modeLabel + '中';
            this._updateIslandPlayIcon(false);
        } else {
            if (island) { island.classList.remove('is-paused', 'flow-island-paused', 'is-complete', 'flow-island-complete'); }
            if (islandLabel) islandLabel.textContent = modeLabel + '模式';
            this._updateIslandPlayIcon(true);
        }
    }

    enter() {
        if (this.active) return;
        this.active = true;
        document.body.classList.add('flow-mode-active');
        const overlay = document.getElementById('flow-overlay');
        if (overlay) {
            overlay.classList.toggle('rest-mode', this.currentMode === 'rest');
            overlay.classList.add('visible');
        }
        const island = document.getElementById('flow-dynamic-island');
        if (island) island.classList.add('visible');
        this.resetTimer();
        this.loadPrefs();
        this._renderFlowPresets();
        this._renderFlowMusicGenres();
        this._renderFlowMusicList();
        this._syncFlowMusicPlayer();
        this._updateSidebarExpandBtns();
        document.addEventListener('keydown', this._escHandler);
        if (lucide) lucide.createIcons();
    }

    exit() {
        if (!this.active) return;
        this.active = false;
        this.timerRunning = false;
        this.timerPaused = false;
        this.stopAudio();
        document.body.classList.remove('flow-mode-active');
        const overlay = document.getElementById('flow-overlay');
        if (overlay) {
            overlay.classList.remove('visible', 'floating-mode');
        }
        const island = document.getElementById('flow-dynamic-island');
        if (island) {
            island.classList.remove('visible', 'is-paused', 'is-complete', 'flow-island-paused', 'flow-island-complete');
        }
        document.removeEventListener('keydown', this._escHandler);
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        this.state.update({
            is_timer_running: false,
            remaining_time: this.totalSeconds,
            is_paused: false,
            is_complete: false
        });
        this.savePrefs();
    }

    exitOverlayOnly() {
        document.body.classList.remove('flow-mode-active');
        const overlay = document.getElementById('flow-overlay');
        if (overlay) {
            overlay.classList.remove('visible', 'floating-mode');
        }
        document.removeEventListener('keydown', this._escHandler);
        const island = document.getElementById('flow-dynamic-island');
        if (island) island.classList.add('visible');
    }

    _escHandler = (e) => {
        if (e.key === 'Escape') this.exitOverlayOnly();
    };

    resetTimer() {
        this.remainingSeconds = this.totalSeconds;
        this.timerRunning = false;
        this.timerPaused = false;
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        this.state.update({
            is_timer_running: false,
            remaining_time: this.totalSeconds,
            is_paused: false,
            is_complete: false
        });
        const container = document.querySelector('.flow-timer-container');
        if (container) container.classList.remove('flow-timer-complete');
        const modeLabel = this.currentMode === 'rest' ? '休息' : '专注';
        const btn = document.getElementById('flow-start-btn');
        if (btn) btn.innerHTML = '<i data-lucide="play" class="w-4 h-4"></i> 开始' + modeLabel;
        const label = document.getElementById('flow-timer-label');
        if (label) label.textContent = modeLabel + '模式';
        this._updateIslandPlayIcon(true);
        if (lucide) lucide.createIcons();
    }

    toggleTimer() {
        if (!this.active) return;
        if (!this.timerRunning) {
            this.startTimer();
        } else if (this.timerPaused) {
            this.resumeTimer();
        } else {
            this.pauseTimer();
        }
    }

    startTimer() {
        this.timerRunning = true;
        this.timerPaused = false;
        this.lastTickTime = performance.now();
        this._tick();
        const modeLabel = this.currentMode === 'rest' ? '休息' : '专注';
        const btn = document.getElementById('flow-start-btn');
        if (btn) btn.innerHTML = '<i data-lucide="pause" class="w-4 h-4"></i> 暂停';
        const label = document.getElementById('flow-timer-label');
        if (label) label.textContent = modeLabel + '中...';
        this.state.update({ is_timer_running: true, is_paused: false, is_complete: false });
        if (lucide) lucide.createIcons();
    }

    pauseTimer() {
        this.timerPaused = true;
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        const btn = document.getElementById('flow-start-btn');
        if (btn) btn.innerHTML = '<i data-lucide="play" class="w-4 h-4"></i> 继续';
        const label = document.getElementById('flow-timer-label');
        if (label) label.textContent = '已暂停';
        this.state.update({ is_paused: true });
        if (lucide) lucide.createIcons();
    }

    resumeTimer() {
        this.timerPaused = false;
        this.lastTickTime = performance.now();
        this._tick();
        const modeLabel = this.currentMode === 'rest' ? '休息' : '专注';
        const btn = document.getElementById('flow-start-btn');
        if (btn) btn.innerHTML = '<i data-lucide="pause" class="w-4 h-4"></i> 暂停';
        const label = document.getElementById('flow-timer-label');
        if (label) label.textContent = modeLabel + '中...';
        this.state.update({ is_paused: false });
        if (lucide) lucide.createIcons();
    }

    _tick = () => {
        if (!this.timerRunning || this.timerPaused) return;
        const now = performance.now();
        const deltaMs = now - this.lastTickTime;
        if (deltaMs >= 1000) {
            const elapsed = Math.floor(deltaMs / 1000);
            this.remainingSeconds = Math.max(0, this.remainingSeconds - elapsed);
            this.lastTickTime = now - (deltaMs % 1000);
            this.state.update({ remaining_time: this.remainingSeconds });
            if (this.remainingSeconds <= 0) {
                this.onTimerComplete();
                return;
            }
        }
        this.animationFrameId = requestAnimationFrame(this._tick);
    };

    onTimerComplete() {
        this.timerRunning = false;
        this.timerPaused = false;
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        const container = document.querySelector('.flow-timer-container');
        if (container) container.classList.add('flow-timer-complete');
        const modeLabel = this.currentMode === 'rest' ? '休息' : '专注';
        const btn = document.getElementById('flow-start-btn');
        if (btn) btn.innerHTML = '<i data-lucide="rotate-ccw" class="w-4 h-4"></i> 再来一轮';
        const label = document.getElementById('flow-timer-label');
        if (label) label.textContent = modeLabel + '完成！';
        this.state.update({ is_timer_running: false, is_complete: true });
        if (lucide) lucide.createIcons();
        this.playCompletionSound();
        this._showPlantReward();

        // 成就触发：专注完成
        if (window.AchievementManager && this.currentMode === 'focus') {
            const minutes = Math.round((this.totalSeconds || this.state.total_time || 1500) / 60);
            AchievementManager.incrementStat('study_count');
            AchievementManager.incrementStat('study_minutes', minutes);
        }

        // 记录学习时间到数据库（用于 hub 页面学习概览）
        if (this.currentMode === 'focus' && window.StarData) {
            const userId = StarData.getUserId();
            const minutes = Math.round((this.totalSeconds || this.state.total_time || 1500) / 60);
            if (userId && minutes > 0) {
                fetch('/api/cockpit/learning-time', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ userId, minutes }),
                }).then(() => {
                    localStorage.setItem('starlearn_learning_update', String(Date.now()));
                }).catch(() => {});
            }
        }
    }

    _showPlantReward() {
        if (this.currentMode === 'rest') return;
        const seeds = parseInt(localStorage.getItem('starlearn_seeds') || '0');
        localStorage.setItem('starlearn_seeds', String(seeds + 1));
        const modal = document.getElementById('plant-reward-modal');
        const countEl = document.getElementById('plant-reward-seed-count');
        if (countEl) countEl.textContent = seeds + 1;
        if (modal) {
            modal.classList.remove('hidden');
            requestAnimationFrame(() => {
                requestAnimationFrame(() => modal.classList.add('visible'));
            });
        }
    }

    _updateIslandPlayIcon(isPaused) {
        const icon = document.getElementById('island-play-icon');
        if (!icon) return;
        if (isPaused) {
            icon.innerHTML = '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
        } else {
            icon.innerHTML = '<rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect>';
        }
    }

    playCompletionSound() {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [523.25, 659.25, 783.99, 1046.50];
            notes.forEach((freq, i) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.value = freq;
                gain.gain.setValueAtTime(0.15, ctx.currentTime + i * 0.2);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.2 + 0.5);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(ctx.currentTime + i * 0.2);
                osc.stop(ctx.currentTime + i * 0.2 + 0.5);
            });
        } catch (e) {}
    }

    updateTimerDisplay() {
        this._syncIslandDisplay();
    }

    updateRingProgress(fraction) {
        const ring = document.getElementById('flow-ring-progress');
        if (ring) {
            ring.setAttribute('stroke-dasharray', `${this.circumference * fraction} ${this.circumference}`);
        }
        const progressBar = document.getElementById('island-progress-bar');
        if (progressBar) {
            progressBar.style.width = `${fraction * 100}%`;
        }
    }

    toggleAudio() {
        const audio = document.getElementById('flow-audio');
        if (!audio) return;
        if (this.audioPlaying) {
            this.stopAudio();
        } else {
            this.playAudio();
        }
    }

    playAudio() {
        const audio = document.getElementById('flow-audio');
        if (!audio) return;
        audio.volume = (parseInt(document.getElementById('flow-volume')?.value || 40)) / 100;
        audio.play().then(() => {
            this.audioPlaying = true;
            const btn = document.getElementById('flow-audio-toggle');
            if (btn) btn.classList.add('active');
        }).catch(err => {
            console.warn('[FlowMode] Audio play failed:', err);
        });
    }

    stopAudio() {
        const audio = document.getElementById('flow-audio');
        if (audio) {
            audio.pause();
            audio.currentTime = 0;
        }
        this.audioPlaying = false;
        const btn = document.getElementById('flow-audio-toggle');
        if (btn) btn.classList.remove('active');
    }

    setVolume(val) {
        const audio = document.getElementById('flow-audio');
        if (audio) audio.volume = val / 100;
        const label = document.getElementById('flow-volume-label');
        if (label) label.textContent = val + '%';
        this.prefs.volume = parseInt(val);
    }

    loadPrefs() {
        if (this.prefs.volume !== undefined) {
            const slider = document.getElementById('flow-volume');
            if (slider) slider.value = this.prefs.volume;
            this.setVolume(this.prefs.volume);
        }
    }

    savePrefs() {
        localStorage.setItem('starlearn_flow_prefs', JSON.stringify(this.prefs));
    }

    switchFlowMode(mode) {
        if (this.currentMode === mode) return;
        this.currentMode = mode;
        this.selectedMinutes = mode === 'focus' ? 25 : 5;
        const overlay = document.getElementById('flow-overlay');
        if (overlay) overlay.classList.toggle('rest-mode', mode === 'rest');
        const island = document.getElementById('flow-dynamic-island');
        if (island) {
            island.classList.toggle('rest-mode', mode === 'rest');
            island.classList.toggle('flow-island-rest', mode === 'rest');
        }
        const islandLabel = document.getElementById('island-timer-label');
        if (islandLabel) islandLabel.textContent = mode === 'rest' ? '休息模式' : '专注模式';
        document.querySelectorAll('#flow-mode-switch .flow-mode-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.mode === mode);
        });
        this._renderFlowPresets();
        const label = document.getElementById('flow-timer-label');
        if (label) label.textContent = mode === 'rest' ? '休息模式' : '专注模式';
    }

    _renderFlowPresets() {
        const container = document.getElementById('flow-presets-grid');
        if (!container) return;
        const presets = this.flowPresets[this.currentMode] || this.flowPresets.focus;
        container.innerHTML = presets.map(p => {
            const isSelected = this.selectedMinutes === p.minutes;
            return `<button class="flow-preset-item${isSelected ? ' selected' : ''}" data-minutes="${p.minutes}" onclick="window.flowMode.selectFlowPreset(${p.minutes})">
                <span class="preset-time">${p.label}</span>
                <span class="preset-desc">${p.sub}</span>
            </button>`;
        }).join('');
    }

    selectFlowPreset(minutes) {
        this.selectedMinutes = minutes;
        this._renderFlowPresets();
        const totalSeconds = minutes * 60;
        this.totalSeconds = totalSeconds;
        this.remainingSeconds = totalSeconds;
        this.state.update({
            total_time: totalSeconds,
            remaining_time: totalSeconds,
            is_timer_running: false,
            is_paused: false,
            is_complete: false
        });
        this.resetTimer();
    }

    confirmCustomDuration() {
        const input = document.getElementById('flow-custom-field');
        if (!input) return;
        const val = parseInt(input.value);
        if (!val || val < 1 || val > 180) {
            input.style.borderColor = 'var(--danger-border)';
            setTimeout(() => { input.style.borderColor = ''; }, 1500);
            return;
        }
        this.selectFlowPreset(val);
        input.value = '';
        input.style.borderColor = 'var(--success-border)';
        setTimeout(() => { input.style.borderColor = ''; }, 1000);
    }

    toggleLeftSidebar() {
        this.leftSidebarOpen = !this.leftSidebarOpen;
        const sidebar = document.getElementById('flow-sidebar-left');
        if (sidebar) sidebar.classList.toggle('collapsed', !this.leftSidebarOpen);
        this._updateSidebarExpandBtns();
    }

    toggleRightSidebar() {
        this.rightSidebarOpen = !this.rightSidebarOpen;
        const sidebar = document.getElementById('flow-sidebar-right');
        if (sidebar) sidebar.classList.toggle('collapsed', !this.rightSidebarOpen);
        this._updateSidebarExpandBtns();
    }

    _updateSidebarExpandBtns() {
        const leftExpand = document.getElementById('flow-expand-left');
        const rightExpand = document.getElementById('flow-expand-right');
        if (leftExpand) leftExpand.classList.toggle('visible', !this.leftSidebarOpen);
        if (rightExpand) rightExpand.classList.toggle('visible', !this.rightSidebarOpen);
    }

    _renderFlowMusicGenres() {
        const container = document.getElementById('flow-music-genres');
        if (!container) return;
        const genres = [
            { key: 'all', label: '全部' },
            { key: 'piano', label: '钢琴' },
            { key: 'ambient', label: '环境' },
            { key: 'nature', label: '自然' },
            { key: 'lofi', label: '低保真' }
        ];
        const currentGenre = window.musicPanel?.currentGenre || 'all';
        container.innerHTML = genres.map(g =>
            `<button class="flow-music-genre-chip${g.key === currentGenre ? ' active' : ''}" onclick="window.flowMode._filterFlowMusic('${g.key}')">${g.label}</button>`
        ).join('');
    }

    _filterFlowMusic(genre) {
        if (window.musicPanel) {
            window.musicPanel.currentGenre = genre;
            window.musicPanel._renderGenres();
            window.musicPanel._renderList();
        }
        this._renderFlowMusicGenres();
        this._renderFlowMusicList();
    }

    _renderFlowMusicList() {
        const container = document.getElementById('flow-music-list');
        if (!container || !window.musicPanel) return;
        const songs = window.musicPanel.songs || [];
        const genre = window.musicPanel.currentGenre || 'all';
        const filtered = genre === 'all' ? songs : songs.filter(s => s.genre === genre);
        const currentSongId = window.musicPanel.currentIndex >= 0 ? window.musicPanel.songs[window.musicPanel.currentIndex]?.id : -1;
        container.innerHTML = filtered.map(song =>
            `<div class="flow-music-item${song.id === currentSongId ? ' playing' : ''}" onclick="window.musicPanel.play(${song.id})">
                <div class="flow-music-item-cover">${song.coverSvg || ''}</div>
                <div class="flow-music-item-info">
                    <div class="flow-music-item-title">${song.title}</div>
                    <div class="flow-music-item-artist">${song.artist}</div>
                </div>
            </div>`
        ).join('');
    }

    _syncFlowMusicPlayer() {
        if (!window.musicPanel) return;
        const title = document.getElementById('flow-music-title');
        const artist = document.getElementById('flow-music-artist');
        const cover = document.getElementById('flow-music-cover');
        const playIcon = document.getElementById('flow-music-play-icon');
        if (window.musicPanel.currentIndex >= 0) {
            const song = window.musicPanel.songs[window.musicPanel.currentIndex];
            if (title) title.textContent = song.title;
            if (artist) artist.textContent = song.artist;
            if (cover) cover.innerHTML = song.coverSvg || '';
        } else {
            if (title) title.textContent = '未在播放';
            if (artist) artist.textContent = '';
        }
        if (playIcon) {
            playIcon.innerHTML = window.musicPanel.isPlaying
                ? '<rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect>'
                : '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
        }
    }

    syncVisualizers() {
        const isPlaying = window.musicPanel?.isPlaying || false;
        document.querySelectorAll('.flow-vis-bar').forEach(bar => {
            bar.classList.toggle('playing', isPlaying);
        });
        document.querySelectorAll('.mini-vis-bar').forEach(bar => {
            bar.classList.toggle('playing', isPlaying);
        });
        document.querySelectorAll('.music-vis-bar').forEach(bar => {
            bar.classList.toggle('playing', isPlaying);
        });
    }
}

function formatTime(seconds) {
    if (typeof seconds !== 'number' || !isFinite(seconds) || seconds <= 0) return '00:00';
    const totalSec = Math.floor(Math.max(0, seconds));
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

class FlashcardUI {
    constructor() {
        this.cards = [];
        this.currentIndex = 0;
        this.flipped = false;
        this.container = null;
        this.timeLeft = 180;
        this.timerInterval = null;
        this.autoFlipTimer = null;
        this.AUTO_FLIP_DELAY = parseInt(localStorage.getItem('starlearn_flashcard_duration') || '180') * 1000;
        this.COUNTDOWN_WARNING = 10;
        this._countdownStartTs = 0;
        this._countdownTotalSec = 0;
        this._visibilityHandler = null;
        this._beforeUnloadHandler = null;
        this._destroyed = false;
        // 沉浸模式属性
        this.immersiveMode = false;
        this.immersiveEl = null;
        this.cardProgress = {};
        this.sessionStats = { cardsTotal: 0, cardsAnswered: 0, cardsMastered: 0, cardsFavorited: 0, startTime: 0, duration: 0 };
        this.userStats = { totalCards: 0, totalMastered: 0, totalFavorited: 0, todayCount: 0, streakDays: 0 };
        this.filterMode = 'all';
        this.dataPodOpen = false;
        this.navPodOpen = false;
        this.nebulaCanvas = null;
        this.nebulaCtx = null;
        this.particles = [];
        this._nebularAF = null;
        this._immersiveKeyHandler = null;
        this.userId = null;
        // 沉浸模式倒计时
        this.immersiveCountdown = {
            active: false,
            timeLeft: 0,
            totalTime: 0,
            interval: null,
            timer: null,
            startTs: 0,
        };
        this.immersiveCountdownDelay = parseInt(localStorage.getItem('starlearn_flashcard_duration') || '15') * 1000;
    }

    async open() {
        if (this._destroyed) return;
        this.immersiveMode = true;
        const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
        this.userId = user.id || null;
        this.immersiveEl = document.getElementById('capsule-immersive');
        if (!this.immersiveEl) return;
        this.immersiveEl.classList.add('active');
        await this.generateCards();
        this.sessionStats = { cardsTotal: this.cards.length, cardsAnswered: 0, cardsMastered: 0, cardsFavorited: 0, startTime: Date.now(), duration: 0 };
        if (this.userId) await this._loadProgressFromDB();
        this._initNebula();
        this.renderOrbitTrack();
        this.renderCardImmersive();
        this._initImmersiveCountdown();
        this.updateStatsUI();
        this.renderNavPodList();
        document.addEventListener('keydown', this._immersiveKeyHandler = (e) => this._handleImmersiveKey(e));
    }

    close() {
        if (this.immersiveMode) {
            this.exitImmersive();
            return;
        }
        this._forceClearAllTimers();
        this._clearCountdownState();
        if (this.container) {
            this.container.style.opacity = '0';
            this.container.style.visibility = 'hidden';
        }
        document.removeEventListener('keydown', this._keyHandler);
        this._unbindVisibilityChange();
        this._unbindBeforeUnload();
    }

    destroy() {
        this.close();
        this._destroyed = true;
        if (this.container && this.container.parentNode) {
            this.container.parentNode.removeChild(this.container);
        }
        this.container = null;
        this.cards = [];
    }

    _forceClearAllTimers() {
        if (this.timerInterval !== null) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        if (this.autoFlipTimer !== null) {
            clearTimeout(this.autoFlipTimer);
            this.autoFlipTimer = null;
        }
        this.timeLeft = 0;
    }

    _keyHandler = (e) => {
        if (e.key === 'Escape') this.close();
        else if (e.key === 'ArrowLeft') this.prev();
        else if (e.key === 'ArrowRight') this.next();
        else if (e.key === ' ') { e.preventDefault(); this.flip(); }
    };

    _startAutoFlip() {
        this._forceClearAllTimers();

        this._countdownTotalSec = Math.floor(this.AUTO_FLIP_DELAY / 1000);
        this.timeLeft = this._countdownTotalSec;
        this._countdownStartTs = Date.now();
        this._updateCountdownDisplay();

        this.timerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this._countdownStartTs) / 1000);
            this.timeLeft = Math.max(0, this._countdownTotalSec - elapsed);
            this._updateCountdownDisplay();

            if (this.timeLeft <= 0) {
                this._clearCountdown();
                if (!this.flipped) {
                    this.flip(true);
                }
            }
        }, 1000);

        this.autoFlipTimer = setTimeout(() => {
            if (!this.flipped) {
                this.flip(true);
            }
        }, this.AUTO_FLIP_DELAY);

        this._saveCountdownState();
    }

    _clearAutoFlip() {
        if (this.autoFlipTimer !== null) {
            clearTimeout(this.autoFlipTimer);
            this.autoFlipTimer = null;
        }
        this._clearCountdown();
    }

    _clearCountdown() {
        if (this.timerInterval !== null) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    _updateCountdownDisplay() {
        const frontEl = document.getElementById('flashcard-countdown-front');
        const backEl = document.getElementById('flashcard-countdown');
        const text = formatTime(this.timeLeft);

        [frontEl, backEl].forEach(el => {
            if (!el) return;
            el.textContent = text;
            el.classList.remove('countdown-warning', 'countdown-expired');
            if (this.timeLeft <= 0) {
                el.classList.add('countdown-expired');
            } else if (this.timeLeft <= this.COUNTDOWN_WARNING) {
                el.classList.add('countdown-warning');
            }
        });
    }

    _saveCountdownState() {
        try {
            const state = {
                cardIndex: this.currentIndex,
                flipped: this.flipped,
                countdownStartTs: this._countdownStartTs,
                countdownTotalSec: this._countdownTotalSec,
                timestamp: Date.now(),
            };
            sessionStorage.setItem('starlearn_flashcard_state', JSON.stringify(state));
        } catch (e) {}
    }

    _restoreCountdownState() {
        try {
            const saved = sessionStorage.getItem('starlearn_flashcard_state');
            if (!saved) return;
            const state = JSON.parse(saved);
            if (state.cardIndex !== undefined && state.cardIndex < this.cards.length) {
                this.currentIndex = state.cardIndex;
            }
            const elapsed = Math.floor((Date.now() - (state.countdownStartTs || 0)) / 1000);
            const remaining = Math.max(0, (state.countdownTotalSec || 0) - elapsed);
            if (remaining > 0 && state.countdownTotalSec > 0) {
                this._countdownTotalSec = remaining;
                this.AUTO_FLIP_DELAY = remaining * 1000;
                this.flipped = state.flipped || false;
            }
        } catch (e) {}
    }

    _clearCountdownState() {
        try {
            sessionStorage.removeItem('starlearn_flashcard_state');
        } catch (e) {}
    }

    _bindVisibilityChange() {
        this._visibilityHandler = () => {
            if (document.visibilityState === 'visible' && this.timerInterval) {
                const elapsed = Math.floor((Date.now() - this._countdownStartTs) / 1000);
                this.timeLeft = Math.max(0, this._countdownTotalSec - elapsed);
                this._updateCountdownDisplay();
                if (this.timeLeft <= 0) {
                    this._clearCountdown();
                    if (!this.flipped) {
                        this.flip(true);
                    }
                }
            } else if (document.visibilityState === 'hidden') {
                this._saveCountdownState();
            }
        };
        document.addEventListener('visibilitychange', this._visibilityHandler);
    }

    _unbindVisibilityChange() {
        if (this._visibilityHandler) {
            document.removeEventListener('visibilitychange', this._visibilityHandler);
            this._visibilityHandler = null;
        }
    }

    _bindBeforeUnload() {
        this._beforeUnloadHandler = () => {
            this._saveCountdownState();
            this._forceClearAllTimers();
        };
        window.addEventListener('beforeunload', this._beforeUnloadHandler);
    }

    _unbindBeforeUnload() {
        if (this._beforeUnloadHandler) {
            window.removeEventListener('beforeunload', this._beforeUnloadHandler);
            this._beforeUnloadHandler = null;
        }
    }

    async generateCards() {
        const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
        const evaluation = JSON.parse(localStorage.getItem('starlearn_evaluation') || '{}');
        const recentContent = evaluation.lastTopics || '大数据基础';
        // 尝试从多处获取更丰富的学习上下文
        let chapterContent = recentContent;
        try {
            const studyData = JSON.parse(localStorage.getItem('starlearn_study') || '{}');
            const recentTopics = studyData.recentTopics || studyData.lastChapter || '';
            if (recentTopics && recentTopics.length > chapterContent.length) {
                chapterContent = recentTopics;
            }
        } catch (e) {}
        try {
            const prefs = JSON.parse(localStorage.getItem('starlearn_preferences') || '{}');
            if (prefs.currentChapter && prefs.currentChapter.length > chapterContent.length) {
                chapterContent = prefs.currentChapter;
            }
        } catch (e) {}

        const makeRequest = async () => {
            const res = await fetch(`${API_BASE}/api/v2/flashcard/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_id: user.id || user.name || 'anonymous',
                    course_id: user.currentTask || 'bigdata',
                    chapter_name: recentContent,
                    chapter_content: chapterContent,
                }),
            });
            return await res.json();
        };

        let cards = null;
        try {
            const data = await makeRequest();
            if (data.success && data.data?.flashcards?.length > 0) {
                cards = data.data.flashcards;
            }
        } catch (err) {
            console.warn('[Flashcard] Generate failed (attempt 1):', err);
        }
        // 重试一次
        if (!cards) {
            try {
                await new Promise(r => setTimeout(r, 600));
                const data = await makeRequest();
                if (data.success && data.data?.flashcards?.length > 0) {
                    cards = data.data.flashcards;
                }
            } catch (err) {
                console.warn('[Flashcard] Generate failed (attempt 2):', err);
            }
        }
        this.cards = cards && cards.length > 0 ? cards : this._fallbackCards(recentContent);
        this.currentIndex = 0;
        this.flipped = false;
    }

    _fallbackCards(topic) {
        // 回退卡片也提供有教育意义的具体答案，而非空洞提示
        const t = this._escapeHtml(topic);
        return [
            { front: `【概念】${t}的定义是什么？`, back: `${t}是计算机科学与数据工程领域的一个重要概念，指围绕该主题形成的一套理论、方法与技术体系。其核心在于通过系统化的手段解决特定领域的问题。`, hint: '关注定义中的关键词和适用范围' },
            { front: `【原理】${t}的底层工作原理是什么？`, back: '其底层机制通常包含数据输入→处理转换→输出生成的三段式流程，依赖分布式计算、内存优化与算法调度等核心技术实现高效运转。', hint: '从数据流转角度理解' },
            { front: `【特征】${t}有哪些关键特征？`, back: '主要特征包括：1) 高扩展性，支持海量数据；2) 容错性，自动处理节点故障；3) 并行性，充分利用多核/多机资源；4) 抽象性，屏蔽底层复杂细节。', hint: '列举3-5个最本质的特征' },
            { front: `【对比】${t}与传统方案有何区别？`, back: '与传统单机或关系型方案相比，它在横向扩展能力、实时处理性能和成本效益上具有明显优势，但引入了更高的系统复杂度和运维门槛。', hint: '从扩展性、性能、成本三个维度对比' },
            { front: `【应用】${t}的典型应用场景有哪些？`, back: '典型场景包括：海量日志分析、实时推荐系统、用户行为画像、金融风控建模、IoT数据汇聚与可视化大屏等。', hint: '联系你熟悉的行业或产品' },
            { front: `【组件】${t}的核心组件/模块有哪些？`, back: '通常包含存储层（分布式文件系统）、计算层（批处理/流处理引擎）、资源调度层（集群管理器）以及服务接口层（SQL/REST API）。', hint: '按层次结构梳理组件' },
            { front: `【优化】使用${t}时常见的性能优化手段？`, back: '常见优化：数据本地化减少网络传输、内存缓存热点数据、合理设置并行度、压缩减少IO、避免数据倾斜以及预聚合降低计算量。', hint: '从计算、存储、网络三个层面思考' },
            { front: `【安全】${t}涉及哪些安全与隐私问题？`, back: '主要涉及：数据访问权限控制（认证授权）、传输与存储加密、敏感数据脱敏、审计日志追踪以及合规性（如GDPR、等保）要求。', hint: '从数据生命周期角度思考' },
            { front: `【趋势】${t}的未来发展趋势如何？`, back: '趋势包括：云原生与Serverless化、AI驱动的自动化调优、实时化与边缘计算融合、湖仓一体架构统一以及更低代码的使用门槛。', hint: '关注技术演进和业界动态' },
            { front: `【实践】学习${t}的最佳实践路径？`, back: '建议路径：1) 理解基础概念与架构；2) 搭建本地环境动手实验；3) 阅读官方文档与经典论文；4) 参与开源项目或复现案例；5) 在生产环境中逐步落地。', hint: '理论→实验→项目→生产' },
        ];
    }

    renderCard() {
        if (!this.container || this.cards.length === 0) return;
        const card = this.cards[this.currentIndex];
        const wasFlipped = this.flipped;
        this.flipped = false;
        this._forceClearAllTimers();
        const durationSec = Math.floor(this.AUTO_FLIP_DELAY / 1000);
        const initialDisplay = formatTime(durationSec);
        this.container.innerHTML = `
            <div style="max-width: 480px; width: 90%; padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="color: var(--text-primary); font-size: 16px; font-weight: 700;">⚡ 知识胶囊</h3>
                    <button onclick="window.flashcardUI.close()" style="background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 20px;">✕</button>
                </div>
                <div class="flashcard-container" onclick="window.flashcardUI.flip()">
                    <div class="flashcard-card" id="flashcard-card" style="height: 240px;">
                        <div class="flashcard-front">
                            <div style="font-size: 11px; color: var(--text-tertiary); margin-bottom: 12px;">点击翻转查看答案</div>
                            <div class="flashcard-question">${card.front}</div>
                            <div class="flashcard-countdown flashcard-countdown-front" id="flashcard-countdown-front">${initialDisplay}</div>
                        </div>
                        <div class="flashcard-back">
                            <div class="flashcard-answer">${card.back}</div>
                            ${card.hint ? `<div class="flashcard-hint">💡 ${card.hint}</div>` : ''}
                            <div class="flashcard-countdown" id="flashcard-countdown">${initialDisplay}</div>
                        </div>
                    </div>
                </div>
                <div id="flashcard-auto-flip-hint" style="text-align: center; margin-top: 8px; font-size: 10px; color: var(--text-tertiary); opacity: 0; transition: opacity 0.5s ease;">
                    ⏱ ${durationSec}秒后自动展示答案
                </div>
                <div class="flashcard-nav" style="justify-content: center; margin-top: 16px;">
                    <button class="flashcard-nav-btn" onclick="window.flashcardUI.prev()" ${this.currentIndex === 0 ? 'disabled' : ''}>
                        <i data-lucide="chevron-left" class="w-4 h-4"></i>
                    </button>
                    <span class="flashcard-counter">${this.currentIndex + 1} / ${this.cards.length}</span>
                    <button class="flashcard-nav-btn" onclick="window.flashcardUI.next()" ${this.currentIndex >= this.cards.length - 1 ? 'disabled' : ''}>
                        <i data-lucide="chevron-right" class="w-4 h-4"></i>
                    </button>
                </div>
                <div style="text-align: center; margin-top: 12px; font-size: 11px; color: var(--text-tertiary);">
                    ← → 切换卡片 · 空格翻转 · Esc 关闭
                </div>
            </div>
        `;
        if (lucide) lucide.createIcons();

        if (wasFlipped) {
            this.flipped = true;
            const cardEl = document.getElementById('flashcard-card');
            if (cardEl) cardEl.classList.add('flipped');
            this._clearCountdown();
        } else {
            this._startAutoFlip();
        }

        const hintEl = document.getElementById('flashcard-auto-flip-hint');
        if (hintEl && !wasFlipped) setTimeout(() => { hintEl.style.opacity = '1'; }, 500);
    }

    flip(isAutoFlip = false) {
        const card = document.getElementById('flashcard-card');
        if (card) {
            this.flipped = !this.flipped;
            card.classList.toggle('flipped', this.flipped);
            this._clearAutoFlip();
            const hintEl = document.getElementById('flashcard-auto-flip-hint');
            if (this.flipped && isAutoFlip) {
                const answerEl = card.querySelector('.flashcard-answer');
                if (answerEl) {
                    answerEl.classList.add('auto-flip-highlight');
                    setTimeout(() => answerEl.classList.remove('auto-flip-highlight'), 3000);
                }
                if (hintEl) {
                    hintEl.textContent = '✅ 已自动展示答案';
                    hintEl.style.color = 'var(--success)';
                    hintEl.style.opacity = '1';
                }
            } else if (hintEl) {
                hintEl.style.opacity = '0';
            }
            if (this.flipped) {
                this._clearCountdown();
                this._clearCountdownState();
            }
        }
    }

    next() {
        if (this.currentIndex < this.cards.length - 1) {
            this.currentIndex++;
            this._clearCountdownState();
            this.renderCard();
        }
    }

    prev() {
        if (this.immersiveMode) {
            this._navigateCard(-1);
            return;
        }
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this._clearCountdownState();
            this.renderCard();
        }
    }

    // ========== 沉浸模式方法 ==========
    exitImmersive() {
        this.immersiveMode = false;
        this._clearImmersiveCountdown();
        this.sessionStats.duration = Math.floor((Date.now() - this.sessionStats.startTime) / 1000);
        if (this.userId) this._saveSessionToDB();
        this._destroyNebula();
        if (this.immersiveEl) this.immersiveEl.classList.remove('active');
        if (this._immersiveKeyHandler) {
            document.removeEventListener('keydown', this._immersiveKeyHandler);
            this._immersiveKeyHandler = null;
        }
        const completion = document.getElementById('capsule-completion');
        if (completion) completion.classList.add('hidden');
    }

    renderOrbitTrack() {
        const curve = document.getElementById('capsule-orbit-curve');
        if (!curve) return;
        curve.innerHTML = '';
        this.cards.forEach((_, i) => {
            const star = document.createElement('div');
            star.className = 'capsule-orbit-star';
            star.dataset.index = i;
            if (i === this.currentIndex) star.classList.add('current');
            const hash = this._hashCard(this.cards[i].front, this.cards[i].back);
            const prog = this.cardProgress[hash];
            if (prog?.is_mastered) star.classList.add('mastered');
            if (prog?.is_favorite) star.classList.add('favorite');
            curve.appendChild(star);
        });
    }

    updateOrbitCurrent() {
        document.querySelectorAll('.capsule-orbit-star').forEach((star, i) => {
            star.classList.remove('current');
            if (i === this.currentIndex) star.classList.add('current');
        });
    }

    renderCardImmersive() {
        const front = document.getElementById('capsule-card-front');
        const back = document.getElementById('capsule-card-back');
        const card3d = document.getElementById('capsule-card-3d');
        const counter = document.getElementById('capsule-counter');
        const sessionInfo = document.getElementById('capsule-session-info');
        if (!front || !back || !card3d) return;
        const card = this.cards[this.currentIndex];
        const hash = this._hashCard(card.front, card.back);
        const prog = this.cardProgress[hash] || {};
        this.flipped = false;
        card3d.classList.remove('flipped');
        front.innerHTML = `
            <div class="capsule-card-label">问题</div>
            <div class="capsule-card-content">${this._escapeHtml(card.front)}</div>
            <div class="capsule-countdown-bar" id="capsule-countdown-bar">
                <div class="capsule-countdown-fill" id="capsule-countdown-fill"></div>
            </div>
            <div class="capsule-countdown-text" id="capsule-countdown-text">${this._formatTime(Math.floor(this.immersiveCountdownDelay / 1000))}</div>
            <div class="capsule-card-hint" id="capsule-flip-hint">思考后方可翻转</div>
            ${card.hint ? `<div class="capsule-card-hint">💡 ${this._escapeHtml(card.hint)}</div>` : ''}
            <div class="capsule-thinking-overlay" id="capsule-thinking-overlay">
                <div class="capsule-thinking-spinner"></div>
                <div class="capsule-thinking-text">深度思考中…</div>
                <div class="capsule-thinking-sub">倒计时结束后可查看答案</div>
            </div>
        `;
        back.innerHTML = `
            <div class="capsule-card-label">答案</div>
            <div class="capsule-card-content">${this._escapeHtml(card.back)}</div>
            ${card.hint ? `<div class="capsule-card-hint">💡 ${this._escapeHtml(card.hint)}</div>` : ''}
            <div class="capsule-ai-badge">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>
                AI 生成
            </div>
        `;
        if (counter) counter.textContent = `${this.currentIndex + 1} / ${this.cards.length}`;
        if (sessionInfo) sessionInfo.textContent = `已掌握 ${this.sessionStats.cardsMastered} / ${this.cards.length}`;
        const masterBtn = document.getElementById('capsule-master-btn');
        const favBtn = document.getElementById('capsule-fav-btn');
        const notePanel = document.getElementById('capsule-note-panel');
        const noteInput = document.getElementById('capsule-note-input');
        if (masterBtn) masterBtn.classList.toggle('mastered', !!prog.is_mastered);
        if (favBtn) favBtn.classList.toggle('favorited', !!prog.is_favorite);
        if (notePanel) notePanel.classList.add('collapsed');
        if (noteInput) noteInput.value = prog.user_note || '';
        this.updateOrbitCurrent();
        this.renderNavPodList();
    }

    flip() {
        if (!this.immersiveMode) {
            const card = document.getElementById('flashcard-card');
            if (card) {
                this.flipped = !this.flipped;
                card.classList.toggle('flipped', this.flipped);
                this._clearAutoFlip();
                const hintEl = document.getElementById('flashcard-auto-flip-hint');
                if (this.flipped && hintEl) hintEl.style.opacity = '0';
                if (this.flipped) {
                    this._clearCountdown();
                    this._clearCountdownState();
                }
            }
            return;
        }
        // 沉浸模式：倒计时结束前禁止翻转
        if (this.immersiveCountdown.active && this.immersiveCountdown.timeLeft > 0) {
            this._showNoFlipHint();
            return;
        }
        const card3d = document.getElementById('capsule-card-3d');
        if (!card3d) return;
        this.flipped = !this.flipped;
        card3d.classList.toggle('flipped', this.flipped);
        if (this.flipped && !this._hasAnsweredCurrent()) {
            this.sessionStats.cardsAnswered++;
            this.updateStatsUI();
        }
        // 翻转后隐藏倒计时条
        const bar = document.getElementById('capsule-countdown-bar');
        const text = document.getElementById('capsule-countdown-text');
        if (bar) bar.classList.add('hidden');
        if (text) text.style.opacity = '0';
    }

    _showNoFlipHint() {
        const container = document.querySelector('.capsule-card-container');
        if (!container) return;
        container.classList.remove('no-flip');
        void container.offsetWidth; // force reflow
        container.classList.add('no-flip');
        const overlay = document.getElementById('capsule-thinking-overlay');
        if (overlay) {
            overlay.classList.add('active');
            setTimeout(() => overlay.classList.remove('active'), 800);
        }
        setTimeout(() => container.classList.remove('no-flip'), 400);
    }

    async toggleMastered() {
        const card = this.cards[this.currentIndex];
        const hash = this._hashCard(card.front, card.back);
        const prog = this.cardProgress[hash] || {};
        const newState = !prog.is_mastered;
        prog.is_mastered = newState ? 1 : 0;
        prog.is_favorite = prog.is_favorite || 0;
        prog.difficulty = prog.difficulty || 'medium';
        prog.user_note = prog.user_note || '';
        prog.review_count = (prog.review_count || 0) + 1;
        this.cardProgress[hash] = prog;
        if (newState) {
            this.sessionStats.cardsMastered++;
            this._showMasteryBurst();
        } else {
            this.sessionStats.cardsMastered = Math.max(0, this.sessionStats.cardsMastered - 1);
        }
        const btn = document.getElementById('capsule-master-btn');
        if (btn) btn.classList.toggle('mastered', newState);
        this.updateOrbitCurrent();
        this.renderNavPodList();
        this.updateStatsUI();
        if (this.userId) await this._saveProgressToDB(card, prog);
        this.checkCompletion();
        if (newState) {
            schedulePathRefresh('flashcard_mastered');
            updateEvaluation({ flashcardsStudied: (evaluation.flashcardsStudied || 0) + 1 });
        }
    }

    async toggleFavorite() {
        const card = this.cards[this.currentIndex];
        const hash = this._hashCard(card.front, card.back);
        const prog = this.cardProgress[hash] || {};
        const newState = !prog.is_favorite;
        prog.is_favorite = newState ? 1 : 0;
        prog.is_mastered = prog.is_mastered || 0;
        prog.difficulty = prog.difficulty || 'medium';
        prog.user_note = prog.user_note || '';
        this.cardProgress[hash] = prog;
        if (newState) this.sessionStats.cardsFavorited++;
        else this.sessionStats.cardsFavorited = Math.max(0, this.sessionStats.cardsFavorited - 1);
        const btn = document.getElementById('capsule-fav-btn');
        if (btn) btn.classList.toggle('favorited', newState);
        this.updateOrbitCurrent();
        this.renderNavPodList();
        if (this.userId) await this._saveProgressToDB(card, prog);
    }

    toggleNotePanel() {
        const panel = document.getElementById('capsule-note-panel');
        if (panel) panel.classList.toggle('collapsed');
    }

    async saveNote(text) {
        const card = this.cards[this.currentIndex];
        const hash = this._hashCard(card.front, card.back);
        const prog = this.cardProgress[hash] || {};
        prog.user_note = text;
        this.cardProgress[hash] = prog;
        if (this.userId) await this._saveProgressToDB(card, prog);
    }

    toggleDataPod() {
        this.dataPodOpen = !this.dataPodOpen;
        const pod = document.getElementById('capsule-data-pod');
        if (pod) pod.classList.toggle('collapsed', !this.dataPodOpen);
        if (this.dataPodOpen) this.updateStatsUI();
    }

    toggleNavPod() {
        this.navPodOpen = !this.navPodOpen;
        const pod = document.getElementById('capsule-nav-pod');
        if (pod) pod.classList.toggle('collapsed', !this.navPodOpen);
        if (this.navPodOpen) this.renderNavPodList();
    }

    renderNavPodList() {
        const list = document.getElementById('capsule-nav-pod-list');
        if (!list) return;
        list.innerHTML = '';
        const filtered = this.cards.map((c, i) => ({ card: c, index: i })).filter(({ card }) => {
            const hash = this._hashCard(card.front, card.back);
            const prog = this.cardProgress[hash] || {};
            if (this.filterMode === 'unmastered') return !prog.is_mastered;
            if (this.filterMode === 'favorite') return prog.is_favorite;
            return true;
        });
        filtered.forEach(({ card, index }) => {
            const hash = this._hashCard(card.front, card.back);
            const prog = this.cardProgress[hash] || {};
            const item = document.createElement('div');
            item.className = 'capsule-nav-pod-item';
            if (index === this.currentIndex) item.classList.add('current');
            if (prog.is_mastered) item.classList.add('mastered');
            if (prog.is_favorite) item.classList.add('favorite');
            item.innerHTML = `
                <div class="item-index">${index + 1}</div>
                <div class="item-text">${this._escapeHtml(card.front.slice(0, 30))}${card.front.length > 30 ? '...' : ''}</div>
                <div class="item-badges">
                    ${prog.is_mastered ? '<div class="item-badge mastered"></div>' : ''}
                    ${prog.is_favorite ? '<div class="item-badge favorite"></div>' : ''}
                </div>
            `;
            item.onclick = () => this.jumpToCard(index);
            list.appendChild(item);
        });
    }

    filterCards(mode) {
        this.filterMode = mode;
        document.querySelectorAll('.capsule-nav-pod-filter .filter-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.filter === mode);
        });
        this.renderNavPodList();
    }

    jumpToCard(index) {
        if (index < 0 || index >= this.cards.length || index === this.currentIndex) return;
        const direction = index > this.currentIndex ? 1 : -1;
        this.currentIndex = index;
        const card3d = document.getElementById('capsule-card-3d');
        if (card3d) {
            card3d.classList.add(direction > 0 ? 'slide-out-left' : 'slide-out-right');
            setTimeout(() => {
                this.renderCardImmersive();
                this._restartImmersiveCountdown();
                card3d.classList.remove('slide-out-left', 'slide-out-right');
                card3d.classList.add(direction > 0 ? 'slide-in-right' : 'slide-in-left');
                setTimeout(() => card3d.classList.remove('slide-in-right', 'slide-in-left'), 300);
            }, 250);
        } else {
            this.renderCardImmersive();
            this._restartImmersiveCountdown();
        }
    }

    _navigateCard(direction) {
        const nextIndex = this.currentIndex + direction;
        if (nextIndex >= 0 && nextIndex < this.cards.length) {
            this.jumpToCard(nextIndex);
        }
    }

    next() {
        if (this.immersiveMode) {
            this._navigateCard(1);
            return;
        }
        if (this.currentIndex < this.cards.length - 1) {
            this.currentIndex++;
            this._clearCountdownState();
            this.renderCard();
        }
    }

    updateStatsUI() {
        const total = this.cards.length;
        const mastered = this.sessionStats.cardsMastered;
        const percent = total > 0 ? Math.round((mastered / total) * 100) : 0;
        const ringFill = document.getElementById('capsule-stat-ring-fill');
        if (ringFill) {
            const circumference = 2 * Math.PI * 42;
            ringFill.style.strokeDashoffset = circumference - (percent / 100) * circumference;
        }
        const percentEl = document.getElementById('capsule-stat-percent');
        if (percentEl) percentEl.textContent = percent + '%';
        const todayEl = document.getElementById('capsule-stat-today');
        if (todayEl) todayEl.textContent = this.sessionStats.cardsAnswered;
        const totalEl = document.getElementById('capsule-stat-total');
        if (totalEl) totalEl.textContent = this.userStats.totalCards + this.sessionStats.cardsAnswered;
        const streakEl = document.getElementById('capsule-stat-streak');
        if (streakEl) streakEl.textContent = this.userStats.streakDays;
        const sessionInfo = document.getElementById('capsule-session-info');
        if (sessionInfo) sessionInfo.textContent = `已掌握 ${mastered} / ${total}`;
    }

    checkCompletion() {
        const total = this.cards.length;
        const mastered = this.sessionStats.cardsMastered;
        if (total > 0 && mastered >= total) {
            setTimeout(() => this.showCompletion(), 600);
        }
    }

    showCompletion() {
        const completion = document.getElementById('capsule-completion');
        const text = document.getElementById('capsule-completion-text');
        if (text) text.textContent = `已掌握 ${this.sessionStats.cardsMastered}/${this.cards.length} 张胶囊`;
        if (completion) completion.classList.remove('hidden');
        this._fireConfetti();
    }

    _hasAnsweredCurrent() {
        const card = this.cards[this.currentIndex];
        const hash = this._hashCard(card.front, card.back);
        return (this.cardProgress[hash]?.review_count || 0) > 0;
    }

    _hashCard(front, back) {
        let h = 0;
        const str = (front || '') + '|' + (back || '');
        for (let i = 0; i < str.length; i++) {
            h = ((h << 5) - h) + str.charCodeAt(i);
            h |= 0;
        }
        return 'c' + Math.abs(h).toString(36);
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    _handleImmersiveKey(e) {
        switch (e.key) {
            case 'Escape': this.exitImmersive(); break;
            case 'ArrowLeft': e.preventDefault(); this.prev(); break;
            case 'ArrowRight': e.preventDefault(); this.next(); break;
            case ' ':
                e.preventDefault();
                if (this.immersiveCountdown.active && this.immersiveCountdown.timeLeft > 0) {
                    this._showNoFlipHint();
                } else {
                    this.flip();
                }
                break;
            case 'f': case 'F': this.toggleFavorite(); break;
            case 'm': case 'M': this.toggleMastered(); break;
            case 'n': case 'N': this.toggleNotePanel(); break;
            case 'd': case 'D': this.toggleDataPod(); break;
            case 'l': case 'L': this.toggleNavPod(); break;
        }
    }

    // ========== 星云粒子动画 ==========
    _initNebula() {
        const canvas = document.getElementById('capsule-nebula-canvas');
        if (!canvas) return;
        this.nebulaCanvas = canvas;
        this.nebulaCtx = canvas.getContext('2d');
        this._resizeNebula();
        this.particles = [];
        for (let i = 0; i < 80; i++) {
            this.particles.push(this._createParticle());
        }
        this._animateNebula();
        window.addEventListener('resize', this._resizeNebula);
    }

    _createParticle() {
        const w = this.nebulaCanvas?.width || window.innerWidth;
        const h = this.nebulaCanvas?.height || window.innerHeight;
        return {
            x: Math.random() * w,
            y: Math.random() * h,
            r: Math.random() * 2 + 0.5,
            dx: (Math.random() - 0.5) * 0.3,
            dy: (Math.random() - 0.5) * 0.3,
            alpha: Math.random() * 0.5 + 0.1,
            color: ['rgba(100,149,237,', 'rgba(139,92,246,', 'rgba(59,130,246,', 'rgba(147,197,253,'][Math.floor(Math.random() * 4)]
        };
    }

    _resizeNebula = () => {
        if (!this.nebulaCanvas) return;
        this.nebulaCanvas.width = window.innerWidth;
        this.nebulaCanvas.height = window.innerHeight;
    }

    _animateNebula = () => {
        if (!this.nebulaCtx || !this.nebulaCanvas) return;
        const ctx = this.nebulaCtx;
        const w = this.nebulaCanvas.width;
        const h = this.nebulaCanvas.height;
        ctx.clearRect(0, 0, w, h);
        this.particles.forEach(p => {
            p.x += p.dx;
            p.y += p.dy;
            if (p.x < 0) p.x = w;
            if (p.x > w) p.x = 0;
            if (p.y < 0) p.y = h;
            if (p.y > h) p.y = 0;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = p.color + p.alpha + ')';
            ctx.fill();
        });
        this._nebularAF = requestAnimationFrame(this._animateNebula);
    }

    _destroyNebula() {
        if (this._nebularAF) {
            cancelAnimationFrame(this._nebularAF);
            this._nebularAF = null;
        }
        window.removeEventListener('resize', this._resizeNebula);
        this.nebulaCanvas = null;
        this.nebulaCtx = null;
        this.particles = [];
    }

    // ========== 沉浸模式倒计时 ==========
    _initImmersiveCountdown() {
        this._clearImmersiveCountdown();
        const totalSec = Math.floor(this.immersiveCountdownDelay / 1000);
        this.immersiveCountdown.totalTime = totalSec;
        this.immersiveCountdown.timeLeft = totalSec;
        this.immersiveCountdown.active = true;
        this.immersiveCountdown.startTs = Date.now();
        this._updateImmersiveCountdownUI();
        this.immersiveCountdown.interval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.immersiveCountdown.startTs) / 1000);
            this.immersiveCountdown.timeLeft = Math.max(0, this.immersiveCountdown.totalTime - elapsed);
            this._updateImmersiveCountdownUI();
            if (this.immersiveCountdown.timeLeft <= 0) {
                this._clearImmersiveCountdown();
            }
        }, 1000);
        this.immersiveCountdown.timer = setTimeout(() => {
            this._clearImmersiveCountdown();
        }, this.immersiveCountdownDelay);
    }

    _restartImmersiveCountdown() {
        this._initImmersiveCountdown();
    }

    _clearImmersiveCountdown() {
        if (this.immersiveCountdown.interval) {
            clearInterval(this.immersiveCountdown.interval);
            this.immersiveCountdown.interval = null;
        }
        if (this.immersiveCountdown.timer) {
            clearTimeout(this.immersiveCountdown.timer);
            this.immersiveCountdown.timer = null;
        }
        this.immersiveCountdown.active = false;
        this.immersiveCountdown.timeLeft = 0;
        this._updateImmersiveCountdownUI(true);
    }

    _updateImmersiveCountdownUI(expired = false) {
        const bar = document.getElementById('capsule-countdown-fill');
        const text = document.getElementById('capsule-countdown-text');
        const hint = document.getElementById('capsule-flip-hint');
        if (!bar || !text) return;
        const timeLeft = this.immersiveCountdown.timeLeft;
        const total = this.immersiveCountdown.totalTime;
        const pct = total > 0 ? (timeLeft / total) * 100 : 0;
        bar.style.width = pct + '%';
        text.textContent = this._formatTime(timeLeft);
        text.classList.remove('warning', 'expired');
        bar.classList.remove('warning', 'expired');
        if (expired || timeLeft <= 0) {
            text.classList.add('expired');
            bar.classList.add('expired');
            if (hint) hint.textContent = '点击翻转查看答案';
        } else if (timeLeft <= 10) {
            text.classList.add('warning');
            bar.classList.add('warning');
        }
    }

    _formatTime(seconds) {
        if (typeof seconds !== 'number' || !isFinite(seconds) || seconds <= 0) return '00:00';
        const totalSec = Math.floor(Math.max(0, seconds));
        const mins = Math.floor(totalSec / 60);
        const secs = totalSec % 60;
        return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }

    // ========== 视觉反馈 ==========
    _showMasteryBurst() {
        const stage = document.getElementById('capsule-card-stage');
        if (!stage) return;
        const burst = document.createElement('div');
        burst.className = 'mastery-burst';
        const rect = stage.getBoundingClientRect();
        burst.style.left = rect.left + rect.width / 2 + 'px';
        burst.style.top = rect.top + rect.height / 2 + 'px';
        for (let i = 0; i < 12; i++) {
            const p = document.createElement('div');
            p.className = 'mastery-burst-particle';
            const angle = (Math.PI * 2 / 12) * i;
            const dist = 60 + Math.random() * 40;
            p.style.setProperty('--tx', Math.cos(angle) * dist + 'px');
            p.style.setProperty('--ty', Math.sin(angle) * dist + 'px');
            burst.appendChild(p);
        }
        document.body.appendChild(burst);
        setTimeout(() => burst.remove(), 900);
    }

    _fireConfetti() {
        const colors = ['#fbbf24', '#f59e0b', '#22c55e', '#3b82f6', '#8b5cf6', '#ef4444'];
        for (let i = 0; i < 60; i++) {
            setTimeout(() => {
                const el = document.createElement('div');
                el.style.cssText = `
                    position: fixed; z-index: 9999; width: 8px; height: 8px; border-radius: 50%;
                    background: ${colors[Math.floor(Math.random() * colors.length)]};
                    left: 50%; top: 50%;
                    pointer-events: none;
                `;
                const dx = (Math.random() - 0.5) * 600;
                const dy = (Math.random() - 0.5) * 600 - 100;
                el.style.transition = 'all 1s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                document.body.appendChild(el);
                requestAnimationFrame(() => {
                    el.style.transform = `translate(${dx}px, ${dy}px) scale(0)`;
                    el.style.opacity = '0';
                });
                setTimeout(() => el.remove(), 1000);
            }, i * 20);
        }
    }

    // ========== 数据库同步 ==========
    async _saveProgressToDB(card, prog) {
        if (!this.userId) return;
        try {
            const body = {
                user_id: this.userId,
                card_hash: this._hashCard(card.front, card.back),
                course_id: 'bigdata',
                chapter_name: card.chapter || '',
                front: card.front,
                back: card.back,
                hint: card.hint || '',
                is_mastered: prog.is_mastered ? 1 : 0,
                is_favorite: prog.is_favorite ? 1 : 0,
                difficulty: prog.difficulty || 'medium',
                user_note: prog.user_note || '',
                review_count: prog.review_count || 0,
            };
            await fetch(`${API_BASE}/api/v2/flashcard/progress`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
        } catch (e) { console.warn('[Flashcard] Save progress failed:', e); }
    }

    async _loadProgressFromDB() {
        if (!this.userId) return;
        try {
            const res = await fetch(`${API_BASE}/api/v2/flashcard/progress?user_id=${this.userId}&course_id=bigdata`);
            const data = await res.json();
            if (data.success && data.data) {
                data.data.forEach(p => {
                    this.cardProgress[p.card_hash] = p;
                });
            }
        } catch (e) { console.warn('[Flashcard] Load progress failed:', e); }
        try {
            const res = await fetch(`${API_BASE}/api/v2/flashcard/stats?user_id=${this.userId}`);
            const data = await res.json();
            if (data.success && data.data) {
                this.userStats = { ...this.userStats, ...data.data };
            }
        } catch (e) { console.warn('[Flashcard] Load stats failed:', e); }
    }

    async _saveSessionToDB() {
        if (!this.userId) return;
        try {
            const session = {
                user_id: this.userId,
                course_id: 'bigdata',
                cards_total: this.sessionStats.cardsTotal,
                cards_answered: this.sessionStats.cardsAnswered,
                cards_mastered: this.sessionStats.cardsMastered,
                cards_favorited: this.sessionStats.cardsFavorited,
                duration_seconds: this.sessionStats.duration,
                session_json: JSON.stringify({ cardProgress: this.cardProgress }),
            };
            await fetch(`${API_BASE}/api/v2/flashcard/session`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(session),
            });
        } catch (e) { console.warn('[Flashcard] Save session failed:', e); }
    }
}

function toggleSection(sectionId, btnEl) {
    const section = document.getElementById(sectionId);
    if (!section) return;
    const isCollapsed = section.classList.contains('collapsed');
    if (isCollapsed) {
        section.classList.remove('collapsed');
        if (btnEl) {
            btnEl.classList.remove('collapsed');
            btnEl.setAttribute('aria-expanded', 'true');
            const icon = btnEl.querySelector('.expand-icon');
            const text = btnEl.querySelector('.expand-text');
            if (icon) icon.style.transform = 'rotate(0deg)';
            if (text) text.textContent = '收起';
        }
    } else {
        section.classList.add('collapsed');
        if (btnEl) {
            btnEl.classList.add('collapsed');
            btnEl.setAttribute('aria-expanded', 'false');
            const icon = btnEl.querySelector('.expand-icon');
            const text = btnEl.querySelector('.expand-text');
            if (icon) icon.style.transform = 'rotate(-180deg)';
            if (text) text.textContent = '展开';
        }
    }
}

window.flowMode = new FlowModeManager();
window.flashcardUI = new FlashcardUI();

function goToPlantFarm() {
    const modal = document.getElementById('plant-reward-modal');
    if (modal) {
        modal.classList.remove('visible');
        setTimeout(() => modal.classList.add('hidden'), 300);
    }
    window.location.href = '/plant.html';
}

class SidebarManager {
    constructor() {
        this.prefs = JSON.parse(localStorage.getItem('starlearn_sidebar_prefs') || '{}');
        this._debounceTimers = {};
    }

    init() {
        if (this.prefs.leftCollapsed === undefined) {
            this.prefs.leftCollapsed = true;
        }
        if (this.prefs.rightCollapsed === undefined) {
            this.prefs.rightCollapsed = false;
        }
        if (this.prefs.leftCollapsed) {
            document.getElementById('left-col')?.classList.add('collapsed');
        }
        if (this.prefs.rightCollapsed) {
            document.getElementById('right-col')?.classList.add('collapsed');
        }
        this._updateToggleIcons();
        this._updateExpandBtns();
    }

    toggleLeft() {
        if (this._debounceTimers.left) return;
        this._debounceTimers.left = true;
        setTimeout(() => { this._debounceTimers.left = false; }, 350);
        const col = document.getElementById('left-col');
        if (!col) return;
        col.classList.toggle('collapsed');
        this.prefs.leftCollapsed = col.classList.contains('collapsed');
        this._savePrefs();
        this._updateToggleIcons();
        this._updateExpandBtns();
    }

    toggleRight() {
        if (this._debounceTimers.right) return;
        this._debounceTimers.right = true;
        setTimeout(() => { this._debounceTimers.right = false; }, 350);
        const col = document.getElementById('right-col');
        if (!col) return;
        col.classList.toggle('collapsed');
        this.prefs.rightCollapsed = col.classList.contains('collapsed');
        this._savePrefs();
        this._updateToggleIcons();
        this._updateExpandBtns();
    }

    _updateToggleIcons() {
        const leftCol = document.getElementById('left-col');
        const rightCol = document.getElementById('right-col');
        const leftBtn = leftCol?.querySelector('.sidebar-toggle-btn svg');
        const rightBtn = rightCol?.querySelector('.sidebar-toggle-btn svg');
        const rightInlineBtn = document.getElementById('right-toggle-inline')?.querySelector('svg');
        if (leftBtn) {
            leftBtn.innerHTML = leftCol.classList.contains('collapsed')
                ? '<polyline points="9 18 15 12 9 6"></polyline>'
                : '<polyline points="15 18 9 12 15 6"></polyline>';
        }
        if (rightBtn) {
            rightBtn.innerHTML = rightCol.classList.contains('collapsed')
                ? '<polyline points="15 18 9 12 15 6"></polyline>'
                : '<polyline points="9 18 15 12 9 6"></polyline>';
        }
        if (rightInlineBtn) {
            rightInlineBtn.innerHTML = rightCol.classList.contains('collapsed')
                ? '<polyline points="15 18 9 12 15 6"></polyline>'
                : '<polyline points="9 18 15 12 9 6"></polyline>';
        }
    }

    _updateExpandBtns() {
        const leftCol = document.getElementById('left-col');
        const rightCol = document.getElementById('right-col');
        const leftExpand = document.getElementById('left-expand-btn');
        const rightExpand = document.getElementById('right-expand-btn');
        if (leftExpand) {
            leftExpand.classList.toggle('visible', leftCol?.classList.contains('collapsed'));
        }
        if (rightExpand) {
            rightExpand.classList.toggle('visible', rightCol?.classList.contains('collapsed'));
        }
    }

    _savePrefs() {
        localStorage.setItem('starlearn_sidebar_prefs', JSON.stringify(this.prefs));
    }
}

window.sidebarManager = new SidebarManager();

class LightboxManager {
    constructor() {
        this.overlay = null;
        this.img = null;
        this.closeBtn = null;
        this.isOpen = false;
        this._dragState = null;
        this._initialized = false;
        this._boundOnDblClick = this._onDblClick.bind(this);
        this._boundOnBackdropClick = this._onBackdropClick.bind(this);
        this._boundOnKeyDown = this._onKeyDown.bind(this);
        this._boundOnDragStart = this._onDragStart.bind(this);
        this._boundOnDragMove = this._onDragMove.bind(this);
        this._boundOnDragEnd = this._onDragEnd.bind(this);
    }

    init() {
        if (this._initialized) return;
        this.overlay = document.getElementById('lightbox-overlay');
        this.img = document.getElementById('lightbox-img');
        this.closeBtn = document.getElementById('lightbox-close-btn');
        if (!this.overlay) return;
        this.overlay.querySelector('.lightbox-backdrop').addEventListener('click', this._boundOnBackdropClick);
        this.closeBtn?.addEventListener('click', () => this.close());
        this.img?.addEventListener('mousedown', this._boundOnDragStart);
        this.img?.addEventListener('touchstart', this._boundOnDragStart, { passive: false });
        document.addEventListener('mousemove', this._boundOnDragMove);
        document.addEventListener('touchmove', this._boundOnDragMove, { passive: false });
        document.addEventListener('mouseup', this._boundOnDragEnd);
        document.addEventListener('touchend', this._boundOnDragEnd);
        this._observeChat();
        this._initialized = true;
    }

    _observeChat() {
        const chatContainer = document.getElementById('chat-container');
        if (!chatContainer) return;
        const observer = new MutationObserver(() => this._bindImages());
        observer.observe(chatContainer, { childList: true, subtree: true });
        this._bindImages();
    }

    _bindImages() {
        const chatContainer = document.getElementById('chat-container');
        if (!chatContainer) return;
        const images = chatContainer.querySelectorAll('.msg-bubble-bot img, .prose img');
        images.forEach(img => {
            if (!img.dataset.lightboxBound) {
                img.dataset.lightboxBound = 'true';
                img.addEventListener('dblclick', this._boundOnDblClick);
            }
        });
    }

    _onDblClick(e) {
        e.preventDefault();
        const img = e.currentTarget;
        if (img.src) {
            this.open(img.src, img.alt || '');
        }
    }

    open(src, alt = '') {
        this.init();
        if (!this.overlay || !this.img) return;
        this.img.src = src;
        this.img.alt = alt || '放大预览';
        this.img.style.transform = '';
        this._dragState = null;
        this.overlay.classList.remove('closing');
        this.overlay.classList.add('open');
        this.isOpen = true;
        document.addEventListener('keydown', this._boundOnKeyDown);
        document.body.style.overflow = 'hidden';
    }

    close() {
        if (!this.overlay || !this.isOpen) return;
        this.overlay.classList.add('closing');
        this.overlay.classList.remove('open');
        this.isOpen = false;
        document.removeEventListener('keydown', this._boundOnKeyDown);
        setTimeout(() => {
            this.overlay?.classList.remove('closing');
            this.img.src = '';
            this.img.style.transform = '';
            this._dragState = null;
        }, 300);
    }

    _onBackdropClick(e) {
        if (e.target === e.currentTarget) {
            this.close();
        }
    }

    _onKeyDown(e) {
        if (e.key === 'Escape') {
            this.close();
        }
    }

    _onDragStart(e) {
        if (!this.isOpen) return;
        e.preventDefault();
        const pos = e.touches ? e.touches[0] : e;
        this._dragState = {
            startX: pos.clientX,
            startY: pos.clientY,
            offsetX: 0,
            offsetY: 0,
        };
        this.img.classList.add('dragging');
    }

    _onDragMove(e) {
        if (!this._dragState) return;
        e.preventDefault();
        const pos = e.touches ? e.touches[0] : e;
        this._dragState.offsetX = pos.clientX - this._dragState.startX;
        this._dragState.offsetY = pos.clientY - this._dragState.startY;
        this.img.style.transform = `translate(${this._dragState.offsetX}px, ${this._dragState.offsetY}px)`;
    }

    _onDragEnd() {
        if (!this._dragState) return;
        this._dragState = null;
        this.img.classList.remove('dragging');
        this.img.style.transform = '';
    }
}

window.lightboxManager = new LightboxManager();

class MusicPanel {
    constructor() {
        this.isOpen = false;
        this.currentIndex = -1;
        this.isPlaying = false;
        this.currentGenre = 'all';
        this.audio = new Audio();
        this.audio.volume = 0.6;
        this._previousVolume = 60;
        const slider = document.getElementById('music-volume-slider');
        const label = document.getElementById('music-volume-label');
        if (slider) slider.value = 60;
        if (label) label.textContent = '60';
        this._boundOnError = this._onAudioError.bind(this);
        this._boundOnEnded = this._onAudioEnded.bind(this);
        this.audio.addEventListener('error', this._boundOnError);
        this.audio.addEventListener('ended', this._boundOnEnded);

        this.songs = this._createSongData();
        this._renderGenres();
        this._renderList();
    }

    _createSongData() {
        const genres = {
            piano: {
                label: '经典钢琴',
                colors: ['#818cf8', '#6366f1', '#a5b4fc'],
                shapes: ['circle', 'diamond', 'hexagon', 'star', 'triangle']
            },
            ambient: {
                label: '环境音乐',
                colors: ['#34d399', '#10b981', '#6ee7b7'],
                shapes: ['circle', 'diamond', 'hexagon', 'star', 'triangle']
            },
            nature: {
                label: '自然声',
                colors: ['#fbbf24', '#f59e0b', '#fcd34d'],
                shapes: ['circle', 'diamond', 'hexagon', 'star', 'triangle']
            },
            lofi: {
                label: '低保真',
                colors: ['#f472b6', '#ec4899', '#f9a8d4'],
                shapes: ['circle', 'diamond', 'hexagon', 'star', 'triangle']
            }
        };

        const rawFiles = [
            { file: 'clavier-music-song-from-a-secret-garden-sad-piano-205576.mp3', genre: 'piano' },
            { file: 'sigmamusicart-emotional-piano-music-256262.mp3', genre: 'piano' },
            { file: 'nickpanekaiassets-peaceful-piano-background-music-218762.mp3', genre: 'piano' },
            { file: 'paulyudin-piano-background-182519.mp3', genre: 'piano' },
            { file: 'viacheslavstarostin-piano-background-music-soft-344547.mp3', genre: 'piano' },

            { file: 'good_b_music-ambient-piano-and-strings-10711.mp3', genre: 'ambient' },
            { file: 'music_for_video-please-calm-my-mind-125566.mp3', genre: 'ambient' },
            { file: 'the_mountain-soft-background-music-492811.mp3', genre: 'ambient' },
            { file: 'joyinsound-inspiring-soft-corporate-background-music-391736.mp3', genre: 'ambient' },
            { file: 'sigmamusicart-inspiring-inspirational-background-music-412596.mp3', genre: 'ambient' },

            { file: 'sergepavkinmusic-field-grass-115973.mp3', genre: 'nature' },
            { file: 'the_mountain-piano-background-music-487020.mp3', genre: 'nature' },
            { file: 'trtasfiq-sad-piano-instrumental-background-music-279069.mp3', genre: 'nature' },
            { file: 'white_records-legacy-of-vivaldi-epic-background-orchestral-music-hip-hop-version-143986.mp3', genre: 'nature' },
            { file: 'joyinsound-corporate-upbeat-motivational-music-403406.mp3', genre: 'nature' },

            { file: 'ikoliks_aj-jazz-lounge-elevator-music-332339.mp3', genre: 'lofi' },
            { file: '34910776-for-her-chill-upbeat-summel-travel-vlog-and-ig-music-royalty-free-use-202298.mp3', genre: 'lofi' },
            { file: 'lnplusmusic-vlogs-background-music-335289.mp3', genre: 'lofi' },
            { file: 'kontraa-hype-drill-music-438398.mp3', genre: 'lofi' },
            { file: 'paulyudin-happy-happy-music-513014.mp3', genre: 'lofi' }
        ];

        const songs = rawFiles.map((item, i) => {
            const title = this._cleanFileName(item.file);
            return {
                id: i + 1,
                title: title,
                artist: this._genreArtist(item.genre),
                genre: item.genre,
                duration: this._estimateDuration(item.file),
                audioUrl: `/static/audio/${item.file}`
            };
        });

        return songs.map((song, i) => {
            const g = genres[song.genre];
            const shapeIdx = i % g.shapes.length;
            song.coverSvg = this._generateCoverSvg(g.shapes[shapeIdx], g.colors, song.genre, song.id);
            return song;
        });
    }

    _cleanFileName(filename) {
        let name = filename.replace(/\.mp3$/i, '');
        name = name.replace(/^\d+-/, '');
        name = name.replace(/_+/g, ' ');
        name = name.replace(/-/g, ' ');
        const parts = name.split(/\s+/);
        const stopWords = new Set(['music', 'background', 'royalty', 'free', 'use', 'for', 'and', 'the', 'of', 'video', 'vlog', 'ig']);
        const filtered = parts.filter(p => !stopWords.has(p.toLowerCase()) && !/^\d{5,}$/.test(p));
        const title = filtered.map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
        return title || name.replace(/\.mp3$/i, '');
    }

    _genreArtist(genre) {
        const map = { piano: 'Piano Collection', ambient: 'Ambient Space', nature: 'Nature Sound', lofi: 'Lofi Beats' };
        return map[genre] || 'Star-Learn';
    }

    _estimateDuration(filename) {
        let hash = 0;
        for (let i = 0; i < filename.length; i++) hash = ((hash << 5) - hash) + filename.charCodeAt(i);
        const mins = 3 + Math.abs(hash % 6);
        const secs = Math.abs((hash >> 8) % 60);
        return `${mins}:${String(secs).padStart(2, '0')}`;
    }

    _generateCoverSvg(shape, colors, genre, songId) {
        const [c1, c2, c3] = colors;
        let shapeEl = '';

        switch (shape) {
            case 'circle':
                shapeEl = `<circle cx="20" cy="20" r="10" fill="${c3}" opacity="0.9"/><circle cx="20" cy="20" r="5" fill="white" opacity="0.6"/>`;
                break;
            case 'diamond':
                shapeEl = `<rect x="10" y="10" width="14" height="14" rx="2" fill="${c3}" opacity="0.9" transform="rotate(45 17 17)"/><rect x="14" y="14" width="6" height="6" rx="1" fill="white" opacity="0.5" transform="rotate(45 17 17)"/>`;
                break;
            case 'hexagon':
                shapeEl = `<polygon points="20,6 30,12 30,24 20,30 10,24 10,12" fill="${c3}" opacity="0.9"/><polygon points="20,11 25,14 25,22 20,25 15,22 15,14" fill="white" opacity="0.4"/>`;
                break;
            case 'star':
                shapeEl = `<polygon points="20,4 23,14 34,14 25,20 28,30 20,24 12,30 15,20 6,14 17,14" fill="${c3}" opacity="0.9"/><circle cx="20" cy="18" r="3" fill="white" opacity="0.5"/>`;
                break;
            case 'triangle':
                shapeEl = `<polygon points="20,6 32,28 8,28" fill="${c3}" opacity="0.9"/><polygon points="20,13 26,25 14,25" fill="white" opacity="0.4"/>`;
                break;
        }

        const icons = {
            piano: `<rect x="8" y="24" width="3" height="8" rx="0.5" fill="white" opacity="0.7"/><rect x="13" y="24" width="3" height="8" rx="0.5" fill="white" opacity="0.7"/><rect x="18" y="24" width="3" height="8" rx="0.5" fill="white" opacity="0.7"/><rect x="23" y="24" width="3" height="8" rx="0.5" fill="white" opacity="0.7"/><rect x="28" y="24" width="3" height="8" rx="0.5" fill="white" opacity="0.7"/>`,
            ambient: `<circle cx="12" cy="28" r="3" fill="white" opacity="0.5"/><circle cx="20" cy="26" r="4" fill="white" opacity="0.6"/><circle cx="28" cy="28" r="3" fill="white" opacity="0.5"/>`,
            nature: `<path d="M20 28 Q14 22 14 18 Q14 14 20 12 Q26 14 26 18 Q26 22 20 28Z" fill="white" opacity="0.6"/><line x1="20" y1="28" x2="20" y2="32" stroke="white" opacity="0.5" stroke-width="1.5"/>`,
            lofi: `<rect x="10" y="22" width="20" height="12" rx="2" fill="white" opacity="0.5"/><circle cx="16" cy="28" r="3" fill="${c2}" opacity="0.8"/><circle cx="24" cy="28" r="3" fill="${c2}" opacity="0.8"/>`
        };

        const uid = `bg_${songId}_${shape}`;
        return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">
            <defs><linearGradient id="${uid}" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="${c1}"/><stop offset="100%" stop-color="${c2}"/>
            </linearGradient></defs>
            <rect width="40" height="40" rx="8" fill="url(#${uid})"/>
            ${shapeEl}
            ${icons[genre] || ''}
        </svg>`;
    }

    _renderGenres() {
        const container = document.getElementById('music-genres');
        if (!container) return;

        const genres = [
            { key: 'all', label: '全部' },
            { key: 'piano', label: '经典钢琴' },
            { key: 'ambient', label: '环境音乐' },
            { key: 'nature', label: '自然声' },
            { key: 'lofi', label: '低保真' }
        ];

        container.innerHTML = genres.map(g =>
            `<button class="music-genre-chip shrink-0 whitespace-nowrap${g.key === this.currentGenre ? ' active' : ''}" data-genre="${g.key}" onclick="window.musicPanel.filterGenre('${g.key}')">${g.label}</button>`
        ).join('');
    }

    _renderList() {
        const container = document.getElementById('music-list');
        if (!container) return;

        const filtered = this.currentGenre === 'all'
            ? this.songs
            : this.songs.filter(s => s.genre === this.currentGenre);

        container.innerHTML = filtered.map(song => {
            const isPlaying = this.currentIndex >= 0 && this.songs[this.currentIndex].id === song.id;
            return `<div class="music-item${isPlaying ? ' playing' : ''}" data-id="${song.id}" onclick="window.musicPanel.play(${song.id})">
                <div class="music-item-cover">${song.coverSvg}</div>
                <div class="music-item-info">
                    <div class="music-item-title">${song.title}</div>
                    <div class="music-item-meta">
                        <span>${song.artist}</span>
                        <span>·</span>
                        <span>${this._genreLabel(song.genre)}</span>
                    </div>
                </div>
                <div class="music-item-duration">${song.duration}</div>
                <div class="music-item-playing-indicator">
                    <div class="music-playing-bar"></div>
                    <div class="music-playing-bar"></div>
                    <div class="music-playing-bar"></div>
                </div>
            </div>`;
        }).join('');
    }

    _genreLabel(genre) {
        const map = { piano: '钢琴', ambient: '环境', nature: '自然', lofi: 'Lofi' };
        return map[genre] || genre;
    }

    _updatePlayerUI() {
        const titleEl = document.getElementById('music-player-title');
        const artistEl = document.getElementById('music-player-artist');
        const coverEl = document.getElementById('music-player-cover');
        const playIcon = document.getElementById('music-play-icon');
        const toggleBtn = document.getElementById('music-toggle-btn');

        if (this.currentIndex >= 0) {
            const song = this.songs[this.currentIndex];
            if (titleEl) titleEl.textContent = song.title;
            if (artistEl) artistEl.textContent = song.artist;
            if (coverEl) coverEl.innerHTML = song.coverSvg;
        } else {
            if (titleEl) titleEl.textContent = '未选择音乐';
            if (artistEl) artistEl.textContent = '--';
            if (coverEl) coverEl.innerHTML = '';
        }

        if (playIcon) {
            playIcon.innerHTML = this.isPlaying
                ? '<rect x="6" y="4" width="4" height="16" rx="1"></rect><rect x="14" y="4" width="4" height="16" rx="1"></rect>'
                : '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
        }

        if (toggleBtn) {
            toggleBtn.classList.toggle('is-playing', this.isPlaying);
        }

        this._updateMiniPlayer();

        if (window.flowMode && window.flowMode.active) {
            window.flowMode._syncFlowMusicPlayer();
            window.flowMode._renderFlowMusicList();
        }
        if (window.flowMode) {
            window.flowMode.syncVisualizers();
        }
    }

    _updateListItemStates() {
        const items = document.querySelectorAll('.music-item');
        items.forEach(item => {
            const id = parseInt(item.dataset.id);
            const isCurrent = this.currentIndex >= 0 && this.songs[this.currentIndex].id === id;
            item.classList.toggle('playing', isCurrent && this.isPlaying);
        });
    }

    toggle() {
        const panel = document.getElementById('music-panel');
        if (!panel) return;
        this.isOpen = !this.isOpen;
        panel.classList.toggle('open', this.isOpen);
        if (this.isOpen) {
            this._renderGenres();
            this._renderList();
            if (window.focusDurationPanel && window.focusDurationPanel.isOpen) {
                window.focusDurationPanel.toggle();
            }
        }
        const miniPlayer = document.getElementById('mini-player');
        if (miniPlayer && this.currentIndex >= 0) {
            miniPlayer.classList.toggle('visible', !this.isOpen);
        }
    }

    filterGenre(genre) {
        this.currentGenre = genre;
        this._renderGenres();
        this._renderList();
    }

    play(songId) {
        const idx = this.songs.findIndex(s => s.id === songId);
        if (idx < 0) return;

        if (this.currentIndex === idx && this.isPlaying) {
            this.togglePlay();
            return;
        }

        if (this.currentIndex === idx && !this.isPlaying) {
            this.audio.play().catch(() => {});
            this.isPlaying = true;
            this._updatePlayerUI();
            this._updateListItemStates();
            return;
        }

        this.audio.pause();
        this.audio.currentTime = 0;
        this.currentIndex = idx;
        this.audio.src = this.songs[idx].audioUrl;
        this.audio.play().then(() => {
            this.isPlaying = true;
            this._updatePlayerUI();
            this._updateListItemStates();
        }).catch((err) => {
            console.warn('[MusicPanel] Play failed:', err);
            this._showError('音频加载失败，请稍后重试');
        });
    }

    togglePlay() {
        if (this.currentIndex < 0) {
            if (this.songs.length > 0) {
                this.play(this.songs[0].id);
            }
            return;
        }

        if (this.isPlaying) {
            this.audio.pause();
            this.isPlaying = false;
        } else {
            this.audio.play().catch(() => {
                this._showError('播放失败，请检查网络连接');
            });
            this.isPlaying = true;
        }
        this._updatePlayerUI();
        this._updateListItemStates();
    }

    prev() {
        if (this.songs.length === 0) return;

        if (this.currentGenre !== 'all') {
            const filtered = this.songs.filter(s => s.genre === this.currentGenre);
            if (filtered.length === 0) return;
            if (this.currentIndex < 0) { this.play(filtered[filtered.length - 1].id); return; }
            const currentSong = this.songs[this.currentIndex];
            const fIdx = filtered.findIndex(s => s.id === currentSong.id);
            const prevIdx = fIdx <= 0 ? filtered.length - 1 : fIdx - 1;
            this.play(filtered[prevIdx].id);
            return;
        }

        const idx = this.currentIndex < 0 ? this.songs.length - 1 : (this.currentIndex - 1 + this.songs.length) % this.songs.length;
        this.play(this.songs[idx].id);
    }

    next() {
        if (this.songs.length === 0) return;

        if (this.currentGenre !== 'all') {
            const filtered = this.songs.filter(s => s.genre === this.currentGenre);
            if (filtered.length === 0) return;
            if (this.currentIndex < 0) { this.play(filtered[0].id); return; }
            const currentSong = this.songs[this.currentIndex];
            const fIdx = filtered.findIndex(s => s.id === currentSong.id);
            const nextIdx = fIdx >= filtered.length - 1 ? 0 : fIdx + 1;
            this.play(filtered[nextIdx].id);
            return;
        }

        const idx = this.currentIndex < 0 ? 0 : (this.currentIndex + 1) % this.songs.length;
        this.play(this.songs[idx].id);
    }

    _onAudioError(e) {
        console.error('[MusicPanel] Audio error:', e);
        this.isPlaying = false;
        this._updatePlayerUI();
        this._updateListItemStates();
        this._showError('音频加载失败，请检查网络');
    }

    _onAudioEnded() {
        this.next();
    }

    _showError(msg) {
        const existing = document.querySelector('.music-error-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'music-error-toast';
        toast.textContent = msg;
        Object.assign(toast.style, {
            position: 'fixed',
            bottom: '80px',
            right: '20px',
            background: 'var(--danger)',
            color: 'var(--text-on-accent)',
            padding: '8px 16px',
            borderRadius: '10px',
            fontSize: '12px',
            fontWeight: '600',
            zIndex: '300',
            backdropFilter: 'blur(10px)',
            boxShadow: '0 4px 12px var(--danger-bg)',
            animation: 'fadeInUp 0.3s ease',
            pointerEvents: 'none'
        });
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    _updateMiniPlayer() {
        const miniPlayer = document.getElementById('mini-player');
        const miniTitle = document.getElementById('mini-player-title');
        const miniPlayIcon = document.getElementById('mini-play-icon');

        if (!miniPlayer) return;

        const shouldShow = this.currentIndex >= 0;
        miniPlayer.classList.toggle('visible', shouldShow);

        if (miniTitle && this.currentIndex >= 0) {
            miniTitle.textContent = this.songs[this.currentIndex].title;
        } else if (miniTitle) {
            miniTitle.textContent = '未在播放';
        }

        if (miniPlayIcon) {
            miniPlayIcon.innerHTML = this.isPlaying
                ? '<rect x="6" y="4" width="4" height="16" rx="1"></rect><rect x="14" y="4" width="4" height="16" rx="1"></rect>'
                : '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
        }
    }

    setVolume(val) {
        const volume = Math.max(0, Math.min(100, parseInt(val)));
        this.audio.volume = volume / 100;
        const slider = document.getElementById('music-volume-slider');
        const label = document.getElementById('music-volume-label');
        if (slider) slider.value = volume;
        if (label) label.textContent = volume;
        this._updateVolumeIcon();
    }

    toggleMute() {
        if (this.audio.volume > 0) {
            this._previousVolume = this.audio.volume * 100;
            this.audio.volume = 0;
            const slider = document.getElementById('music-volume-slider');
            const label = document.getElementById('music-volume-label');
            if (slider) slider.value = 0;
            if (label) label.textContent = '0';
        } else {
            const vol = this._previousVolume || 60;
            this.audio.volume = vol / 100;
            const slider = document.getElementById('music-volume-slider');
            const label = document.getElementById('music-volume-label');
            if (slider) slider.value = vol;
            if (label) label.textContent = vol;
        }
        this._updateVolumeIcon();
    }

    _updateVolumeIcon() {
        const iconEl = document.getElementById('music-volume-icon');
        if (!iconEl) return;
        const vol = this.audio.volume;
        if (vol === 0) {
            iconEl.innerHTML = '<line x1="1" y1="1" x2="23" y2="23"></line><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>';
        } else if (vol < 0.5) {
            iconEl.innerHTML = '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>';
        } else {
            iconEl.innerHTML = '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>';
        }
    }

    destroy() {
        this.audio.pause();
        this.audio.removeEventListener('error', this._boundOnError);
        this.audio.removeEventListener('ended', this._boundOnEnded);
        this.audio.src = '';
    }
}

window.musicPanel = new MusicPanel();

class FocusDurationPanel {
    constructor() {
        this.isOpen = false;
        this.selectedMinutes = 30;
        this.selectionType = 'preset';
        this.currentMode = 'focus';
        this._initialized = false;
        this.presets = {
            focus: [
                { minutes: 5, label: '5 分钟', sub: '快速' },
                { minutes: 10, label: '10 分钟', sub: '短时' },
                { minutes: 15, label: '15 分钟', sub: '适中' },
                { minutes: 30, label: '30 分钟', sub: '标准' },
                { minutes: 45, label: '45 分钟', sub: '深度' },
                { minutes: 60, label: '60 分钟', sub: '沉浸' }
            ],
            rest: [
                { minutes: 3, label: '3 分钟', sub: '微休' },
                { minutes: 5, label: '5 分钟', sub: '短休' },
                { minutes: 10, label: '10 分钟', sub: '小憩' },
                { minutes: 15, label: '15 分钟', sub: '放松' },
                { minutes: 20, label: '20 分钟', sub: '充电' },
                { minutes: 30, label: '30 分钟', sub: '深度' }
            ]
        };
        this.recentDurations = this._loadRecent();
        this._debounceTimer = null;
    }

    init() {
        if (this._initialized) return;
        this._initialized = true;
        this._renderPresets();
        this._renderRecent();
        this._bindInputEvents();
        this._updateToggleBtn();
    }

    _loadRecent() {
        try {
            return JSON.parse(localStorage.getItem('starlearn_focus_recent') || '[]');
        } catch { return []; }
    }

    _saveRecent(minutes) {
        let recent = this.recentDurations.filter(m => m !== minutes);
        recent.unshift(minutes);
        recent = recent.slice(0, 3);
        this.recentDurations = recent;
        localStorage.setItem('starlearn_focus_recent', JSON.stringify(recent));
    }

    _renderPresets() {
        const container = document.getElementById('focus-presets');
        if (!container) return;

        const presets = this.presets[this.currentMode] || this.presets.focus;
        container.innerHTML = presets.map(p => {
            const isSelected = this.selectedMinutes === p.minutes && this.selectionType === 'preset';
            return `<button class="focus-preset-btn${isSelected ? ' selected' : ''}" data-minutes="${p.minutes}" onclick="window.focusDurationPanel.selectPreset(${p.minutes})">
                <span class="preset-label">${p.label}</span>
                <span class="preset-sub">${p.sub}</span>
            </button>`;
        }).join('');
    }

    _renderRecent() {
        const container = document.getElementById('focus-recent');
        if (!container) return;

        if (this.recentDurations.length === 0) {
            container.innerHTML = '';
            return;
        }

        container.innerHTML = `
            <div class="focus-recent-label">最近使用</div>
            <div class="focus-recent-chips">
                ${this.recentDurations.map(m =>
                    `<button class="focus-recent-chip" onclick="window.focusDurationPanel.selectPreset(${m})">${m}分钟</button>`
                ).join('')}
            </div>`;
    }

    _bindInputEvents() {
        const input = document.getElementById('focus-custom-input');
        if (!input) return;

        input.addEventListener('input', () => {
            const val = input.value.replace(/[^\d]/g, '');
            input.value = val;
            this._clearError();
            input.classList.remove('success', 'invalid');
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.confirmCustom();
            }
        });
    }

    toggle() {
        this.init();
        const panel = document.getElementById('focus-duration-panel');
        if (!panel) return;
        this.isOpen = !this.isOpen;
        panel.classList.toggle('open', this.isOpen);
        if (this.isOpen && window.musicPanel && window.musicPanel.isOpen) {
            window.musicPanel.toggle();
        }
    }

    switchMode(mode) {
        if (this.currentMode === mode) return;
        this.currentMode = mode;
        this.selectedMinutes = mode === 'focus' ? 30 : 15;
        this.selectionType = 'preset';

        const panel = document.getElementById('focus-duration-panel');
        if (panel) panel.classList.toggle('rest-mode', mode === 'rest');

        document.querySelectorAll('.focus-mode-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.mode === mode);
        });

        this._renderPresets();
        this._updateToggleBtn();

        const input = document.getElementById('focus-custom-input');
        if (input) { input.value = ''; input.classList.remove('invalid', 'success'); }
        this._clearError();
    }

    selectPreset(minutes) {
        this.selectedMinutes = minutes;
        this.selectionType = 'preset';
        this._renderPresets();
        this._updateToggleBtn();
        this._animateSelection(minutes);

        const input = document.getElementById('focus-custom-input');
        if (input) {
            input.value = '';
            input.classList.remove('invalid', 'success');
        }
        this._clearError();
    }

    _animateSelection(minutes) {
        const btn = document.querySelector(`.focus-preset-btn[data-minutes="${minutes}"]`);
        if (!btn) return;
        btn.classList.remove('just-selected');
        void btn.offsetWidth;
        btn.classList.add('just-selected');
        setTimeout(() => btn.classList.remove('just-selected'), 300);
    }

    confirmCustom() {
        const input = document.getElementById('focus-custom-input');
        if (!input) return;

        const raw = input.value.trim();
        if (!raw) {
            this._showError('请输入时长');
            input.classList.add('invalid');
            return;
        }

        const minutes = parseInt(raw, 10);

        if (isNaN(minutes)) {
            this._showError('请输入有效数字');
            input.classList.add('invalid');
            return;
        }

        if (minutes < 1 || minutes > 180) {
            this._showError('时长范围：1-180 分钟');
            input.classList.add('invalid');
            return;
        }

        this.selectedMinutes = minutes;
        this.selectionType = 'custom';
        this._renderPresets();
        this._updateToggleBtn();

        input.classList.remove('invalid');
        input.classList.add('success');
        this._clearError();

        const confirmBtn = document.getElementById('focus-custom-confirm');
        if (confirmBtn) {
            confirmBtn.classList.add('success-flash');
            setTimeout(() => confirmBtn.classList.remove('success-flash'), 400);
        }

        setTimeout(() => {
            input.classList.remove('success');
        }, 1500);
    }

    startFocus() {
        const minutes = this.selectedMinutes;
        if (!minutes || minutes < 1) {
            this._showError('请先选择时长');
            return;
        }

        this._saveRecent(minutes);
        this._renderRecent();

        if (window.flowMode) {
            const totalSeconds = minutes * 60;
            window.flowMode.totalSeconds = totalSeconds;
            window.flowMode.remainingSeconds = totalSeconds;
            window.flowMode.currentMode = this.currentMode;
            window.flowMode.selectedMinutes = minutes;
            window.flowMode.state.update({
                total_time: totalSeconds,
                remaining_time: totalSeconds,
                is_timer_running: false,
                is_paused: false,
                is_complete: false
            });

            const island = document.getElementById('flow-dynamic-island');
            if (island) {
                island.classList.toggle('rest-mode', this.currentMode === 'rest');
                island.classList.toggle('flow-island-rest', this.currentMode === 'rest');
                island.classList.add('visible');
            }

            const islandLabel = document.getElementById('island-timer-label');
            if (islandLabel) {
                islandLabel.textContent = this.currentMode === 'rest' ? '休息模式' : '专注模式';
            }

            const overlay = document.getElementById('flow-overlay');
            if (overlay) {
                overlay.classList.toggle('rest-mode', this.currentMode === 'rest');
                // 添加浮动岛模式：显示展开按钮但隐藏中间内容
                overlay.classList.add('floating-mode');
            }

            if (!window.flowMode.active) {
                // 激活心流模式，显示浮动岛，隐藏左右侧边栏，显示展开按钮
                window.flowMode.active = true;
                document.body.classList.add('flow-mode-active');
                // 初始状态下侧边栏是折叠的，显示展开按钮
                window.flowMode.leftSidebarOpen = false;
                window.flowMode.rightSidebarOpen = false;
                window.flowMode._updateSidebarExpandBtns();
                window.flowMode.resetTimer();
                window.flowMode._updateIslandPlayIcon(true);
            } else {
                window.flowMode.resetTimer();
                window.flowMode._renderFlowPresets();
            }
        }

        if (this.isOpen) {
            this.toggle();
        }
    }

    _updateToggleBtn() {
        const btn = document.getElementById('focus-duration-toggle-btn');
        if (!btn) return;
        btn.classList.toggle('has-selection', this.selectedMinutes > 0);
    }

    _showError(msg) {
        const el = document.getElementById('focus-duration-error');
        if (!el) return;
        el.textContent = msg;
        el.classList.add('visible');
    }

    _clearError() {
        const el = document.getElementById('focus-duration-error');
        if (!el) return;
        el.classList.remove('visible');
    }
}

window.focusDurationPanel = new FocusDurationPanel();

// ========== 辩论模式功能 ==========

function isDebateModeEnabled() {
    try {
        const prefs = JSON.parse(localStorage.getItem('starlearn_preferences') || '{}');
        return prefs.debateModeEnabled === true;
    } catch (e) {
        return false;
    }
}

function initDebatePanel() {
    const agentsRow = document.getElementById('debate-agents-row');
    if (!agentsRow) return;

    agentsRow.innerHTML = AGENTS_CONFIG.map(agent => `
        <div class="debate-agent-card" data-agent-id="${agent.id}" style="--agent-color: ${agent.themeColor}">
            <div class="agent-avatar">${agent.icon}</div>
            <div class="agent-name">${agent.name}</div>
            <div class="status-dot"></div>
        </div>
    `).join('');
}

function toggleDebatePanel(expand) {
    const panel = document.getElementById('debate-panel');
    const expandBtn = document.getElementById('debate-panel-expand-btn');
    const collapseBtn = document.getElementById('debate-panel-collapse-btn');
    if (!panel) return;

    if (expand === undefined) {
        expand = !panel.classList.contains('expanded');
    }

    if (expand) {
        panel.classList.add('expanded');
        expandBtn?.classList.add('hidden');
        collapseBtn?.classList.remove('hidden');
    } else {
        panel.classList.remove('expanded');
        expandBtn?.classList.remove('hidden');
        collapseBtn?.classList.add('hidden');
    }
}

function resetDebateState() {
    debateState = {
        isActive: true,
        currentRound: 0,
        agentResponses: {},
        crossComments: {},
        debateHistory: [],
        isComplete: false
    };

    const panel = document.getElementById('debate-panel');
    if (panel) {
        panel.classList.remove('hidden');
        toggleDebatePanel(true);
    }

    const messagesEl = document.getElementById('debate-messages');
    if (messagesEl) messagesEl.innerHTML = '';

    // 隐藏旧的 judge-area（兼容旧结构）
    const judgeArea = document.getElementById('debate-judge-area');
    if (judgeArea) judgeArea.classList.add('hidden');

    // 隐藏裁判悬浮卡片
    const floatCard = document.getElementById('debate-judge-float-card');
    if (floatCard) floatCard.classList.remove('visible');

    const judgeContent = document.getElementById('judge-content');
    if (judgeContent) judgeContent.textContent = '';

    // 重置所有身份卡片状态
    document.querySelectorAll('.debate-agent-card').forEach(card => {
        card.dataset.status = '';
        const dot = card.querySelector('.status-dot');
        if (dot) dot.className = 'status-dot';
    });

    updateDebateStatus('正在召集AI身份...');
    updateDebateRoundLabel('第一轮：独立观点');
}

function updateDebateStatus(status, type = '') {
    const el = document.getElementById('debate-status');
    if (!el) return;
    el.textContent = status;
    el.className = 'debate-status';
    if (type) el.classList.add(type);
}

function updateDebateRoundLabel(label) {
    const el = document.getElementById('debate-round-label');
    if (el) el.textContent = label;
}

function updateDebateAgentStatus(agentId, status) {
    const card = document.querySelector(`.debate-agent-card[data-agent-id="${agentId}"]`);
    if (!card) return;

    card.dataset.status = status;
    const dot = card.querySelector('.status-dot');
    if (dot) {
        dot.className = 'status-dot';
        if (status === 'thinking') dot.classList.add('thinking');
        else if (status === 'complete') dot.classList.add('complete');
    }
}

function appendDebateAgentResponse(agentId, content, isComment = false) {
    const container = document.getElementById('debate-messages');
    if (!container) return;

    let bubble = container.querySelector(`.debate-bubble[data-agent="${agentId}"][data-type="${isComment ? 'comment' : 'answer'}"]`);
    if (!bubble) {
        const agent = AGENTS_CONFIG.find(a => a.id === agentId);
        bubble = document.createElement('div');
        bubble.className = 'debate-bubble';
        bubble.dataset.agent = agentId;
        bubble.dataset.type = isComment ? 'comment' : 'answer';
        bubble.style.setProperty('--agent-color', agent?.themeColor || '#666');
        bubble.innerHTML = `
            <div class="bubble-header" style="color: ${agent?.themeColor || '#666'}">
                <span class="bubble-agent-name">${agent?.name || agentId}${isComment ? ' (评论)' : ''}</span>
            </div>
            <div class="bubble-content"></div>
        `;
        container.appendChild(bubble);
    }

    const contentEl = bubble.querySelector('.bubble-content');
    if (contentEl) {
        // 压缩多余换行：超过2个连续换行压缩为最多2个，避免段落间间距过大
        const normalized = content.replace(/\n{3,}/g, '\n\n');
        contentEl.textContent += normalized;
    }

    // 滚动到底部
    const contentArea = document.getElementById('debate-content-area');
    if (contentArea) contentArea.scrollTop = contentArea.scrollHeight;
}

function showDebateJudgeArea() {
    const floatCard = document.getElementById('debate-judge-float-card');
    if (floatCard) floatCard.classList.add('visible');
}

function appendDebateJudgeContent(content) {
    const judgeContent = document.getElementById('judge-content');
    if (judgeContent) {
        const normalized = content.replace(/\n{3,}/g, '\n\n');
        judgeContent.textContent += normalized;
    }
}

function addDebateSandboxLog(agentId, content) {
    const logEntry = {
        agent: agentId.startsWith('debate_') ? agentId : `debate_${agentId}`,
        content: content,
        timestamp: Date.now()
    };
    sandboxLogs.push(logEntry);
    activeAgents.add(logEntry.agent);
    renderSandboxLog(logEntry, false);
    renderFlowNodes();
    renderFilterChips();
}

async function handleDebateStream(userMsg) {
    const sendButton = document.getElementById('send-btn');

    ensureCurrentPathValid();
    clearInput();
    setInputDisabled(true);
    if (sendButton) sendButton.disabled = true;

    messages.push({ role: 'user', content: userMsg });
    renderMessages();

    // 重置沙盘
    sandboxLogs = [];
    activeAgents = new Set();
    sandboxFilterSet = new Set();
    const sandboxLogsEl = document.getElementById('sandbox-logs');
    if (sandboxLogsEl) sandboxLogsEl.innerHTML = '';
    renderFlowNodes();
    renderFilterChips();
    updateSandboxStatus('辩论中', 'bg-purple-100 text-purple-600');

    // 初始化辩论面板
    initDebatePanel();
    resetDebateState();

    debateAbortController = new AbortController();

    try {
        const res = await fetch(DEBATE_API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: String(currentUser?.id || 'anonymous'),
                course_id: 'bigdata',
                user_input: userMsg,
                context_id: '',
                current_profile: profile,
                agents: AGENTS_CONFIG.map(a => ({
                    id: a.id,
                    name: a.name,
                    systemPrompt: a.systemPrompt,
                    themeColor: a.themeColor
                }))
            }),
            signal: debateAbortController.signal
        });

        if (!res.ok) {
            throw new Error(`辩论API错误: ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const event = JSON.parse(line.slice(6).trim());
                    handleDebateEvent(event);
                } catch (e) {
                    console.warn('解析辩论事件失败:', e);
                }
            }
        }

    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('辩论请求已取消');
            return;
        }
        console.error('辩论错误:', error);
        updateDebateStatus('辩论出错', 'error');
        addDebateSandboxLog('system', `辩论过程出错: ${error.message}`);

        // 回退到普通模式
        messages.push({ role: 'assistant', content: '抱歉，辩论模式出现问题，请稍后重试。' });
        renderMessages();
    } finally {
        setInputDisabled(false);
        if (sendButton) sendButton.disabled = false;
        debateAbortController = null;
    }
}

function handleDebateEvent(event) {
    switch (event.type) {
        case 'debate_start':
            updateDebateStatus('辩论开始');
            addDebateSandboxLog('system', '辩论开始，各AI身份正在思考...');
            break;

        case 'agent_start':
            updateDebateAgentStatus(event.agent_id, 'thinking');
            addDebateSandboxLog(event.agent_id, `${event.agent_name || event.agent_id} 开始思考...`);
            break;

        case 'agent_chunk':
            appendDebateAgentResponse(event.agent_id, event.content);
            break;

        case 'agent_complete':
            updateDebateAgentStatus(event.agent_id, 'complete');
            debateState.agentResponses[event.agent_id] = event.full_response;
            addDebateSandboxLog(event.agent_id, `${event.agent_name || event.agent_id} 完成回答`);
            break;

        case 'debate_round_complete':
            debateState.currentRound = event.round;
            if (event.round === 1) {
                updateDebateRoundLabel('第二轮：交叉评论');
                updateDebateStatus('交叉评论中...');
            }
            addDebateSandboxLog('system', `第${event.round}轮完成`);
            break;

        case 'comment_start':
            updateDebateAgentStatus(event.agent_id, 'thinking');
            addDebateSandboxLog(event.agent_id, `${event.agent_name || event.agent_id} 开始评论...`);
            break;

        case 'comment_chunk':
            appendDebateAgentResponse(event.agent_id, event.content, true);
            break;

        case 'comment_complete':
            updateDebateAgentStatus(event.agent_id, 'complete');
            debateState.crossComments[event.agent_id] = event.comment;
            break;

        case 'judge_start':
            showDebateJudgeArea();
            updateDebateRoundLabel('裁判综合判定');
            updateDebateStatus('裁判判定中...', 'thinking');
            addDebateSandboxLog('judge', '裁判开始综合评估...');
            break;

        case 'judge_chunk':
            appendDebateJudgeContent(event.content);
            break;

        case 'judge_complete':
            addDebateSandboxLog('judge', '裁判完成综合判定');
            break;

        case 'debate_complete':
            debateState.isComplete = true;
            updateDebateStatus('辩论完成', 'complete');
            updateSandboxStatus('完成', 'bg-green-100 text-green-600');

            // 将最终答案添加到消息列表
            const finalAnswer = event.final_answer || '辩论完成，请查看上方各身份观点。';
            messages.push({ role: 'assistant', content: finalAnswer });
            renderMessages();

            addDebateSandboxLog('system', '辩论结束');
            break;

        case 'agent_error':
            addDebateSandboxLog('system', `${event.agent_id} 出错: ${event.message}`);
            break;

        case 'error':
            updateDebateStatus('出错', 'error');
            addDebateSandboxLog('system', `错误: ${event.message}`);
            break;

        default:
            console.log('未知辩论事件:', event);
    }
}

// ============================================================
// 用户长期记忆面板
// ============================================================

const MEMORY_API_URL = `${API_BASE}/api/memories`;
const MEMORY_TYPE_LABELS = {
    background: { label: '背景', icon: '📋', class: 'memory-type-bg' },
    preference: { label: '偏好', icon: '⭐', class: 'memory-type-pref' },
    knowledge: { label: '知识', icon: '📚', class: 'memory-type-know' },
    interest: { label: '兴趣', icon: '💡', class: 'memory-type-interest' },
    goal: { label: '目标', icon: '🎯', class: 'memory-type-goal' },
    emotion: { label: '情感', icon: '💭', class: 'memory-type-emotion' },
    fact: { label: '事实', icon: '📝', class: 'memory-type-bg' },
};

let _memoriesCache = [];
let _memoryPollingInterval = null;
let _activeMemoryFilter = 'all';
let _memorySearchQuery = '';
let _editingMemoryId = null;

function formatRelativeTime(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '';
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 5) return '刚刚';
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays === 1) return '昨天';
    if (diffDays < 7) return `${diffDays}天前`;
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

function renderConfidenceBar(confidence) {
    const c = Math.max(0, Math.min(1, confidence || 0));
    const activeSegments = Math.round(c * 8);
    let level = 'low';
    if (c >= 0.7) level = 'high';
    else if (c >= 0.4) level = 'medium';

    let html = '<div class="memory-confidence-bar">';
    for (let i = 0; i < 8; i++) {
        const active = i < activeSegments ? `active ${level}` : '';
        html += `<div class="memory-confidence-segment ${active}"></div>`;
    }
    html += `<span class="memory-confidence-value">${(c * 100).toFixed(0)}%</span></div>`;
    return html;
}

async function loadUserMemories() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user || !user.id) {
        console.log('[MemoryPanel] 未登录，跳过加载');
        return;
    }

    const statusEl = document.getElementById('memory-footer-status');
    if (statusEl) statusEl.textContent = '🔄 刷新中...';

    const url = `${MEMORY_API_URL}/${user.id}?limit=50`;
    console.log('[MemoryPanel] 请求:', url);

    try {
        const res = await fetch(url);
        console.log('[MemoryPanel] 响应状态:', res.status, res.statusText);
        if (!res.ok) {
            const errText = await res.text().catch(() => '');
            console.error('[MemoryPanel] 响应失败:', res.status, errText);
            if (statusEl) statusEl.textContent = `⚠️ 服务器错误 (${res.status})`;
            return;
        }
        const data = await res.json();
        console.log('[MemoryPanel] 数据:', data);
        if (data.success) {
            _memoriesCache = data.memories || [];
            filterAndRenderMemories();
            if (statusEl) {
                const count = _memoriesCache.length;
                statusEl.textContent = count > 0 ? `✓ ${count} 条记忆 · 刚刚更新` : '🤖 暂无记忆';
            }
        } else {
            console.error('[MemoryPanel] 后端返回失败:', data);
            if (statusEl) statusEl.textContent = '⚠️ 数据异常';
        }
    } catch (e) {
        console.error('[MemoryPanel] 网络请求失败:', e);
        const isFileProtocol = window.location.protocol === 'file:';
        if (isFileProtocol) {
            if (statusEl) statusEl.textContent = '⚠️ 请通过 http://localhost:8000 访问';
        } else {
            if (statusEl) statusEl.textContent = '⚠️ 网络错误 (后端未启动?)';
        }
    }
}

function filterAndRenderMemories() {
    let filtered = _memoriesCache;

    // 类型筛选
    if (_activeMemoryFilter && _activeMemoryFilter !== 'all') {
        filtered = filtered.filter(m => m.memory_type === _activeMemoryFilter);
    }

    // 搜索过滤
    if (_memorySearchQuery && _memorySearchQuery.trim()) {
        const q = _memorySearchQuery.trim().toLowerCase();
        filtered = filtered.filter(m => (m.content || '').toLowerCase().includes(q));
    }

    renderMemories(filtered);
}

function renderMemories(memories) {
    const container = document.getElementById('memory-list-container');
    const badge = document.getElementById('memory-count-badge');
    if (!container) return;

    if (!memories || memories.length === 0) {
        const hasMemories = _memoriesCache.length > 0;
        container.innerHTML = `
            <div class="memory-empty-state">
                <div>🤖 ${hasMemories ? '没有匹配的记忆' : 'AI 正在了解你...'}</div>
                <div style="font-size:10px;margin-top:4px;color:var(--text-tertiary);">
                    ${hasMemories ? '试试其他筛选条件或搜索关键词' : '每次聊天，AI 都会自动记住你的特点，并在后续对话中自然地提起'}
                </div>
                ${!hasMemories ? `
                <div style="font-size:10px;margin-top:6px;color:var(--text-tertiary);">
                    💡 试着和 AI 聊聊你自己吧，比如你的专业、已学过的技能、感兴趣的方向...
                </div>
                ` : ''}
            </div>
        `;
        if (badge) {
            badge.textContent = _memoriesCache.length;
            badge.classList.toggle('hidden', _memoriesCache.length === 0);
        }
        return;
    }

    if (badge) {
        badge.textContent = _memoriesCache.length;
        badge.classList.remove('hidden');
    }

    const now = Date.now();
    const isNewThreshold = 5 * 60 * 1000; // 5分钟内算新

    const html = memories.map(mem => {
        const typeInfo = MEMORY_TYPE_LABELS[mem.memory_type] || MEMORY_TYPE_LABELS.fact;
        const confirmedClass = mem.confirmed ? 'confirmed' : 'unconfirmed';
        const confirmedLabel = mem.confirmed ? '✓ 已确认' : '⏳ 待确认';
        const timeStr = formatRelativeTime(mem.created_at);

        // 是否为新记忆
        const createdTime = mem.created_at ? new Date(mem.created_at).getTime() : 0;
        const isNew = (now - createdTime) < isNewThreshold;
        const newBadge = isNew ? '<span class="memory-new-badge">新</span>' : '';

        // 展开/收起
        const content = escapeHtml(mem.content || '');
        const isLong = content.length > 60;
        const contentClass = isLong && !mem._expanded ? 'is-truncated' : '';
        const expandBtn = isLong ? `<button class="memory-expand-btn" onclick="toggleMemoryExpand('${mem.id}')">${mem._expanded ? '收起' : '展开'}</button>` : '';

        // 搜索高亮
        let displayContent = content;
        if (_memorySearchQuery && _memorySearchQuery.trim()) {
            const q = escapeHtml(_memorySearchQuery.trim());
            const regex = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
            displayContent = content.replace(regex, '<span class="highlight">$1</span>');
        }

        // 编辑态
        const isEditing = _editingMemoryId === mem.id;
        if (isEditing) {
            return `
                <div class="memory-item ${confirmedClass} is-new" data-id="${mem.id}">
                    <div class="memory-item-type ${typeInfo.class}">
                        <span>${typeInfo.icon}</span>
                        <span>${typeInfo.label}</span>${newBadge}
                    </div>
                    <div class="memory-edit-form">
                        <textarea class="memory-edit-textarea" id="memory-edit-text-${mem.id}" rows="2">${escapeHtml(mem.content || '')}</textarea>
                        <div class="memory-edit-actions">
                            <button class="memory-edit-btn save" onclick="saveMemoryEdit('${mem.id}')">保存</button>
                            <button class="memory-edit-btn cancel" onclick="cancelMemoryEdit()">取消</button>
                        </div>
                    </div>
                </div>
            `;
        }

        return `
            <div class="memory-item ${confirmedClass} ${isNew ? 'is-new' : ''}" data-id="${mem.id}">
                <div class="memory-item-type ${typeInfo.class}">
                    <span>${typeInfo.icon}</span>
                    <span>${typeInfo.label}</span>${newBadge}
                </div>
                <div class="memory-item-content ${contentClass}">${displayContent}</div>
                ${expandBtn}
                ${renderConfidenceBar(mem.confidence)}
                <div class="memory-item-meta">
                    <span>${confirmedLabel} · ${timeStr}</span>
                    <div class="memory-item-actions">
                        ${!mem.confirmed ? `<button class="memory-btn confirm" onclick="confirmUserMemory('${mem.id}')" title="确认">✓</button>` : ''}
                        <button class="memory-btn edit" onclick="editUserMemory('${mem.id}')" title="编辑">✎</button>
                        <button class="memory-btn delete" onclick="deleteUserMemory('${mem.id}')" title="删除">✕</button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

function toggleMemoryExpand(memoryId) {
    const mem = _memoriesCache.find(m => m.id === memoryId);
    if (mem) {
        mem._expanded = !mem._expanded;
        filterAndRenderMemories();
    }
}

function editUserMemory(memoryId) {
    _editingMemoryId = memoryId;
    filterAndRenderMemories();
    const textarea = document.getElementById(`memory-edit-text-${memoryId}`);
    if (textarea) {
        textarea.focus();
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    }
}

async function saveMemoryEdit(memoryId) {
    const textarea = document.getElementById(`memory-edit-text-${memoryId}`);
    if (!textarea) return;
    const newContent = textarea.value.trim();
    if (!newContent) {
        showMemoryToast('⚠️ 记忆内容不能为空');
        return;
    }

    try {
        const res = await fetch(`${MEMORY_API_URL}/${memoryId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: newContent })
        });
        if (res.ok) {
            showMemoryToast('✓ 记忆已更新');
            _editingMemoryId = null;
            loadUserMemories();
        } else {
            showMemoryToast('⚠️ 更新失败');
        }
    } catch (e) {
        console.log('[MemoryPanel] 编辑记忆失败:', e);
        showMemoryToast('⚠️ 网络错误');
    }
}

function cancelMemoryEdit() {
    _editingMemoryId = null;
    filterAndRenderMemories();
}

function showMemoryJustRemembered() {
    const container = document.getElementById('memory-list-container');
    if (!container) return;
    // 如果顶部已经有提示，不重复添加
    if (container.querySelector('.memory-just-remembered')) return;

    const tip = document.createElement('div');
    tip.className = 'memory-just-remembered';
    tip.textContent = '💡 AI 刚刚记住了你的新特征';
    container.insertBefore(tip, container.firstChild);

    // 3.5秒后移除
    setTimeout(() => {
        if (tip.parentNode) tip.parentNode.removeChild(tip);
    }, 3500);
}

async function confirmUserMemory(memoryId) {
    try {
        const res = await fetch(`${MEMORY_API_URL}/${memoryId}/confirm`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ confirmed: true })
        });
        if (res.ok) {
            showMemoryToast('✓ 记忆已确认，AI 会更信赖这条信息');
            loadUserMemories();
        }
    } catch (e) {
        console.log('[MemoryPanel] 确认记忆失败:', e);
    }
}

async function deleteUserMemory(memoryId) {
    if (!confirm('确定要删除这条记忆吗？AI 将不再记住这个信息。')) return;
    try {
        const res = await fetch(`${MEMORY_API_URL}/${memoryId}`, { method: 'DELETE' });
        if (res.ok) {
            showMemoryToast('🗑 记忆已删除');
            loadUserMemories();
        }
    } catch (e) {
        console.log('[MemoryPanel] 删除记忆失败:', e);
    }
}

// ========== AI眼中的你 画像卡片 ==========

let currentProfileData = null;

async function loadUserProfile() {
    const user = JSON.parse(localStorage.getItem('starlearn_user') || '{}');
    if (!user || !user.id) {
        console.log('[Profile] 未登录，跳过加载');
        return;
    }

    try {
        const resp = await fetch(`/api/profile/${user.id}`);
        if (!resp.ok) return;
        const data = await resp.json();
        if (data.success && data.profile) {
            currentProfileData = data.profile;
            renderProfileCard(data.profile);
        }
    } catch (e) {
        console.warn('[Profile] 加载画像失败:', e);
    }
}

function renderProfileCard(profile) {
    const container = document.getElementById('profile-card-container');
    if (!container) return;

    // 收集所有标签并扁平化
    const allTags = [];
    for (const [key, items] of Object.entries(profile)) {
        if (key === 'last_updated' || !items || items.length === 0) continue;
        items.forEach(item => allTags.push(item));
    }

    if (allTags.length === 0) {
        container.innerHTML = `
            <div class="profile-empty-state text-center py-2 text-[11px]" style="color: var(--text-tertiary);">
                🤖 AI 正在了解你…
            </div>
        `;
        return;
    }

    // 按评分排序
    allTags.sort((a, b) => (b.score || 0) - (a.score || 0));

    const tagsHtml = allTags.map(item => {
        const isWeakness = item.label.includes('薄弱') || item.label.includes('困难') || item.label.includes('不擅长');
        const isActive = _activeMemoryFilter === item.memory_type;
        return `<span class="profile-tag ${isWeakness ? 'weakness' : ''} ${isActive ? 'is-filter-active' : ''}" data-memory-type="${escapeHtml(item.memory_type)}" data-memory-id="${escapeHtml(item.memory_id)}" title="置信度: ${(item.confidence * 100).toFixed(0)}% | 引用次数: ${item.access_count}">${escapeHtml(item.label)}</span>`;
    }).join('');

    container.innerHTML = tagsHtml;

    // 绑定标签点击事件 → 筛选记忆
    container.querySelectorAll('.profile-tag').forEach(tag => {
        tag.addEventListener('click', () => {
            const memoryType = tag.dataset.memoryType;
            if (memoryType) {
                filterMemoriesByType(memoryType);
            }
        });
    });

    // 更新最后更新时间
    const updatedEl = document.getElementById('profile-last-updated');
    if (updatedEl && profile.last_updated) {
        const date = new Date(profile.last_updated);
        const diff = Math.floor((Date.now() - date.getTime()) / 60000);
        updatedEl.textContent = diff < 1 ? '刚刚更新' : diff < 60 ? `${diff}分钟前` : `${Math.floor(diff/60)}小时前`;
    }
}

function filterMemoriesByType(type) {
    // Toggle: 已激活则取消
    if (_activeMemoryFilter === type) {
        _activeMemoryFilter = 'all';
    } else {
        _activeMemoryFilter = type;
    }

    // 同步筛选芯片 UI
    const chipsContainer = document.getElementById('memory-filter-chips');
    if (chipsContainer) {
        chipsContainer.querySelectorAll('.memory-chip').forEach(c => {
            c.classList.toggle('active', c.dataset.type === _activeMemoryFilter);
        });
    }

    // 同步画像标签 UI
    const profileContainer = document.getElementById('profile-card-container');
    if (profileContainer) {
        profileContainer.querySelectorAll('.profile-tag').forEach(tag => {
            tag.classList.toggle('is-filter-active', tag.dataset.memoryType === _activeMemoryFilter);
        });
    }

    filterAndRenderMemories();
}

function showMemoryToast(message) {
    const existing = document.querySelector('.memory-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'memory-toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function confirmUnderstanding(understood, timestamp) {
    const msg = messages.find(m => m._timestamp === timestamp || String(m._timestamp) === String(timestamp));
    if (!msg) return;

    // 移除交互条，显示用户选择
    msg._socraticCheckpoint = false;
    msg._checkpointResult = understood ? 'understood' : 'confused';

    // 跟踪苏格拉底通关率
    if (!evaluation._socraticStats) {
        evaluation._socraticStats = { total: 0, passed: 0 };
    }
    evaluation._socraticStats.total = (evaluation._socraticStats.total || 0) + 1;
    if (understood) {
        evaluation._socraticStats.passed = (evaluation._socraticStats.passed || 0) + 1;
    }
    const socraticPassRate = evaluation._socraticStats.total > 0
        ? evaluation._socraticStats.passed / evaluation._socraticStats.total
        : 0;
    updateEvaluation({ socraticPassRate });

    if (understood) {
        showMemoryToast('✓ 已记录，继续加油！');
    } else {
        showMemoryToast('💡 进入苏格拉底深度诊断模式...');
        // 触发强轨道：发送一条消息并强制后端进入苏格拉底模式
        handleSendStream('我对这部分还不太理解，能详细讲讲吗？', { forceSocratic: true });
    }

    // 持久化到后端
    try {
        await fetch('/api/socratic/checkpoint', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic: msg._checkpointTopic || '',
                understood: understood,
                message_timestamp: timestamp,
                course_id: null
            })
        });
    } catch (e) {
        console.warn('[Socratic] checkpoint persist failed:', e);
    }

    renderMessages();
}

// 页面加载时启动记忆轮询
document.addEventListener('DOMContentLoaded', () => {
    loadUserMemories();
    loadUserProfile();
    // 每30秒刷新一次记忆面板（兜底）
    _memoryPollingInterval = setInterval(loadUserMemories, 30000);

    // 绑定筛选 chip 点击事件
    const chipsContainer = document.getElementById('memory-filter-chips');
    if (chipsContainer) {
        chipsContainer.addEventListener('click', (e) => {
            const chip = e.target.closest('.memory-chip');
            if (!chip) return;
            chipsContainer.querySelectorAll('.memory-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            _activeMemoryFilter = chip.dataset.type || 'all';
            // 同步画像标签高亮态
            const profileContainer = document.getElementById('profile-card-container');
            if (profileContainer) {
                profileContainer.querySelectorAll('.profile-tag').forEach(tag => {
                    tag.classList.toggle('is-filter-active', tag.dataset.memoryType === _activeMemoryFilter);
                });
            }
            filterAndRenderMemories();
        });
    }

    // 页面重新可见时立即刷新记忆
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            loadUserMemories();
        }
    });
});
