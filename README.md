# skill-evolver 🥢

> 一句话，从 GitHub 上千个 agent skill 里帮你淘出最好的那一个。

**skill-evolver** 是一个 [Agent Skills](https://skill.md) 开放格式的技能包：你说"帮我筛选自动剪辑 skill"，它就自动去 GitHub 搜索相关 skill 仓库 → 多维加权打分排名 → 语义复排过滤蹭关键词的高星仓库 → 把最优的一个直接交付到你的 skills 目录。

不吹不黑，它给的不是"star 最高的"，是"对你的任务最有用的"。

## 它是怎么打分的

| 维度 | 权重 | 说明 |
|------|------|------|
| 相关性 | 35% | 关键词在仓库名 / 简介 / topics 中的命中度 |
| Star 热度 | 25% | 对数归一化，10k star 封顶 |
| 活跃度 | 25% | 最近提交时间，30 天内满分，2 年归零 |
| 含 SKILL.md | +10% | 标准Agent skill 结构，拿来就能用 |

脚本粗排之后，Agent 会对前 3-5 名逐一阅读 README / SKILL.md 做语义复排，排除四类 impostor：蹭关键词的、步骤跑不通的、久不维护的、无 license 的。

**实测示例**（搜索 "video editing skill"）：

| # | 仓库 | Star | SKILL.md | 总分 |
|---|------|------|----------|------|
| 1 | maxazure/video-editing-skill | 206 | ✅ | 0.806 |
| 2 | Vincentwei1021/video-shotcraft | 14342 | ✅ | 0.740 |
| 5 | Recordly（35k star，但纯录屏工具，不相关） | 35464 | ❌ | 0.673 |

35k star 的录屏工具被正确压到第 5——star 高只说明人多，不说明对你的任务有用。

## 安装

### WorkBuddy

```bash
git clone https://github.com/cbx87/skill-evolver.git
cp -R skill-evolver ~/.workbuddy/skills/
```

重开会话后说一句话即自动触发。

### Claude Code

```bash
cp -R skill-evolver ~/.claude/skills/
```

### Codex CLI

```bash
cp -R skill-evolver ~/.codex/skills/
```

> Codex 的 skills 为实验特性，若未生效请在 `~/.codex/config.toml` 中添加 `[features] skills = true`，并重开会话。

## 用法

三个要素：**动词（筛选/找/排名/进化）+ "skill" + 领域关键词**。

```
帮我在 GitHub 上找最好的自动剪辑 skill，排名次，把最优的给我
```

或点名调用：

```
$skill-evolver 帮我筛选自动剪辑 skill
```

标准流程：关键词解析（中译英提高召回）→ GitHub 多组关键词搜索 → 加权排名 → 前 5 名语义复排 → 交付第一名（自动装到本地 skills 目录），第 2、3 名作备选。

## 进化模式 🧬

说"融合 / 进化 / 超越这些 skill"进入完整进化回路：

```
任务解析 → 搜索筛选 → 提取融合(v0) → 执行任务 → 对比打分
                              ↑                      │
                              └──── 差距分析 ←─ 未达标 ┘
                                                     ↓ 达标（连续 2 轮）
                                            交付 skill + 进化报告
```

- 四维评分：准确性 40% / 完整性 30% / 效率 15% / 稳健性 15%，**优先客观判据**（脚本断言、格式校验），LLM judge 仅兜底
- 评测集 ≥ 3 个变体任务，留 1 个盲测防过拟合
- 迭代上限 5 轮；不达标如实交付当前最优 + 差距报告，不虚报"已超越"

详见 [skill-evolver/references/evolution.md](skill-evolver/references/evolution.md)。

## 提速与限流

脚本仅用 Python 标准库、零依赖。GitHub 未认证搜索限流 10 次/分钟（脚本已内置组间等待与 403 自动重试）。如果你有 token：

```bash
export GITHUB_TOKEN=ghp_xxx   # 限流放宽到 5000 次/小时
```

## 目录结构

```
skill-evolver/
├── SKILL.md                      # 触发条件 + 标准模式流程 + 进化模式入口
├── scripts/
│   └── github_search_rank.py     # 搜索与加权排名（输出 Markdown 排名表 + JSON）
└── references/
    └── evolution.md              # 进化模式完整设计：融合、评测、迭代、终止标准
```

## License

[MIT](LICENSE) © 2026 cbx87
