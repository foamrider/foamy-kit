// Unit tests for kit/FoamyText.js (QML JS library, loaded here in node
// through kit/node-loader.cjs, the way plugins load it).
const assert = require("assert");
const Text = require("../kit/node-loader.cjs").load("FoamyText");

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

const E = "…";
const codePoints = (s) => Array.from(s).length;
const wellFormed = (s) => {
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c >= 0xd800 && c <= 0xdbff) {
      const n = s.charCodeAt(i + 1);
      if (!(n >= 0xdc00 && n <= 0xdfff)) return false;
      i++;
    } else if (c >= 0xdc00 && c <= 0xdfff) return false;
  }
  return true;
};

test("short text is unchanged", () => {
  assert.strictEqual(Text.cap("Song — Artist", 3, 40), "Song — Artist");
  assert.strictEqual(Text.cap("a\nb", 2, 5), "a\nb");
  assert.strictEqual(Text.cap("", 2, 5), "");
});

test("non-strings", () => {
  assert.strictEqual(Text.cap(null, 2, 5), "");
  assert.strictEqual(Text.cap(undefined, 2, 5), "");
  assert.strictEqual(Text.cap(12345678, 1, 4), "123" + E);
});

test("a long line is cut to maxChars with a visible ellipsis", () => {
  assert.strictEqual(Text.cap("abcdefgh", 1, 5), "abcd" + E);
  assert.strictEqual(codePoints(Text.cap("x".repeat(1000), 1, 80)), 80);
  assert.strictEqual(Text.cap("abcde", 1, 5), "abcde", "exactly maxChars is not cut");
});

test("extra lines are dropped and the last kept line says so", () => {
  assert.strictEqual(Text.cap("a\nb\nc\nd", 2, 10), "a\nb" + E);
  assert.strictEqual(Text.cap("aaaaa\nb\nc", 1, 5), "aaaa" + E, "a full last line makes room for the ellipsis");
  assert.strictEqual(Text.cap("aaaaaaa\nb", 1, 5), "aaaa" + E, "a cut last line keeps one ellipsis");
});

test("every line break Qt honours counts", () => {
  assert.strictEqual(Text.cap("a\r\nb\rc d e", 5, 5), "a\nb\nc\nd\ne");
  assert.strictEqual(Text.cap("a b c", 2, 5), "a\nb" + E);
});

test("trailing blank lines are not 'more text'", () => {
  assert.strictEqual(Text.cap("a\nb\n\n  \n", 2, 5), "a\nb");
  assert.strictEqual(Text.cap("a\n\n", 1, 5), "a");
  assert.strictEqual(Text.cap("a\n" + " ".repeat(5000) + "x", 1, 5), "a" + E, "blank run past the lookahead");
});

test("a surrogate pair is never split", () => {
  const emoji = "😀"; // U+1F600, two UTF-16 units
  for (let chars = 1; chars <= 6; chars++) {
    const out = Text.cap(emoji.repeat(10), 1, chars);
    assert.ok(wellFormed(out), `chars ${chars}: ${JSON.stringify(out)}`);
    assert.strictEqual(codePoints(out), chars, `chars ${chars} counts code points`);
  }
  assert.strictEqual(Text.cap("ab😀cd", 1, 3), "ab" + E);
  assert.strictEqual(Text.cap("a😀", 1, 2), "a😀", "a pair at the end fits as one character");
  const lines = Text.cap(("😀".repeat(3) + "\n").repeat(4), 2, 3);
  assert.ok(wellFormed(lines), JSON.stringify(lines));
  assert.strictEqual(lines, "😀😀😀\n😀😀" + E);
});

test("lone surrogates pass through as one character each", () => {
  const out = Text.cap("\ud800\ud800\ud800", 1, 2);
  assert.strictEqual(out, "\ud800" + E);
});

// A cut keeps what a reader sees as one character whole (foamy-media's
// tooltip rows): the letter at the cut goes with its marks, an emoji
// sequence or a flag goes whole. Both cuts: a line too long, and the last
// kept line of a text with more lines.
const a = "a".repeat(10);
const cutBoth = (piece, chars, expected, label) => {
  assert.strictEqual(Text.cap(a + piece + "zz", 1, chars), expected, `${label}: a long line`);
  assert.strictEqual(Text.cap(a + piece + "\nmore", 1, chars), expected, `${label}: lines dropped after it`);
};

test("a letter keeps its marks at a cut", () => {
  // An Arabic fatha, a Hebrew point, a Devanagari and a Thai vowel sign, a
  // Cyrillic titlo, Tibetan, Myanmar and Khmer vowel signs, the kana voiced
  // sound mark (also the halfwidth ones), the Thai and Lao vowel sign AM, a
  // Brahmi vowel sign past U+FFFF, the vowel or final of a Hangul syllable
  // written in jamo, and a Latin combining acute.
  const marked = [
    ["ب", "َ"], ["ב", "ָ"], ["क", "ि"], ["ก", "ิ"],
    ["а", "҃"], ["ཀ", "ཱ"], ["က", "ိ"], ["ក", "ា"],
    ["か", "゙"], ["ｶ", "ﾞ"], ["ｶ", "ﾟ"], ["น", "ำ"],
    ["ກ", "ຳ"], ["\u{11013}", "\u{11038}"], ["ᄀ", "ᅡ"], ["ᄀ", "ힰ"],
    ["가", "ᆨ"], ["e", "́"],
  ];
  for (const [letter, mark] of marked) {
    const code = "U+" + mark.codePointAt(0).toString(16).toUpperCase().padStart(4, "0");
    cutBoth(letter + mark, 12, a + E, code);
  }
  const accents = Text.cap("é".repeat(100), 1, 100);
  assert.ok(/^(é)+…$/.test(accents), JSON.stringify(accents));
});

test("an emoji sequence or a flag goes whole at a cut", () => {
  const family = "\u{1F468}‍\u{1F469}‍\u{1F467}"; // ZWJ sequence, 5 code points
  cutBoth(family, 13, a + E, "a cut inside a ZWJ sequence");
  cutBoth(family, 15, a + E, "a cut after its last part");
  cutBoth("\u{1F44D}\u{1F3FD}", 12, a + E, "a skin tone");
  cutBoth("❤️", 12, a + E, "a variation selector");
  const england = "\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}"; // tag sequence
  cutBoth(england, 17, a + E, "a tag sequence");
  // A flag is a pair of regional indicators, paired from the start of a run.
  const norway = "\u{1F1F3}\u{1F1F4}";
  cutBoth(norway, 12, a + E, "a flag");
  cutBoth(norway + norway, 14, a + norway + E, "the second of two flags");
});

test("output is bounded for any input", () => {
  const huge = ("x".repeat(5000) + "\n").repeat(2000);
  const out = Text.cap(huge, 4, 50);
  assert.strictEqual(out.split("\n").length, 4);
  assert.ok(out.split("\n").every((line) => codePoints(line) <= 50));
  const many = "a\n".repeat(100000);
  assert.strictEqual(Text.cap(many, 3, 10), "a\na\na" + E);
});

// The host bar tooltip shows at most 6 lines of 100 characters; plain
// numbers here, so a changed constant fails instead of passing along.
test("tooltip() keeps to the host tooltip's 6 lines of 100 characters", () => {
  const out = Text.tooltip(("y".repeat(500) + "\n").repeat(20));
  const lines = out.split("\n");
  assert.strictEqual(lines.length, 6);
  assert.ok(lines.every((line) => codePoints(line) === 100 && line.endsWith(E)));
});

test("bad limits fall back to the tooltip's 100 characters", () => {
  const long = "z".repeat(500);
  assert.strictEqual(codePoints(Text.cap(long, 0, -3)), 100);
  assert.strictEqual(codePoints(Text.cap(long, "x", NaN)), 100);
});

console.log(`PASS FoamyText: ${passed} tests`);
