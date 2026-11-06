// Unit tests for kit/FoamyNative.js (QML JS library, loaded here in node
// through kit/node-loader.cjs), including the real `bash -c 'exec …'` launch
// against stub helpers in a temporary plugin directory.
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync, spawnSync } = require("child_process");

const Native = require("../kit/node-loader.cjs").load("FoamyNative");
// Arrays from the loader's vm context have that context's prototype.
const plain = (value) => JSON.parse(JSON.stringify(value));
let passed = 0;
function test(name, fn) {
  try { fn(); passed++; } catch (error) { console.log(`FAIL FoamyNative.js: ${name}`); throw error; }
}

const hosttype = execFileSync("bash", ["-c", "printf %s \"$HOSTTYPE\""]).toString();
const base = fs.mkdtempSync(path.join(os.tmpdir(), "foamy-native-test-"));
const plugin = path.join(base, "My Plugin");
const bin = path.join(plugin, "bin", hosttype);
fs.mkdirSync(bin, { recursive: true });
function stub(name, script, mode) {
  fs.writeFileSync(path.join(bin, name), "#!/bin/sh\n" + script + "\n");
  fs.chmodSync(path.join(bin, name), mode === undefined ? 0o755 : mode);
}
// Prints its PID, then each argument on its own NUL-terminated record.
stub("foamy-echo-helper", 'printf "%s\\0" "$$" "$@"; exit "${FOAMY_EXIT:-0}"');
stub("foamy-plain-helper", "exit 0", 0o644);

function run(argv, env) {
  return spawnSync(argv[0], argv.slice(1), { env: Object.assign({}, process.env, env || {}) });
}

try {
  test("command builds the bash exec argv", () => {
    assert.deepStrictEqual(plain(Native.command("/p", "foamy-x-helper", ["set", "balanced"])),
      ["bash", "-c", 'exec -- "$1/bin/$HOSTTYPE/$2" "${@:3}"', "foamy-native", "/p", "foamy-x-helper", "set", "balanced"]);
    assert.deepStrictEqual(plain(Native.command("/p", "foamy-x-helper").slice(3)), ["foamy-native", "/p", "foamy-x-helper"]);
    assert.deepStrictEqual(plain(Native.command("/p", "h", [1, "2"]).slice(6)), ["1", "2"]);
  });

  test("command rejects unsafe names and non-string arguments", () => {
    for (const name of ["", "../x", "a/b", ".hidden", "-x", " x", undefined, 3])
      assert.throws(() => Native.command("/p", name, []), { name: "TypeError" }, String(name));
    assert.throws(() => Native.command("", "h", []), { name: "TypeError" });
    assert.throws(() => Native.command(undefined, "h", []), { name: "TypeError" });
    assert.throws(() => Native.command("/p", "h", "set"), { name: "TypeError" });
    assert.throws(() => Native.command("/p", "h", [{}]), { name: "TypeError" });
    assert.throws(() => Native.command("/p", "h", [NaN]), { name: "TypeError" });
    assert.throws(() => Native.command("/p", "h", [null]), { name: "TypeError" });
  });

  test("unavailable is true only for 126 and 127", () => {
    assert.ok(Native.unavailable(127) && Native.unavailable(126));
    for (const code of [0, 1, 2, 124, 125, 128, 137, -1, undefined, null, "127"])
      assert.ok(!Native.unavailable(code), String(code));
    assert.strictEqual(Native.UNAVAILABLE_TEXT, "This plugin's helper isn't available for this CPU.");
  });

  test("localPath turns file URLs into paths", () => {
    assert.strictEqual(Native.localPath("file:///home/u/My%20Plugin/"), "/home/u/My Plugin");
    assert.strictEqual(Native.localPath("file:///home/u/plugin"), "/home/u/plugin");
    assert.strictEqual(Native.localPath("/home/u/plugin//"), "/home/u/plugin");
    assert.strictEqual(Native.localPath("file:///"), "/");
  });

  test("bash runs bin/$HOSTTYPE/<name> with the arguments verbatim and no bash left over", () => {
    const args = ["set", "two words", "", "$HOME", "'q\"", "-n", "line\nbreak", "ünï"];
    const result = run(plain(Native.command(plugin, "foamy-echo-helper", args)));
    assert.strictEqual(result.status, 0, String(result.stderr));
    const records = result.stdout.toString().split("\0").slice(0, -1);
    assert.strictEqual(records[0], String(result.pid), "exec replaced bash: the helper has bash's PID");
    assert.deepStrictEqual(records.slice(1), args);
  });

  test("the helper's own exit code passes through", () => {
    const result = run(Native.command(plugin, "foamy-echo-helper", []), { FOAMY_EXIT: "5" });
    assert.strictEqual(result.status, 5);
    assert.ok(!Native.unavailable(result.status));
  });

  test("a missing helper exits 127, a non-executable one 126", () => {
    const missing = run(Native.command(plugin, "foamy-missing-helper", ["x"]));
    assert.strictEqual(missing.status, 127, String(missing.stderr));
    assert.ok(Native.unavailable(missing.status));
    const other = run(Native.command(path.join(base, "nowhere"), "foamy-echo-helper", []));
    assert.strictEqual(other.status, 127);
    const plain = run(Native.command(plugin, "foamy-plain-helper", []));
    assert.strictEqual(plain.status, 126, String(plain.stderr));
    assert.ok(Native.unavailable(plain.status));
  });
} finally {
  fs.rmSync(base, { recursive: true, force: true });
}
console.log(`PASS FoamyNative.js: ${passed} tests`);
