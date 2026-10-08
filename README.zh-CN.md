# PRP Core

完整的 PRP（Product Requirement Prompt）工作流自动化，以 **Agent Skills** 加专职
子 agent 的形式打包，支持 Claude Code、Codex 和 Pi。

[English](./README.md)

本仓库同时是 `nanoboom` marketplace，发布两个插件。**`prp-core`** 是 PRP 工作
流，下文绝大部分内容都在讲它。**`github-project`** 是一个更小的独立插件，用于把
需求当作 GitHub Issue 来管理，它有自己的
[README](./plugins/github-project/README.md)，单独安装。两者互不依赖。

> **本仓库是一个 fork。** 它 fork 自
> [Wirasm/PRPs-agentic-eng](https://github.com/Wirasm/PRPs-agentic-eng) 的
> `prp-core` 插件，fork 点是提交 `2cced43`（2026-09-01），此后在这里独立维护。
> 原始工作的全部功劳归 Rasmus Widing。fork 点上具体改了什么见
> [NOTICE](./NOTICE)，授权条款见 [LICENSE](./LICENSE)。

## 概览

本插件提供一套完整的工作流，用 PRP 方法论来创建、执行并交付功能。这里的
**PRP = PRD + 经过整理的代码库情报 + agent/runbook**，目标是让 AI agent 一次
就能交付可上生产的代码。

所有内容都以 **skill** 形式发布（不是 slash command）。大部分 skill 既
**可由用户主动调用**（输入 `/prp-core:<name>`），也**可由 agent 自动调用**（当
请求与 skill 的 description 匹配时，Claude 会自动加载）。维护者的 triage 和
worklist 两个 skill 仅支持用户主动调用。

> **要装上 agent，而不只是 skill。** 多数 skill 会派发
> [`agents/`](./plugins/prp-core/agents) 里的 `prp-core:<agent>` 子 agent，还有两个
> skill 用到 [`hooks/`](./plugins/prp-core/hooks) 里的 Stop hook。`npx skills` 只复
> 制 `SKILL.md` 文件。请按[你所用环境的安装方式](#安装)把 agent 一起装上；
> [docs/harnesses.md](./docs/harnesses.md)（英文）说明了每个环境保留和丢失什么。

## Skills

### 产品与规划

| Skill | 说明 |
|-------|------|
| `/prp-core:prp-prd` | 交互式、问题优先的 PRD 生成器，产出带实施阶段表的文档 |
| `/prp-core:prp-prd-update` | 随着工作落地，维护 PRD 的阶段状态和产物链接 |
| `/prp-core:prp-plan` | 创建实施计划（来自 PRD 或自由描述）。同时通过 `update-references` 工作流建立计划之间的双向引用 |
| `/prp-core:prp-diagram` | 给计划补一份纯 mermaid 的可视化：数据模型、架构与流程 |
| `/prp-core:prp-spike` | 用能证伪它的最小一次性产物，来了结一个可行性问题 |
| `/prp-core:prp-research-team` | 用 agent 团队设计一支动态研究队伍和研究计划 |
| `/prp-core:prp-codebase-question` | 用并行 agent 研究代码库如何运作，记录现状 |

### 构建与交付

| Skill | 说明 |
|-------|------|
| `/prp-core:prp-issue` | 在同一个上下文里，把一个 issue、PRD、文档、计划或想法一路带到发布出来的 `READY TO MERGE` 评审和绿色 CI |
| `/prp-core:prp-implement` | 执行计划直到通过校验的提交和 PR，并写下可长期留存的实施报告 |
| `/prp-core:prp-commit` | 支持自然语言指定文件的智能提交 |
| `/prp-core:prp-pr` | 推送分支并按模板创建 PR |
| `/prp-core:prp-loop` | **自驱动**的循环流水线：plan → implement → PR → review，评审与修复反复循环直到干净，每个阶段都在一个可实时查看的全新子 agent 里运行。`--until implement` 会在实施变绿、PR 打开后停下 |
| `/prp-core:prp-deliver` | 实验性。只有被显式调用时才会运行 |

### 评审与分诊

| Skill | 说明 |
|-------|------|
| `/prp-core:prp-review` | 基于 agent 的 PR 评审，使用该 skill 当前的默认评审员集合；指定专项 scope 是叠加而非替换 |
| `/prp-core:prp-debug` | 定位根因，并把证据发布到对应的 GitHub issue |
| `/prp-core:prp-maintainer-triage` | 用轻量的维护者分诊流程处理外部贡献的 PR 或上报的 issue。仅用户主动调用 |
| `/prp-core:prp-issue-contract` | 创建 issue，或在 agent 自动化开始前检查它的前置条件 |

### 编排与工作区

| Skill | 说明 |
|-------|------|
| `/prp-core:prp-orchestrate` | 把当前会话变成**编排者**：在 git worktree 里协调多条自主交付流，带人工闸门和合并闸门、长期决策记录以及合并排序 |
| `/prp-core:prp-worktree` | 在 `.worktrees/` 下创建、列出并安全拆除隔离的检出 |
| `/prp-core:prp-worklist` | 渲染一个仓库上待办的工作，让维护者看清下一步该接哪件。仅用户主动调用 |
| `/prp-core:agent-policy` | 启动 agent 时按任务类型选定 model 和 effort，以节省 token。附 Claude Code 与 Codex 的速查表 |
| `/prp-core:response-policy` | 给用户的每条回复都用用户的语言、先给结论，并遵守受控写作规则：英文用 ASD-STE100（80% 达标），中文用受控技术中文。所有需要汇报的 skill 都会应用它 |

### 撰写

| Skill | 说明 |
|-------|------|
| `/prp-core:prp-meta-skill` | 编写新 skill，并把臃肿的 skill 重构成精简的 `SKILL.md` + `references/`（它规定的是手艺，不是你项目的内容） |
| `/prp-core:prp-technical-writing` | 撰写和编辑清晰、具体、可验证的开发者文档 |
| `/prp-core:prp-bro` | 用大白话重述上一条回复，不带术语 |

### GitHub Issue 需求管理

这是 `github-project` 插件，单独用 `/plugin install github-project@nanoboom`
安装。这三个 skill 只通过 `gh` CLI 与 GitHub 打交道，别的什么都不用：没有子
agent，没有插件根路径，也不读取各自目录之外的任何文件。因此单独用
`npx skills` 拿走一个 `SKILL.md` 仍然可用，这一点上面的 `prp-core` skill 做不
到。完整文档见 [插件 README](./plugins/github-project/README.md)。

| Skill | 说明 |
|-------|------|
| `/github-project:github-project-setup` | 检查、初始化或修复 Project、它的 `Status` 与 `Priority` 字段、Board 与 Backlog 视图、内置自动化、Issue 模板、`.github/github-project.yml`，以及 Issue 文本使用的语言 |
| `/github-project:github-project-manage` | 以十一种模式运行 Issue 生命周期，从起草需求到关闭它，并让每个 Issue 的 Project 条目保持同步 |
| `/github-project:github-project-audit` | 只读审计，按 28 条带稳定规则 ID 的规则目录检查 Issue 质量以及 Issue 与 Project 的一致性 |

## Agents

供评审和规划 skill 使用的专职顾问型 agent。它们在设计上只出报告：只做分析和汇
报，绝不修改文件或提交。每个 agent 都设置了 `disallowedTools: Write, Edit, NotebookEdit`，
在 Codex 里对应成只读 sandbox，在 Pi 里对应成只读的工具列表。

### 代码库分析

| Agent | 说明 |
|-------|------|
| `codebase-analyst` | 用 file:line 引用说明代码是「怎么」工作的 |
| `codebase-explorer` | 找出代码「在哪」，并提取其中的模式 |
| `root-cause-analyzer` | 对失效行为给出因果链证明、最小修复边界和回归检查 |
| `web-researcher` | 在网上检索文档、API 与最佳实践 |

### 评审

| Agent | 说明 |
|-------|------|
| `code-reviewer` | 通用正确性、合理性、范围以及与仓库的契合度 |
| `comment-analyzer` | 实质性失真的说明文字，以及具体的维护陷阱 |
| `pr-test-analyzer` | 有实际意义却缺少回归保护的行为 |
| `silent-failure-hunter` | 变得与成功无法区分的失败路径 |
| `seam-analyzer` | 缺失的类型，以及跨系统边界的漂移 |
| `code-simplifier` | 用已验证的更小原语去掉可避免的机械结构 |
| `docs-impact-agent` | 会改变读者行为的错误文档或缺失文档 |

评审 agent 由 `/prp-core:prp-review` 和 `/prp-core:prp-issue` 的评审阶段自动调
用，也可以通过 Agent 工具手动调用。在 Claude Code 之外，每个 agent 的名字是
`prp-core__<agent>`，安装后的 skill 里也是这样写的。

## 项目附属文档

有两份可选文档，如果你的项目里有，需要它们的 skill 就会读取。放在仓库任何位置都
行。从你的 `AGENTS.md` 或 `CLAUDE.md` 链过去，agent 就能立刻找到；否则 skill 会
按文件名去找。不要把它们放进 PRP store，那个目录在仓库之外、存放生成的产物；这
两份是你自己的东西，应当跟它们所约束的代码一起进版本控制。没有任何东西会创建它
们，缺失时也不会有任何东西失败。

| 文件 | 内容 | 谁会读 |
|------|------|--------|
| `direction.md` | 产品方向与范围：这个项目是为什么而存在的，以及它拒绝变成什么 | `prp-plan`、`prp-review`、`prp-issue-contract`、`prp-maintainer-triage` |
| `engineering.md` | 用工程经理的口吻写下工作被检验的标准：目标函数、品味、风险姿态，以及评审到底是为了什么 | `prp-plan`、`prp-implement`、`prp-review` 及其评审 agent、`prp-issue-contract`、`prp-maintainer-triage` |

它们的存在是为了把判断从 prompt 里挪出去。`AGENTS.md` 承载简短而长期有效的指
引；产品方向会变，属于 `direction.md`；工作被检验的标准属于 `engineering.md`，
它保留需要判断的部分，把一旦可以机器检查的东西交给 lint 规则、类型或 CI 检查。
一个与既定产品方向相冲突的改动，是需要操作者裁定的范围问题，而不是作者能在 diff
里修掉的缺陷。

## Hooks

插件带两个 Stop hook 和一个需要手动开启的 UserPromptSubmit hook。

`hooks/prp-research-team-stop.sh` 用于校验 `prp-research-team` 的输出。该 skill 会把它的计划路径写进
`.prp/state/prp-research-team.state` 这个哨兵文件；Stop 时 hook
检查该计划是否包含六个必需章节，若有缺失，就带着缺失清单阻断一次完成。成功后它
会清理哨兵文件，忽略过期哨兵（超过 2 小时），并且绝不连续阻断两次。

`hooks/prp-loop-stop.sh` 让驱动 `prp-loop` 的会话一直工作到循环 done 或 halted，
正是它让一次 `/prp-core:prp-loop` 调用跑完所有阶段。它只读
`.prp/state/prp-loop.state.json`：循环运行期间拦住记录为 owner 的那个会话；已派发的
阶段子 agent 在运行时放行；连续三次续跑都没有状态变化时也放行。其他会话照常停止。

`hooks/prp-response-policy-prompt.sh` 默认关闭。每个需要向你汇报的 PRP skill 在汇报这一步
已经应用 `response-policy` skill；这个 hook 把同一套规则扩展到其他所有回复。开启方法：在
Claude Code 设置的 `env` 块里把 `PRP_RESPONSE_POLICY` 设为 `1`：

```json
{ "env": { "PRP_RESPONSE_POLICY": "1" } }
```

开启后，每条 prompt 会附带一条不到 100 token 的简短提醒：用你的语言回复、先给结论、遵守
受控写作规则。它不读取 prompt 内容。删掉这个变量即可关闭。

三个 hook 都只随插件分发，并且是为 Claude Code 写的。如果你只是把 skill 直接复制进
`.claude/skills/`，它们都不会运行。其他环境的情况见
[docs/harnesses.md](./docs/harnesses.md#hooks)。

## 工作流

### 大型功能：PRD → 计划 → 实施

```
/prp-core:prp-prd "user authentication system"
    ↓  生成带实施阶段表的 PRD
/prp-core:prp-plan .prp/prds/user-auth.prd.md
    ↓  自动选中下一个待办阶段，生成计划
/prp-core:prp-implement .prp/plans/user-auth-phase-1.plan.md
    ↓  执行、校验、提交、开 PR，并把交付结果回链到 PRD
对下一个阶段重复 /prp-core:prp-plan
```

### 中型功能：计划 → 实施

```
/prp-core:prp-plan "add pagination to the API"
/prp-core:prp-implement .prp/plans/add-pagination.plan.md
```

### 放手不管：自主循环

```
/prp-core:prp-loop "add pagination to the API"
    ↓  plan → implement（循环到绿）→ PR → review → fix → 重新 review → 干净
       每个阶段一个全新子 agent，由当前会话驱动
```

### 从输入到一个已评审的 PR

```
/prp-core:prp-issue 123
    ↓  plan → implement → PR → review → 修正 → 重新 review → CI 变绿
```

## 安装

所有环境都从同一份源码 `plugins/<plugin>/` 安装，但不是每个环境都能拿到全部内容。
细节见 [docs/harnesses.md](./docs/harnesses.md)。

| 环境 | 安装方式 | Skills | 11 个 agent | Hooks |
|---|---|---|---|---|
| Claude Code | 插件 marketplace | 有 | 有 | 有 |
| Codex | clone 后 `make install-codex` | 有 | 有 | 无 |
| Pi | clone 后 `make install-pi` | 有 | 需要 Pi 的 `subagent` 扩展 | 无 |
| 任意 Agent Skills 环境 | `npx skills add` | 有 | 无 | 无 |

从 clone 安装需要 [`uv`](https://docs.astral.sh/uv/) 和 `make`。`git pull` 后再跑一次
同一个 `make` 目标即可更新，`make uninstall-<harness>` 只删除它安装过的内容。

### Claude Code 插件（推荐）

marketplace 只需注册一次，之后从中安装任一插件。两个插件互相独立，谁也不需要
谁。

```
/plugin marketplace add NanoBoom/skills
/plugin install prp-core@nanoboom
/plugin install github-project@nanoboom   # 可选，独立
```

重启 Claude Code，让 skill、agent 和 hook 加载。

同样的事在 REPL 之外也能做，写脚本或 Dockerfile 时你要的就是这个：

```bash
claude plugin marketplace add NanoBoom/skills
claude plugin install prp-core@nanoboom --scope user
claude plugin install github-project@nanoboom --scope user
```

`--scope` 可取 `user`（默认，对你所有项目生效）、`project`（写进仓库的
`.claude/settings.json` 并提交，克隆这个仓库的人都会共享）或 `local`（只在这个
仓库、只在你这台机器上生效）。

#### 验证

```bash
claude plugin list
claude plugin details prp-core@nanoboom
```

`details` 会打印组件清单：`prp-core` 是 25 个 skill、11 个 agent、3 个 hook，
`github-project` 是 3 个 skill。在会话里，`/plugin` 会把两者列在 `nanoboom`
marketplace 之下，输入 `/prp-core:` 也能补全出已安装的 skill。

#### 更新与卸载

```bash
claude plugin marketplace update nanoboom
claude plugin update prp-core@nanoboom      # 重启后生效
claude plugin uninstall prp-core@nanoboom
```

#### 给整个团队安装

把下面这段提交到项目的 `.claude/settings.json`。此后每个打开这个仓库的人都会被
提示安装这两个插件，不需要手动加 marketplace：

```json
{
  "extraKnownMarketplaces": {
    "nanoboom": {
      "source": {
        "source": "github",
        "repo": "NanoBoom/skills"
      }
    }
  },
  "enabledPlugins": {
    "prp-core@nanoboom": true,
    "github-project@nanoboom": true
  }
}
```

#### 直接跑本地工作树

要试用本地检出，就把 marketplace 指向目录而不是 GitHub。这会改写你设置里的
`nanoboom` 条目，用完记得改回来：

```
/plugin marketplace add /absolute/path/to/skills
/plugin install prp-core@nanoboom
# 重启 Claude Code
```

如果只想在单次会话里加载某个插件而不真的安装，用
`claude --plugin-dir /absolute/path/to/skills/plugins/prp-core`，或
`.../plugins/github-project`。

### Codex

```bash
git clone https://github.com/NanoBoom/skills && cd skills
make install-codex
```

需要 `PATH` 上有 Codex CLI。它会生成 `build/codex/` 作为一个本地 Codex marketplace，
用 `codex plugin marketplace add` 注册为 `nanoboom`，再用 `codex plugin add` 逐个安
装其中的插件。skill 里的派发名已经改写成 `prp-core__<agent>`，超过 Codex 8000 字节
提示上限的 skill 会被拆分，内容不会被截掉。Codex 插件不能携带自定义 agent，所以 11
个 agent 以 `prp-core__<agent>.toml` 的形式链接进 `${CODEX_HOME:-~/.codex}/agents/`，
各自带上模型、推理强度和只读 sandbox。`ONLY=agents` 或 `ONLY=plugins` 只装其中一半（配合 `PROJECT` 时可选 `ONLY=skills|agents`）。

Codex 会把安装的插件复制进自己的缓存，所以 `git pull` 后要重新运行
`make install-codex`。如果之前把 `NanoBoom/skills` 添加成了 Codex marketplace，先移除
它（`codex plugin marketplace remove nanoboom`）：这种方式不受支持，因为 Codex 会原样
读取 Claude Code 格式的插件。也不要再混用 `npx skills` 装的副本，否则 Codex 会把这些
skill 列两遍。

### Pi

```bash
git clone https://github.com/NanoBoom/skills && cd skills
make install-pi
```

这会把 skill、agent、prompt 模板和扩展链接进 `~/.pi/agent/`（或
`$PI_CODING_AGENT_DIR`）。Pi 核心没有子 agent，这些 agent 要配合 Pi 的参考扩展
`subagent` 或兼容扩展才能加载。agent 使用从 Claude 别名映射过来的 Anthropic 模型；
要换 provider，修改 [`tools/adapters/capabilities.py`](./tools/adapters/capabilities.py)
里的 `MODEL_ALIASES` 后重新运行。

### 选择插件，或安装到项目

`make install-codex` 和 `make install-pi` 都支持下面这些变量，
`make uninstall-<harness>` 支持 `PLUGINS` 和 `PROJECT`：

```bash
make install-pi PLUGINS=github-project               # 只装部分插件（默认全部）
make install-pi PROJECT=/abs/path/to/app             # 装进项目的 .pi/，而不是 ~/.pi/agent
make install-codex PROJECT=/abs/path/to/app COPY=1   # 拷贝真实文件，项目可以提交
make uninstall-pi PROJECT=/abs/path/to/app
```

装到项目时，Codex 会在 `<project>/.codex/` 拿到 skill 和 agent，但不安装插件，所以没有
Codex 的 hooks 和 MCP 服务。两个工具都要在你信任该项目之后才会加载项目里的文件。不加
`COPY=1` 时项目里放的是指向你本机 clone 的软链接，只在你自己的机器上有效。细节见
[docs/harnesses.md](./docs/harnesses.md#install-options)。

### `npx skills add`（任意支持 Agent Skills 的环境）

这会把 skill 复制进任何理解 Agent Skills 的环境，不需要 marketplace，也不需要
clone：

```bash
npx skills@latest add NanoBoom/skills            # 交互式挑选
npx skills@latest add NanoBoom/skills --list     # 先看看有什么
npx skills@latest add NanoBoom/skills --skill github-project-manage
npx skills@latest add NanoBoom/skills --skill prp-technical-writing --global
```

常用参数：`--global` 装到用户级而不是当前项目，`--agent '*'` 面向所有检测到的环
境，`--copy` 写入真实文件而不是符号链接，`-y` 跳过提示。之后可以用
`npx skills list`、`npx skills update`、`npx skills remove` 管理装过的内容。

它只复制 `SKILL.md` 文件及其目录，别的都不带，所以**不会**带上 agent 和
hook。三个 `github-project` skill 在设计上就是自包含的，什么都不会丢。多数
`prp-core` skill 会派发子 agent，这样拿走会降级：skill 能加载，但它要委派的工作
无处可去。这条路适合单独取一个 skill；要用整个工作流，请走上面对应环境的安装方式。

## 环境要求

- 上面任一环境
- 已配置 Git；PR 与 issue 操作需要 GitHub CLI（`gh`）
- [`uv`](https://docs.astral.sh/uv/)，用于运行内置的 `prp-loop` 状态机
  （`plugins/prp-core/skills/prp-loop/scripts/prp_loop.py`）、`prp-worktree` 脚本，以及
  `make` 安装目标

## 产物

产物和运行期状态写在目标项目的 PRP store 里，也就是当前检出根目录下的 `.prp/`：

```
<checkout-root>/.prp/
├── .gitignore         # 内容是 `*`，store 连同它自己一起被忽略
├── prds/              # 产品需求文档
├── plans/             # 实施计划
├── research/          # 代码库研究
├── research-plans/    # 多 agent 研究计划
├── reports/           # 实施报告
├── reviews/           # 给人读的 PR 评审
├── debug/             # 根因分析报告
├── orchestration/     # 并行工作流的运行文件
└── state/             # 循环状态、日志和 hook 哨兵文件
```

根目录由 `git rev-parse --show-toplevel` 解析，所以每个 worktree 都有自己的 store，
就放在它正在改的代码旁边。不在仓库里时，store 落在当前目录。也就是说 worktree 看不到
主检出里的 PRD、计划和报告：需要就拷进来，或者用 `PRP_DIR` 把两边指到同一个 store。

store 永远不会被提交：它会写一个内容为 `*` 的 `.gitignore`，同时忽略自身和里面的
内容，因此 `git status` 看不到它，`git add -A` 也扫不进去。store 跟着仓库一起移动，
不需要重新算 key；但删掉检出也会带走产物，删 worktree 正是最常见的情形，想保留就先把
`.prp/` 拷出去。

设置 `PRP_DIR` 可以把 store 放到别处：在必须保持仓库干净的机器上放回 `$HOME` 下，或者
指向主检出的 `.prp/`，让多个 worktree 共用一个 store。`/prp-orchestrate` 就是这么做的，
它把每个工作流 owner 都钉在编排者的 store 上，产物因此比 worktree 活得久。

## PRP 方法论

**PRP = PRD + 经过整理的代码库情报 + agent/runbook。** 核心原则：

1. **上下文为王**：把 agent 需要的全部上下文写进来（或引用进来）
2. **校验循环**：可执行的关卡，AI 自己跑、自己修，直到变绿
3. **信息密度高**：真实的模式、file:line、命令；不掺水
4. **渐进式成功**：从小处起步，先校验，再增强

计划是长期有效的实施契约。实施结果、校验、偏离、提交和 PR 交付都写在配套的报告
里，这样后续的上下文无需改动或归档计划，就能恢复出当前的真实状态。

## 故障排查

**插件加载不出来**：先 `/plugin uninstall prp-core@nanoboom`，再重装并重启。

**找不到 skill**：确认安装后重启过 Claude Code；检查 `/help` 和 `/plugin`。

**每个 skill 都出现两份**：说明你同时装了本插件和上游的
`prp-core@prp-marketplace`。卸掉其中一个。

## 参与贡献

[AGENTS.md](./AGENTS.md) 是贡献者契约：目录布局、不变量、如何新增 skill、agent、
插件或运行环境，以及如何验证一次改动。`make help` 列出维护用的目标。

## 许可

MIT。见 [LICENSE](./LICENSE) 和 [NOTICE](./NOTICE)。

## 支持

- Issues：https://github.com/NanoBoom/skills/issues
- 上游项目：https://github.com/Wirasm/PRPs-agentic-eng
