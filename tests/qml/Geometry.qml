import QtQuick
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"

// FoamyPopup / FoamyPopupCard placement against a mock bar, for every bar
// position. FOAMY_MODE=fullscreen: the bar window spans the screen (4.5);
// FOAMY_MODE=strip: the bar window is the strip itself (4.0).
ShellRoot {
  id: shell
  readonly property bool fullScreen: Quickshell.env("FOAMY_MODE") === "fullscreen"
  readonly property string out: Quickshell.env("FOAMY_OUT")
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property bool hasFork: Quickshell.env("FOAMY_FORK") === "1"
  readonly property int stripThickness: 34
  readonly property int screenW: 1920
  readonly property int screenH: 1080
  property string position: "top"
  property int failures: 0
  property int checks: 0

  function check(ok, label) {
    checks++
    if (!ok) { failures++; console.log("FOAMY FAIL " + label) }
  }
  function near(a, b) { return Math.abs(a - b) <= 1 }

  FloatingWindow {
    id: screenWindow
    implicitWidth: shell.screenW
    implicitHeight: shell.screenH
    color: "black"
    ScreenSim {
      id: sim
      position: shell.position
      thickness: shell.stripThickness
      fullScreenBar: shell.fullScreen
      stripColor: Commons.Color.background
      iconColor: Commons.Color.foreground
    }
  }

  // The 4.0 bar windows: just the strip, horizontal or vertical. Unused in 4.5 mode.
  FloatingWindow {
    id: horizontalStrip
    visible: !shell.fullScreen
    implicitWidth: shell.screenW
    implicitHeight: shell.stripThickness
    color: "black"
    Rectangle {
      id: horizontalAnchor
      width: sim.anchor.width
      height: sim.anchor.height
      x: sim.anchor.x
      y: (shell.stripThickness - height) / 2
    }
  }
  FloatingWindow {
    id: verticalStrip
    visible: !shell.fullScreen
    implicitWidth: shell.stripThickness
    implicitHeight: shell.screenH
    color: "black"
    Rectangle {
      id: verticalAnchor
      width: sim.anchor.width
      height: sim.anchor.height
      x: (shell.stripThickness - width) / 2
      y: sim.anchor.y
    }
  }

  readonly property Item anchorItem: fullScreen ? sim.anchor : (sim.vertical ? verticalAnchor : horizontalAnchor)

  MockBar { id: facadeBar; position: shell.position; barSize: shell.stripThickness }
  MockFullBar { id: fullBar; position: shell.position; barSize: shell.stripThickness; barSizes: ({ "FOAMY-1": 44 }) }

  Component {
    id: tallPopup
    FoamyPopup {
      maxHeight: 0          // only the screen limits the card
      body: Component { Rectangle { implicitHeight: 3000; color: "transparent" } }
    }
  }
  Component {
    id: cappedPopup
    FoamyPopup {
      body: Component { Rectangle { implicitHeight: 3000; color: "transparent" } }
    }
  }
  Component {
    id: maxedPopup
    FoamyPopup {
      maxHeight: 300
      body: Component { Rectangle { implicitHeight: 3000; color: "transparent" } }
    }
  }
  Component {
    id: standardPopup
    FoamyPopup {
      body: Component {
        Column {
          property bool built: true
          spacing: FoamyStyle.gap
          FoamyHeader { width: parent.width; iconName: "monitor"; title: "Geometry"; meta: shell.position + " bar" }
        }
      }
    }
  }
  Component {
    id: card
    FoamyPopupCard {
      body: Component { Rectangle { implicitHeight: 2400; color: "transparent" } }
      contentHeight: fittedContentHeight(bodyImplicitHeight)
    }
  }
  readonly property Component forkComponent: hasFork ? Qt.createComponent(Qt.resolvedUrl("fork/ForkedPopup.qml")) : null

  // Expected bar strip thickness for `bar` on this host/mode.
  function thicknessFor(bar) {
    if (!fullScreen) return stripThickness                       // 4.0: the window is the strip
    return typeof bar.barSizeFor === "function" ? bar.barSizeFor("FOAMY-1") : bar.barSize
  }

  function checkPlacement(label, x, y, w, h, t, popup) {
    var gap = popup.gap, margin = popup.margin
    var vertical = position === "left" || position === "right"
    var expectedAvail = screenH - (vertical ? margin * 2 : t + gap + margin)
    check(near(popup.availableCardHeight, expectedAvail), label + " availableCardHeight " + popup.availableCardHeight + " expected " + expectedAvail)
    check(popup.availableCardHeight > screenH / 2, label + " available height is sane (" + popup.availableCardHeight + ")")
    if (position === "top") check(near(y, t + gap), label + " top: card y " + y + " expected " + (t + gap))
    if (position === "bottom") check(near(y + h, screenH - t - gap), label + " bottom: card bottom " + (y + h) + " expected " + (screenH - t - gap))
    if (position === "left") check(near(x, t + gap), label + " left: card x " + x + " expected " + (t + gap))
    if (position === "right") check(near(x + w, screenW - t - gap), label + " right: card right " + (x + w) + " expected " + (screenW - t - gap))
    check(x >= 0 && y >= 0 && x + w <= screenW && y + h <= screenH, label + " card is on screen " + [x, y, w, h])
  }

  property var cases: []
  property int step: 0
  property var current: null
  property string currentLabel: ""
  property var currentBar: null
  property string currentKind: ""

  Component.onCompleted: {
    Style.cornerRadius = 6
    var positions = ["top", "bottom", "left", "right"]
    var list = []
    for (var i = 0; i < positions.length; i++) {
      list.push({ position: positions[i], kind: "tall", bar: "facade" })
      list.push({ position: positions[i], kind: "tall", bar: "full" })
      list.push({ position: positions[i], kind: "standard", bar: "facade" })
      list.push({ position: positions[i], kind: "card", bar: "facade" })
      list.push({ position: positions[i], kind: "capped", bar: "facade" })
      list.push({ position: positions[i], kind: "maxed", bar: "facade" })
      if (hasFork) list.push({ position: positions[i], kind: "fork", bar: "facade" })
    }
    cases = list
    runner.start()
  }

  Timer {
    id: runner
    interval: 120
    onTriggered: shell.begin()
  }
  Timer {
    id: settle
    interval: 450
    onTriggered: shell.measure()
  }

  function begin() {
    if (step >= cases.length) { finish(); return }
    var c = cases[step]
    position = c.position
    currentBar = c.bar === "full" ? fullBar : facadeBar
    currentKind = c.kind
    currentLabel = host + "/" + (fullScreen ? "fullscreen" : "strip") + "/" + c.position + "/" + c.kind + "/" + c.bar
    var props = { anchorItem: shell.anchorItem, bar: currentBar, open: false }
    if (c.kind === "fork") {
      current = forkComponent.createObject(shell, props)
      current.contentHeight = current.fittedContentHeight(3000)
      current.open = true
    } else {
      var components = { tall: tallPopup, standard: standardPopup, card: card, capped: cappedPopup, maxed: maxedPopup }
      current = components[c.kind].createObject(shell, props)
      if (c.kind === "standard") check(current.bodyItem === null, currentLabel + " body is lazy (not built before open)")
      current.open = true
    }
    settle.start()
  }

  function measure() {
    var p = current
    var t = thicknessFor(currentBar)
    if (currentKind === "fork") {
      var o = p.cardOrigin
      var broken = p.availableCardHeight <= 120 || (position === "top" && !near(o.y, t + p.gap))
        || (position === "bottom" && !near(o.y + p.contentHeight, screenH - t - p.gap))
        || (position === "right" && !near(o.x + p.contentWidth, screenW - t - p.gap))
        || (position === "left" && !near(o.x, t + p.gap))
      if (fullScreen && host === "4.5") {
        check(broken, currentLabel + " the old 4.0 fork should misplace on a full-screen bar window")
        if (broken) console.log("FOAMY NOTE " + currentLabel + " fork broken as expected: availableCardHeight " + p.availableCardHeight + " origin " + o.x + "," + o.y)
      } else {
        checkPlacement(currentLabel, o.x, o.y, p.contentWidth, p.contentHeight, t, p)
      }
      p.open = false
      p.destroy()
      next()
      return
    }
    if (currentKind === "card") {
      var vertical = position === "left" || position === "right"
      var expected = screenH - (vertical ? 0 : t) - p.margin * 2
      check(near(p.availableCardHeight, expected), currentLabel + " PopupCard availableCardHeight " + p.availableCardHeight + " expected " + expected)
      check(p.cardItem !== null && near(p.cardItem.radius, FoamyStyle.radius), currentLabel + " PopupCard foamy radius")
      check(p.cardItem !== null && p.cardItem.border.width === 1, currentLabel + " PopupCard 1px border")
      check(p.padding === FoamyStyle.menuPadding && p.cardItem && near(p.cardItem.contentTopInset, FoamyStyle.menuPadding + 1), currentLabel + " PopupCard menu padding " + p.padding)
      p.open = false
      p.destroy()
      next()
      return
    }
    var c = p.cardItem
    check(c !== null, currentLabel + " card found")
    if (c) {
      checkPlacement(currentLabel, c.x, c.y, c.width, c.height, t, p)
      check(near(c.radius, FoamyStyle.radius) && FoamyStyle.radius === 12, currentLabel + " foamy radius " + c.radius)
      check(c.border.width === 1, currentLabel + " 1px foamy border")
      check(Qt.colorEqual(c.border.color, FoamyPalette.border), currentLabel + " border colour alpha(text, .15)")
      check(p.layerNamespace === "omarchy-keyboard-panel", currentLabel + " layer namespace " + p.layerNamespace)
    }
    if (currentKind === "tall") check(near(c.height, p.availableCardHeight), currentLabel + " maxHeight 0: card fills the available height " + c.height)
    if (currentKind === "capped") check(near(c.height, Math.min(FoamyStyle.popupMaxHeight, p.availableCardHeight)), currentLabel + " default cap popupMaxHeight " + c.height)
    if (currentKind === "maxed") check(near(c.height, 300), currentLabel + " maxHeight 300 " + c.height)
    if (currentKind === "standard") {
      check(p.bodyItem !== null && p.bodyItem.built === true, currentLabel + " body built on open")
      check(p.contentWidth === FoamyStyle.popupWidth, currentLabel + " standard width " + p.contentWidth)
      if (position === "top" && currentBar === facadeBar) {
        var shot = out + "/geometry-" + host + "-" + (fullScreen ? "fullscreen" : "strip") + ".png"
        sim.grabToImage(function(result) { if (!result.saveToFile(shot)) console.log("FOAMY FAIL save " + shot) })
      }
      p.open = false
      closeCheck.target = p
      closeCheck.start()
      return
    }
    p.open = false
    p.destroy()
    next()
  }

  Timer {
    id: closeCheck
    property var target: null
    interval: 300
    onTriggered: {
      shell.check(target.bodyItem !== null, shell.currentLabel + " body kept after close")
      target.destroy()
      shell.next()
    }
  }

  function next() { step++; runner.start() }

  function finish() {
    console.log("FOAMY RESULT " + host + " " + (fullScreen ? "fullscreen" : "strip") + " checks=" + checks + " failures=" + failures)
    console.log("FOAMY DONE")
    Qt.quit()
  }
}
