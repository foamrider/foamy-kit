import QtQuick
import QtQuick.Controls as Controls
import QtTest
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"

// SafeTextArea: Enter and Shift+Enter insert newlines, the keyPressed hook
// (Ctrl+Enter), Tab moves the focus, editingFinished on focus loss, paste
// through kit/clipboard.sh `multiline` and the fake wl-paste (line breaks
// kept, NUL and oversized text refused, cut at maximumLength, a late result
// dropped after newer typing or clear(), middle-click pastes the primary
// selection), never Qt's own clipboard; typing at maximumLength drops the
// key instead of the text's end; the height grows from minimumHeight to
// maximumHeight and then scrolls to the caret; accessibility and the menu.
// FOAMY_RTL=1 mirrors. A shot of the field goes to FOAMY_OUT.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property bool rtl: Quickshell.env("FOAMY_RTL") === "1"
  readonly property string tag: host + "/" + (rtl ? "rtl" : "ltr") + "/" + Quickshell.env("FOAMY_THEME")
  readonly property string state: Quickshell.env("TEST_CLIPBOARD_STATE")
  property int checks: 0
  property int failures: 0
  property int edits: 0
  property int finished: 0
  property int saves: 0

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
    return Math.abs(a - b) <= (t === undefined ? 1.01 : t)
  }
  function key(k, modifiers) {
    ev.keyClick(k, modifiers === undefined ? Qt.NoModifier : modifiers, -1)
  }
  function type(text) {
    for (var i = 0; i < text.length; i++)
      ev.keyClickChar(text.charAt(i), Qt.NoModifier, -1)
  }
  function readFile(path) {
    var request = new XMLHttpRequest()
    request.open("GET", "file://" + path, false)
    request.send(null)
    return String(request.responseText || "")
  }

  FloatingWindow {
    id: window
    implicitWidth: 800
    implicitHeight: 600
    color: Commons.Color.background

    Rectangle {
      id: card
      x: 20
      y: 20
      width: 380
      height: column.height + 24
      color: Commons.Color.background

      Column {
        id: column
        x: 12
        y: 12
        width: 356
        spacing: 8
        LayoutMirroring.enabled: shell.rtl
        LayoutMirroring.childrenInherit: true

        SafeTextArea {
          id: area
          width: parent.width
          placeholderText: "Description"
          Accessible.name: "Description"
          translate: function (key) {
            return "«" + key + "»"
          }
          onTextEdited: shell.edits++
          onEditingFinished: shell.finished++
          onKeyPressed: function (event) {
            if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && (event.modifiers & Qt.ControlModifier)) {
              shell.saves++
              event.accepted = true
            }
          }
        }
        SafeTextField {
          id: after
          width: parent.width
        }
        // Qt's own (offscreen, in-process) clipboard, as a native TextEdit reads it.
        TextEdit {
          id: probe
          width: parent.width
          height: 1
          opacity: 0
        }
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

  // What the fake wl-paste prints next (hostenv.clipboard_fakes()).
  Process {
    id: fixture
  }
  function setClipboard(mode, then) {
    fixture.command = ["clipboard-fixture", mode]
    fixture.running = true
    wait.waitFor(function () {
      return !fixture.running
    }, 5000, then, "clipboard-fixture " + mode)
  }
  function paste(trigger, label, then) {
    trigger()
    check(area.pasteRunning, label + ": the paste runs out of process")
    wait.waitFor(function () {
      return !area.pasteRunning
    }, 10000, then, label + " ends")
  }
  function pasteWith(mode, label, then) {
    setClipboard(mode, function () {
      shell.paste(function () {
        key(Qt.Key_V, Qt.ControlModifier)
      }, label, then)
    })
  }

  Timer {
    running: true
    interval: 300
    onTriggered: shell.typing()
  }

  function typing() {
    var editor = area.editorItem
    check(editor.Accessible.role === Accessible.EditableText && editor.Accessible.multiLine === true, "accessible as a multi-line edit")
    eq(editor.Accessible.name, "Description", "the editor carries the field's name")
    check(near(area.height, area.minimumHeight), "empty: minimumHeight " + area.height)
    area.focusInput()
    check(editor.activeFocus, "the field takes focus")
    type("ab")
    key(Qt.Key_Return)
    type("c")
    key(Qt.Key_Return, Qt.ShiftModifier)
    type("d")
    eq(area.text, "ab\nc\nd", "Enter and Shift+Enter insert newlines")
    eq(shell.edits, 6, "textEdited per typed key")
    key(Qt.Key_Return, Qt.ControlModifier)
    eq([area.text, shell.saves], ["ab\nc\nd", 1], "keyPressed takes Ctrl+Enter (no newline)")
    key(Qt.Key_Tab)
    check(after.inputActiveFocus, "Tab moves the focus to the next field")
    eq(shell.finished, 1, "editingFinished when the field loses the focus")
    area.focusInput()
    key(Qt.Key_Tab, Qt.ShiftModifier)
    check(!editor.activeFocus, "Shift+Tab moves the focus back")
    eq(area.text, "ab\nc\nd", "Tab types nothing")
    var menu = editor.Controls.ContextMenu.menu
    var labels = []
    for (var i = 0; i < menu.count; i++) {
      var item = menu.itemAt(i)
      if (item && item.text)
        labels.push(item.text)
    }
    eq(labels, ["«Undo»", "«Redo»", "«Cut»", "«Copy»", "«Paste»", "«Select all»"], "menu labels through translate")
    shell.pasting()
  }

  // Paste: Qt's clipboard is never read; line breaks kept; one textEdited.
  function pasting() {
    probe.text = "sentinel"
    probe.selectAll()
    probe.copy()
    area.clear()
    area.focusInput()
    type("ab")
    key(Qt.Key_Left)
    var edits = shell.edits
    pasteWith("lines", "Ctrl+V", function () {
      eq(area.text, "aone\ntwo\nthreeb", "Ctrl+V pastes with its line breaks, at the caret")
      eq(area.cursorPosition, 14, "caret after the paste")
      eq(shell.edits, edits + 1, "one textEdited per paste")
      eq(readFile(shell.state + ".args"), "[\"--no-newline\",\"--type\",\"text\"]", "wl-paste reads the clipboard")
      area.select(0, 1)
      setClipboard("breaks", function () {
        shell.paste(function () {
          key(Qt.Key_Insert, Qt.ShiftModifier)
        }, "Shift+Insert", function () {
          eq(area.text, "a\nb\n\nc\nd\none\ntwo\nthreeb", "Shift+Insert replaces the selection; CR, U+2029 and CR LF are newlines")
          shell.refused()
        })
      })
    })
  }

  // NUL and oversized text never land, and say why.
  function refused() {
    var before = area.text
    var edits = shell.edits
    pasteWith("nul", "NUL", function () {
      eq(area.text, before, "a NUL paste is refused")
      eq(area.pasteError, "Clipboard text is too large or contains invalid characters.", "NUL: the error says why")
      pasteWith("large", "16385 bytes", function () {
        eq(area.text, before, "an oversized paste is refused")
        eq(area.pasteError, "Clipboard text is too large or contains invalid characters.", "oversized: the error says why")
        eq(shell.edits, edits, "a refused paste edits nothing")
        type("x")
        eq(area.pasteError, "", "typing clears the error")
        shell.limits()
      })
    })
  }

  // maximumLength: a paste is cut to fit (never inside a surrogate pair),
  // typing at the limit drops the key, not the end of the text.
  function limits() {
    area.clear()
    area.maximumLength = 19
    area.focusInput()
    pasteWith("unicode", "paste at the limit", function () {
      // 18 units before the emoji: its two units do not fit, nor half of it.
      eq(area.text, "/home/test/Blåbær ", "a paste stops at maximumLength, by whole code point")
      type("xy")
      eq(area.text, "/home/test/Blåbær x", "typing stops at maximumLength")
      key(Qt.Key_Home)
      type("z")
      key(Qt.Key_Return)
      eq(area.text, "/home/test/Blåbær x", "typing at the limit drops the key, never the text's end")
      area.maximumLength = 10
      eq(area.text, "/home/test", "lowering maximumLength cuts the end")
      area.maximumLength = 32767
      shell.late()
    })
  }

  // A result that arrives after newer typing, or after clear(), never lands.
  function late() {
    area.clear()
    area.focusInput()
    setClipboard("delayed", function () {
      key(Qt.Key_V, Qt.ControlModifier)
      check(area.pasteRunning, "a slow paste runs")
      type("typed")
      wait.waitFor(function () {
        return !area.pasteRunning
      }, 10000, function () {
        eq(area.text, "typed", "a late paste never overwrites newer typing")
        key(Qt.Key_V, Qt.ControlModifier)
        check(area.pasteRunning, "another slow paste runs")
        area.clear()
        wait.waitFor(function () {
          return !area.pasteRunning
        }, 10000, function () {
          eq(area.text, "", "clear() drops a paste in flight")
          key(Qt.Key_V, Qt.ControlModifier)
          after.focusInput()
          wait.waitFor(function () {
            return !area.pasteRunning
          }, 10000, function () {
            eq(area.text, "", "losing the focus drops a paste in flight")
            shell.middle()
          }, "the focus-loss paste ends")
        }, "the cleared paste ends")
      }, "the late paste ends")
    })
  }

  // Middle-click pastes the primary selection at the click.
  function middle() {
    area.focusInput()
    type("ab")
    var editor = area.editorItem
    var rect = editor.positionToRectangle(1)
    setClipboard("normal", function () {
      shell.paste(function () {
        ev.mouseClick(editor, rect.x + 1, rect.y + rect.height / 2, Qt.MiddleButton, Qt.NoModifier, -1)
      }, "middle-click", function () {
        eq(area.text, "afolderb", "middle-click pastes at the click")
        check(readFile(shell.state + ".args").indexOf("--primary") >= 0, "middle-click reads the primary selection")
        probe.text = ""
        probe.paste()
        eq(probe.text, "sentinel", "Qt's clipboard was never written")
        shell.sizing()
      })
    })
  }

  // The height follows the text up to maximumHeight, then the field scrolls
  // to keep the caret in view.
  function sizing() {
    area.clear()
    area.focusInput()
    var minimum = area.height
    for (var i = 0; i < 3; i++) {
      type("line")
      key(Qt.Key_Return)
    }
    check(area.height > minimum && area.height < area.maximumHeight, "grows with its lines " + [minimum, area.height])
    for (i = 0; i < 12; i++) {
      type("more")
      key(Qt.Key_Return)
    }
    type("end")
    check(near(area.height, area.maximumHeight), "stops at maximumHeight " + area.height)
    check(area.contentHeight > area.height && area.contentY > 0, "scrolls past it " + [area.contentHeight, area.contentY])
    var editor = area.editorItem
    var caret = editor.cursorRectangle
    check(caret.y >= area.contentY - 0.5 && caret.y + caret.height <= area.contentY + area.height + 0.5, "the caret line is in view " + [caret.y, area.contentY])
    key(Qt.Key_Home, Qt.ControlModifier)
    check(near(area.contentY, 0), "Ctrl+Home scrolls back to the top " + area.contentY)
    var long = "word ".repeat(40)
    area.text = long
    check(editor.lineCount > 1 && editor.contentWidth <= editor.width, "long lines wrap inside the field " + [editor.lineCount, editor.contentWidth, editor.width])
    area.text = "short"
    var left = editor.positionToRectangle(0).x
    var right = editor.positionToRectangle(5).x
    if (shell.rtl)
      check(near(right, editor.width - editor.rightPadding, 1.5), "RTL: text ends at the right padding " + [right, editor.width - editor.rightPadding])
    else
      check(near(left, editor.leftPadding, 1.5), "LTR: text starts at the padding " + left)
    area.text = "First line\nSecond line"
    area.select(0, 5)
    wait.after(50, function () {
      card.grabToImage(function (result) {
        check(result.saveToFile(Quickshell.env("FOAMY_OUT") + "/text-area.png"), "saved text-area")
        console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
        console.log("FOAMY DONE")
        Qt.quit()
      })
    })
  }
}
