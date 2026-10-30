// Unit tests for kit/FoamyPrefs.js (QML JS library, loaded here in node).
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const source = fs.readFileSync(path.join(__dirname, "../kit/FoamyPrefs.js"), "utf8").replace(/^\.pragma library\s*$/m, "");
const sandbox = { module: { exports: {} }, console: { log: console.log, warn() {} } };
vm.runInNewContext(source, sandbox);
const Prefs = sandbox.module.exports;

const fields = [
  { key: "showPercentage", type: "boolean", defaultValue: true },
  { key: "layout", type: "enum", options: ["list", "tiles"], defaultValue: "list" },
  { key: "refreshSeconds", type: "integer", min: 30, max: 3600, step: 30, defaultValue: 60 },
  { key: "scale", type: "number", min: 0.5, max: 2, defaultValue: 1 },
  { key: "label", type: "string", maxLength: 8, pattern: "^[a-z]*$", defaultValue: "" },
];
let passed = 0;
function test(name, fn) { fn(); passed++; }

test("valid by type", () => {
  assert.ok(Prefs.valid(fields, "showPercentage", false));
  assert.ok(!Prefs.valid(fields, "showPercentage", "false"));
  assert.ok(Prefs.valid(fields, "layout", "tiles"));
  assert.ok(!Prefs.valid(fields, "layout", "grid"));
  assert.ok(Prefs.valid(fields, "refreshSeconds", 45), "step is a hint, not enforced");
  assert.ok(!Prefs.valid(fields, "refreshSeconds", 29));
  assert.ok(!Prefs.valid(fields, "refreshSeconds", 60.5));
  assert.ok(!Prefs.valid(fields, "refreshSeconds", NaN));
  assert.ok(Prefs.valid(fields, "scale", 1.25));
  assert.ok(Prefs.valid(fields, "label", "abc"));
  assert.ok(!Prefs.valid(fields, "label", "ABC"));
  assert.ok(!Prefs.valid(fields, "label", "abcdefghi"));
  assert.ok(!Prefs.valid(fields, "unknown", 1));
});

test("value falls back to defaults", () => {
  assert.strictEqual(Prefs.value(fields, { layout: "grid" }, "layout"), "list");
  assert.strictEqual(Prefs.value(fields, null, "refreshSeconds"), 60);
  assert.strictEqual(Prefs.value(fields, { refreshSeconds: 120 }, "refreshSeconds"), 120);
  assert.strictEqual(Prefs.value(fields, {}, "nope"), undefined);
  assert.deepStrictEqual(JSON.parse(JSON.stringify(Prefs.values(fields, { layout: "tiles" }))),
    { showPercentage: true, layout: "tiles", refreshSeconds: 60, scale: 1, label: "" });
});

test("merged keeps other keys and drops id", () => {
  const out = Prefs.merged({ id: "foamy.x", layout: "list", custom: [1] }, "layout", "tiles");
  assert.deepStrictEqual(JSON.parse(JSON.stringify(out)), { layout: "tiles", custom: [1] });
});

test("save prefers updateEntryInline with the full entry", () => {
  const calls = [];
  const bar = { shell: { updateEntryInline: (id, settings) => { calls.push([id, settings]); return true; } } };
  const r = Prefs.save(bar, "foamy.x", fields, { id: "foamy.x", layout: "list", other: 1 }, "layout", "tiles");
  assert.ok(r.ok && r.changed && r.inline);
  assert.strictEqual(r.command.length, 0);
  assert.deepStrictEqual(JSON.parse(JSON.stringify(calls)), [["foamy.x", { layout: "tiles", other: 1 }]]);
});

test("unchanged values write nothing", () => {
  let called = false;
  const bar = { shell: { updateEntryInline: () => { called = true; return true; } } };
  const r = Prefs.save(bar, "foamy.x", fields, { layout: "list" }, "layout", "list");
  assert.ok(r.ok && !r.changed && !called && r.command.length === 0);
});

test("refused inline save falls back to the CLI", () => {
  const bar = { shell: { updateEntryInline: () => false } };
  const r = Prefs.save(bar, "foamy.x", fields, {}, "refreshSeconds", 300);
  assert.deepStrictEqual(Array.from(r.command), ["omarchy", "bar", "set", "foamy.x", "refreshSeconds", "300", "--json"]);
  const noShell = Prefs.save({}, "foamy.x", fields, {}, "showPercentage", false);
  assert.deepStrictEqual(Array.from(noShell.command), ["omarchy", "bar", "set", "foamy.x", "showPercentage", "false", "--json"]);
  const throws = Prefs.save({ shell: { updateEntryInline: () => { throw new Error("x"); } } }, "foamy.x", fields, {}, "layout", "tiles");
  assert.strictEqual(throws.command[5], '"tiles"');
});

test("invalid values and missing module are refused", () => {
  assert.ok(!Prefs.save(null, "foamy.x", fields, {}, "layout", "grid").ok);
  assert.ok(!Prefs.save(null, "", fields, {}, "layout", "tiles").ok);
});

test("module name is a parameter (no hardcoded plugin id)", () => {
  assert.ok(!/foamy\.[a-z]/.test(source.replace(/\/\/.*$/gm, "")));
});

console.log(`PASS FoamyPrefs.js: ${passed} tests`);
