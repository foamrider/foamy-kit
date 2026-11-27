import QtQuick
import QtQuick.Layouts
import QtTest
import Quickshell
import qs.Commons
import qs.Ui
import "harness"
import "plugin/kit"

// FoamyButton's three kinds in each state (active, inert: actionEnabled
// false, disabled: enabled false, and busy) in a real FoamyPopup: one grid
// on the popup's body, one in a FoamySettingsPage section, where plugins
// put their forms. The body grid's labels are a full block (█), so
// test_button_states.py can read the label's colour as drawn from the
// card's pixels; the settings grid has real labels and icons, for the
// pictures. Here: the icon draws in the label's colour, an inert button
// keeps its look and the plain cursor under the pointer and takes no
// click, a busy one draws as an active one, and the states keep the
// active button's size. Prints FOAMY BUTTONS <json> (where each button and
// its label are on the card) and saves the card to FOAMY_OUT/card.png.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property string tag: host + "@" + Quickshell.env("FOAMY_SCALE")
  property int checks: 0
  property int failures: 0
  property int clicks: 0
  function check(ok, label) {
    checks++
    if (!ok) {
      failures++
      console.log("FOAMY FAIL " + tag + " " + label)
    }
  }

  FloatingWindow {
    id: window
    implicitWidth: 1920
    implicitHeight: 1080
    color: "black"
    ScreenSim {
      id: sim
    }
  }
  MockBar {
    id: bar
  }
  FoamyWait {
    id: wait
  }

  readonly property var kinds: ["primary", "secondary", "destructive"]
  readonly property var states: ["active", "inert", "disabled", "busy"]

  component StateGrid: GridLayout {
    id: grid
    property bool block: false
    property var labels: ({})
    property var icons: ({})
    // The settings grid shows three states: four don't fit the popup.
    property var states: block ? shell.states : shell.states.slice(0, 3)
    columns: states.length
    rowSpacing: FoamyStyle.gap
    columnSpacing: FoamyStyle.gap
    Repeater {
      model: shell.kinds.length * grid.states.length
      FoamyButton {
        readonly property string stateName: grid.states[index % grid.states.length]
        objectName: shell.kinds[Math.floor(index / grid.states.length)] + "-" + stateName
        kind: shell.kinds[Math.floor(index / grid.states.length)]
        text: grid.block ? "\u2588" : grid.labels[kind]
        iconName: grid.block ? "" : grid.icons[kind]
        // Busy as plugins set it (foamy-audio): inert while it runs.
        actionEnabled: stateName === "active" || stateName === "disabled"
        enabled: stateName !== "disabled"
        busy: stateName === "busy"
        onClicked: shell.clicks++
      }
    }
  }

  FoamyPopup {
    id: popup
    anchorItem: sim.anchor
    bar: bar
    open: true
    body: Component {
      Column {
        property alias blocks: blocks
        property alias page: page
        spacing: FoamyStyle.gapLarge
        StateGrid {
          id: blocks
          x: FoamyStyle.padding
          block: true
        }
        FoamySettingsPage {
          id: page
          width: parent.width
          implicitHeight: 360
          FoamySettingsSection {
            width: parent.width
            title: "Buttons"
            StateGrid {
              labels: ({
                  primary: "Save",
                  secondary: "Verify",
                  destructive: "Remove"
                })
              icons: ({
                  primary: "check",
                  secondary: "refresh-cw",
                  destructive: "trash"
                })
            }
          }
        }
      }
    }
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
  function findWhere(item, test) {
    if (!item)
      return null
    if (test(item))
      return item
    for (var i = 0; i < item.children.length; i++) {
      var found = findWhere(item.children[i], test)
      if (found)
        return found
    }
    return null
  }
  function button(grid, kind, state) {
    return findByName(grid, kind + "-" + state)
  }
  function label(b) {
    return findWhere(b, function (c) {
      return c.text === b.text && c.font !== undefined && c !== b
    })
  }
  function icon(b) {
    return findWhere(b, function (c) {
      return c.strokeWidth !== undefined
    })
  }
  function rect(item) {
    var p = item.mapToItem(popup.cardItem, 0, 0)
    return [p.x, p.y, item.width, item.height]
  }

  Component.onCompleted: wait.waitFor(function () {
    var body = popup.bodyItem
    return body && body.blocks && button(body.blocks, "destructive", "busy") && popup.cardItem.opacity === 1 && popup.cardItem.Window.window
  }, 5000, function (ok) {
    check(ok, "the popup shows its buttons")
    var w = popup.cardItem.Window.window
    if (!w.active)
      w.requestActivate()
    // Fills animate (Behavior on color): wait until no button's fill
    // changes on three polls in a row.
    var last = "", same = 0
    wait.waitFor(function () {
      var now = fills()
      same = now === last ? same + 1 : 0
      last = now
      return same >= 2 && w.active
    }, 5000, function (settled) {
      check(settled, "the fills settle and the window is active")
      shell.measure()
    })
  })

  function fills() {
    var body = popup.bodyItem
    var out = []
    for (var k = 0; k < kinds.length; k++)
      for (var s = 0; s < states.length; s++)
        out.push(String(button(body.blocks, kinds[k], states[s]).color))
    return out.join()
  }

  function measure() {
    var body = popup.bodyItem
    var settings = findWhere(body.page, function (c) {
      return c.labels !== undefined && c.labels.primary === "Save"
    })
    var info = {
      card: [popup.cardItem.width, popup.cardItem.height],
      surface: String(popup.surfaceColor),
      buttons: {}
    }
    for (var k = 0; k < kinds.length; k++) {
      var active = button(body.blocks, kinds[k], "active")
      for (var s = 0; s < states.length; s++) {
        var name = kinds[k] + "-" + states[s]
        var b = button(body.blocks, kinds[k], states[s])
        var real = button(settings, kinds[k], states[s]) || button(settings, kinds[k], "active")
        info.buttons[name] = {
          button: rect(b),
          label: rect(label(b))
        }
        // The icon is the label's ink, in every state and on any button.
        var glyph = icon(real)
        check(glyph && Qt.colorEqual(glyph.color, label(real).color) && glyph.opacity === 1 && label(real).opacity === 1, name + ": the icon draws in the label's colour " + (glyph ? glyph.color : "none") + " / " + label(real).color)
        // Inert and disabled keep the active button's size (busy adds its
        // spinner glyph to a button without an icon).
        if (states[s] !== "busy")
          check(b.implicitWidth === active.implicitWidth && b.implicitHeight === active.implicitHeight && real.implicitWidth === button(settings, kinds[k], "active").implicitWidth, name + ": the size of the active button " + [b.implicitWidth, active.implicitWidth])
      }
      // Busy draws as active: full strength, only the icon spins.
      var busy = button(body.blocks, kinds[k], "busy")
      check(Qt.colorEqual(busy.color, active.color) && Qt.colorEqual(label(busy).color, label(active).color) && Qt.colorEqual(busy.border.color, active.border.color), kinds[k] + ": busy draws as active " + [busy.color, active.color, label(busy).color, label(active).color])
    }
    console.log("FOAMY BUTTONS " + JSON.stringify(info))
    popup.cardItem.grabToImage(function (result) {
      result.saveToFile(Quickshell.env("FOAMY_OUT") + "/card.png")
      shell.pointer(0)
    })
  }

  // Each kind's inert button under the pointer: the same fill and label
  // as before, the plain cursor, and a click does nothing.
  function pointer(k) {
    if (k === kinds.length) {
      check(clicks === 0, "no inert button took a click " + clicks)
      finish()
      return
    }
    var b = button(popup.bodyItem.blocks, kinds[k], "inert")
    var before = [String(b.color), String(label(b).color), String(b.border.color)]
    var area = findWhere(b, function (c) {
      return c.cursorShape !== undefined && c.containsMouse !== undefined
    })
    ev.mouseMove(b, b.width / 2, b.height / 2, -1, Qt.NoButton, Qt.NoModifier)
    wait.waitFor(function () {
      return area.containsMouse
    }, 3000, function (ok) {
      check(ok, kinds[k] + ": the pointer reaches the inert button")
      // A hover fill would have started its animation by now.
      wait.after(FoamyMotion.hover + 100, function () {
        var after = [String(b.color), String(label(b).color), String(b.border.color)]
        check(JSON.stringify(after) === JSON.stringify(before), kinds[k] + ": an inert button keeps its look under the pointer " + before + " -> " + after)
        check(area.cursorShape === Qt.ArrowCursor, kinds[k] + ": an inert button shows the plain cursor " + area.cursorShape)
        ev.mouseClick(b, b.width / 2, b.height / 2, Qt.LeftButton, Qt.NoModifier, -1)
        ev.mouseMove(popup.cardItem, 1, popup.cardItem.height - 1, -1, Qt.NoButton, Qt.NoModifier)
        shell.pointer(k + 1)
      })
    }, tag + " " + kinds[k] + " pointer")
  }

  function finish() {
    console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
    console.log("FOAMY DONE")
    Qt.quit()
  }

  Item {
    parent: popup.bodyItem
    TestEvent {
      id: ev
    }
  }
}
