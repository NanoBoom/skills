#!/usr/bin/env node
// Enforces the invariants in CLAUDE.md. Run it before the `claude plugin
// validate` and `npx skills` checks, which know the manifest schema but not this
// repository's own rules.
//
//   node scripts/check-skills.mjs
//
// Exits non-zero on any error. Warnings never fail the run.

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const BUCKET = "prp-core";
const PLUGIN_NAME = "prp-core";
const KEBAB = /^[a-z0-9]+(-[a-z0-9]+)*$/;

const errors = [];
const warnings = [];
const err = (where, msg) => errors.push(`${where}: ${msg}`);
const warn = (where, msg) => warnings.push(`${where}: ${msg}`);

const read = (rel) => readFileSync(join(REPO, rel), "utf8");
const readJson = (rel) => {
  try {
    return JSON.parse(read(rel));
  } catch (e) {
    err(rel, `cannot parse (${e.message})`);
    return null;
  }
};

// Minimal frontmatter reader: the leading `---` block, top-level `key: value`
// pairs, with folded continuation lines. Enough for `name` and `description`.
const frontmatter = (path) => {
  const text = readFileSync(path, "utf8");
  if (!text.startsWith("---\n")) return null;
  const end = text.indexOf("\n---", 3);
  if (end === -1) return null;
  const fields = {};
  let key = null;
  for (const line of text.slice(4, end).split("\n")) {
    const match = /^([A-Za-z0-9_.-]+):\s?(.*)$/.exec(line);
    if (match) {
      key = match[1];
      fields[key] = match[2].trim().replace(/^["']|["']$/g, "");
    } else if (key && line.trim()) {
      fields[key] = `${fields[key]} ${line.trim()}`.trim();
    }
  }
  // A YAML folded scalar (`description: >-`) leaves the marker behind. Treat the
  // folded lines that followed as the value.
  for (const [k, v] of Object.entries(fields)) {
    if (v === ">-" || v === ">" || v === "|" || v === "|-") fields[k] = "";
  }
  return fields;
};

const plugin = readJson(".claude-plugin/plugin.json");
const marketplace = readJson(".claude-plugin/marketplace.json");
const skillsSh = readJson("skills.sh.json");

// --- manifests agree with each other -------------------------------------

if (plugin && plugin.name !== PLUGIN_NAME) {
  err("plugin.json", `\`name\` must stay "${PLUGIN_NAME}": the skills dispatch ${PLUGIN_NAME}:<agent> subagents by scoped name`);
}

const entry = marketplace?.plugins?.find((p) => p.name === plugin?.name);
if (marketplace && !entry) {
  err("marketplace.json", `no entry for plugin "${plugin?.name}"`);
} else if (entry) {
  if (entry.source !== "./") err("marketplace.json", `\`source\` must be "./" (the repository root is the plugin), got "${entry.source}"`);
  if (entry.version !== plugin.version) {
    err("marketplace.json", `version drift: entry ${entry.version} vs plugin.json ${plugin.version}`);
  }
}

// --- skills on disk match the plugin manifest ----------------------------

const bucketDir = join(REPO, "skills", BUCKET);
const onDisk = existsSync(bucketDir)
  ? readdirSync(bucketDir)
      .filter((n) => !n.startsWith("."))
      .filter((n) => statSync(join(bucketDir, n)).isDirectory())
      .sort()
  : [];

if (onDisk.length === 0) err(`skills/${BUCKET}`, "bucket is empty or missing");

const declared = (plugin?.skills ?? []).map((p) => p.replace(/^\.\//, ""));
const declaredNames = new Set();

for (const path of declared) {
  const expected = `skills/${BUCKET}/`;
  if (!path.startsWith(expected)) {
    err("plugin.json", `\`skills\` entry "${path}" is outside the ${BUCKET} bucket`);
    continue;
  }
  const name = path.slice(expected.length);
  declaredNames.add(name);
  if (!existsSync(join(REPO, path, "SKILL.md"))) {
    err("plugin.json", `\`skills\` entry "${path}" has no SKILL.md on disk`);
  }
}

for (const name of onDisk) {
  if (!declaredNames.has(name)) {
    err(`skills/${BUCKET}/${name}`, "missing from plugin.json `skills`. Claude Code does not scan bucket folders, so it will not load");
  }
}

// --- each SKILL.md ---------------------------------------------------------

const bucketReadme = existsSync(join(bucketDir, "README.md")) ? read(`skills/${BUCKET}/README.md`) : "";
const rootReadme = existsSync(join(REPO, "README.md")) ? read("README.md") : "";
const grouped = new Set((skillsSh?.groupings ?? []).flatMap((g) => g.skills ?? []));

if (!bucketReadme) err(`skills/${BUCKET}`, "bucket has no README.md");

for (const name of onDisk) {
  const where = `skills/${BUCKET}/${name}`;
  const skillMd = join(bucketDir, name, "SKILL.md");
  if (!existsSync(skillMd)) {
    err(where, "directory has no SKILL.md");
    continue;
  }

  const fm = frontmatter(skillMd);
  if (!fm) {
    err(where, "SKILL.md has no YAML frontmatter block");
    continue;
  }
  if (!fm.name) err(where, "frontmatter is missing `name`");
  else if (!KEBAB.test(fm.name)) err(where, `frontmatter \`name\` must be kebab-case (got "${fm.name}")`);
  else if (fm.name !== name) err(where, `frontmatter \`name\` is "${fm.name}" but the directory is "${name}"`);
  if (!("description" in fm)) err(where, "frontmatter is missing `description`");

  const text = readFileSync(skillMd, "utf8");
  const lines = text.split("\n").length;
  if (lines > 500) warn(where, `SKILL.md is ${lines} lines. Move detail into references/`);

  // A ${CLAUDE_PLUGIN_ROOT} path into skills/ must carry the bucket segment.
  // Dropping it is the classic mistake when porting from upstream, where the
  // skills sat one level higher.
  for (const match of text.matchAll(/\$\{CLAUDE_PLUGIN_ROOT\}\/skills\/([a-z0-9-]+)/g)) {
    if (match[1] !== BUCKET) {
      err(where, `\${CLAUDE_PLUGIN_ROOT}/skills/${match[1]}/... is missing the ${BUCKET} bucket segment`);
    }
  }

  if (!bucketReadme.includes(`(./${name}/SKILL.md)`)) err(where, `not linked from skills/${BUCKET}/README.md`);
  if (!rootReadme.includes(name)) err(where, "not listed in the top-level README.md");
  if (!grouped.has(name)) err(where, "not in any grouping in skills.sh.json");
}

for (const name of grouped) {
  if (!onDisk.includes(name)) err("skills.sh.json", `groups "${name}", which is not a skill on disk`);
}

// --- agents ---------------------------------------------------------------

const agentsDir = join(REPO, "agents");
const agents = existsSync(agentsDir) ? readdirSync(agentsDir).filter((f) => f.endsWith(".md")).sort() : [];
const agentNames = new Set(agents.map((f) => f.replace(/\.md$/, "")));

// Every prp-core:<agent> the skills dispatch has to exist, or the call fails at
// run time with nothing to fall back on.
for (const name of onDisk) {
  const text = readFileSync(join(bucketDir, name, "SKILL.md"), "utf8");
  for (const match of text.matchAll(new RegExp(`${PLUGIN_NAME}:([a-z0-9-]+)`, "g"))) {
    const target = match[1];
    if (!agentNames.has(target) && !onDisk.includes(target)) {
      err(`skills/${BUCKET}/${name}`, `dispatches ${PLUGIN_NAME}:${target}, which is neither an agent in agents/ nor a skill in this bucket`);
    }
  }
}

// --- hooks ----------------------------------------------------------------

if (existsSync(join(REPO, "hooks", "hooks.json"))) {
  const hooks = read("hooks/hooks.json");
  for (const match of hooks.matchAll(/\$\{CLAUDE_PLUGIN_ROOT\}\/([^"'\s]+)/g)) {
    if (!existsSync(join(REPO, match[1]))) err("hooks/hooks.json", `command path does not exist: ${match[1]}`);
  }
}

// --- report ---------------------------------------------------------------

for (const w of warnings) console.warn(`warn  ${w}`);
for (const e of errors) console.error(`error ${e}`);

const counted = `${onDisk.length} skill(s), ${agents.length} agent(s)`;
if (errors.length > 0) {
  console.error(`\nFAIL  ${errors.length} error(s), ${warnings.length} warning(s) across ${counted}`);
  process.exit(1);
}
console.log(`\nOK    ${counted}, ${warnings.length} warning(s)`);
