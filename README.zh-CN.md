# PRP Core

面向 Claude Code 的完整 PRP（Product Requirement Prompt）工作流自动化，以
**Agent Skills** 的形式打包。

[English](./README.md)

本仓库同时是 `nanoboom` marketplace，发布两个插件。**`prp-core`** 是 PRP 工作
流，下文绝大部分内容都在讲它。**`github-project`** 是一个更小的独立插件，用于把
需求当作 GitHub Issue 来管理，它有自己的
[README](./skills/github-project/README.md)，单独安装。两者互不依赖。

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

> **Claude Code 是官方支持的运行环境。** 多数 skill 会派发
> [`agents/`](./agents) 里的 `prp-core:<agent>` 子 agent，还有一个 skill 用到
> [`hooks/`](./hooks) 里的 Stop hook。这两类东西都不会经由 `npx skills` 分发，
> 后者只复制 `SKILL.md` 文件。要获得完整能力，请安装插件。

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
| `/prp-core:prp-loop` | **脱离会话**的循环流水线：plan → implement → PR → review，评审与修复反复循环直到干净。`--until implement` 会在实施变绿、PR 打开后停下 |
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
到。完整文档见 [bucket README](./skills/github-project/README.md)。

| Skill | 说明 |
|-------|------|
| `/github-project:github-project-setup` | 检查、初始化或修复 Project、它的 `Status` 与 `Priority` 字段、Board 与 Backlog 视图、内置自动化、Issue 模板以及 `.github/github-project.yml` |
| `/github-project:github-project-manage` | 以十一种模式运行 Issue 生命周期，从起草需求到关闭它，并让每个 Issue 的 Project 条目保持同步 |
| `/github-project:github-project-audit` | 只读审计，按 28 条带稳定规则 ID 的规则目录检查 Issue 质量以及 Issue 与 Project 的一致性 |

## Agents

供评审和规划 skill 使用的专职顾问型 agent。它们在设计上只出报告：只做分析和汇
报，绝不修改文件或提交（这是由它们的 prompt 约束的，不是靠 `tools:` 白名单）。

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
用，也可以通过 Task 工具手动调用。

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

插件带一个 Stop hook，`hooks/prp-research-team-stop.sh`，用于校验
`prp-research-team` 的输出。该 skill 会把它的计划路径写进
`~/.prp/<project-key>/state/prp-research-team.state` 这个哨兵文件；Stop 时 hook
检查该计划是否包含六个必需章节，若有缺失，就带着缺失清单阻断一次完成。成功后它
会清理哨兵文件，忽略过期哨兵（超过 2 小时），并且绝不连续阻断两次。注意：这个
hook 只随插件分发。如果你只是把 skill 直接复制进 `.claude/skills/`，这项校验不
会运行。

## 工作流

### 大型功能：PRD → 计划 → 实施

```
/prp-core:prp-prd "user authentication system"
    ↓  生成带实施阶段表的 PRD
/prp-core:prp-plan ~/.prp/<project-key>/prds/user-auth.prd.md
    ↓  自动选中下一个待办阶段，生成计划
/prp-core:prp-implement ~/.prp/<project-key>/plans/user-auth-phase-1.plan.md
    ↓  执行、校验、提交、开 PR，并把交付结果回链到 PRD
对下一个阶段重复 /prp-core:prp-plan
```

### 中型功能：计划 → 实施

```
/prp-core:prp-plan "add pagination to the API"
/prp-core:prp-implement ~/.prp/<project-key>/plans/add-pagination.plan.md
```

### 放手不管：自主循环

```
/prp-core:prp-loop "add pagination to the API"
    ↓  plan → implement（循环到绿）→ PR → review → fix → 重新 review → 干净
```

### 从输入到一个已评审的 PR

```
/prp-core:prp-issue 123
    ↓  plan → implement → PR → review → 修正 → 重新 review → CI 变绿
```

## 安装

有两条路可以进来，它们给到的东西并不一样。

| | Claude Code 插件 | `npx skills add` |
|---|---|---|
| 装到本地的是什么 | skills、11 个 agent、Stop hook | `SKILL.md` 文件及其配套目录 |
| 调用方式 | `/prp-core:<name>`、`/github-project:<name>`，外加自动加载 | 取决于你的运行环境怎么处理 Agent Skill |
| 安装单位 | 一次一个插件，`prp-core` 与 `github-project` 分开装 | 一整份扁平的 26 个 skill，或你点名的那几个 |
| 更新 | 对着 marketplace 执行 `/plugin update` | `npx skills update` |
| 适合场景 | 把 PRP 工作流当作整体使用 | 单独取一个自包含的 skill，或运行环境不是 Claude Code |

如果你用 Claude Code，就装插件。只有当你想把某一个 skill 拿到别处用时，才该动
`npx skills`。

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

`details` 会打印组件清单：`prp-core` 是 23 个 skill、11 个 agent、1 个 hook，
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

如果只想在单次会话里加载某棵工作树而不真的安装，用
`claude --plugin-dir /absolute/path/to/skills`。`github-project` 插件对应的目录
是它自己的 bucket：
`--plugin-dir /absolute/path/to/skills/skills/github-project`。

### `npx skills add`（任意支持 Agent Skills 的环境）

这条路把 skill 复制进任何能理解 Agent Skills 的运行环境。不需要 marketplace，也
不需要 Claude Code。

```bash
npx skills@latest add NanoBoom/skills            # 交互式挑选
npx skills@latest add NanoBoom/skills --list     # 先看看里面有什么
npx skills@latest add NanoBoom/skills --all      # 全部 skill、全部 agent，不再询问
```

只取一个 skill，这才是这条路真正擅长的用法：

```bash
npx skills@latest add NanoBoom/skills --skill github-project-manage
npx skills@latest add NanoBoom/skills --skill prp-technical-writing --global
```

常用参数：`--global` 装在用户级而不是当前项目，`--agent '*'` 面向检测到的每一个
运行环境，`--copy` 写入真实文件而不是符号链接，`-y` 跳过确认。之后可以用
`npx skills list`、`npx skills update` 和 `npx skills remove` 管理已取用的
skill。

#### 你能得到什么，得不到什么

`npx skills` 是靠扫描 `skills/` 目录来发现 skill 的，所以它会找到两个 bucket 里
全部 26 个，并且不看插件清单。它只复制 `SKILL.md` 文件及其配套目录，本仓库的其
余内容一概不复制。它**不会**带上 [`agents/`](./agents) 里的 `prp-core:<agent>`
子 agent，也不会带上 [`hooks/`](./hooks) 里的 Stop hook。

于是：

- `github-project` 的三个 skill 在设计上就是自包含的。它们只通过 `gh` CLI 与
  GitHub 打交道，不读取自身目录之外的任何文件，所以这条路上什么都不会丢。
- 多数 `prp-core` skill 会派发子 agent 或读取 `${CLAUDE_PLUGIN_ROOT}`。用这种方
  式取走后它们会降级：skill 本身仍能加载，但它要委派出去的工作无处可去。这条路
  请用来取单个 skill，而不是取整套工作流。

取来的 skill 会归在 `General` 这个标题下，而不是它所在 bucket 的名字。这个标题
来自根目录的 `.claude-plugin/plugin.json`，纯属显示效果。

#### 用符号链接挂载工作树

面向维护者：[`scripts/link-skills.sh`](./scripts/link-skills.sh) 会把
`deprecated/` 之外的每个 skill 都符号链接进 `~/.claude/skills` 和
`~/.agents/skills`，这样在工作树里改动会立即生效。

## 环境要求

- 已安装 Claude Code
- 已配置 Git；PR 与 issue 操作需要 GitHub CLI（`gh`）
- [`uv`](https://docs.astral.sh/uv/)，用于运行内置的 `prp-loop` 编排器
  （`skills/prp-core/prp-loop/scripts/prp_loop.py`）

## 产物

产物和运行期状态写在仓库之外，落在目标项目共享的 PRP store 里：

```
~/.prp/<project-key>/
├── project.json       # 项目的规范路径与名称
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

`<project-key>` 的形式是 `<slug>-<hash8>`，其中 slug 取自规范主检出的目录名，
`hash8` 是 Git 对该检出路径算出的 blob hash 的前八位。这样每个 linked worktree
都会解析到同一个 store。设置 `PRP_HOME` 可覆盖默认的 `~/.prp` 根目录。

如果仓库被移动，它由路径推导出的 key 也会变。把旧 store 移到新推导出的 key 下，
并更新 `project.json` 里的 `path`；PRP 从不删除、也不会自动接管旧 store。

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

[CLAUDE.md](./CLAUDE.md) 是贡献者契约：目录布局、不变量、如何新增 skill，以及如
何验证一次改动。

## 许可

MIT。见 [LICENSE](./LICENSE) 和 [NOTICE](./NOTICE)。

## 支持

- Issues：https://github.com/NanoBoom/skills/issues
- 上游项目：https://github.com/Wirasm/PRPs-agentic-eng
