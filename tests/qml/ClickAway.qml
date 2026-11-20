import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"

// Click-away (FoamyClickAway) in a real FoamyPopup: a click on the body's
// empty space, a Flickable's empty space (below its rows, on a heading
// between them) or a settings page's empty space takes the keys from a
// focused SafeTextField or SafeTextArea and gives them to the key home
// (the popup's focusTarget, the body item while it is the default, the
// settings page, or a plugin's `foamyKeyHome`); the field ends its edit
// once. A click on a real control (a button, a row) changes no focus; a
// drag on empty space still flicks and the wheel still scrolls, and
// neither takes the keys. FoamyWheelScroll says `spaceClicked`.
ShellRoot {
  id: shell
  readonly property string tag: Quickshell.env("FOAMY_TAG")
  property int checks: 0
  property int failures: 0
  property int buttonClicks: 0
  property int rowClicks: 0
  property int listSpace: 0
  property int tallSpace: 0
  property int fieldDone: 0
  property int areaDone: 0
  property int pageDone: 0
  property int pageBacks: 0
  readonly property var body: popup.bodyItem

  function check(ok, label) {
    checks++
    if (!ok) {
      failures++
      console.log("FOAMY FAIL " + tag + " " + label)
    }
  }
  function focused() {
    var window = body ? body.Window.window : null
    return window ? window.activeFocusItem : null
  }
  function click(item, x, y) {
    ev.mouseClick(item, x, y, Qt.LeftButton, Qt.NoModifier, -1)
  }

  FloatingWindow {
    implicitWidth: 1920
    implicitHeight: 1080
    color: "black"
    ScreenSim {
      id: sim
    }
    Item {
      TestEvent {
        id: ev
      }
    }
  }
  MockBar {
    id: bar
  }

  FoamyPopup {
    id: popup
    anchorItem: sim.anchor
    bar: bar
    open: true
    // As a plugin whose keys live in an item of its own (todoist).
    focusTarget: bodyItem ? bodyItem.keys : null
    body: Component {
      Item {
        id: view
        property alias keys: keys
        property alias field: field
        property alias button: button
        property alias list: list
        property alias heading: heading
        property alias rowA: rowA
        property alias tall: tall
        property alias area: area
        property alias scopeKeys: scopeKeys
        property alias scopeField: scopeField
        property alias page: page
        property alias pageField: pageField
        implicitHeight: 720
        focus: true

        // The panel's key catcher.
        Item {
          id: keys
          focus: true
          Keys.onPressed: function (event) {
            event.accepted = true
          }
        }
        SafeTextField {
          id: field
          x: 20
          y: 10
          width: 200
          height: 32
          onEditingFinished: shell.fieldDone++
        }
        Rectangle {
          id: button
          x: 240
          y: 10
          width: 80
          height: 32
          color: "transparent"
          MouseArea {
            anchors.fill: parent
            onClicked: shell.buttonClicks++
          }
        }
        // y 50…90: empty.
        Flickable {
          id: list
          y: 90
          width: parent.width
          height: 120
          contentHeight: rows.height
          clip: true
          FoamyWheelScroll {
            target: list
            onSpaceClicked: shell.listSpace++
          }

          Column {
            id: rows
            width: list.width
            Rectangle {
              id: rowA
              width: parent.width
              height: 30
              color: "transparent"
              MouseArea {
                anchors.fill: parent
                onClicked: shell.rowClicks++
              }
            }
            Text {
              id: heading
              width: parent.width
              height: 20
              text: "Heading"
              color: FoamyPalette.text
            }
            Rectangle {
              width: parent.width
              height: 30
              color: "transparent"
              MouseArea {
                anchors.fill: parent
                onClicked: shell.rowClicks++
              }
            }
          }
        }
        // Taller content than its view, nothing in it takes a press.
        Flickable {
          id: tall
          y: 220
          width: parent.width
          height: 100
          contentHeight: 600
          clip: true
          boundsBehavior: Flickable.StopAtBounds
          FoamyWheelScroll {
            target: tall
            onSpaceClicked: shell.tallSpace++
          }
          Rectangle {
            width: tall.width
            height: 600
            color: "transparent"
          }
        }
        SafeTextArea {
          id: area
          x: 20
          y: 330
          width: 200
          height: 60
          onEditingFinished: shell.areaDone++
        }
        // A plugin's own key home (a page in the body).
        Item {
          y: 400
          width: parent.width
          height: 40
          readonly property Item foamyKeyHome: scopeKeys
          Item {
            id: scopeKeys
          }
          SafeTextField {
            id: scopeField
            x: 20
            width: 200
            height: 32
          }
        }
        FoamySettingsPage {
          id: page
          y: 450
          width: parent.width
          height: 250
          onBack: shell.pageBacks++
          SafeTextField {
            id: pageField
            width: 200
            height: 32
            onEditingFinished: shell.pageDone++
          }
        }
      }
    }
  }

  FoamyWait {
    id: wait
  }

  Timer {
    interval: 900
    running: true
    onTriggered: shell.run()
  }

  function run() {
    // The body's empty space: the field lets go once, the catcher has the keys.
    body.field.focusInput()
    check(body.field.inputActiveFocus, "the field has the keys")
    click(body, 200, 70)
    check(!body.field.inputActiveFocus && shell.fieldDone === 1, "a click on the body's empty space ended the edit once (" + shell.fieldDone + ")")
    check(focused() === body.keys, "the keys went to the popup's focusTarget (" + focused() + ")")

    // A real control: its click, the field keeps the keys.
    body.field.focusInput()
    click(body.button, 40, 16)
    check(shell.buttonClicks === 1 && body.field.inputActiveFocus && shell.fieldDone === 1, "a button's click leaves the field alone")

    // A list's empty space below its rows, and a heading between them.
    click(body.list, 100, 110)
    check(!body.field.inputActiveFocus && shell.fieldDone === 2 && focused() === body.keys && shell.listSpace === 1, "a click below the list's rows took the keys (" + shell.listSpace + ")")
    body.field.focusInput()
    click(body.heading, 40, 10)
    check(!body.field.inputActiveFocus && shell.listSpace === 2, "a click on a heading between rows took the keys")
    // A row: its click; no field: nothing moves, the list still says so.
    body.field.focusInput()
    click(body.rowA, 40, 15)
    check(shell.rowClicks === 1 && shell.listSpace === 2 && body.field.inputActiveFocus, "a row's click leaves the field alone")
    body.keys.forceActiveFocus()
    click(body.list, 100, 110)
    check(shell.listSpace === 3 && focused() === body.keys, "with no field focused a click changes no focus")

    // A drag on empty space flicks; the wheel scrolls; neither takes the keys.
    body.field.focusInput()
    ev.mousePress(body.tall, 100, 90, Qt.LeftButton, Qt.NoModifier, -1)
    for (var step = 1; step <= 8; step++)
      ev.mouseMove(body.tall, 100, 90 - step * 10, -1, Qt.LeftButton, Qt.NoModifier)
    ev.mouseRelease(body.tall, 100, 10, Qt.LeftButton, Qt.NoModifier, -1)
    var dragged = body.tall.contentY
    check(dragged > 20 && body.field.inputActiveFocus && shell.tallSpace === 0, "a drag on empty space flicked (" + dragged + ") and kept the field")
    wait.waitFor(function () {
      return !body.tall.moving
    }, 3000, function () {
      var before = body.tall.contentY
      ev.mouseWheel(body.tall, 100, 50, Qt.NoButton, Qt.NoModifier, 0, 120, -1)
      wait.waitFor(function () {
        return body.tall.contentY < before - 20
      }, 3000, function (ok) {
        check(ok && body.field.inputActiveFocus, "the wheel still scrolls (" + [before, body.tall.contentY] + ") and keeps the field")
        shell.rest()
      })
    })
  }

  function rest() {
    // The text area: the same, and no click-away inside the field itself.
    body.area.focusInput()
    click(body, 300, 360)
    check(!body.area.inputActiveFocus && shell.areaDone === 1 && focused() === body.keys, "the text area let go once (" + shell.areaDone + ")")
    check(findByName(body.area, "clickAway") === null && findByName(body.list, "clickAway") !== null, "a SafeTextArea has no click-away of its own; a list has one")

    // A nearer key home.
    body.scopeField.focusInput()
    click(body, 300, 420)
    check(!body.scopeField.inputActiveFocus && focused() === body.scopeKeys, "a plugin's foamyKeyHome took the keys (" + focused() + ")")

    // A settings page keeps the keys: Esc still goes back.
    body.pageField.focusInput()
    click(body.page, 300, 200)
    check(!body.pageField.inputActiveFocus && shell.pageDone === 1 && focused() === body.page, "a click on the page's empty space left the keys with the page (" + focused() + ")")
    ev.keyClick(Qt.Key_Escape, Qt.NoModifier, -1)
    check(shell.pageBacks === 1, "Esc goes back after it (" + shell.pageBacks + ")")

    // The default focusTarget (the body loader): the body item takes the keys.
    popup.focusTarget = body.parent
    body.field.focusInput()
    click(body, 200, 70)
    check(!body.field.inputActiveFocus && focused() === body, "the default focusTarget: the body item has the keys (" + focused() + ")")
    finish()
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
