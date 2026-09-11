#!/usr/bin/env node
// Enforces the invariants in CLAUDE.md. Run it before the `claude plugin
// validate` and `npx skills` checks, which know the manifest schema but not this
// repository's own rules.
//
//   node scripts/check-skills.mjs
//
// Exits non-zero on any error. Warnings never fail the run.

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const KEBAB = /^[a-z0-9]+(-[a-z0-9]+)*$/;

// Every promoted bucket and the plugin that ships it. A bucket absent from this
// list is unpromoted: it reaches users through `npx skills` and
// `scripts/link-skills.sh` only, and nothing below applies to it.
//
// `root` is the plugin root relative to the repository, which is also what
// ${CLAUDE_PLUGIN_ROOT} resolves to for that plugin's skills. The repository
// root is the `prp-core` plugin, so its root is "".
const PLUGINS = [
  {
    bucket: "prp-core",
    name: "prp-core",
    root: "",
    source: "./",
    // 36 call sites dispatch prp-core:<agent> by scoped name, so this plugin
    // may reference agents/ and its own plugin root.
    selfContained: false,
  },
  {
    bucket: "github-project",
    name: "github-project",
    root: "skills/github-project",
    source: "./skills/github-project",
    // Ships no agents and reads nothing outside each skill's own directory, so
    // a single SKILL.md copied out through `npx skills` still works.
    selfContained: true,
  },
];

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

// Every file under a directory, recursively, skipping dot-directories.
const filesUnder = (dir) =>
  readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    if (e.name.startsWith(".")) return [];
    const path = join(dir, e.name);
    return e.isDirectory() ? filesUnder(path) : [path];
  });

const marketplace = readJson(".claude-plugin/marketplace.json");
const skillsSh = readJson("skills.sh.json");
const rootReadme = existsSync(join(REPO, "README.md")) ? read("README.md") : "";
const grouped = new Set((skillsSh?.groupings ?? []).flatMap((g) => g.skills ?? []));

// Every skill name that belongs to a promoted bucket, so skills.sh.json can be
// checked once against the whole set rather than once per plugin.
const promoted = new Set();

for (const spec of PLUGINS) {
  const manifestPath = join(spec.root, ".claude-plugin/plugin.json").replace(/\\/g, "/");
  const plugin = readJson(manifestPath);
  const bucketRel = `skills/${spec.bucket}`;
  const bucketDir = join(REPO, bucketRel);

  // --- manifests agree with each other -------------------------------------

  if (plugin && plugin.name !== spec.name) {
    err(manifestPath, `\`name\` must stay "${spec.name}": the marketplace entry and every scoped ${spec.name}:<component> reference resolve by it`);
  }

  const entry = marketplace?.plugins?.find((p) => p.name === spec.name);
  if (marketplace && !entry) {
    err("marketplace.json", `no entry for plugin "${spec.name}"`);
  } else if (entry && plugin) {
    if (entry.source !== spec.source) {
      err("marketplace.json", `\`source\` for "${spec.name}" must be "${spec.source}", got "${entry.source}"`);
    }
    if (entry.version !== plugin.version) {
      err("marketplace.json", `version drift for "${spec.name}": entry ${entry.version} vs ${manifestPath} ${plugin.version}`);
    }
  }

  // --- skills on disk match the plugin manifest ----------------------------

  const onDisk = existsSync(bucketDir)
    ? readdirSync(bucketDir)
        .filter((n) => !n.startsWith("."))
        .filter((n) => statSync(join(bucketDir, n)).isDirectory())
        .sort()
    : [];

  if (onDisk.length === 0) err(bucketRel, "bucket is empty or missing");
  for (const name of onDisk) promoted.add(name);

  // A manifest path is relative to the plugin root, which is the repository root
  // for prp-core and the bucket itself for a bucket-rooted plugin.
  const expected = (name) => relative(spec.root, `${bucketRel}/${name}`).replace(/\\/g, "/");
  const declared = (plugin?.skills ?? []).map((p) => p.replace(/^\.\//, ""));
  const declaredNames = new Set();
  const byPath = new Map(onDisk.map((name) => [expected(name), name]));

  for (const path of declared) {
    const name = byPath.get(path);
    if (name === undefined) {
      err(manifestPath, `\`skills\` entry "${path}" is not a directory in the ${spec.bucket} bucket`);
      continue;
    }
    declaredNames.add(name);
    if (!existsSync(join(REPO, spec.root, path, "SKILL.md"))) {
      err(manifestPath, `\`skills\` entry "${path}" has no SKILL.md on disk`);
    }
  }

  for (const name of onDisk) {
    if (!declaredNames.has(name)) {
      err(`${bucketRel}/${name}`, `missing from ${manifestPath} \`skills\`. Claude Code does not scan bucket folders, so it will not load`);
    }
  }

  // --- each SKILL.md -------------------------------------------------------

  const bucketReadme = existsSync(join(bucketDir, "README.md")) ? read(`${bucketRel}/README.md`) : "";
  if (!bucketReadme) err(bucketRel, "bucket has no README.md");

  const agentsDir = join(REPO, spec.root, "agents");
  const agentNames = new Set(
    existsSync(agentsDir)
      ? readdirSync(agentsDir).filter((f) => f.endsWith(".md")).map((f) => f.replace(/\.md$/, ""))
      : [],
  );

  for (const name of onDisk) {
    const where = `${bucketRel}/${name}`;
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

    if (spec.selfContained) {
      // The promise this bucket's README makes to `npx skills` users: a copied
      // skill still works. A plugin root path or a cross-plugin subagent would
      // silently break it, and only for them. References and assets count:
      // the skill reads them, so a leak there is a leak.
      for (const file of filesUnder(join(bucketDir, name))) {
        const body = readFileSync(file, "utf8");
        const at = `${where}/${relative(join(bucketDir, name), file).replace(/\\/g, "/")}`;
        if (body.includes("${CLAUDE_PLUGIN_ROOT}")) {
          err(at, `references \${CLAUDE_PLUGIN_ROOT}, but ${spec.name} is documented as self-contained`);
        }
        for (const other of PLUGINS) {
          if (other.name !== spec.name && body.includes(`${other.name}:`)) {
            err(at, `dispatches ${other.name}:<component> from another plugin, which is not installed with this one`);
          }
        }
      }
    } else {
      // A ${CLAUDE_PLUGIN_ROOT} path into skills/ must carry the bucket segment.
      // Dropping it is the classic mistake when porting from upstream, where the
      // skills sat one level higher.
      for (const match of text.matchAll(/\$\{CLAUDE_PLUGIN_ROOT\}\/skills\/([a-z0-9-]+)/g)) {
        if (match[1] !== spec.bucket) {
          err(where, `\${CLAUDE_PLUGIN_ROOT}/skills/${match[1]}/... is missing the ${spec.bucket} bucket segment`);
        }
      }
      // Every <plugin>:<agent> the skills dispatch has to exist, or the call
      // fails at run time with nothing to fall back on.
      for (const match of text.matchAll(new RegExp(`${spec.name}:([a-z0-9-]+)`, "g"))) {
        const target = match[1];
        if (!agentNames.has(target) && !onDisk.includes(target)) {
          err(where, `dispatches ${spec.name}:${target}, which is neither an agent in ${spec.root || "."}/agents nor a skill in this bucket`);
        }
      }
    }

    if (!bucketReadme.includes(`(./${name}/SKILL.md)`)) err(where, `not linked from ${bucketRel}/README.md`);
    if (!rootReadme.includes(name)) err(where, "not listed in the top-level README.md");
    if (!grouped.has(name)) err(where, "not in any grouping in skills.sh.json");
  }
}

for (const name of grouped) {
  if (!promoted.has(name)) err("skills.sh.json", `groups "${name}", which is not a skill in any promoted bucket`);
}

// --- hooks ------------------------------------------------------------------

if (existsSync(join(REPO, "hooks", "hooks.json"))) {
  const hooks = read("hooks/hooks.json");
  for (const match of hooks.matchAll(/\$\{CLAUDE_PLUGIN_ROOT\}\/([^"'\s]+)/g)) {
    if (!existsSync(join(REPO, match[1]))) err("hooks/hooks.json", `command path does not exist: ${match[1]}`);
  }
}

// --- report -----------------------------------------------------------------

for (const w of warnings) console.warn(`warn  ${w}`);
for (const e of errors) console.error(`error ${e}`);

const agents = existsSync(join(REPO, "agents"))
  ? readdirSync(join(REPO, "agents")).filter((f) => f.endsWith(".md"))
  : [];
const counted = `${promoted.size} skill(s) in ${PLUGINS.length} plugin(s), ${agents.length} agent(s)`;
if (errors.length > 0) {
  console.error(`\nFAIL  ${errors.length} error(s), ${warnings.length} warning(s) across ${counted}`);
  process.exit(1);
}
console.log(`\nOK    ${counted}, ${warnings.length} warning(s)`);
