---
name: skill-evolver
description: GitHub skill 搜索、排名与进化系统。当用户要求"筛选/搜索/找最好的 XX skill"、"进化一个 skill"、"把 GitHub 上的同类 skill 排名/融合"时使用。自动在 GitHub 搜索相关 skill 仓库，按 star、活跃度、相关性、文档完整度打分排名，交付最优 skill；可选进入融合进化模式，把多个 skill 融合并通过评测迭代直到优于所有原始候选。
agent_created: true
---

# Skill Evolver

## Overview

面向"一句话找最优 skill"的需求：用户提供一个领域关键词或任务描述（如"自动剪辑 skill"），本 skill 自动完成 **GitHub 搜索 → 候选筛选 → 加权排名 → 交付最优 skill**。用户明确要求"融合/进化/超越"时，进入进化模式（见 references/evolution.md）。

## 触发条件

- "帮我筛选/找/搜 XX skill"、"把最好的 XX skill 给我" → 标准模式
- "进化/融合/超越这些 skill" → 进化模式
- 输入中必须能提取出明确的领域关键词；提取不出时先向用户追问一句

## 标准模式流程（默认）

### Step 1: 关键词解析

从用户输入提取：领域关键词（中译英，GitHub 英文召回更好，可中英各搜一组）、判定相关性的关键词列表、最低 star 门槛（默认 20，小众领域可降为 5）。

### Step 2: 搜索与排名

运行排名脚本（仅标准库，无依赖；设了 `GITHUB_TOKEN` 环境变量则限流更宽）：

```bash
python3 <skill-dir>/scripts/github_search_rank.py \
  --query "video editing skill" \
  --keywords "video,editing,cut,ffmpeg" \
  --top 10 --min-stars 20 \
  --json /tmp/skill-evolver-candidates.json
```

脚本输出 Markdown 排名表 + JSON。评分构成：相关性 35% + star 热度 25% + 活跃度 25% + 含 SKILL.md 加分 10%（有 SKILL.md 的仓库是标准 agent skill，优先级天然更高）。

### Step 3: 语义复排（必须做，脚本只做粗排）

对排名前 3-5 的候选，逐一读取其 README / SKILL.md（可用 WebFetch 抓 raw.githubusercontent.com 上的文件），按以下维度人工复排：

1. **任务匹配度**：skill 真正解决的问题是否就是用户要的（排除蹭关键词的仓库）
2. **可执行性**：SKILL.md 步骤是否清晰、脚本是否可直接运行、依赖是否可安装
3. **维护状态**：最近提交时间、issue 响应情况
4. **许可合规**：MIT/Apache 优先；GPL 标注传染条款；无 license 不可交付

复排后产出最终排名表，明确标注"推荐第一名"及理由。

### Step 4: 交付最优 skill

- 第一名仓库若结构标准（根目录含 SKILL.md）：克隆或下载该仓库（`git clone --depth 1`），将其复制为 `~/.workbuddy/skills/<skill-name>/`，检查 frontmatter 完整性后告知用户可直接使用
- 若结构不标准：提取其核心逻辑改写成标准 skill 目录后交付，并在 CHANGELOG 中注明来源仓库
- 排名表 + 推荐理由 + 交付路径一并在回复中给出；第 2、3 名作为备选列出

## 进化模式

用户要求"融合/进化/超越"时，按 `references/evolution.md` 执行完整回路：任务解析 → 搜索筛选 → 提取融合 → 多方执行同一任务 → 四维评分 → 定向迭代，终止标准与交付格式见该文档。核心约束：

- 评分必须优先使用客观判据（脚本断言、格式校验），LLM judge 只兜底
- 评测集 ≥ 3 个变体任务，留 1 个盲测防过拟合
- 迭代上限 5 轮；不达标时如实交付当前最优 + 差距报告，不虚报"已超越"

## Resources

### scripts/
- `github_search_rank.py` — GitHub 仓库搜索与加权排名，输出 Markdown 排名表和 JSON

### references/
- `evolution.md` — 进化模式的完整回路设计：各步骤输入输出、评分矩阵、终止标准、交付格式
