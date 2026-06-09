/**
 * Course Learn — Sample Learning Content
 *
 * 每个 sub-chapter 都带一份内容:
 *   - subtitles[]:     { from, content } 时间戳字幕
 *   - transcript:      string  AI 讲义 (HTML)
 *   - concepts[]:      { term, definition, example, level } 关键概念
 *   - mindMap:         { name, children[] }                  思维导图
 *   - exercises[]:     { type, question, options|answer, explanation, answer }
 *
 * 当后端没有返回这些字段时, 会回退到本文件的样本数据,
 * 至少保证页面 5 步学习流程能展示.
 */
(function (global) {
  'use strict';

  /**
   * 把"子章节 id"映射到内容. 兼容两种 id 来源:
   *   - 来自 /api/courses/courses/<id> (数字 id)
   *   - 来自 /api/bilibili/parse (sub-1 / sub-2)
   */
  const SAMPLE_CONTENT = {
    /* ---------- sub-1: 计算机的发展-古代的计算工具 ---------- */
    'sub-1': {
      subtitles: [
        { from: 0,   content: '同学们好,今天我们开始学习计算机基础入门第一章。' },
        { from: 12,  content: '在正式介绍电子计算机之前,我们先要了解计算工具的发展历史。' },
        { from: 28,  content: '人类最早的计算工具可以追溯到远古时期的结绳记事。' },
        { from: 45,  content: '所谓"结绳记事",就是用绳子上打结的多少来记录事物的数量。' },
        { from: 62,  content: '在中国古代的典籍《周易》中就有关于结绳记事的明确记载。' },
        { from: 80,  content: '到了春秋战国时期,我们的祖先发明了算筹。' },
        { from: 98,  content: '算筹是一种用小木棍或者竹棍组成的计算工具,可以进行加减乘除。' },
        { from: 118, content: '《老子》所说的"善数者不用筹策",说明算筹在当时已经非常普遍。' },
        { from: 138, content: '到了唐宋时期,算盘开始普及,成为商业活动中最重要的计算工具。' },
        { from: 158, content: '算盘通过珠子的位置表示数字,熟练的使用者可以快速完成复杂的运算。' },
        { from: 178, content: '明朝数学家程大位所著的《算法统宗》系统总结了珠算的算法。' },
        { from: 200, content: '这些工具虽然简单,但是已经具备了计算工具的基本特征: 表达、存储、运算。' },
        { from: 220, content: '下面我们来思考一个问题: 结绳记事算不算"计算工具"?' }
      ],
      transcript: `
        <h4>📜 古代计算工具发展史</h4>
        <p>本节我们从最早的<mark>结绳记事</mark>讲起,沿着历史脉络梳理人类计算工具的演化:</p>
        <ol>
          <li><strong>结绳记事 (远古 - 上古)</strong> — 用绳子打结的数量和位置记录事件与数目。</li>
          <li><strong>算筹 (春秋 - 秦汉)</strong> — 小棍摆位,实现十进制加减乘除。</li>
          <li><strong>算盘 (唐宋 - 近代)</strong> — 二五珠结构,商业计算利器。</li>
          <li><strong>机械计算器 (17世纪)</strong> — 帕斯卡加法器、莱布尼茨乘法器。</li>
        </ol>
        <h4>🔑 核心规律</h4>
        <p>无论形式如何变化,所有计算工具都在解决三个核心问题:</p>
        <ul>
          <li><strong>表示</strong>: 如何用物理符号代表数字</li>
          <li><strong>存储</strong>: 如何记录中间结果</li>
          <li><strong>运算</strong>: 如何按规则改变状态</li>
        </ul>
        <p>这三个能力,也是后来电子计算机的核心架构。理解这一点,你就理解了计算机的"灵魂"。</p>
      `,
      concepts: [
        { term: '结绳记事', definition: '远古人类用绳结的形状和数量记录事件与数目的方法。',
          example: '《周易·系辞下》:"上古结绳而治,后世圣人易之以书契。"',
          level: 'basic' },
        { term: '算筹', definition: '用小棍(竹、骨、玉)按位摆放表示数字并进行运算的工具。',
          example: '纵式与横式交替,纵表示个百千万,横表示十百千万,实现十进制。',
          level: 'basic' },
        { term: '算盘', definition: '一种手动操作的计算工具,由框、梁、档、珠四部分组成。',
          example: '二五珠算盘: 上方两珠(每珠=5),下方五珠(每珠=1),靠梁表示计数。',
          level: 'basic' },
        { term: '十进制', definition: '每 10 个低位向高位进一的计数法,人类最常用的数制。',
          example: '算筹与算盘都采用十进制,与人有 10 根手指这一生理特征相符。',
          level: 'core' },
        { term: '算法', definition: '为解决特定问题而采取的有限步骤的运算序列。',
          example: '珠算口诀"三下五除二"就是一种典型的算法表达。',
          level: 'core' }
      ],
      mindMap: {
        name: '计算机的发展 · 古代',
        children: [
          { name: '结绳记事',
            children: [
              { name: '起源: 远古' },
              { name: '载体: 绳结' },
              { name: '作用: 记事 / 计数' }
            ]
          },
          { name: '算筹',
            children: [
              { name: '春秋战国' },
              { name: '纵式 / 横式' },
              { name: '十进制运算' }
            ]
          },
          { name: '算盘',
            children: [
              { name: '唐宋普及' },
              { name: '二五珠结构' },
              { name: '珠算口诀' }
            ]
          },
          { name: '机械计算器',
            children: [
              { name: '帕斯卡 1642' },
              { name: '莱布尼茨 1672' }
            ]
          }
        ]
      },
      exercises: [
        { type: 'choice',
          question: '下列哪一项<strong>不属于</strong>古代计算工具?',
          options: ['结绳', '算筹', '算盘', '电子管'],
          answer: 3,
          explanation: '电子管是 20 世纪电子计算机的元件,不属于古代工具。' },
        { type: 'choice',
          question: '"三下五除二"是中国古代______的口诀。',
          options: ['结绳', '算筹', '珠算', '心算'],
          answer: 2,
          explanation: '这是珠算除法典型口诀,源自《算法统宗》。' },
        { type: 'bool',
          question: '算筹采用的是二进制计数法。',
          answer: false,
          explanation: '算筹采用十进制,通过纵式与横式交替区分位数。' },
        { type: 'fill',
          question: '《______》中"上古结绳而治"明确记载了结绳记事。',
          answer: '周易',
          explanation: '《周易·系辞下》:"上古结绳而治,后世圣人易之以书契。"' }
      ]
    },

    /* ---------- sub-2: 计算机的发展-机械时代 ---------- */
    'sub-2': {
      subtitles: [
        { from: 0,   content: '这一节我们来聊聊机械时代的计算工具。' },
        { from: 15,  content: '17 世纪,欧洲的科学家开始尝试用机械装置实现自动计算。' },
        { from: 35,  content: '1642 年,法国科学家帕斯卡发明了加法器。' },
        { from: 55,  content: '加法器通过齿轮的转动实现进位,原理和今天的机械计数器一样。' },
        { from: 78,  content: '1672 年,德国数学家莱布尼茨在帕斯卡的基础上,做出了能乘除的计算器。' },
        { from: 100, content: '莱布尼茨还是二进制的大力推广者,他认为二进制最适合机器表示。' },
        { from: 125, content: '到了 19 世纪,英国数学家巴贝奇设计了"差分机"和"分析机"。' },
        { from: 148, content: '分析机被认为是现代计算机的雏形,它已经有了输入、运算、存储、控制四部分。' },
        { from: 175, content: '为分析机编写程序的是 Ada Lovelace,她也因此被称为"世界第一位程序员"。' }
      ],
      transcript: `
        <h4>⚙️ 机械时代: 从齿轮到程序</h4>
        <p>机械计算器是连接"古代手工计算"与"现代电子计算"的桥梁,这一时期出现了几个关键人物:</p>
        <ul>
          <li><strong>帕斯卡 (Blaise Pascal, 1642)</strong> — 加法器,首次用齿轮实现自动进位</li>
          <li><strong>莱布尼茨 (Gottfried Leibniz, 1672)</strong> — 步进计算器,支持乘除</li>
          <li><strong>巴贝奇 (Charles Babbage, 1822)</strong> — 差分机 / 分析机,引入存储与程序思想</li>
          <li><strong>Ada Lovelace (1843)</strong> — 编写了历史上第一段"程序"</li>
        </ul>
        <h4>🧠 思想飞跃</h4>
        <p>分析机的设计已经包含了现代计算机的核心架构 — 存储程序与顺序执行。Ada 给巴贝奇的信中甚至讨论了循环与条件分支,这些概念在 100 年后才被真正实现。</p>
      `,
      concepts: [
        { term: '加法器', definition: '通过齿轮咬合实现十进制数加法及进位的机械装置。',
          example: '帕斯卡加法器: 输入数字旋转表盘,齿轮自动完成进位。',
          level: 'basic' },
        { term: '差分机', definition: '巴贝奇设计的用于计算多项式数表的机械装置。',
          example: '利用"差分"方法,只需加减法即可计算高阶多项式。',
          level: 'core' },
        { term: '分析机', definition: '巴贝奇设计的通用计算机,含存储、运算、控制、输入输出四大部件。',
          example: '被视为现代计算机架构的雏形,因工艺限制未能完成。',
          level: 'core' },
        { term: '存储程序', definition: '将程序和数据都存放在同一存储器中的设计思想。',
          example: '分析机使用穿孔卡片存储程序,这种思想延续到现代计算机。',
          level: 'advanced' },
        { term: '二进制', definition: '只用 0 和 1 两个数码表示数的进位制。',
          example: '莱布尼茨在《论二进制》中系统阐述,后成为计算机的基础。',
          level: 'core' }
      ],
      mindMap: {
        name: '机械计算时代',
        children: [
          { name: '帕斯卡 1642',
            children: [
              { name: '加法器' },
              { name: '齿轮进位' }
            ]
          },
          { name: '莱布尼茨 1672',
            children: [
              { name: '步进计算器' },
              { name: '乘除运算' },
              { name: '二进制先驱' }
            ]
          },
          { name: '巴贝奇 1822/1834',
            children: [
              { name: '差分机' },
              { name: '分析机' },
              { name: '存储程序思想' }
            ]
          },
          { name: 'Ada 1843',
            children: [
              { name: '第一段程序' },
              { name: '循环 / 分支' }
            ]
          }
        ]
      },
      exercises: [
        { type: 'choice',
          question: '下列哪位科学家被称为"计算机之父"?',
          options: ['帕斯卡', '莱布尼茨', '巴贝奇', '图灵'],
          answer: 2,
          explanation: '巴贝奇设计了分析机,被后人尊称为计算机之父。' },
        { type: 'choice',
          question: '世界上第一段"程序"的编写者是?',
          options: ['巴贝奇', '图灵', 'Ada Lovelace', '冯·诺依曼'],
          answer: 2,
          explanation: 'Ada Lovelace 为巴贝奇的分析机编写了伯努利数求解程序。' },
        { type: 'bool',
          question: '帕斯卡加法器支持乘除运算。',
          answer: false,
          explanation: '帕斯卡加法器仅支持加减,乘除由莱布尼茨的步进计算器实现。' },
        { type: 'fill',
          question: '莱布尼茨系统化了______进制,为现代计算机的数制基础奠定基础。',
          answer: '二',
          explanation: '二进制只用 0/1,最易用电路高/低电平表示,成为计算机基础。' }
      ]
    },

    /* ---------- sub-3: 计算机的发展-电子时代 ---------- */
    'sub-3': {
      subtitles: [
        { from: 0,   content: '电子计算机的出现,标志着人类计算工具进入了全新阶段。' },
        { from: 18,  content: '1946 年,世界上第一台电子计算机 ENIAC 在美国宾夕法尼亚大学诞生。' },
        { from: 40,  content: 'ENIAC 重达 30 吨,使用了 18000 多个电子管。' },
        { from: 62,  content: '虽然体积庞大,但它的计算速度比人工快了几千倍。' },
        { from: 85,  content: '后来,冯·诺依曼提出了"存储程序"的设计思想,这就是著名的冯氏架构。' },
        { from: 110, content: '冯氏架构的核心是: 程序和数据都存放在同一存储器中。' },
        { from: 135, content: '这一架构一直沿用到今天,无论是 PC、服务器还是手机。' }
      ],
      transcript: `
        <h4>💡 电子时代: ENIAC 与冯·诺依曼架构</h4>
        <p>20 世纪 40 年代,电子管的出现让计算速度产生质的飞跃:</p>
        <ul>
          <li><strong>ENIAC (1946)</strong> — 第一台电子计算机,18000+ 电子管,30 吨重</li>
          <li><strong>冯·诺依曼 (1945)</strong> — 提出"存储程序"思想,EDVAC 设计</li>
          <li><strong>晶体管 (1947)</strong> — 贝尔实验室发明,体积功耗大幅降低</li>
          <li><strong>集成电路 (1958)</strong> — 让计算机走入千家万户</li>
        </ul>
        <h4>🏛️ 冯氏架构</h4>
        <p>运算器、控制器、存储器、输入设备、输出设备 — 这五大部件构成了现代计算机的标准结构,70 余年未变。</p>
      `,
      concepts: [
        { term: 'ENIAC', definition: '1946 年诞生于宾夕法尼亚大学的第一台电子计算机。',
          example: '重 30 吨,占地 167 平方米,每秒钟可做 5000 次加法。',
          level: 'basic' },
        { term: '电子管', definition: '在真空玻璃管中控制电子流动的早期电子元件。',
          example: 'ENIAC 使用 18000 多个电子管,寿命短、发热大。',
          level: 'basic' },
        { term: '冯·诺依曼架构', definition: '将程序指令和数据共同存储在同一存储器中的计算机架构。',
          example: '现代 PC、服务器、手机几乎都采用此架构。',
          level: 'core' },
        { term: '晶体管', definition: '用半导体材料制成的可控制电流开关的元件。',
          example: '1947 年贝尔实验室发明,体积小、寿命长、功耗低,逐步取代电子管。',
          level: 'core' },
        { term: '集成电路', definition: '在单一半导体基片上集成多个晶体管和元件的电路。',
          example: 'Intel 4004 (1971) 是第一款商用微处理器,集成了 2300 个晶体管。',
          level: 'advanced' }
      ],
      mindMap: {
        name: '电子计算机时代',
        children: [
          { name: '电子管时代 (1946-1957)',
            children: [
              { name: 'ENIAC' },
              { name: '体积大 / 发热高' }
            ]
          },
          { name: '晶体管时代 (1958-1964)',
            children: [
              { name: '体积缩小' },
              { name: '可靠性提升' }
            ]
          },
          { name: '集成电路时代 (1965-)',
            children: [
              { name: '摩尔定律' },
              { name: '微处理器' }
            ]
          },
          { name: '冯·诺依曼架构',
            children: [
              { name: '运算器' },
              { name: '控制器' },
              { name: '存储器' },
              { name: '输入 / 输出' }
            ]
          }
        ]
      },
      exercises: [
        { type: 'choice',
          question: '世界上第一台电子计算机的名字是?',
          options: ['EDVAC', 'ENIAC', 'UNIVAC', 'IBM 360'],
          answer: 1,
          explanation: 'ENIAC (Electronic Numerical Integrator and Computer) 于 1946 年诞生。' },
        { type: 'choice',
          question: '下列哪一项<strong>不属于</strong>冯·诺依曼架构的五大部件?',
          options: ['运算器', '控制器', '存储器', '网络接口'],
          answer: 3,
          explanation: '五大部件: 运算器、控制器、存储器、输入设备、输出设备。' },
        { type: 'bool',
          question: '冯·诺依曼架构的核心思想是"程序和数据分离存储"。',
          answer: false,
          explanation: '恰好相反,冯氏架构强调程序和数据<strong>统一</strong>存放在同一存储器中。' },
        { type: 'fill',
          question: '1947 年贝尔实验室发明了______,逐步取代了电子管。',
          answer: '晶体管',
          explanation: '晶体管体积小、功耗低、寿命长,是第二代计算机的标志。' }
      ]
    }
  };

  /**
   * 兜底默认内容 — 当 sub-chapter 没有匹配时, 用这个保证页面正常
   */
  const DEFAULT_CONTENT = {
    subtitles: [
      { from: 0,   content: '欢迎来到本节课程。' },
      { from: 18,  content: '本节我们将围绕核心概念展开学习。' },
      { from: 42,  content: '请结合字幕和讲义同步理解。' },
      { from: 68,  content: '关键概念会高亮显示,记得做笔记。' },
      { from: 95,  content: '看完视频后,完成课后练习巩固所学。' }
    ],
    transcript: '<p>本节为示例讲义,后端可注入真实 AI 讲义内容。</p>',
    concepts: [
      { term: '示例概念', definition: '这是一个关键概念的占位说明。', example: '示例: 在实际学习中,概念会与视频内容对应。', level: 'basic' }
    ],
    mindMap: {
      name: '本节导图',
      children: [
        { name: '核心概念', children: [{ name: '定义' }, { name: '应用' }] },
        { name: '关联知识', children: [{ name: '前置' }, { name: '延伸' }] }
      ]
    },
    exercises: [
      { type: 'choice', question: '本节内容是否对你有帮助?', options: ['非常有帮助', '有帮助', '一般', '没帮助'], answer: 0, explanation: '感谢你的反馈!' }
    ]
  };

  /**
   * 公共 API — 根据子章节 id 取出内容
   */
  function getContent(subId) {
    if (!subId) return DEFAULT_CONTENT;
    return SAMPLE_CONTENT[subId] || DEFAULT_CONTENT;
  }

  global.CourseLearnData = {
    getContent,
    SAMPLE_CONTENT,
    DEFAULT_CONTENT
  };
})(window);
