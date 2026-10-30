// Unit tests for kit/FoamyPrefs.js (QML JS library, loaded here in node).
// Loaded the way plugins load it: through kit/node-loader.cjs.
const assert = require("assert");
const fs = require("fs");
const path = require("path");

const source = fs.readFileSync(path.join(__dirname, "../kit/FoamyPrefs.js"), "utf8");
const Prefs = require("../kit/node-loader.cjs").load("FoamyPrefs", { console: { log: console.log, warn() {} } });

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

const rich = [
  { key: "folders", type: "array", maxItems: 2, defaultValue: [],
    validate: (v) => v.every((f) => f && typeof f.path === "string") || "Each folder needs a path." },
  { key: "route", type: "object", defaultValue: null, validate: (v) => !!(v.from && v.to) },
  { key: "plan", type: "object", defaultValue: { days: [] } },
  { key: "name", type: "string", defaultValue: "" },
];

test("array and object types", () => {
  assert.ok(Prefs.valid(rich, "folders", [{ path: "/a" }]));
  assert.ok(!Prefs.valid(rich, "folders", [{ path: "/a" }, { path: "/b" }, { path: "/c" }]), "maxItems");
  assert.strictEqual(Prefs.problem(rich, "folders", [{ nope: 1 }]), "Each folder needs a path.", "validate() message");
  assert.ok(!Prefs.valid(rich, "folders", { path: "/a" }), "an object is not an array");
  assert.ok(Prefs.valid(rich, "route", { from: { id: 1 }, to: { id: 2 } }));
  assert.ok(!Prefs.valid(rich, "route", { from: { id: 1 } }), "validate false");
  assert.ok(!Prefs.valid(rich, "route", [1]), "an array is not an object");
  assert.ok(!Prefs.valid(rich, "route", null));
  assert.strictEqual(Prefs.value(rich, {}, "route"), null);
  const plan = Prefs.value(rich, {}, "plan");
  plan.days.push("mon");
  assert.deepStrictEqual(JSON.parse(JSON.stringify(Prefs.value(rich, {}, "plan"))), { days: [] }, "defaults are copied");
});

test("equal / overlay / settle", () => {
  assert.ok(Prefs.equal({ a: 1, b: [1, { c: 2, d: 3 }] }, { b: [1, { d: 3, c: 2 }], a: 1 }), "key order");
  assert.ok(!Prefs.equal([1, 2], [2, 1]));
  const pending = { a: "one", b: [1] };
  assert.deepStrictEqual(JSON.parse(JSON.stringify(Prefs.overlay({ a: "x", c: 3 }, pending))), { a: "one", c: 3, b: [1] });
  assert.deepStrictEqual(JSON.parse(JSON.stringify(Prefs.settle({ a: "one", b: [2] }, pending))), { b: [1] });
});

test("a second save merges over pending values, not the stale entry", () => {
  const writes = [];
  const bar = { shell: { updateEntryInline: (id, settings) => { writes.push(JSON.parse(JSON.stringify(settings))); return true; } } };
  const stale = { id: "foamy.x", name: "", keep: 1 };
  Prefs.save(bar, "foamy.x", rich, stale, "name", "first");
  const second = Prefs.save(bar, "foamy.x", rich, stale, "route", { from: 1, to: 2 }, { name: "first" });
  assert.ok(second.inline);
  assert.deepStrictEqual(writes[1], { name: "first", keep: 1, route: { from: 1, to: 2 } });
  const same = Prefs.save(bar, "foamy.x", rich, stale, "name", "first", { name: "first" });
  assert.ok(!same.changed, "a value equal to the pending one is a no-op");
});

test("array values bypass qs ipc list parsing on the CLI path", () => {
  const command = Array.from(Prefs.saveCommand("foamy.x", "folders", [{ path: "/a" }]));
  assert.strictEqual(command[0], "sh");
  assert.ok(command[2].includes('omarchy-shell shell setBarWidget "$1" "$2" "$3" "{}"'));
  assert.deepStrictEqual(command.slice(3), ["foamy-prefs", "foamy.x", "folders", ' [{"path":"/a"}]']);
  assert.strictEqual(Prefs.saveCommand("foamy.x", "route", { a: 1 })[0], "omarchy", "objects keep omarchy bar set");
  const refused = Prefs.save({ shell: { updateEntryInline: () => false } }, "foamy.x", rich, {}, "folders", [{ path: "/a" }]);
  assert.strictEqual(refused.command[0], "sh");
});

test("invalid values and missing module are refused", () => {
  assert.ok(!Prefs.save(null, "foamy.x", fields, {}, "layout", "grid").ok);
  assert.ok(!Prefs.save(null, "", fields, {}, "layout", "tiles").ok);
});

test("module name is a parameter (no hardcoded plugin id)", () => {
  assert.ok(!/foamy\.[a-z]/.test(source.replace(/\/\/.*$/gm, "")));
});

console.log(`PASS FoamyPrefs.js: ${passed} tests`);
