import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import qs.Commons as Commons
import "harness"
import "plugin/kit"

// A plain (not masked) SafeTextField through real keys, the mouse and real
// pastes (kit/clipboard.sh with the hostenv.clipboard_fakes() stand-ins,
// never the real clipboard): hiding or disabling drops a paste in flight;
// a paste over a selection, with undo and redo; a late result after a caret
// move or typing is dropped; the caret fits a 34 px field; a long paste
// scrolls to the caret and Home back; middle-click pastes the primary
// selection; pastes stop at the default maximumLength; a refused paste
// (too large, endless, failed, stalled) keeps the text and the selection
// and says why; a second Ctrl+V while one runs is ignored; Shift+Insert,
// also of an empty clipboard over a selection; a paste and the typing after
// it are separate undo steps; typing, Backspace, Tab and Shift+Tab, Return.
ShellRoot {
  id: shell
  readonly property string state: Quickshell.env("TEST_CLIPBOARD_STATE")
  property int checks: 0
  property int failures: 0
  property int edits: 0
  property int accepts: 0
  property int finishes: 0
  property var steps: []

  function check(ok, label) {
    checks++
    if (!ok) {
      failures++
      console.log("FOAMY FAIL " + label)
    }
  }
  function eq(actual, expected, label) {
    check(JSON.stringify(actual) === JSON.stringify(expected), label + ": got " + JSON.stringify(actual).slice(0, 200) + ", expected " + JSON.stringify(expected).slice(0, 200))
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
    implicitWidth: 500
    implicitHeight: 250
    color: Commons.Color.background
    SafeTextField {
      id: field
      x: 20
      y: 20
      width: 200
      height: 36
      placeholderText: "Folder path"
      onTextEdited: shell.edits++
      onAccepted: shell.accepts++
      onEditingFinished: shell.finishes++
    }
    // The next stop in the focus chain (Tab).
    Item {
      id: nextStop
      x: 20
      y: 80
      width: 40
      height: 20
      activeFocusOnTab: true
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
  // What the stand-in wl-paste does on the next paste.
  Process {
    id: fixture
  }
  function source(mode, then) {
    fixture.command = ["clipboard-fixture", mode]
    fixture.running = true
    wait.waitFor(function () {
      return !fixture.running
    }, 5000, then, "clipboard-fixture " + mode)
  }
  // `trigger` starts a paste; `then` runs once it has ended.
  function paste(trigger, label, then) {
    trigger()
    check(field.pasteRunning, label + ": the paste runs out of process")
    wait.waitFor(function () {
      return !field.pasteRunning
    }, 10000, then, label + ": the paste ends")
  }
  function ctrlV() {
    key(Qt.Key_V, Qt.ControlModifier)
  }

  // Keys reach the focused item only in the active window.
  Component.onCompleted: wait.waitFor(function () {
    return window.visible && field.Window.window !== null
  }, 5000, function () {
    var w = field.Window.window
    if (!w.active)
      w.requestActivate()
    wait.waitFor(function () {
      return w.active
    }, 5000, function (active) {
      check(active, "the window is active")
      shell.steps = [hidingAndDisabling, selectionUndoRedo, lateAfterMove, lateAfterTyping, caretFits, longPaste, middleClick, lengthLimit, refusedLarge, refusedStream, refusedFailure, refusedStall, secondCtrlV, shiftInsert, separateUndo, typingAndTab]
      shell.next()
    })
  })

  // Each case starts from an empty, shown, enabled, focused field.
  function next() {
    var step = steps.shift()
    if (!step) {
      console.log("FOAMY RESULT checks=" + checks + " failures=" + failures)
      console.log("FOAMY DONE")
      Qt.quit()
      return
    }
    field.visible = true
    field.enabled = true
    field.clear()
    field.pasteError = ""
    field.focusInput()
    edits = 0
    accepts = 0
    finishes = 0
    source("normal", step)
  }

  // Hiding or disabling the field drops a paste in flight, also when it is
  // shown, enabled and focused again before the read ends.
  function hidingAndDisabling() {
    source("delayed", function () {
      ctrlV()
      check(field.pasteRunning, "a slow paste runs before the field is hidden")
      field.visible = false
      field.visible = true
      field.focusInput()
      wait.waitFor(function () {
        return !field.pasteRunning
      }, 10000, function () {
        eq(field.text, "", "hiding the field drops a paste in flight")
        ctrlV()
        check(field.pasteRunning, "a slow paste runs before the field is disabled")
        field.enabled = false
        field.enabled = true
        field.focusInput()
        wait.waitFor(function () {
          return !field.pasteRunning
        }, 10000, function () {
          eq(field.text, "", "disabling the field drops a paste in flight")
          shell.next()
        }, "the disabled paste ends")
      }, "the hidden paste ends")
    })
  }

  // A paste replaces the selection with non-ASCII text, one textEdited, and
  // undo and redo work on it.
  function selectionUndoRedo() {
    field.text = "before-old-after"
    field.select(7, 10)
    source("unicode", function () {
      paste(ctrlV, "Ctrl+V over a selection", function () {
        eq([field.text, shell.edits], ["before-/home/test/Blåbær 📁-after", 1], "a paste replaces the selection, one textEdited")
        field.undo()
        eq(field.text, "before-old-after", "undo takes the paste back")
        field.redo()
        eq(field.text, "before-/home/test/Blåbær 📁-after", "redo puts it back")
        shell.next()
      })
    })
  }

  // A result that arrives after a caret move is dropped.
  function lateAfterMove() {
    field.text = "keep"
    field.cursorPosition = 4
    source("delayed", function () {
      paste(function () {
        ctrlV()
        key(Qt.Key_Left)
      }, "a slow paste, then Left", function () {
        eq(field.text, "keep", "a late result after a caret move is dropped")
        shell.next()
      })
    })
  }

  // A result that arrives after typing is dropped.
  function lateAfterTyping() {
    source("delayed", function () {
      paste(function () {
        ctrlV()
        type("x")
      }, "a slow paste, then typing", function () {
        eq(field.text, "x", "a late result never overwrites newer typing")
        shell.next()
      })
    })
  }

  // In a 34 px field with 7 px side paddings and a 12 px font (a numeric
  // settings field) the caret stays inside the field.
  function caretFits() {
    field.height = 34
    field.leftPadding = 7
    field.rightPadding = 7
    field.font.pixelSize = 12
    field.text = "3600"
    field.cursorPosition = 4
    var editor = field.editorItem
    var caret = editor.mapToItem(field, editor.cursorRectangle.x, editor.cursorRectangle.y)
    check(caret.y >= 0 && caret.y + editor.cursorRectangle.height <= field.height, "the caret fits a 34 px field: top " + caret.y + ", height " + editor.cursorRectangle.height)
    field.height = 36
    shell.next()
  }

  // A long paste scrolls to the caret; Home scrolls back.
  function longPaste() {
    source("long", function () {
      paste(ctrlV, "a 400-character paste", function () {
        eq(field.text.length, 400, "the whole paste lands")
        check(field.contentX > 0, "the field scrolls to the caret: " + field.contentX)
        key(Qt.Key_Home)
        wait.waitFor(function () {
          return field.contentX === 0
        }, 3000, function (ok) {
          check(ok, "Home scrolls back: " + field.contentX)
          shell.next()
        })
      })
    })
  }

  // A middle-click pastes the primary selection.
  function middleClick() {
    paste(function () {
      ev.mouseClick(field, 15, 15, Qt.MiddleButton, Qt.NoModifier, -1)
    }, "middle-click", function () {
      eq(field.text, "folder", "a middle-click pastes")
      check(readFile(shell.state + ".args").indexOf("--primary") >= 0, "from the primary selection")
      shell.next()
    })
  }

  // Repeated pastes stop at the default maximumLength (32767); a full
  // field takes nothing more; undo takes the cut paste back.
  function lengthLimit() {
    source("limit", function () {
      paste(ctrlV, "a first 16384-byte paste", function () {
        paste(ctrlV, "a second one", function () {
          eq(field.text.length, 32767, "the second paste is cut at maximumLength")
          paste(ctrlV, "a third one", function () {
            eq(field.text.length, 32767, "a full field takes nothing more")
            field.undo()
            eq(field.text.length, 16384, "undo takes the cut paste back")
            shell.next()
          })
        })
      })
    })
  }

  // A refused paste keeps the text and the selection and says why.
  function refused(mode) {
    field.text = "keep"
    field.selectAll()
    source(mode, function () {
      paste(ctrlV, mode, function () {
        eq([field.text, field.selectionStart, field.selectionEnd], ["keep", 0, 4], mode + ": the text and the selection stay")
        check(field.pasteError !== "", mode + ": the field says why: " + field.pasteError)
        shell.next()
      })
    })
  }
  function refusedLarge() {
    refused("large")
  }
  function refusedStream() {
    refused("stream")
  }
  function refusedFailure() {
    refused("failure")
  }
  function refusedStall() {
    refused("stall")
  }

  // A second Ctrl+V while a paste runs is ignored; undo takes back only
  // the last paste.
  function secondCtrlV() {
    source("delayed", function () {
      paste(function () {
        ctrlV()
        ctrlV()
      }, "Ctrl+V twice", function () {
        eq(field.text, "later", "the second Ctrl+V while a paste runs is ignored")
        source("normal", function () {
          paste(ctrlV, "another paste", function () {
            eq(field.text, "laterfolder", "the next paste lands after it")
            field.undo()
            eq(field.text, "later", "undo takes back only the last paste")
            shell.next()
          })
        })
      })
    })
  }

  // Shift+Insert pastes; an empty clipboard over a selection deletes it.
  function shiftInsert() {
    field.text = "keep"
    field.selectAll()
    source("empty", function () {
      paste(function () {
        key(Qt.Key_Insert, Qt.ShiftModifier)
      }, "Shift+Insert of an empty clipboard", function () {
        eq(field.text, "", "an empty clipboard over a selection deletes it")
        field.text = "keep"
        field.selectAll()
        source("normal", function () {
          paste(function () {
            key(Qt.Key_Insert, Qt.ShiftModifier)
          }, "Shift+Insert", function () {
            eq(field.text, "folder", "Shift+Insert pastes")
            shell.next()
          })
        })
      })
    })
  }

  // A paste and the typing after it are separate undo steps.
  function separateUndo() {
    paste(ctrlV, "a paste", function () {
      type("x")
      eq(field.text, "folderx", "typing after the paste")
      field.undo()
      eq(field.text, "folder", "undo takes back the typing alone")
      field.undo()
      eq(field.text, "", "and then the paste")
      shell.next()
    })
  }

  // Typing, Left and Backspace; Tab leaves (editingFinished once) and
  // Shift+Tab comes back; Return emits accepted and editingFinished.
  function typingAndTab() {
    type("abc")
    eq(field.text, "abc", "typing")
    key(Qt.Key_Left)
    key(Qt.Key_Backspace)
    eq(field.text, "ac", "Left and Backspace")
    key(Qt.Key_Tab)
    wait.waitFor(function () {
      return nextStop.activeFocus
    }, 3000, function (left) {
      check(left && shell.finishes === 1, "Tab moves the focus on and ends the edit once: " + shell.finishes)
      key(Qt.Key_Backtab, Qt.ShiftModifier)
      wait.waitFor(function () {
        return field.inputActiveFocus
      }, 3000, function (back) {
        check(back, "Shift+Tab comes back to the field")
        key(Qt.Key_Return)
        eq([field.text, shell.accepts, shell.finishes], ["ac", 1, 2], "Return emits accepted and editingFinished")
        shell.next()
      })
    })
  }
}
