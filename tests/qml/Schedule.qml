import QtQuick
import QtTest
import Quickshell
import "harness"
import "plugin/kit"

// FoamyScheduleDay (kit 0.9.0, moved from foamy-train and foamy-zendesk):
// the default and an injected label component, and through real keys and a
// pointer: the switch (Space, a click), committing on Enter and on focus
// loss, rejecting, and restoring the time fields on Escape.
ShellRoot {
  id: shell
  property int checks: 0
  property int failures: 0
  property var changes: []
  property int invalids: 0
  function check(ok, label) {
    checks++
    if (!ok) {
      failures++
      console.log("FOAMY FAIL " + label)
    }
  }
  function eq(actual, expected, label) {
    check(JSON.stringify(actual) === JSON.stringify(expected), label + ": got " + JSON.stringify(actual) + ", expected " + JSON.stringify(expected))
  }
  function find(item, name) {
    if (!item)
      return null
    if (item.objectName === name)
      return item
    var kids = item.children || []
    for (var i = 0; i < kids.length; i++) {
      var found = find(kids[i], name)
      if (found)
        return found
    }
    return null
  }

  FloatingWindow {
    id: win
    implicitWidth: 600
    implicitHeight: 240
    Column {
      width: 560
      spacing: 8
      FoamyScheduleDay {
        id: monday
        width: parent.width
        label: "Monday <b>1</b>"
        value: "08:00-16:00"
        // Reflects the new value at once, as a FoamyPrefsQueue-backed caller does.
        onChanged: function (range) {
          shell.changes = shell.changes.concat([range])
          monday.value = range
        }
        onInvalid: shell.invalids++
      }
      FoamyScheduleDay {
        id: tuesday
        width: parent.width
        label: "Tuesday"
        value: ""
        lastRange: "22:00-02:00"
        labelComponent: Component {
          Text {
            property bool injected: true
            textFormat: Text.PlainText
          }
        }
        // Does not reflect: the row must leave its value alone.
        onChanged: function (range) {
          shell.changes = shell.changes.concat(["tue " + range])
        }
      }
      FoamyScheduleDay {
        id: wednesday
        width: parent.width
        label: "Wednesday"
        value: "08:00-16:00"
        // Does not reflect either: its value catches up later, if at all.
        onChanged: function (range) {
          shell.changes = shell.changes.concat(["wed " + range])
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
  Component.onCompleted: wait.waitFor(function () {
    return monday.labelItem !== null && tuesday.labelItem !== null && win.visible
  }, 5000, activate)

  // Keys reach the focused item only in the active window.
  function activate(ready) {
    check(ready, "both labels load")
    var w = monday.Window.window
    if (!w.active)
      w.requestActivate()
    wait.waitFor(function () {
      return w.active
    }, 5000, run)
  }

  function run(active) {
    check(active, "the window is active")
    var label = monday.labelItem
    eq(label.text, "Monday <b>1</b>", "default label shows the label")
    eq(label.textFormat, Text.PlainText, "default label is plain text")
    check(label.width > 300, "the label fills the row: " + label.width)
    eq(tuesday.labelItem.injected, true, "labelComponent injects the plugin's text type")
    tuesday.label = "Tirsdag"
    eq(tuesday.labelItem.text, "Tirsdag", "the injected label follows the label")

    var from = find(monday, "fromTime"), to = find(monday, "toTime")
    eq([from.text, to.text], ["08:00", "16:00"], "fields show the value")
    from.focusInput()
    from.text = "09:00"
    ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
    eq(changes, ["09:00-16:00"], "Enter commits a valid new range")
    to.focusInput()
    to.text = "17:30"
    ev.keyClick(Qt.Key_Tab, Qt.NoModifier, -1)
    eq(changes, ["09:00-16:00", "09:00-17:30"], "focus-out commits; the unchanged from field commits nothing")
    from.focusInput()
    from.text = "9:7"
    ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
    eq(invalids, 1, "an invalid range is rejected")
    eq(changes.length, 2, "and not committed")
    ev.keyClick(Qt.Key_Escape, Qt.NoModifier, -1)
    eq(from.text, "09:00", "Escape brings back the value")
    to.focusInput()
    eq(changes.length, 2, "the restored text commits nothing")
    var mondaySwitch = find(monday, "daySwitch")
    mondaySwitch.forceActiveFocus()
    monday.value = "10:00-12:00"
    eq([from.text, to.text], ["10:00", "12:00"], "fields follow an outside change")

    var before = changes.length
    ev.keyClick(Qt.Key_Space, Qt.NoModifier, -1)
    eq(changes.slice(before), [""], "Space on the switch turns an enabled day off, once")
    before = changes.length
    var tuesdaySwitch = find(tuesday, "daySwitch")
    ev.mouseClick(tuesdaySwitch, tuesdaySwitch.width / 2, tuesdaySwitch.height / 2, Qt.LeftButton, Qt.NoModifier, -1)
    eq(changes.slice(before), ["tue 22:00-02:00"], "a click turns a day off back on with its last range")
    check(!find(tuesday, "fromTime").enabled, "a day off has its fields disabled")
    eq(tuesday.value, "", "the row never assigns its value")

    // A caller whose value has not caught up: the focus loss after Enter
    // must not send the same range again; an edit may send it again.
    var wedFrom = find(wednesday, "fromTime")
    wedFrom.focusInput()
    wedFrom.text = "09:00"
    before = changes.length
    ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
    ev.keyClick(Qt.Key_Tab, Qt.NoModifier, -1)
    eq(changes.slice(before), ["wed 09:00-16:00"], "Enter, then focus-out: the range is sent once")
    wedFrom.focusInput()
    ev.keyClick(Qt.Key_End, Qt.NoModifier, -1)
    ev.keyClick(Qt.Key_Backspace, Qt.NoModifier, -1)
    ev.keyClick(Qt.Key_0, Qt.NoModifier, -1)
    eq(wedFrom.text, "09:00", "typing gives the same text again")
    ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
    eq(changes.slice(before), ["wed 09:00-16:00", "wed 09:00-16:00"], "after an edit, Enter sends the same range again")

    console.log("FOAMY RESULT checks=" + checks + " failures=" + failures)
    console.log("FOAMY DONE")
    Qt.quit()
  }
}
