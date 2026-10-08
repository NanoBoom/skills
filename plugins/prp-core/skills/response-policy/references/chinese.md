# Chinese: controlled technical Chinese

These rules adapt the controlled-language method of ASD-STE100 to Chinese
syntax. They are not a Chinese edition of ASD-STE100, and a reply that
follows them does not conform to it. The English limits on word count,
tense, and part of speech do not carry over to Chinese; only the method
does.

Adapted from
[Fenng/Tech-Doc-Style-Chinese](https://github.com/Fenng/Tech-Doc-Style-Chinese)
(MIT), `references/controlled-technical-chinese.md` and
`references/terminology-and-typography.md`. The sentence limits and the
light-verb and `的` checks follow
[answer-me-with-html](https://github.com/QingYunA/answer-me-with-html)
(MIT), `src/lint/ste.js`. See `NOTICE` at the repository root.

Chinese text below is a sample, quoted as code. Write the reply itself in
Chinese.

## Six rules

1. **Keep the facts.** Do not add a number, date, limit, capability,
   condition, or conclusion. Do not drop a warning, limit, exception, unit,
   default, or failure. Keep the certainty of `可能`, `建议`, `计划`, and
   `通常`.
2. **One concept, one term.** Choose one preferred term for each object,
   state, and action, and keep it. Do not rotate synonyms. Spell out an
   abbreviation the first time, then keep one form.
3. **One step, one main action.** Start a step with a concrete verb and
   name its object; do not stop at `处理`, `操作`, or `执行`. Split actions
   that run in sequence into numbered steps. Do not split a condition, a
   negation, or a cause away from its action to make a sentence shorter.
4. **Conditions and risks before actions.** Put what the user must know
   before the action that needs it. Put a warning before the risky step.
   Do not hide a key limit in a trailing parenthesis.
5. **Name the actor, object, and result.** Separate what the system does
   from what the user does. Replace `该`, `其`, `此`, `上述`, and `相关`
   with the concrete name when the target could be unclear.
6. **Follow the real order.** Describe operations in the order they run.
   In troubleshooting, list low-risk, reversible, high-evidence checks
   first. Keep symptom, cause, action, and result in separate sentences.

## Sentence checks

These are prompts to check a sentence, not failures.

- A step has 35 Chinese characters or fewer. A descriptive sentence has 45
  or fewer. A paragraph has six sentences or fewer.
- Drop light verbs: `进行优化` becomes `优化`, `加以说明` becomes `说明`,
  `予以处理` becomes a concrete verb.
- Use no more than two `的` in one sentence. Split the sentence or cut a
  modifier.
- Drop vague words unless they are a defined term or a quotation:

| Avoid | Write instead |
| --- | --- |
| `赋能` | `提供`, or name the capability |
| `抓手` | `关键措施` |
| `闭环` | `完整流程`, or list the start, handling, and done conditions |
| `沉淀` | `形成`, `积累`, `保存` |
| `对齐` | `统一`, `确认一致` |
| `拉通`, `打通` | `连接` |
| `兜底` | the concrete fallback after a failure |
| `落盘` | `写入文件`, `保存到本地` |
| `透传` | `原样传给下游` |
| `至关重要` | state the consequence |

Words such as `场景`, `链路`, `梳理`, `输出`, and `复盘` depend on context.
Rewrite them only when a more concrete word fits.

## Typography

These apply to visible Chinese prose. They never apply inside code, paths,
URLs, commands, field names, or quoted literals.

- Use full-width Chinese punctuation. Put no space before or after a
  full-width mark: `支持 API、SDK 和命令行。`
- Quote with `「」` and nest with `『』`, unless the project sets another
  convention. Use `《》` for document and book titles.
- Put one half-width space between Chinese and Latin letters, digits, or
  version numbers: `使用 API 获取数据`, `等待 3 秒`, `版本 2.0 已发布`.
- Put one half-width space between Chinese and inline code, except next to
  full-width punctuation: ``运行 `npm install` 安装依赖``,
  ``运行 `npm install`。``
- Put a space between a number and a unit symbol, but not before `%` or
  `°`: `10 GB`, `200 ms`, `增长 50%`.
- Use `……` for an ellipsis. When a dash is needed, use `——`, but prefer to
  restructure the sentence.
- Write dates as `2026 年 10 月 5 日`. Separate a percentage from a change
  in percentage points.

## Terms and common errors

- Use official casing: `API`, `ID`, `URL`, `JSON`, `HTTP`, `GitHub`,
  `JavaScript`, `TypeScript`, `Node.js`, `PostgreSQL`, `YAML`, unless the
  project spells a name differently.
- Fix certain errors: `阀值` to `阈值`, `布署` to `部署`, `反回` to `返回`,
  `做为` to `作为`.
- Check by context: `截至 4 月 12 日` (up to a date) and `截止日期` (a
  deadline); `登录系统` and `登陆月球`; `认证` (identity) and `授权`
  (permission).

## Templates

For steps the user runs:

1. Preconditions
2. Risk or limit
3. Numbered steps
4. The expected result of each step
5. When to stop, and how to recover

For troubleshooting:

1. The observed symptom
2. The logs, state, or error codes to collect
3. Checks ordered by evidence and risk, each with its decision condition
4. The cause, only when the evidence supports it
5. Recovery, how to verify it, and when to stop

Do not invent an expected result or a recovery step the source does not
give. Mark it `待确认`.

## Regression samples

Each sample is a source sentence, its rewrite, and what to check. A rewrite
must not add information the source lacks.

1. Source: `在安装代理程序之前需要确认服务器能够访问更新地址，然后运行安装命令。`
   Rewrite: `1. 确认服务器能够访问更新地址。` `2. 运行安装命令。`
   Check: the condition comes first; no address or command was added.
2. Source: `选择保存以后系统会写入配置并重新加载服务。`
   Rewrite: `选择「保存」。系统随后写入配置并重新加载服务。`
   Check: the user action and the system action are separate.
3. Source: `请求失败时最多重试 3 次，每次间隔 5 秒。`
   Rewrite: `请求失败时，最多重试 3 次。每次重试间隔 5 秒。`
   Check: the count and the interval are unchanged.
4. Source: `页面无法打开时可能是网络问题，可以先检查浏览器是否能够访问其他站点。`
   Rewrite: `页面无法打开时，先检查浏览器能否访问其他站点。网络异常是可能原因之一。`
   Check: a possible cause stays possible.
5. Source: `系统通常会在任务完成后发送通知。`
   Rewrite: `系统通常在任务完成后发送通知。`
   Check: `通常` survives.
6. Source: `平台提供任务创建、状态查询和结果下载能力。`
   Rewrite: unchanged.
   Check: the source is already clear. Do not rewrite for variety.
