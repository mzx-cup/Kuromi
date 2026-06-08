# 演示用预存测试结果

所有测试已于 2026-06-08 提前运行并保存结果。面试演示时直接打开这些文件，不依赖终端实时运行。

## 文件速查

| 文件名 | 对应演示步骤 | 核心数字 | 用途 |
|--------|------------|---------|------|
| `01-core-tests-verbose.txt` | 步骤 5 | **91 passed, 3 skipped in 0.23s** | 主展示：逐条显示所有 91 个用例 PASSED |
| `02-parametrize.txt` | 步骤 2 | **10 passed in 0.14s** | parametrize 改造：8 个等价类 + 2 个边界值 |
| `03-ai-quality.txt` | 步骤 3 | **26 passed in 0.15s** | AI 输出质量：5 个维度 26 个用例 |
| `04-cv-validation.txt` | 补充展示 | **31 passed, 3 skipped in 0.04s** | CV 算法测试：分辨率/时长/宽高比/MP4 |
| `05-profile-aggregator.txt` | 补充展示 | **24 passed in 0.04s** | 画像聚合器：9 种映射 + 7 组评分公式 |
| `06-full-suite-summary.txt` | 全景展示 | **201 passed, 4 failed, 7 skipped** | 全量测试概览（4 个 failed 是项目原有问题）|
| `07-custom-markers.txt` | 步骤 4 | 5 个自定义 markers | pytest markers 注册信息 |

## 演示操作

1. 在 VS Code 左侧文件树展开 `demo-results/` 文件夹
2. 双击对应文件打开
3. **Ctrl+End** 跳到文件末尾 → 指汇总数字
4. **往上翻** → 让面试官看 PASSED 列表
