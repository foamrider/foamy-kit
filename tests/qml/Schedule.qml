import QtQuick
import Quickshell
import "harness"
import "plugin/kit"
import "plugin/kit/FoamySchedule.js" as Schedule

// FoamyScheduleDay (kit 0.9.0, moved from foamy-train and foamy-zendesk):
// the default and an injected label component, the switch, committing,
// rejecting and restoring the time fields.
ShellRoot {
  id: shell
  property int checks: 0
  property int failures: 0
  property var changes: []
  property int invalids: 0
  function check(ok, label) {
    checks++
    if (!ok) { failures++; console.log("FOAMY FAIL " + label) }
  }
  function eq(actual, expected, label) {
    check(JSON.stringify(actual) === JSON.stringify(expected), label + ": got " + JSON.stringify(actual) + ", expected " + JSON.stringify(expected))
  }
  function find(item, name) {
    if (!item) return null
    if (item.objectName === name) return item
    var kids = item.children || []
    for (var i = 0; i < kids.length; i++) {
      var found = find(kids[i], name)
      if (found) return found
    }
    return null
  }

  FloatingWindow {
    implicitWidth: 600
    implicitHeight: 200
    Column {
      width: 560
      spacing: 8
      FoamyScheduleDay {
        id: monday
        width: parent.width
        label: "Monday <b>1</b>"
        value: "08:00-16:00"
        onChanged: function(range) { shell.changes = shell.changes.concat([range]) }
        onInvalid: shell.invalids++
      }
      FoamyScheduleDay {
        id: tuesday
        width: parent.width
        label: "Tuesday"
        value: ""
        lastRange: "22:00-02:00"
        labelComponent: Component { Text { property bool injected: true; textFormat: Text.PlainText } }
        onChanged: function(range) { shell.changes = shell.changes.concat(["tue " + range]) }
      }
    }
  }

  FoamyWait { id: wait }
  Component.onCompleted: wait.waitFor(function() { return monday.labelItem !== null && tuesday.labelItem !== null }, 5000, run)

  function run(ready) {
    check(ready, "both labels load")
    var label = monday.labelItem
    eq(label.text, "Monday <b>1</b>", "default label shows the label")
    eq(label.textFormat, Text.PlainText, "default label is plain text")
    check(label.width > 300, "the label fills the row: " + label.width)
    eq(tuesday.labelItem.injected, true, "labelComponent injects the plugin's text type")
    tuesday.label = "Tirsdag"
    eq(tuesday.labelItem.text, "Tirsdag", "the injected label follows the label")

    var from = find(monday, "fromTime"), to = find(monday, "toTime")
    eq([from.text, to.text], ["08:00", "16:00"], "fields show the value")
    from.text = "09:00"
    monday.saveInputs()
    eq(changes, ["09:00-16:00"], "a valid new range is committed")
    from.text = "9:7"
    monday.saveInputs()
    eq(invalids, 1, "an invalid range is rejected")
    eq(changes.length, 1, "and not committed")
    monday.restoreInputs(true)
    eq(from.text, "08:00", "restore brings back the value")
    monday.value = "10:00-12:00"
    eq([from.text, to.text], ["10:00", "12:00"], "fields follow an outside change")

    find(monday, "daySwitch").toggled()
    eq(changes[changes.length - 1], "", "the switch turns an enabled day off")
    find(tuesday, "daySwitch").toggled()
    eq(changes[changes.length - 1], "tue 22:00-02:00", "and a day off back on with its last range")
    check(!find(tuesday, "fromTime").enabled, "a day off has its fields disabled")
    check(Schedule.validRange(monday.value), "the row never assigns its value")

    console.log("FOAMY RESULT checks=" + checks + " failures=" + failures)
    console.log("FOAMY DONE")
    Qt.quit()
  }
}
