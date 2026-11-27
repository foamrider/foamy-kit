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
// click, a busy one draws as an active one, the states keep the active
// button's size, the border fades with the state but a focus ring does
// not, a change of state never shows the new label on the old fill, also
// under the pointer, and an active button's hover still animates.
// Prints FOAMY BUTTONS <json> (where each button and its label are on the
// card) and saves the card to FOAMY_OUT/card.png.
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
    // Measure the card settled: wait until no button's fill changes on
    // three polls in a row.
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
      borders()
      transition(0, 0)
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

  // Inert and disabled fade the border as the fill (.7, .45); a focus ring
  // keeps full strength: a focused button that turns inert (a Verify that
  // runs) still shows where the focus is.
  function borders() {
    var blocks = popup.bodyItem.blocks
    for (var k = 0; k < kinds.length; k++) {
      var active = button(blocks, kinds[k], "active")
      var edge = active.border.color
      var faded = [["inert", 0.7], ["disabled", FoamyStyle.disabledOpacity]]
      for (var f = 0; f < faded.length; f++) {
        var b = button(blocks, kinds[k], faded[f][0])
        var c = b.border.color
        check(Math.abs(c.a - edge.a * faded[f][1]) < 0.01 && Math.abs(c.r - edge.r) < 0.01 && Math.abs(c.g - edge.g) < 0.01 && Math.abs(c.b - edge.b) < 0.01, kinds[k] + " " + faded[f][0] + ": the border is the active one at " + faded[f][1] + " " + edge + " -> " + c)
      }
      var inert = button(blocks, kinds[k], "inert")
      active.focusable = true
      inert.focusable = true
      active.forceActiveFocus()
      var ring = [String(active.border.color), active.border.width]
      inert.forceActiveFocus()
      var shown = [String(inert.border.color), inert.border.width]
      check(active.activeFocus === false && inert.activeFocus && JSON.stringify(shown) === JSON.stringify(ring), kinds[k] + ": a focused inert button shows the full focus ring " + ring + " / " + shown)
      inert.focus = false
      active.focusable = false
      inert.focusable = false
    }
  }

  // A change of state draws the new fill with the new label: sampled right
  // after each change and on each change of the fill or the label through
  // the next 150 ms, the label on the fill as drawn over the card never
  // reads worse than in the weaker of the two states, settled. With motion
  // on: an animated fill under the new label read 1.57:1 (light primary,
  // inert to active).
  readonly property var moves: [["active", "inert"], ["inert", "disabled"], ["disabled", "inert"], ["inert", "active"], ["active", "disabled"], ["disabled", "active"]]
  property var settledRatios: ({})
  function drawnRatio(b) {
    var fill = Qt.color(Qt.tint(popup.surfaceColor, b.color).toString())
    return FoamyPalette.contrastRatio(label(b).color, fill)
  }
  function setState(b, state) {
    b.enabled = state !== "disabled"
    b.actionEnabled = state !== "inert"
  }
  // Calls then(ok) once b's fill and label have kept their colour for three
  // polls in a row (a fill that still moves would be the last change's).
  function settle(b, then) {
    var last = "", same = 0
    wait.waitFor(function () {
      var now = String(b.color) + String(label(b).color)
      same = now === last ? same + 1 : 0
      last = now
      return same >= 2
    }, 3000, then)
  }
  // The worst ratio of b's label on its fill from now on, for
  // FoamyMotion.hover + 50 ms; then(worst). Sampled after each change of
  // the fill or the label, once the bindings of that change have run
  // (Qt.callLater): between the fill's and the label's notification of
  // one change, no frame is drawn.
  function sampleRatio(b, then) {
    var worst = drawnRatio(b)
    var text = label(b)
    var sample = function () {
      worst = Math.min(worst, drawnRatio(b))
    }
    var later = function () {
      Qt.callLater(sample)
    }
    b.colorChanged.connect(later)
    text.colorChanged.connect(later)
    wait.after(FoamyMotion.hover + 50, function () {
      b.colorChanged.disconnect(later)
      text.colorChanged.disconnect(later)
      sample()
      then(worst)
    })
  }
  function transition(k, m) {
    if (k === kinds.length) {
      hover(0)
      return
    }
    if (m === moves.length) {
      setState(button(popup.bodyItem.blocks, kinds[k], "active"), "active")
      transition(k + 1, 0)
      return
    }
    check(FoamyMotion.hover > 0, "motion is on")
    var blocks = popup.bodyItem.blocks
    // The active button is the probe; each state's ratio, settled, comes
    // from the grid before the first change.
    var probe = button(blocks, kinds[k], "active")
    if (m === 0)
      settledRatios = {
        active: drawnRatio(probe),
        inert: drawnRatio(button(blocks, kinds[k], "inert")),
        disabled: drawnRatio(button(blocks, kinds[k], "disabled"))
      }
    var from = moves[m][0], to = moves[m][1]
    var floor = Math.min(settledRatios[from], settledRatios[to])
    var name = kinds[k] + " " + from + " -> " + to
    settle(probe, function (ok) {
      check(ok, name + ": the probe settles")
      setState(probe, to)
      sampleRatio(probe, function (worst) {
        check(worst >= floor - 0.005, name + ": the label reads on the fill through the change " + worst.toFixed(2) + ", settled at least " + floor.toFixed(2))
        shell.transition(k, m + 1)
      })
    })
  }

  // Hover and a change of state together, on each kind's active probe:
  // under the pointer the fill animates from rest to hot; a probe that
  // turns inert as that animation starts draws the inert fill and label at
  // once and keeps them; turned active again under the pointer, the label
  // reads as on the hot fill; turned inert, left by the pointer and active
  // again within the hover time, as on the rest fill, where the fill then
  // stays. (With `Behavior` on the whole active fill, a light primary read
  // 3.90:1 there, settled 4.35: the end of the animation from hot to rest.)
  function colorBetween(c, a, b) {
    var within = function (v, x, y) {
      return v >= Math.min(x, y) - 0.002 && v <= Math.max(x, y) + 0.002
    }
    return !Qt.colorEqual(c, a) && !Qt.colorEqual(c, b) && within(c.r, a.r, b.r) && within(c.g, a.g, b.g) && within(c.b, a.b, b.b) && within(c.a, a.a, b.a)
  }
  function pointerOff() {
    ev.mouseMove(popup.cardItem, 1, popup.cardItem.height - 1, -1, Qt.NoButton, Qt.NoModifier)
  }
  function pointerOn(b) {
    ev.mouseMove(b, b.width / 2, b.height / 2, -1, Qt.NoButton, Qt.NoModifier)
  }
  function hover(k) {
    if (k === kinds.length) {
      finish()
      return
    }
    var blocks = popup.bodyItem.blocks
    var probe = button(blocks, kinds[k], "active")
    var inert = button(blocks, kinds[k], "inert")
    var inertRatio = drawnRatio(inert)
    var name = kinds[k] + " hover"
    var drawn = function () {
      return JSON.stringify([String(probe.color), String(label(probe).color)])
    }
    var want = JSON.stringify([String(inert.color), String(label(inert).color)])
    settle(probe, function (ok) {
      check(ok && !probe.hovered, name + ": the probe settles at rest off the pointer")
      var rest = String(probe.color)
      var restRatio = drawnRatio(probe)
      var seen = []
      var record = function () {
        seen.push(String(probe.color))
      }
      probe.colorChanged.connect(record)
      pointerOn(probe)
      wait.waitFor(function () {
        return probe.hovered
      }, 3000, function (ok) {
        check(ok, name + ": the pointer reaches the probe")
        settle(probe, function (ok) {
          probe.colorChanged.disconnect(record)
          var hot = String(probe.color)
          var between = seen.filter(function (c) {
            return colorBetween(Qt.color(c), Qt.color(rest), Qt.color(hot))
          })
          check(ok && hot !== rest && between.length > 0, name + ": the fill animates from rest to hot " + rest + " -> " + hot + " through " + between.length + " of " + seen.length + " values")
          var hotRatio = drawnRatio(probe)
          pointerOff()
          settle(probe, function (ok) {
            check(ok && String(probe.color) === rest, name + ": off the pointer the fill returns to rest " + probe.color)
            var onHover = function () {
              if (!probe.hovered)
                return
              probe.hoveredChanged.disconnect(onHover)
              // After the bindings of the hover have run: its animation
              // has started.
              Qt.callLater(function () {
                setState(probe, "inert")
                check(drawn() === want, name + ": turned inert under the pointer, the inert fill and label at once " + drawn() + " / " + want)
                wait.after(FoamyMotion.hover + 50, function () {
                  check(drawn() === want, name + ": and still after the hover time " + drawn() + " / " + want)
                  var floor = Math.min(inertRatio, hotRatio)
                  setState(probe, "active")
                  sampleRatio(probe, function (worst) {
                    check(worst >= floor - 0.005, name + ": active again under the pointer, the label reads on the fill " + worst.toFixed(2) + ", settled at least " + floor.toFixed(2))
                    setState(probe, "inert")
                    pointerOff()
                    // Within the hover time on an idle machine; later, the
                    // check still holds and proves less.
                    wait.after(30, function () {
                      var floor = Math.min(inertRatio, restRatio)
                      setState(probe, "active")
                      sampleRatio(probe, function (worst) {
                        check(worst >= floor - 0.005, name + ": inert, left by the pointer and active again, the label reads on the fill " + worst.toFixed(2) + ", settled at least " + floor.toFixed(2))
                        settle(probe, function (ok) {
                          check(ok && String(probe.color) === rest, name + ": the fill settles at rest " + probe.color + " / " + rest)
                          shell.hover(k + 1)
                        })
                      })
                    })
                  })
                })
              })
            }
            probe.hoveredChanged.connect(onHover)
            pointerOn(probe)
          })
        })
      })
    })
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
