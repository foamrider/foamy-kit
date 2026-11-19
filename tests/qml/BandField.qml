import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"

// FoamyHeroBand field mode inside a real FoamyPopup: a SafeTextField grows
// from the "+" action across the title row and back. Every frame of both
// animations keeps the band's height and the content under it in place; the
// field starts on the action and ends between the side paddings in the
// title row's slot; the title row and buttons fade out and take no pointer,
// cursor or menu while it is open. A band with a hero keeps its hero; a
// hidden origin grows from the row's trailing end; reduced motion is
// instant; the compact form has no field mode. FOAMY_RTL=1 mirrors. Shots
// go to FOAMY_OUT.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property bool rtl: Quickshell.env("FOAMY_RTL") === "1"
  readonly property string tag: Quickshell.env("FOAMY_TAG")
  property int checks: 0
  property int failures: 0
  property int settingsClicks: 0
  property int addClicks: 0
  readonly property var input: popup.bodyItem ? popup.bodyItem.input : null

  function check(ok, label) {
    checks++
    if (!ok) {
      failures++
      console.log("FOAMY FAIL " + tag + " " + label)
    }
  }
  function near(a, b, t) {
    return Math.abs(a - b) <= (t === undefined ? 0.51 : t)
  }
  function rectOf(item, target) {
    var p = item.mapToItem(target, 0, 0)
    return [p.x, p.y, item.width, item.height]
  }
  function sameRect(a, b, t) {
    return near(a[0], b[0], t) && near(a[1], b[1], t) && near(a[2], b[2], t) && near(a[3], b[3], t)
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
    body: Component {
      Column {
        property alias band: band
        property alias heroBand: heroBand
        property alias compactBand: compactBand
        property alias list: list
        property alias addAction: addAction
        property alias searchAction: searchAction
        property alias hiddenAction: hiddenAction
        property alias input: input
        property alias heroValue: heroValue
        LayoutMirroring.enabled: shell.rtl
        LayoutMirroring.childrenInherit: true

        // Title only, as in Todoist: "+" left of Search.
        FoamyHeroBand {
          id: band
          width: parent.width
          iconName: "inbox"
          title: "Todoist"
          meta: "12 tasks"
          onSettingsClicked: shell.settingsClicks++
          trailing: [
            FoamyAction {
              id: addAction
              iconName: "plus"
              tooltipText: "Add task"
              onClicked: shell.addClicks++
            },
            FoamyAction {
              id: searchAction
              iconName: "search"
              tooltipText: "Search"
            },
            FoamyAction {
              id: hiddenAction
              visible: false
              iconName: "refresh-cw"
            }
          ]
          field: SafeTextField {
            id: input
            placeholderText: "Buy milk #home"
          }
          fieldOrigin: addAction
        }
        Rectangle {
          id: list
          width: parent.width
          height: 120
          color: "transparent"
        }
        FoamyHeroBand {
          id: heroBand
          width: parent.width
          title: "Power"
          meta: "41%"
          field: SafeTextField {}
          Text {
            id: heroValue
            text: "41%"
            color: FoamyPalette.text
            font.pixelSize: FoamyStyle.font.numeralCompact
          }
        }
        FoamyHeroBand {
          id: compactBand
          width: parent.width
          compact: true
          field: SafeTextField {}
          fieldOpen: true
        }
      }
    }
  }

  FoamyWait {
    id: wait
  }

  // Samples of the field and the layout on every frame of an animation.
  property var samples: []
  property bool sampling: false
  FrameAnimation {
    running: shell.sampling
    onTriggered: shell.sample()
  }
  property bool grewShot: false
  function sample() {
    var b = popup.bodyItem.band
    var slot = findByName(b, "foamyHeroBandField")
    // One shot mid-growth, to look at.
    if (!grewShot && b.fieldOpen && b.fieldProgress >= 0.4) {
      grewShot = true
      popup.cardItem.grabToImage(function (result) {
        result.saveToFile(Quickshell.env("FOAMY_OUT") + "/field-growing.png")
      })
    }
    samples.push({
      progress: b.fieldProgress,
      bandHeight: b.height,
      listY: popup.bodyItem.list.y,
      field: rectOf(slot, b),
      fieldOpacity: slot.opacity,
      headerOpacity: b.titleRow.opacity
    })
  }

  Timer {
    interval: 900
    running: true
    onTriggered: shell.closedState()
  }

  property real height0: 0
  property real listY0: 0
  property var origin: []
  property var openRect: []

  function closedState() {
    var body = popup.bodyItem
    var b = body.band
    height0 = b.height
    listY0 = body.list.y
    origin = rectOf(body.addAction, b)
    var h = Math.min(b.titleRow.height, FoamyStyle.controlHeight)
    openRect = [FoamyStyle.padding, b.titleRow.y + (b.titleRow.height - h) / 2, b.width - FoamyStyle.padding * 2, h]
    check(!b.fieldShown && b.fieldProgress === 0 && b.buttonsActive, "closed: no field, buttons active")
    check(!input.visible, "closed: the field is hidden")
    check(input.parent && input.parent.objectName === "foamyHeroBandField", "the band holds the field")
    check(input.font.pixelSize === FoamyStyle.font.heading && FoamyStyle.font.heading > FoamyStyle.font.body, "the field's text is heading size " + input.font.pixelSize)
    check(openRect[3] <= b.titleRow.height && near(openRect[3], FoamyStyle.controlHeight), "the open field fits the title row")
    var add = body.addAction.mapToItem(b, 0, 0).x
    var search = body.searchAction.mapToItem(b, 0, 0).x
    check(shell.rtl ? add > search : add < search, "\"+\" sits before Search in reading order " + [add, search])
    // Pointer reaches the buttons while closed.
    ev.mouseClick(b.settingsButton, b.settingsButton.width / 2, b.settingsButton.height / 2, Qt.LeftButton, Qt.NoModifier, -1)
    check(settingsClicks === 1, "closed: Settings takes a click")
    shell.opening()
  }

  function opening() {
    var b = popup.bodyItem.band
    samples = []
    sampling = true
    b.fieldOpen = true
    check(!b.buttonsActive && b.fieldShown, "opening: the buttons are inert at once, the field shows")
    wait.waitFor(function () {
      return b.fieldProgress === 1
    }, 3000, function () {
      sampling = false
      sample()
      check(samples.length >= 4, "the growth is animated over frames: " + samples.length)
      var steady = true, growing = true, last = -1
      for (var i = 0; i < samples.length; i++) {
        var s = samples[i]
        steady = steady && near(s.bandHeight, height0) && near(s.listY, listY0)
        growing = growing && s.field[2] >= last - 0.01
        last = s.field[2]
      }
      check(steady, "opening: the band's height and the content under it never move")
      check(growing, "opening: the field only grows")
      var first = samples[0]
      check(first.progress < 0.6 && sameRect(first.field, lerp(origin, openRect, first.progress), 1), "opening: the field starts from the \"+\" action " + JSON.stringify([first.field, origin, first.progress]))
      var end = samples[samples.length - 1]
      check(sameRect(end.field, openRect), "open: the field spans the title row between the paddings " + JSON.stringify([end.field, openRect]))
      check(end.headerOpacity === 0 && end.fieldOpacity === 1, "open: the title row is gone, the field is opaque")
      var faded = samples.filter(function (s) {
        return s.headerOpacity === 0
      })
      check(faded.length > 0 && faded[0].progress < 1, "the title row has faded before the growth ends")
      shell.openState()
    }, "the field opens")
  }
  function lerp(a, b, t) {
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t]
  }

  function openState() {
    var body = popup.bodyItem
    var b = body.band
    check(input.visible && b.titleRow.enabled === false, "open: field visible, title row disabled")
    // No pointer, cursor or menu for the buttons.
    ev.mouseClick(b.settingsButton, b.settingsButton.width / 2, b.settingsButton.height / 2, Qt.LeftButton, Qt.NoModifier, -1)
    check(settingsClicks === 1, "open: a click where Settings was reaches nothing")
    var add = body.addAction
    var p = add.mapToItem(b, add.width / 2, add.height / 2)
    input.focusInput()
    ev.mouseClick(b, p.x, p.y, Qt.LeftButton, Qt.NoModifier, -1)
    check(addClicks === 0, "open: a click where \"+\" was reaches the field, not the action")
    b.settingsHasCursor = true
    b.menuHasCursor = true
    check(!b.settingsButton.hasCursor && !b.titleRow.menuButton.hasCursor, "open: cursor stops light nothing")
    b.settingsHasCursor = false
    b.menuHasCursor = false
    b.menuItems = [menuEntry]
    b.openMenu(true)
    check(!b.menuOpen, "open: the ⋯ menu does not open")
    // Back to the row the closing animation returns to (the header relays out on a timer).
    b.menuItems = []
    // Typing goes to the field.
    ev.keyClickChar("a", Qt.NoModifier, -1)
    check(input.text === "a", "the open field takes typing " + JSON.stringify(input.text))
    console.log("FOAMY BANDFIELD " + JSON.stringify({
      band: rectOf(b, popup.cardItem)
    }))
    wait.after(100, function () {
      check(sameRect(rectOf(body.addAction, b), origin), "the \"+\" action is back in its place")
      popup.cardItem.grabToImage(function (result) {
        check(result.saveToFile(Quickshell.env("FOAMY_OUT") + "/field-open.png"), "saved field-open")
        shell.closing()
      })
    })
  }
  property FoamyMenuItem menuEntry: FoamyMenuItem {
    text: "Entry"
    iconName: "inbox"
  }

  function closing() {
    var b = popup.bodyItem.band
    samples = []
    sampling = true
    b.fieldOpen = false
    check(b.buttonsActive && b.fieldShown, "closing: the buttons are active at once, the field still shows")
    wait.waitFor(function () {
      return !b.fieldShown
    }, 3000, function () {
      sampling = false
      check(samples.length >= 4, "the closing is animated over frames: " + samples.length)
      var steady = true, shrinking = true, last = 1e9
      for (var i = 0; i < samples.length; i++) {
        var s = samples[i]
        steady = steady && near(s.bandHeight, height0) && near(s.listY, listY0)
        shrinking = shrinking && s.field[2] <= last + 0.01
        last = s.field[2]
        if (s.progress > 0 && !sameRect(s.field, lerp(origin, openRect, s.progress), 1))
          shrinking = false
      }
      check(steady, "closing: the band's height and the content under it never move")
      check(shrinking, "closing: the field shrinks back towards the \"+\" action")
      check(b.titleRow.opacity === 1 && !input.visible, "closed again: title row back, field hidden")
      ev.mouseClick(b.settingsButton, b.settingsButton.width / 2, b.settingsButton.height / 2, Qt.LeftButton, Qt.NoModifier, -1)
      check(settingsClicks === 2, "closed again: Settings takes a click")
      shell.others()
    }, "the field closes")
  }

  // A hero band, a hidden origin, reduced motion and the compact form.
  function others() {
    var body = popup.bodyItem
    var hb = body.heroBand
    var heroY = body.heroValue.mapToItem(hb, 0, 0).y
    var h0 = hb.height
    Style.reduceMotion = true
    hb.fieldOpen = true
    check(hb.fieldProgress === 1 && hb.fieldShown && hb.titleRow.opacity === 0, "reduced motion: open at once")
    var slot = findByName(hb, "foamyHeroBandField")
    check(near(hb.height, h0) && near(body.heroValue.mapToItem(hb, 0, 0).y, heroY), "a hero band keeps its height and its hero " + [hb.height, h0])
    var to = slot.mapToItem(hb, 0, 0)
    check(to.y + slot.height <= hb.titleRow.y + hb.titleRow.height + 0.5, "the field stays in the title row, above the hero")
    hb.fieldOpen = false
    check(hb.fieldProgress === 0 && !hb.fieldShown && hb.titleRow.opacity === 1, "reduced motion: closed at once")
    Style.reduceMotion = false
    // No origin in the row: grow from its trailing end.
    var b = body.band
    b.fieldOrigin = body.hiddenAction
    var from = b._fieldFrom
    var end = b.width - FoamyStyle.padding
    check(shell.rtl ? near(from.x, FoamyStyle.padding) : near(from.x + from.width, end), "a hidden origin grows from the row's trailing end " + [from.x, from.width])
    b.fieldOrigin = body.searchAction
    var search = rectOf(body.searchAction, b)
    from = b._fieldFrom
    check(sameRect([from.x, from.y, from.width, from.height], search), "Search as the origin")
    var compact = body.compactBand
    check(!compact.fieldShown && compact.buttonsActive, "the compact form has no field mode")
    shell.finish()
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
