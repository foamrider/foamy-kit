import QtQuick
import QtTest
import Quickshell
import qs.Commons
import "harness"
import "plugin/kit"

// Wheel scrolling (kit 0.4.0). Qt 6's Flickable turns each wheel event into
// a smoothing animation from the current position, so a high-resolution
// notch (8 x 15 instead of 1 x 120) loses most of its distance. Measured
// here on the plain Flickable (a NOTE, it's Qt's behaviour), then
// FoamyWheelScroll: whole notches however they are split, notches add up,
// pixel deltas 1:1, horizontal and inner wheel users left alone, bounds,
// FoamySettingsPage, ensureVisible for a growing section, FoamyInfoNote.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property string tag: host + "@" + Quickshell.env("FOAMY_SCALE")
  property int checks: 0
  property int failures: 0
  function check(ok, label) { checks++; if (!ok) { failures++; console.log("FOAMY FAIL " + tag + " " + label) } }
  function near(a, b, tolerance) { return Math.abs(a - b) <= (tolerance === undefined ? 1 : tolerance) }

  FloatingWindow {
    id: window
    implicitWidth: 1300
    implicitHeight: 500
    color: "black"
    Item {
      anchors.fill: parent
      TestEvent { id: ev }

      Flickable {
        id: plain
        width: 240; height: 400
        contentHeight: 4000
        boundsBehavior: Flickable.StopAtBounds
      }

      Flickable {
        id: fixed
        x: 250; width: 240; height: 400
        contentHeight: 4000
        boundsBehavior: Flickable.StopAtBounds
        // A horizontal list inside: it keeps its horizontal wheel.
        Flickable {
          id: inner
          y: 0; width: 240; height: 60
          contentWidth: 2000
          flickableDirection: Flickable.HorizontalFlick
          boundsBehavior: Flickable.StopAtBounds
        }
        // A slider-like control with its own wheel use.
        MouseArea {
          id: slider
          y: 80; width: 240; height: 40
          property int wheels: 0
          onWheel: function(wheel) { wheels++; wheel.accepted = true }
        }
        // Content that fits: the wheel goes on to the outer view.
        Flickable {
          id: short
          y: 140; width: 240; height: 100
          contentHeight: 50
          FoamyWheelScroll { id: shortWheel; target: short }
        }
      }
      FoamyWheelScroll { id: wheel; target: fixed }

      FoamySettingsPage {
        id: page
        x: 500; width: 420; height: 400
        FoamySettingsSection {
          id: firstSection
          width: parent.width
          title: "Rows"
          Repeater { model: 8; FoamyToggle { width: parent.width; label: "Toggle " + index } }
          Repeater { model: 4; FoamyNumberField { width: parent.width; label: "Number " + index; value: 5 } }
          Repeater { model: 4; FoamyDropdown { width: parent.width; value: "a"; options: ["a", "b"] } }
        }
        FoamySettingsSection {
          id: lfs
          width: parent.width
          title: "Git LFS"
          info: "Automatic checks run Git without a repository's own settings, filters and hooks, so nothing in a repository can run code just by being in these folders. A trusted repository runs its own Git settings."
          FoamyToggle { width: parent.width; label: "Repository" }
        }
        FoamySettingsSection {
          width: parent.width
          title: "Wireless"
          Rectangle {
            id: grower
            width: parent.width
            height: 0
            color: "steelblue"
            NumberAnimation on height { id: grow; running: false; from: 0; to: 260; duration: 250 }
          }
        }
      }
    }
  }

  // --- sequence ----------------------------------------------------------------
  property var steps: []
  property int stepIndex: 0
  function next() {
    if (stepIndex >= steps.length) {
      console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
      console.log("FOAMY DONE")
      Qt.quit()
      return
    }
    var step = steps[stepIndex++]
    step.run()
    stepTimer.interval = step.wait || 450
    stepTimer.restart()
  }
  Timer { id: stepTimer; onTriggered: { if (shell.pendingCheck) shell.pendingCheck(); shell.pendingCheck = null; shell.next() } }
  property var pendingCheck: null
  // Send `count` events of `delta` (angle units) to `item` at (x, y), `gap` ms apart.
  function burst(item, x, y, count, delta, horizontal) {
    for (var i = 0; i < count; i++)
      ev.mouseWheel(item, x, y, Qt.NoButton, Qt.NoModifier, horizontal ? -delta : 0, horizontal ? 0 : -delta, -1)
  }
  function step(run, check, wait) { return { run: function() { run(); shell.pendingCheck = check }, wait: wait } }

  Component.onCompleted: {
    var notch = wheel.notch
    steps = [
      step(function() {}, function() {}, 800),
      // Qt's own wheel handling (NOTE only).
      step(function() { plain.contentY = 0; burst(plain, 100, 100, 1, 120) },
           function() { console.log("FOAMY NOTE " + tag + " plain Flickable, one 120 notch: " + plain.contentY.toFixed(1) + " px") }),
      step(function() { plain.contentY = 0; burst(plain, 100, 100, 8, 15) },
           function() { console.log("FOAMY NOTE " + tag + " plain Flickable, one notch as 8 x 15: " + plain.contentY.toFixed(1) + " px (Qt loses most of it)") }),
      // FoamyWheelScroll.
      step(function() { check(notch >= 3 * FoamyStyle.rowHeight - 0.5, "a notch is about three rows " + notch); fixed.contentY = 0; burst(fixed, 100, 300, 1, 120) },
           function() { check(near(fixed.contentY, notch), "one 120 notch scrolls one notch " + fixed.contentY) }),
      step(function() { fixed.contentY = 0; burst(fixed, 100, 300, 8, 15) },
           function() { check(near(fixed.contentY, notch), "a notch split 8 x 15 scrolls the same " + fixed.contentY) }),
      step(function() { fixed.contentY = 0; burst(fixed, 100, 300, 24, 15) },
           function() { check(near(fixed.contentY, notch * 3), "three quick notches add up " + fixed.contentY) }),
      step(function() { fixed.contentY = 500; burst(fixed, 100, 300, 2, -120) },
           function() { check(near(fixed.contentY, 500 - notch * 2), "scrolling up " + fixed.contentY) }),
      step(function() {
             fixed.contentY = 100
             wheel.wheel({ angleDelta: Qt.point(0, 0), pixelDelta: Qt.point(0, -37) })
             check(near(fixed.contentY, 137), "touchpad pixel delta maps 1:1, at once " + fixed.contentY)
             wheel.wheel({ angleDelta: Qt.point(0, 0), pixelDelta: Qt.point(0, 12) })
             check(near(fixed.contentY, 125), "touchpad up " + fixed.contentY)
           }, function() {}, 50),
      step(function() { fixed.contentY = 0; inner.contentX = 0; burst(inner, 100, 30, 1, 120, true) },
           function() { check(fixed.contentY === 0 && inner.contentX > 0, "a horizontal wheel reaches the inner list " + inner.contentX + " / " + fixed.contentY) }),
      step(function() { fixed.contentY = 0; burst(slider, 100, 20, 1, 120) },
           function() { check(slider.wheels === 1 && fixed.contentY === 0, "a control's own wheel use comes first " + slider.wheels + " / " + fixed.contentY) }),
      step(function() { fixed.contentY = 0; burst(short, 100, 160 - 140 + 20, 1, 120) },
           function() { check(!shortWheel.scrollable && near(fixed.contentY, notch), "content that fits passes the wheel on " + fixed.contentY) }),
      step(function() { fixed.contentY = 4000 - 400 - 30; burst(fixed, 100, 300, 2, 120) },
           function() { check(near(fixed.contentY, 4000 - 400), "stops at the end " + fixed.contentY) }),
      // FoamySettingsPage.
      step(function() { page.flickable.contentY = 0; burst(page, 200, 200, 8, 15) },
           function() { check(near(page.flickable.contentY, page.wheel.notch), "settings page: a split notch scrolls a notch " + page.flickable.contentY) }),
      step(function() { page.flickable.contentY = 0; burst(page, 200, 330, 8, 15) },
           function() { check(near(page.flickable.contentY, page.wheel.notch), "settings page: over a field or dropdown too " + page.flickable.contentY) }),
      // ensureVisible follows a section while it grows.
      step(function() { page.flickable.contentY = 0; grow.start(); page.ensureVisible(grower) },
           function() {
             var y = grower.mapToItem(page.flickable.contentItem, 0, 0).y
             var view = page.flickable
             check(grower.height === 260 && y + grower.height <= view.contentY + view.height + 1 && y >= view.contentY - 1,
                   "ensureVisible keeps a growing section in view " + [y, grower.height, view.contentY, view.height])
           }, 700),
      // FoamyInfoNote: closed by default, opens inline and scrolls into view.
      step(function() {
             check(!lfs.infoNote.expanded && !lfs.infoNote.note.visible, "info note starts folded")
             page.flickable.contentY = 0
             lfs.infoNote.toggle()
           }, function() {
             var note = lfs.infoNote.note
             var y = note.mapToItem(page.flickable.contentItem, 0, 0).y
             var view = page.flickable
             check(note.visible && note.height > FoamyStyle.font.bodySmall * 3, "the note opens inline, wrapped " + note.height)
             check(note.width <= lfs.width + 0.5, "the note is no wider than its column " + note.width)
             check(y + note.height <= view.contentY + view.height + 1, "the opened note is scrolled into view " + [y, note.height, view.contentY])
           }, 700),
      step(function() { lfs.infoNote.infoButton.clicked() }, function() { check(!lfs.infoNote.expanded, "the (i) folds it again") }, 100)
    ]
    next()
  }
}
