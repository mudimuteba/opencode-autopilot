// .opencode/plugin/board.js
// Native board guards + startup freshness marker. Auto-discovered by opencode.
// No dependencies: node stdlib only (fs, path). Startup work never throws;
// dangerous tool calls are denied by throwing in tool.execute.before.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const PLUGIN_DIR = path.dirname(new URL(import.meta.url).pathname);
const ROOT = path.resolve(PLUGIN_DIR, "..", "..");

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}

function writeFreshness() {
  const versions = readJson(path.join(ROOT, "board", "versions.json"));
  const verified = versions?.deps?.["oh-my-openagent"]?.verified ?? "UNKNOWN";
  const home = process.env.HOME || "";
  const cached = home
    ? readJson(
        path.join(
          home,
          ".cache/opencode/packages/oh-my-openagent@latest/node_modules/oh-my-openagent/package.json"
        )
      )
    : null;
  const current = cached?.version ?? "MISSING";
  const lines = [
    `CURRENT: ${current}`,
    `VERIFIED: ${verified}`,
    current === verified
      ? "OK: worker matches verified pin"
      : "WARN: worker drift — run `bash board/sync-deps.sh --check`",
  ];
  try {
    fs.mkdirSync(path.join(ROOT, "dist"), { recursive: true });
    fs.writeFileSync(path.join(ROOT, "dist", ".freshness"), lines.join("\n") + "\n");
  } catch {
    // never break startup
  }
}

// --- bash guards (ported from hooks.yaml) ---
const SEPARATORS = new Set([";", "&&", "||", "|", "&"]);
const READERS = new Set([
  "cat",
  "less",
  "more",
  "head",
  "tail",
  "grep",
  "egrep",
  "fgrep",
  "sed",
  "awk",
  "source",
  ".",
]);

function tokenize(command) {
  const tokens = [];
  const re = /"([^"]*)"|'([^']*)'|(\S+)/g;
  let m;
  while ((m = re.exec(command)) !== null) tokens.push(m[1] ?? m[2] ?? m[3]);
  return tokens;
}

function base(token) {
  return token.split("/").pop();
}

function resolveTarget(target) {
  const expanded = target.replace(/^~(?=\/|$)/, os.homedir());
  const abs = path.isAbsolute(expanded) ? expanded : path.resolve(ROOT, expanded);
  try {
    return fs.realpathSync(abs);
  } catch {
    return abs;
  }
}

function deny(reason) {
  throw new Error(`BLOCKED: ${reason}`);
}

function guardBash(command) {
  const tokens = tokenize(command || "");
  tokens.forEach((token, index) => {
    if (base(token) !== "rm") return;
    for (let i = index + 1; i < tokens.length; i++) {
      const target = tokens[i];
      if (SEPARATORS.has(target)) break;
      if (target.startsWith("-")) continue;
      const rel = path.relative(ROOT, resolveTarget(target));
      if (rel === ".." || rel.startsWith(`..${path.sep}`)) {
        deny("rm target is outside the repository");
      }
    }
  });
  const forcePush =
    /(?:^|[;&|]\s*)git\s+push\b/.test(command) &&
    /(?:^|\s)--force(?:-with-lease)?(?:=\S+)?(?:\s|$)|(?:^|\s)-[^\s]*f[^\s]*(?:\s|$)/.test(
      command
    );
  const pushesMain = /(?:^|\s)(?:refs\/heads\/)?main(?::(?:refs\/heads\/)?main)?(?:\s|$)/.test(
    command
  );
  if (forcePush && pushesMain) deny("force-push to main is not allowed");
  const readsEnv = tokens.some((t) => READERS.has(base(t)));
  const namesEnv = tokens.some((t) => /(?:^|\/)\.env(?:\.[^/]*)?$/.test(t));
  if (readsEnv && namesEnv) deny("reading .env files through Bash is not allowed");
}

export default async () => ({
  config: async () => {
    writeFreshness();
  },
  "tool.execute.before": async (input, output) => {
    if (input.tool === "bash") guardBash(output.args?.command);
  },
});
