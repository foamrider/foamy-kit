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

// SafeTextField `masked: true`: the editor holds only the mask (one • per
// code point), `secretText` the value; typing, caret and selection edits,
// Backspace/Delete (and the word variants), Enter, keyboard navigation in
// step with a normal field, mouse selection, paste (Ctrl+V, Shift+Insert,
// middle-click) through kit/clipboard.sh and the fake wl-paste within
// maximumLength, copy/cut/undo that do nothing and leave Qt's (offscreen,
// in-process) clipboard alone, accessibility and input-method hints, the
// drawn caret on the dots, `text` writes and `masked` changes that clear,
// and RTL alignment. FOAMY_RTL=1 mirrors. Field shots go to FOAMY_OUT.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property bool rtl: Quickshell.env("FOAMY_RTL") === "1"
  // FOAMY_RTL_INPUT=1: the run has an RTL locale, so the input method runs right to left.
  readonly property bool rtlInput: Quickshell.env("FOAMY_RTL_INPUT") === "1"
  readonly property string tag: host + "/" + (rtl ? "rtl" : "ltr") + "/" + Quickshell.env("FOAMY_THEME")
  property int checks: 0
  property int failures: 0
  property int edits: 0
  property int accepts: 0
  property int plainEdits: 0

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
  function dots(n) {
    return "•".repeat(n)
  }
  // The field shows exactly the mask of its value, and never the value.
  function masks(field, value, label) {
    eq(field.secretText, value, label + ": secretText")
    eq(field.text, dots(value.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, "_").length), label + ": text is the mask")
    check(value === "" || field.text !== value, label + ": text is not the value")
  }
  function selection(field) {
    return [field.cursorPosition, field.selectionStart, field.selectionEnd]
  }
  function key(k, modifiers) {
    ev.keyClick(k, modifiers === undefined ? Qt.NoModifier : modifiers, -1)
  }
  function type(text) {
    for (var i = 0; i < text.length; i++)
      ev.keyClickChar(text.charAt(i), Qt.NoModifier, -1)
  }
  // Qt's clipboard as a native TextEdit pastes it (offscreen: in-process).
  function clipboardText() {
    probe.text = ""
    probe.paste()
    return probe.text
  }

  FloatingWindow {
    id: window
    implicitWidth: 800
    implicitHeight: 400
    color: Commons.Color.background

    Rectangle {
      id: card
      x: 20
      y: 20
      width: 360
      height: column.height + 24
      color: Commons.Color.background

      Column {
        id: column
        x: 12
        y: 12
        width: 336
        spacing: 8
        LayoutMirroring.enabled: shell.rtl
        LayoutMirroring.childrenInherit: true

        SafeTextField {
          id: secret
          width: parent.width
          masked: true
          maximumLength: 64
          placeholderText: "API token"
          Accessible.name: "API token"
          onTextEdited: shell.edits++
          onAccepted: shell.accepts++
        }
        SafeTextField {
          id: plain
          width: parent.width
          Accessible.name: "Plain label"
          onTextEdited: shell.plainEdits++
        }
        SafeTextField {
          id: toggled
          width: parent.width
          masked: true
        }
        SafeTextField {
          id: preset
          width: parent.width
          masked: true
          text: "given at creation"
        }
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
    check(secret.pasteRunning, label + ": the paste runs out of process")
    wait.waitFor(function () {
      return !secret.pasteRunning
    }, 10000, then, label + " ends")
  }

  Timer {
    running: true
    interval: 300
    onTriggered: shell.typing()
  }

  // The RTL-input run checks only the input direction: the other steps
  // compare with a normal field, whose Latin text stays left to right.
  function inputDirectionOnly() {
    secret.focusInput()
    type("a")
    eq(Qt.inputMethod.inputDirection === Qt.RightToLeft, true, "the run's input direction is right to left")
    key(Qt.Key_Left)
    eq(secret.cursorPosition, 1, "Left on one glyph moves visually left")
    key(Qt.Key_Right)
    eq(secret.cursorPosition, 0, "Right on one glyph moves visually right")
    type("b")
    key(Qt.Key_Left)
    eq(secret.cursorPosition, 2, "the same with two glyphs")
    shell.finish()
  }

  function typing() {
    if (shell.rtlInput)
      return shell.inputDirectionOnly()
    var editor = secret.editorItem
    // Creation: a `text` never becomes the value.
    masks(preset, "", "a text given at creation is dropped")
    // Contract of the editor itself.
    check(editor.readOnly && !editor.selectByMouse, "masked editor: read-only, no native mouse selection")
    check((editor.inputMethodHints & (Qt.ImhHiddenText | Qt.ImhSensitiveData | Qt.ImhNoPredictiveText)) === (Qt.ImhHiddenText | Qt.ImhSensitiveData | Qt.ImhNoPredictiveText), "hidden, sensitive, no predictive text")
    check(editor.Accessible.passwordEdit === true, "accessible as a password edit")
    check(!plain.editorItem.readOnly && plain.editorItem.selectByMouse && plain.editorItem.Accessible.passwordEdit === false && plain.editorItem.inputMethodHints === Qt.ImhNone, "a normal field is unchanged")
    eq(plain.secretText, "", "secretText is empty when not masked")

    secret.focusInput()
    check(editor.activeFocus, "the masked field takes focus")
    type("abc")
    masks(secret, "abc", "typing")
    eq(shell.edits, 3, "textEdited per typed character")
    eq(secret.cursorPosition, 3, "caret after the typed text")
    key(Qt.Key_Left)
    type("X")
    masks(secret, "abXc", "typing at the caret")
    eq(secret.cursorPosition, 3, "caret after the insert")
    key(Qt.Key_Left, Qt.ShiftModifier)
    key(Qt.Key_Left, Qt.ShiftModifier)
    eq(selection(secret), [1, 1, 3], "Shift+Left selects")
    type("Y")
    masks(secret, "aYc", "typing replaces the selection")
    eq(selection(secret), [2, 2, 2], "caret after the replacement")
    key(Qt.Key_Home)
    key(Qt.Key_Right, Qt.ShiftModifier)
    key(Qt.Key_Backspace)
    masks(secret, "Yc", "Backspace removes the selection")
    key(Qt.Key_End)
    key(Qt.Key_Left, Qt.ShiftModifier)
    key(Qt.Key_Delete)
    masks(secret, "Y", "Delete removes the selection")
    key(Qt.Key_Backspace)
    masks(secret, "", "Backspace removes one character")
    key(Qt.Key_Backspace)
    masks(secret, "", "Backspace at the start does nothing")
    type("hello")
    key(Qt.Key_Home)
    key(Qt.Key_Delete)
    masks(secret, "ello", "Delete removes the next character")
    key(Qt.Key_Right)
    key(Qt.Key_Right)
    key(Qt.Key_Backspace, Qt.ControlModifier)
    masks(secret, "lo", "Ctrl+Backspace removes to the start")
    key(Qt.Key_Right)
    key(Qt.Key_Delete, Qt.ControlModifier)
    masks(secret, "l", "Ctrl+Delete removes to the end")
    var before = shell.edits
    key(Qt.Key_A, Qt.ControlModifier)
    eq(selection(secret), [1, 0, 1], "Ctrl+A selects all")
    type("token-123")
    masks(secret, "token-123", "typing over Ctrl+A")
    eq(shell.edits, before + 9, "textEdited on every change")
    key(Qt.Key_Return)
    eq(shell.accepts, 1, "Enter emits accepted")
    masks(secret, "token-123", "Enter types nothing")
    key(Qt.Key_Z, Qt.ControlModifier)
    key(Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
    key(Qt.Key_Y, Qt.ControlModifier)
    masks(secret, "token-123", "undo and redo do nothing")
    secret.undo()
    secret.redo()
    secret.cut()
    masks(secret, "token-123", "undo(), redo() and cut() do nothing")

    // Copy and cut: a normal field reaches Qt's clipboard (the probe works)…
    plain.text = "visible"
    plain.focusInput()
    key(Qt.Key_A, Qt.ControlModifier)
    key(Qt.Key_C, Qt.ControlModifier)
    eq(clipboardText(), "visible", "a normal field copies (probe check)")
    // …a masked one never does, and keeps its value.
    probe.text = "sentinel"
    probe.selectAll()
    probe.copy()
    secret.focusInput()
    key(Qt.Key_A, Qt.ControlModifier)
    var edits = shell.edits
    key(Qt.Key_C, Qt.ControlModifier)
    key(Qt.Key_X, Qt.ControlModifier)
    key(Qt.Key_Insert, Qt.ControlModifier)
    key(Qt.Key_Delete, Qt.ShiftModifier)
    masks(secret, "token-123", "Ctrl+C, Ctrl+X, Ctrl+Insert, Shift+Delete keep the value")
    eq(selection(secret), [9, 0, 9], "and the selection")
    eq(shell.edits, edits, "and emit nothing")
    eq(clipboardText(), "sentinel", "the clipboard is untouched")
    var menu = secret.editorItem.Controls.ContextMenu.menu
    var labels = []
    for (var i = 0; i < menu.count; i++) {
      var item = menu.itemAt(i)
      if (item && item.text)
        labels.push(item.text + (item.enabled ? "" : " (off)"))
    }
    eq(labels, ["Undo (off)", "Redo (off)", "Cut (off)", "Copy (off)", "Paste", "Select all"], "menu: undo, redo, cut and copy disabled")
    var plainMenu = plain.editorItem.Controls.ContextMenu.menu
    check(plainMenu.itemAt(4).enabled, "a normal field's menu still copies its selection")
    secret.focusInput()
    shell.navigation()
  }

  // Keyboard navigation and selection move like a normal field's.
  function navigation() {
    plain.text = "abcdef"
    secret.clear()
    masks(secret, "", "clear()")
    secret.focusInput()
    type("abcdef")
    var script = [[Qt.Key_Home, 0], [Qt.Key_Right, 0], [Qt.Key_Right, 0], [Qt.Key_Right, Qt.ShiftModifier], [Qt.Key_Right, Qt.ShiftModifier], [Qt.Key_Left, 0], [Qt.Key_End, Qt.ShiftModifier], [Qt.Key_Right, 0], [Qt.Key_Left, Qt.ShiftModifier], [Qt.Key_Home, Qt.ShiftModifier], [Qt.Key_Left, 0], [Qt.Key_End, 0], [Qt.Key_Left, Qt.ControlModifier], [Qt.Key_Right, Qt.ControlModifier | Qt.ShiftModifier], [Qt.Key_Right, Qt.ControlModifier], [Qt.Key_Home, Qt.ControlModifier | Qt.ShiftModifier], [Qt.Key_A, Qt.ControlModifier], [Qt.Key_Right, 0]]
    var plainSteps = []
    var secretSteps = []
    plain.focusInput()
    plain.cursorPosition = 6
    for (var i = 0; i < script.length; i++) {
      key(script[i][0], script[i][1])
      plainSteps.push(selection(plain))
    }
    secret.focusInput()
    secret.cursorPosition = 6
    for (var j = 0; j < script.length; j++) {
      key(script[j][0], script[j][1])
      secretSteps.push(selection(secret))
    }
    eq(secretSteps, plainSteps, "arrows, Home/End, words, Shift and Ctrl+A as in a normal field")
    masks(secret, "abcdef", "navigation edits nothing")
    eq(plain.text, "abcdef", "the normal field is unchanged too")
    shell.mouse()
  }

  // Mouse: click places the caret on the dots, drag and Shift+click
  // select, double-click selects all; nothing reaches Qt's clipboard.
  function mouse() {
    var editor = secret.editorItem
    var y = editor.height / 2
    var at = function (position) {
      var a = editor.positionToRectangle(position).x
      var b = editor.positionToRectangle(position + 1).x
      return (a + b) / 2 - (b - a) * 0.3
    }
    plain.focusInput()
    ev.mouseClick(editor, at(2), y, Qt.LeftButton, Qt.NoModifier, -1)
    check(editor.activeFocus, "a click focuses the field")
    eq(selection(secret), [2, 2, 2], "a click places the caret on the dots")
    ev.mousePress(editor, at(1), y, Qt.LeftButton, Qt.NoModifier, -1)
    ev.mouseMove(editor, at(3), y, -1, Qt.LeftButton, Qt.NoModifier)
    ev.mouseMove(editor, at(4), y, -1, Qt.LeftButton, Qt.NoModifier)
    ev.mouseRelease(editor, at(4), y, Qt.LeftButton, Qt.NoModifier, -1)
    eq([secret.selectionStart, secret.selectionEnd], [1, 4], "a drag selects")
    ev.mouseClick(editor, at(5), y, Qt.LeftButton, Qt.ShiftModifier, -1)
    eq([secret.selectionStart, secret.selectionEnd], [1, 5], "Shift+click extends")
    ev.mouseDoubleClickSequence(editor, at(2), y, Qt.LeftButton, Qt.NoModifier, -1)
    eq([secret.selectionStart, secret.selectionEnd], [0, 6], "a double-click selects all")
    type("Z")
    masks(secret, "Z", "typing over a mouse selection")
    eq(clipboardText(), "sentinel", "mouse selection writes no clipboard")
    shell.pasting()
  }

  // Paste through kit/clipboard.sh: at the caret, over a selection, by
  // Shift+Insert and middle-click, within maximumLength by code point.
  function pasting() {
    secret.clear()
    secret.focusInput()
    type("ab")
    key(Qt.Key_Left)
    var edits = shell.edits
    setClipboard("normal", function () {
      shell.paste(function () {
        key(Qt.Key_V, Qt.ControlModifier)
      }, "Ctrl+V", function () {
        masks(secret, "afolderb", "Ctrl+V pastes into the value at the caret")
        eq(secret.cursorPosition, 7, "caret after the paste")
        eq(shell.edits, edits + 1, "one textEdited per paste")
        eq(clipboardText(), "sentinel", "a paste writes no clipboard")
        secret.select(1, 7)
        setClipboard("unicode", function () {
          shell.paste(function () {
            key(Qt.Key_Insert, Qt.ShiftModifier)
          }, "Shift+Insert", function () {
            masks(secret, "a/home/test/Blåbær 📁b", "Shift+Insert replaces the selection, one dot per code point")
            eq(secret.text.length, 21, "an emoji is one dot")
            setClipboard("normal", function () {
              secret.select(0, 1)
              var menu = secret.editorItem.Controls.ContextMenu.menu
              shell.paste(function () {
                menu.itemAt(5).triggered()
              }, "menu Paste", function () {
                masks(secret, "folder/home/test/Blåbær 📁b", "the menu's Paste replaces the selection")
                setClipboard("unicode", shell.pasteLimits)
              })
            })
          })
        })
      })
    })
  }
  function pasteLimits() {
    secret.clear()
    secret.maximumLength = 19
    secret.focusInput()
    // 18 units before the emoji: the emoji (2 units) does not fit, nor half of it.
    shell.paste(function () {
      key(Qt.Key_V, Qt.ControlModifier)
    }, "paste at the limit", function () {
      masks(secret, "/home/test/Blåbær ", "maximumLength holds for paste, by whole code point")
      type("xy")
      masks(secret, "/home/test/Blåbær x", "maximumLength holds for typing")
      secret.maximumLength = 64
      setClipboard("long", function () {
        secret.clear()
        type("ab")
        var editor = secret.editorItem
        shell.paste(function () {
          ev.mouseClick(editor, editor.positionToRectangle(2).x + 1, editor.height / 2, Qt.MiddleButton, Qt.NoModifier, -1)
        }, "middle-click", function () {
          masks(secret, "ab" + "x".repeat(62), "middle-click pastes the primary selection at the click, cut at maximumLength")
          secret.maximumLength = 20
          masks(secret, "ab" + "x".repeat(18), "lowering maximumLength trims the value")
          shell.clearing()
        })
      })
    })
  }

  // Writes that do not come from the field clear it; so does toggling masked.
  function clearing() {
    secret.maximumLength = 64
    secret.clear()
    secret.focusInput()
    type("abc")
    secret.text = "leak"
    masks(secret, "", "assigning text clears the masked field")
    type("abc")
    secret.text = ""
    masks(secret, "", "assigning \"\" clears the value too")
    toggled.focusInput()
    type("hidden")
    toggled.masked = false
    eq([toggled.text, toggled.secretText], ["", ""], "unmasking clears")
    type("shown")
    toggled.masked = true
    masks(toggled, "", "masking clears")
    eq(clipboardText(), "sentinel", "the clipboard is still untouched")
    // One mask glyph already runs in the input direction: arrows move visually.
    secret.clear()
    secret.focusInput()
    type("a")
    eq(Qt.inputMethod.inputDirection === Qt.RightToLeft, shell.rtlInput, "the run's input direction")
    key(Qt.Key_Left)
    eq(secret.cursorPosition, shell.rtlInput ? 1 : 0, "Left on one glyph moves visually left")
    key(Qt.Key_Right)
    eq(secret.cursorPosition, shell.rtlInput ? 0 : 1, "Right on one glyph moves visually right")
    // clear() while a paste runs: its late result never refills the field.
    secret.clear()
    secret.focusInput()
    key(Qt.Key_V, Qt.ControlModifier)
    check(secret.pasteRunning, "a paste runs before clear()")
    secret.clear()
    wait.waitFor(function () {
      return !secret.pasteRunning
    }, 10000, function () {
      masks(secret, "", "clear() cancels a paste in flight")
      shell.geometry()
    }, "the cancelled paste ends")
  }

  // The dots sit where the text would (RTL mirrored), and the drawn caret on
  // Qt's cursor rectangle between them.
  function geometry() {
    var editor = secret.editorItem
    var caret = findByName(editor, "maskedCaret")
    secret.clear()
    secret.focusInput()
    type("secret-token")
    check(caret && caret.visible, "the caret shows while focused")
    // The blink timer runs only while the field shows: a hidden popup must not wake the shell.
    var blinkTimer = null
    for (var r = 0; r < caret.resources.length; r++) {
      if (caret.resources[r].hasOwnProperty("repeat"))
        blinkTimer = caret.resources[r]
    }
    check(blinkTimer && Application.styleHints.cursorFlashTime >= 2 && blinkTimer.running, "the caret blinks while focused (flash " + Application.styleHints.cursorFlashTime + ")")
    secret.visible = false
    check(!blinkTimer.running, "a hidden field stops blinking")
    secret.visible = true
    secret.focusInput()
    check(blinkTimer.running, "shown again, it blinks again")
    var pitch = editor.positionToRectangle(1).x - editor.positionToRectangle(0).x
    check(Math.abs(pitch) > 2, "dots have width " + pitch)
    var even = true
    for (var i = 1; i <= 12; i++)
      even = even && near(editor.positionToRectangle(i).x - editor.positionToRectangle(i - 1).x, pitch, 0.6)
    check(even, "the dots are evenly spaced")
    key(Qt.Key_Home)
    key(Qt.Key_Right)
    key(Qt.Key_Right)
    key(Qt.Key_Right)
    check(caret.visible && near(caret.x, editor.cursorRectangle.x, 0.01) && near(caret.x, editor.positionToRectangle(3).x, 0.01), "the caret sits between the third and fourth dot " + caret.x)
    check(near(caret.height, editor.cursorRectangle.height, 0.01) && caret.width >= 1, "caret size follows Qt's cursor")
    var left = editor.positionToRectangle(0).x
    var right = editor.positionToRectangle(12).x
    if (shell.rtl)
      check(near(right, editor.width - editor.rightPadding, 1.5) && left > editor.width / 2, "RTL: the dots end at the right padding " + [left, right, editor.width - editor.rightPadding])
    else
      check(near(left, editor.leftPadding, 1.5), "LTR: the dots start at the left padding " + [left, editor.leftPadding])
    plain.text = "secret-token"
    var plainLeft = plain.editorItem.positionToRectangle(0).x
    var plainRight = plain.editorItem.positionToRectangle(12).x
    check(shell.rtl ? near(plainRight, right, 1.5) : near(plainLeft, left, 1.5), "aligned like a normal field " + [plainLeft, plainRight, left, right])
    // Qt 6.12 reports no name for a password edit (QQuickAccessibleAttached::name()).
    eq([secret.editorItem.Accessible.name, secret.editorItem.Accessible.description], ["", ""], "a password edit exposes no name or description")
    eq(plain.editorItem.Accessible.name, "Plain label", "a normal field keeps its label")
    secret.select(3, 8)
    shell.shot("masked-selection", function () {
      secret.cursorPosition = 5
      shell.shot("masked-caret", function () {
        plain.focusInput()
        check(!caret.visible, "no caret without focus")
        shell.finish()
      })
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
  function shot(name, then) {
    wait.after(50, function () {
      // Wake the caret: a blink could hide it at the grab.
      var position = secret.cursorPosition
      var start = secret.selectionStart
      var end = secret.selectionEnd
      secret.cursorPosition = 0
      secret.select(start === end ? position : (position === start ? end : start), position)
      card.grabToImage(function (result) {
        check(result.saveToFile(Quickshell.env("FOAMY_OUT") + "/" + name + ".png"), "saved " + name)
        console.log("FOAMY PNGCHECK " + name + ".png")
        then()
      })
    })
  }
  function finish() {
    console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
    console.log("FOAMY DONE")
    Qt.quit()
  }
}
