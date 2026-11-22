// Unit tests for kit/FoamyI18nText.js, the string code FoamyI18n.qml runs
// (loaded through kit/node-loader.cjs, the way plugin tests load it).
const assert = require("assert");
const I18n = require("../kit/node-loader.cjs").load("FoamyI18nText");

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
  } catch (error) {
    error.message = `${name}: ${error.message}`;
    throw error;
  }
}

test("substitute fills each hole once, values stay literal", () => {
  assert.strictEqual(I18n.substitute("%1 and {name}", ["%2{name}"]), "%2{name} and {name}");
  assert.strictEqual(I18n.substitute("Hello {name}", { name: "$&" }), "Hello $&");
  assert.strictEqual(I18n.substitute("Name %1 {name}", ["$& %2"]), "Name $& %2 {name}");
  assert.strictEqual(I18n.substitute("%1%", 13.5, (v) => String(v).replace(".", ",")), "13,5%", "numbers go through number()");
  assert.strictEqual(I18n.substitute("%1 of %2", [1]), "1 of %2", "a hole without a value stays");
  assert.strictEqual(I18n.substitute("plain", undefined), "plain");
  assert.strictEqual(I18n.substitute("%1", null), "%1");
});

test("translator: language, then English, then the key", () => {
  const en = { Devices: "Devices", "English only": "English only", "%1 devices": { one: "%1 device", other: "%1 devices" } };
  const no = { Devices: "Enheter", "%1 devices": { one: "%1 enhet", other: "%1 enheter" }, Empty: "" };
  const { t, tn } = I18n.translator(no, en);
  assert.strictEqual(t("Devices"), "Enheter");
  assert.strictEqual(t("English only"), "English only");
  assert.strictEqual(t("Unknown"), "Unknown");
  assert.strictEqual(t("Empty"), "Empty", "an empty translation falls back");
  assert.strictEqual(tn("%1 devices", 1), "1 enhet");
  assert.strictEqual(tn("%1 devices", 3), "3 enheter");
  assert.strictEqual(tn("%1 devices", -1), "-1 enhet");
  assert.strictEqual(t("%1 devices"), "%1 enheter", "t() of a plural entry is its other form");
  const english = I18n.translator(en, en);
  assert.strictEqual(english.tn("%1 devices", 1), "1 device");
});

// kit/i18n-texts.json: the texts kit components hand a plugin to translate,
// which check.sh requires in the plugin's catalogs. The constants the kit
// exports for them are listed under their component (the paste and save
// failures are tied to it in tests/qml/Clipboard.qml and Lifecycle.qml).
test("kit/i18n-texts.json lists each text once, under a kit component", () => {
  const listed = require("../kit/i18n-texts.json");
  const components = require("../kit/components.json");
  const load = require("../kit/node-loader.cjs").load;
  for (const entry of listed) {
    assert.ok(Object.hasOwn(components, entry.component), `a kit component: ${entry.component}`);
    assert.ok(typeof entry.text === "string" && entry.text !== "", `a text: ${JSON.stringify(entry)}`);
    assert.ok(typeof entry.source === "string" && entry.source !== "", `a source: ${JSON.stringify(entry)}`);
  }
  const texts = listed.map((entry) => entry.text);
  assert.deepStrictEqual(texts.filter((text, i) => texts.indexOf(text) !== i), [], "no text twice");
  const under = (component) => listed.filter((entry) => entry.component === component).map((entry) => entry.text);
  assert.ok(under("FoamyNative").includes(load("FoamyNative").UNAVAILABLE_TEXT), "FoamyNative.UNAVAILABLE_TEXT");
  const Prefs = load("FoamyPrefs");
  for (const text of [Prefs.NOT_ALLOWED, Prefs.NO_ENTRY, Prefs.STORED_INVALID])
    assert.ok(under("FoamyPrefs").includes(text), `FoamyPrefs: ${text}`);
});

console.log(`PASS FoamyI18nText: ${passed} tests`);
