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

console.log(`PASS FoamyI18nText: ${passed} tests`);
