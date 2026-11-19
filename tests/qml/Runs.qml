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
// selection, in RTL, at a larger font. Runs that don't match the text fall
// back to the plain field. Coloured runs are logged with their x range for
// a colour check. FOAMY_RTL=1 mirrors.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property bool rtl: Quickshell.env("FOAMY_RTL") === "1"
  readonly property string tag: host + "/" + (rtl ? "rtl" : "ltr") + "/" + Quickshell.env("FOAMY_THEME")
  property int checks: 0
  property int failures: 0

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
    check(styled.runsShown, "runs stay shown with a selection")
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
      shot(styled, "coloured", shell.finish)
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
