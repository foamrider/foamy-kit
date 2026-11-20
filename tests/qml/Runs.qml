import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"

// SafeTextField `runs`: each case sets the same text, selection and caret
// on a styled field and on a plain one, then saves both (FOAMY_OUT) for
// test_text_runs.py to compare. Runs in the field's own colour must look
// exactly like the plain field: at the start, scrolled to the end, with a
// selection (plain text then), in RTL, at a larger font, in Arabic.
// Runs that don't match the text fall back to the plain field, and text
// that shrinks under stale runs asks for no position past its end
// (test_text_runs.py checks the log for "out of range"). Mixed Latin and
// CJK runs sit on the editor's baseline, a run whose colour Qt doesn't know
// takes the field's colour, and while an input method composes
// (FOAMY_FAKE_IME=1: tests/fixtures/fake-ime) the plain editor shows the
// preedit. Coloured runs are logged with their x range for a colour check.
// FOAMY_RTL=1 mirrors.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property bool rtl: Quickshell.env("FOAMY_RTL") === "1"
  readonly property string tag: host + "/" + (rtl ? "rtl" : "ltr") + "/" + Quickshell.env("FOAMY_THEME")
  property int checks: 0
  property int failures: 0
  // FakeIme (tests/fixtures/fake-ime), when test_text_runs.py built it.
  property var ime: null
  Component.onCompleted: if (Quickshell.env("FOAMY_FAKE_IME") === "1")
    ime = Qt.createQmlObject("import QtQml; import FoamyFakeIme; QtObject { function compose(item, text) { FakeIme.compose(item, text) } function commit(item, text) { FakeIme.commit(item, text) } }", shell, "FakeIme")

  // A hint tone: between the background and the text, clearly apart from
  // both (a placeholder must not read as typed text in either theme).
  function hintTone(color, text) {
    function lum(c) {
      return 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b
    }
    var b = lum(FoamyPalette.background)
    var span = lum(text) - b
    var p = lum(color) - b
    return span !== 0 && p / span > 0.3 && p / span < 0.85
  }
  function check(ok, label) {
    checks++
    if (!ok) {
      failures++
      console.log("FOAMY FAIL " + tag + " " + label)
    }
  }
  function eq(actual, expected, label) {
    check(JSON.stringify(actual) === JSON.stringify(expected), label + ": got " + JSON.stringify(actual) + ", expected " + JSON.stringify(expected))
  }
  function near(a, b, t) {
    return Math.abs(a - b) <= (t === undefined ? 0.51 : t)
  }

  readonly property string sentence: "Buy oat milk #groceries @errand p1 tomorrow at 17:00 and then some more words"
  // Runs that join to `sentence`, every one in `color`, or coloured by kind.
  function tokens(text) {
    return text.split(/(\s+)/).filter(function (part) {
      return part !== ""
    })
  }
  function sameColour(text, color) {
    return tokens(text).map(function (part) {
      return {
        text: part,
        color: color
      }
    })
  }
  function coloured(text) {
    return tokens(text).map(function (part) {
      return {
        text: part,
        color: part.charAt(0) === "#" ? Commons.Color.accent : part === "p1" ? Commons.Color.urgent : part.charAt(0) === "@" ? "#3fb950" : undefined
      }
    })
  }

  FloatingWindow {
    implicitWidth: 800
    implicitHeight: 400
    color: Commons.Color.background

    Column {
      x: 20
      y: 20
      width: 360
      spacing: 12
      LayoutMirroring.enabled: shell.rtl
      LayoutMirroring.childrenInherit: true

      SafeTextField {
        id: styled
        width: parent.width
      }
      SafeTextField {
        id: plain
        width: parent.width
      }
      SafeTextField {
        id: secret
        width: parent.width
        masked: true
      }
    }
    Item {
      TestEvent {
        id: ev
      }
    }
  }

  FoamyWait {
    id: wait
  }

  // Each case: [name, setup(field, isStyled)]; both fields get the same setup.
  property var cases: []
  property int caseIndex: 0

  function apply(setup) {
    setup(styled, true)
    setup(plain, false)
  }
  function shot(item, name, then) {
    item.grabToImage(function (result) {
      check(result.saveToFile(Quickshell.env("FOAMY_OUT") + "/" + name + ".png"), "saved " + name)
      then()
    })
  }
  // Saves "<name>-styled.png" and "<name>-plain.png" after a frame.
  function pair(name, then) {
    wait.after(60, function () {
      shot(styled, name + "-styled", function () {
        shot(plain, name + "-plain", function () {
          console.log("FOAMY PAIR " + name)
          then()
        })
      })
    })
  }

  Timer {
    running: true
    interval: 300
    onTriggered: shell.start()
  }

  function start() {
    var fg = styled.foreground
    // The editor itself: runs drawn over a transparent editor.
    styled.text = sentence
    styled.runs = sameColour(sentence, fg)
    plain.text = sentence
    check(styled.runsShown, "matching runs are shown")
    check(styled.editorItem.color.a === 0, "the editor's own text is transparent under runs")
    check(!plain.runsShown && plain.editorItem.color.a === 1, "a field without runs draws its text")
    // Each run starts where the editor puts its first character.
    var layer = findByName(styled.editorItem, "runsLayer")
    var texts = layer ? layer.children.filter(function (child) {
      return child.text !== undefined
    }) : []
    eq(texts.length, tokens(sentence).length, "one Text per run")
    var at = 0
    var aligned = true
    for (var i = 0; i < texts.length; i++) {
      var rect = styled.editorItem.positionToRectangle(at)
      aligned = aligned && near(texts[i].x + layer.x, rect.x) && near(texts[i].y, rect.y)
      at += texts[i].text.length
    }
    check(aligned, "each run sits on the editor's own glyph position")
    // Where the editor clips its text (the paddings), in the field's pixels.
    console.log("FOAMY EDGES " + JSON.stringify([Math.round(styled.leftPadding), Math.round(styled.width - styled.rightPadding)]))
    pair("start", shell.scrolled)
  }
  function scrolled() {
    styled.cursorPosition = sentence.length
    plain.cursorPosition = sentence.length
    check(styled.contentX > 10 && near(styled.contentX, plain.contentX), "scrolled to the end " + [styled.contentX, plain.contentX])
    pair("scrolled", shell.selected)
  }
  function selected() {
    styled.select(10, 30)
    plain.select(10, 30)
    check(!styled.runsShown && styled.editorItem.color.a === 1, "a selection shows the plain text")
    pair("selected", shell.larger)
  }
  function larger() {
    styled.select(0, 0)
    plain.select(0, 0)
    styled.font.pixelSize = FoamyStyle.font.heading
    plain.font.pixelSize = FoamyStyle.font.heading
    styled.cursorPosition = 0
    plain.cursorPosition = 0
    check(styled.runsShown, "runs follow a larger font")
    pair("larger", shell.mismatch)
  }
  function mismatch() {
    // Texts that don't join to `text`: the plain field, never misaligned runs.
    styled.runs = sameColour(sentence + "!", Commons.Color.urgent)
    check(!styled.runsShown && styled.editorItem.color.a === 1, "runs longer than the text: plain")
    styled.runs = sameColour(sentence.replace("milk", "mylk"), Commons.Color.urgent)
    check(!styled.runsShown, "runs with other text: plain")
    styled.runs = [
      {
        text: 42
      }
    ]
    check(!styled.runsShown, "a run without text: plain")
    styled.runs = "not an array"
    check(!styled.runsShown, "runs that are not an array: plain")
    styled.runs = sameColour(sentence, Commons.Color.urgent)
    check(styled.runsShown, "matching runs again")
    // An edit before the caller updates the runs: plain until they match.
    styled.focusInput()
    ev.keyClickChar("x", Qt.NoModifier, -1)
    check(!styled.runsShown && styled.editorItem.color.a === 1, "a stale array after typing: plain")
    styled.text = sentence
    styled.runs = sameColour(sentence.slice(0, 20), Commons.Color.urgent)
    check(!styled.runsShown, "runs shorter than the text: plain")
    // Both fields unfocused, at the same caret, for the shot.
    secret.focusInput()
    styled.cursorPosition = 0
    plain.cursorPosition = 0
    pair("mismatch", shell.colours)
  }
  function colours() {
    styled.runs = coloured(sentence)
    check(styled.runsShown, "coloured runs are shown")
    // Where the coloured tokens are, in the field's own pixels.
    var editor = styled.editorItem
    var spans = []
    var at = 0
    var parts = tokens(sentence)
    for (var i = 0; i < parts.length; i++) {
      var kind = parts[i].charAt(0) === "#" ? "accent" : parts[i] === "p1" ? "urgent" : ""
      if (kind) {
        var a = editor.mapToItem(styled, editor.positionToRectangle(at).x, 0).x
        var b = editor.mapToItem(styled, editor.positionToRectangle(at + parts[i].length).x, 0).x
        spans.push({
          kind: kind,
          from: Math.round(Math.min(a, b)),
          to: Math.round(Math.max(a, b)),
          color: String(kind === "accent" ? Commons.Color.accent : Commons.Color.urgent)
        })
      }
      at += parts[i].length
    }
    console.log("FOAMY SPANS " + JSON.stringify(spans))
    // The caret: drawn by the field while runs hide the editor's own.
    styled.focusInput()
    styled.cursorPosition = 4
    var caret = findByName(editor, "maskedCaret")
    check(caret && caret.visible && near(caret.x, editor.cursorRectangle.x, 0.01), "the caret shows at the cursor with runs")
    check(caret.color.a === 1, "and is not transparent")
    plain.focusInput()
    check(!caret.visible, "no caret without focus")
    // A masked field ignores runs.
    secret.runs = [
      {
        text: "",
        color: "red"
      }
    ]
    secret.focusInput()
    ev.keyClickChar("a", Qt.NoModifier, -1)
    secret.runs = [
      {
        text: secret.text,
        color: "red"
      }
    ]
    check(!secret.runsShown && secret.editorItem.color.a === 1, "a masked field ignores runs")
    plain.focusInput()
    wait.after(60, function () {
      shot(styled, "coloured", shell.shrinking)
    })
  }
  // The caller updates its runs after the edit: until then the runs are
  // longer than the text, and nothing may ask the editor for a position
  // past its end.
  function shrinking() {
    var fg = styled.foreground
    var short = "Buy milk #home"
    styled.text = short
    styled.runs = sameColour(short, fg)
    check(styled.runsShown, "shrinking: runs shown")
    styled.focusInput()
    styled.cursorPosition = short.length
    for (var i = 0; i < 6; i++) {
      ev.keyClick(Qt.Key_Backspace, Qt.NoModifier, -1)
      check(!styled.runsShown, "shrinking: stale runs after Backspace give plain text")
      styled.runs = sameColour(styled.text, fg)
    }
    check(styled.runsShown && styled.text === short.slice(0, short.length - 6), "shrinking: runs again once they match " + JSON.stringify(styled.text))
    // Esc in a panel: the text clears, then the runs follow.
    styled.text = ""
    check(!styled.runsShown, "shrinking: cleared text with stale runs: plain")
    styled.runs = []
    styled.text = short
    styled.runs = sameColour(short, fg)
    styled.clear()
    check(!styled.runsShown, "shrinking: clear() with stale runs: plain")
    styled.runs = []
    // Neither field focused, for the shots.
    secret.focusInput()
    shell.arabic()
  }
  // Context-shaped text: one run draws it as the editor does; a selection
  // inside it (which would split it) shows the plain text, so every letter
  // keeps its joined form.
  function arabic() {
    var word = "سلام"
    styled.text = word
    plain.text = word
    styled.runs = [
      {
        text: word,
        color: styled.foreground
      }
    ]
    check(styled.runsShown, "Arabic: one run is shown")
    styled.select(1, 4)
    plain.select(1, 4)
    check(!styled.runsShown && styled.editorItem.color.a === 1, "Arabic: a selection shows the plain, shaped text")
    pair("arabic-selected", function () {
      styled.select(0, 0)
      plain.select(0, 0)
      check(styled.runsShown, "Arabic: runs again without a selection")
      pair("arabic", function () {
        styled.runs = [
          {
            text: word.charAt(0),
            color: styled.foreground
          },
          {
            text: word.slice(1),
            color: styled.foreground
          }
        ]
        check(!styled.runsShown, "Arabic: runs that split a joined word give plain text")
        shell.mixed()
      })
    })
  }
  // The Text items the runs layer draws.
  function runTexts(field) {
    var layer = findByName(field.editorItem, "runsLayer")
    return layer ? layer.children.filter(function (child) {
      return child.text !== undefined
    }) : []
  }
  // Latin and CJK runs: the editor's line is as tall as the CJK fallback
  // font, and every run must sit on the editor's own baseline (the
  // pixels match the plain field).
  function mixed() {
    var text = "Buy 漢字 milk"
    styled.text = text
    plain.text = text
    styled.runs = sameColour(text, styled.foreground)
    styled.cursorPosition = 0
    plain.cursorPosition = 0
    check(styled.runsShown && runTexts(styled).length === tokens(text).length, "mixed: Latin and CJK runs are shown")
    pair("mixed", shell.bogus)
  }
  // A colour string Qt can't read takes the field's colour, not black.
  function bogus() {
    styled.text = sentence
    plain.text = sentence
    styled.runs = sameColour(sentence, "bogus")
    check(styled.runsShown, "bogus: runs with an unusable colour are shown")
    var texts = runTexts(styled)
    check(texts.length > 0 && texts.every(function (item) {
      return Qt.colorEqual(item.color, styled.color)
    }), "bogus: every run takes the field's colour " + (texts.length ? texts[0].color : "none") + " vs " + styled.color)
    pair("bogus", shell.composing)
  }
  // An input method composing in a styled field: its preedit shows only in
  // the editor's own text, so the field shows the plain editor until the
  // composition ends.
  function composing() {
    if (!ime) {
      shell.placeholder()
      return
    }
    var text = "Buy milk"
    styled.text = text
    plain.text = text
    styled.runs = [
      {
        text: "Buy ",
        color: styled.foreground
      },
      {
        text: "milk",
        color: Commons.Color.urgent
      }
    ]
    styled.cursorPosition = 0
    plain.cursorPosition = 0
    check(styled.runsShown, "composing: runs shown before")
    ime.compose(styled.editorItem, "候选")
    ime.compose(plain.editorItem, "候选")
    check(styled.editorItem.inputMethodComposing && styled.editorItem.preeditText === "候选", "composing: the editor has the preedit")
    check(!styled.runsShown && styled.editorItem.color.a === 1, "composing: the plain editor shows the preedit")
    pair("composing", function () {
      ime.commit(styled.editorItem, "")
      ime.commit(plain.editorItem, "")
      check(!styled.editorItem.inputMethodComposing && styled.runsShown, "composing: runs again once the composition ends")
      shell.placeholder()
    })
  }
  // The placeholder, in both themes: a hint tone, never near-black on light.
  function placeholder() {
    styled.runs = []
    styled.text = ""
    styled.placeholderText = "Buy milk #home"
    check(hintTone(styled.placeholderTextColor, styled.foreground), "the placeholder is a hint tone " + [styled.placeholderTextColor, styled.foreground, FoamyPalette.background])
    wait.after(60, function () {
      shot(styled, "placeholder", shell.finish)
    })
  }
  function findByName(item, name) {
    if (!item)
      return null
    if (item.objectName === name)
      return item
    for (var i = 0; i < item.children.length; i++) {
      var found = findByName(item.children[i], name)
      if (found)
        return found
    }
    return null
  }
  function finish() {
    console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
    console.log("FOAMY DONE")
    Qt.quit()
  }
}
