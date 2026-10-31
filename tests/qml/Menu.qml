import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"

// kit 0.4.0 header overflow inside a real FoamyPopup on the simulated
// screen: at most three buttons top right, trailing in priority order,
// Settings into the ⋯ menu when overflowing, the menu as an in-card overlay
// anchored to the ⋯ button's trailing edge (LTR and RTL), single-cursor
// keyboard navigation, submenus, Esc, press outside, focus restore.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property bool rtl: Quickshell.env("FOAMY_RTL") === "1"
  readonly property string tag: host + "/" + (rtl ? "rtl" : "ltr") + "@" + Quickshell.env("FOAMY_SCALE")
  property int checks: 0
  property int failures: 0
  function check(ok, label) { checks++; if (!ok) { failures++; console.log("FOAMY FAIL " + tag + " " + label) } }
  function eq(actual, expected, label) { check(JSON.stringify(actual) === JSON.stringify(expected), label + ": got " + JSON.stringify(actual) + ", expected " + JSON.stringify(expected)) }
  function near(a, b) { return Math.abs(a - b) <= 1.01 }

  FloatingWindow {
    id: window
    implicitWidth: 1920
    implicitHeight: 1080
    color: "black"
    ScreenSim { id: sim; fullScreenBar: shell.host === "4.5" }
  }
  FloatingWindow {
    visible: shell.host !== "4.5"
    implicitWidth: 1920
    implicitHeight: 34
    color: "black"
    Item { id: stripAnchor; x: sim.anchor.x; y: 6; width: 22; height: 22 }
  }
  MockBar { id: bar }

  property int searchClicks: 0
  property int clearClicks: 0
  property int refreshClicks: 0
  property int settingsClicks: 0
  property int snoozed: 0
  property bool silenceEnabled: true
  property bool showSearch: true

  FoamyPopup {
    id: popup
    anchorItem: shell.host === "4.5" ? sim.anchor : stripAnchor
    bar: bar
    open: true
    body: Component {
      FocusScope {
        id: bodyRoot
        property alias nc: nc
        property alias pair: pair
        property alias withMenu: withMenu
        property alias noSettings: noSettings
        property alias catcher: catcher
        property alias rowBelow: rowBelow
        // Synthetic keys and clicks go to the window the card is in.
        property alias ev: bodyEvent
        TestEvent { id: bodyEvent }
        implicitHeight: column.implicitHeight
        LayoutMirroring.enabled: shell.rtl
        LayoutMirroring.childrenInherit: true
        Column {
          id: column
          width: parent.width
          // The notification-center case: three actions, two menu items with
          // a submenu, Settings.
          FoamyHeroBand {
            id: nc
            width: parent.width
            iconName: "bell"
            title: "Notifications"
            meta: "2 notifications"
            onSettingsClicked: shell.settingsClicks++
            trailing: [
              FoamyAction { objectName: "search"; visible: shell.showSearch; iconName: "search"; tooltipText: "Search"; onClicked: shell.searchClicks++ },
              FoamyAction { objectName: "clear"; iconName: "trash"; destructive: true; tooltipText: "Clear all"; onClicked: shell.clearClicks++ },
              FoamyAction { objectName: "refresh"; iconName: "refresh-cw"; tooltipText: "Refresh"; onClicked: shell.refreshClicks++ }
            ]
            menuItems: [
              FoamyMenuItem { objectName: "silence"; text: "Silence notifications"; iconName: "bell-off"; enabled: shell.silenceEnabled },
              FoamyMenuItem {
                objectName: "snooze"
                text: "Snooze notifications"
                iconName: "alarm-clock"
                FoamyMenuItem { text: "30 minutes"; iconName: "clock"; onTriggered: shell.snoozed = 30 }
                FoamyMenuItem { text: "1 hour"; iconName: "clock"; onTriggered: shell.snoozed = 60 }
              }
            ]
            Text { text: "3"; color: FoamyPalette.text; font.pixelSize: FoamyStyle.font.numeralCompact }
          }
          // Room under the band so the menu drops inside the card.
          Rectangle { id: rowBelow; width: parent.width; height: 220; color: "transparent"
            MouseArea { anchors.fill: parent; hoverEnabled: true; property int presses: 0; onPressed: presses++ }
          }
          FoamyHeader { id: pair; width: parent.width; title: "Pair"
            FoamyAction { iconName: "volume-2" }
            FoamyAction { iconName: "mic" }
          }
          FoamyHeader { id: withMenu; width: parent.width; title: "With menu"
            FoamyAction { iconName: "refresh-cw" }
            menuItems: [ FoamyMenuItem { text: "Open"; iconName: "external-link" } ]
          }
          FoamyHeader { id: noSettings; width: parent.width; title: "No settings"; showSettings: false
            FoamyAction { iconName: "play" }
            FoamyAction { iconName: "globe" }
            FoamyAction { iconName: "download" }
          }
          FocusScope { id: catcher; width: 10; height: 10; focus: true }
        }
      }
    }
  }

  readonly property var ev: popup.bodyItem ? popup.bodyItem.ev : null

  // A short popup (band only): the card grows while the menu is open.
  FoamyPopup {
    id: shortPopup
    anchorItem: shell.host === "4.5" ? sim.anchor : stripAnchor
    bar: bar
    open: true
    centerOnBar: true
    body: Component {
      FoamyHeroBand {
        LayoutMirroring.enabled: shell.rtl
        LayoutMirroring.childrenInherit: true
        title: "Nothing here"
        FoamyAction { iconName: "search" }
        menuItems: [
          FoamyMenuItem { text: "One"; iconName: "check" },
          FoamyMenuItem { text: "Two"; iconName: "check" },
          FoamyMenuItem { text: "Three"; iconName: "check" },
          FoamyMenuItem { text: "Four"; iconName: "check" }
        ]
      }
    }
  }

  // Buttons on screen top right: kept actions, ⋯, Settings (moved actions sit
  // far outside the header).
  function visibleButtons(header) {
    var row = header.menuButton.parent
    var n = 0
    for (var i = 0; i < row.children.length; i++) {
      var item = row.children[i]
      var x = item.mapToItem(header, 0, 0).x
      if (item.visible && x >= 0 && x < header.width) n++
    }
    return n + (header.settingsButton.visible ? 1 : 0)
  }
  function names(entries) { return entries.map(function(e) { return e.separator ? "-" : e.text }) }

  Timer {
    interval: 900; running: true
    onTriggered: {
      Style.cornerRadius = 6
      // The live panel has the keyboard while open; the harness's 4.0 stand-in
      // window isn't activated by itself.
      var w = popup.cardItem.Window.window
      if (w && !w.active) w.requestActivate()
      step1.start()
    }
  }

  Timer {
    id: step1
    interval: 500
    onTriggered: {
      var body = popup.bodyItem
      var nc = body.nc
      var header = nc.titleRow
      // --- overflow rule ---------------------------------------------------------
      check(nc.overflowing && nc.settingsInMenu, "NC band overflows and Settings moves into the menu")
      eq(header.shownTrailing.map(function(a) { return a.objectName }), ["search", "clear"], "first two actions stay")
      eq(header.overflowTrailing.map(function(a) { return a.objectName }), ["refresh"], "the least important action moves")
      check(!nc.settingsButton.visible && nc.menuButton.visible, "⋯ shown, settings button hidden")
      eq(visibleButtons(header), 3, "three buttons top right")
      var mx = nc.menuButton.mapToItem(nc, 0, 0).x
      var outer = true
      for (var i = 0; i < header.shownTrailing.length; i++) {
        var ax = header.shownTrailing[i].mapToItem(nc, 0, 0).x
        if (shell.rtl ? ax < mx : ax > mx) outer = false
      }
      check(outer, "⋯ is the last button of the row")
      check(header.shownTrailing[0].mapToItem(nc, 0, 0).x < header.shownTrailing[1].mapToItem(nc, 0, 0).x !== shell.rtl,
            "actions keep their order in reading direction")
      eq(names(nc.menu.entries), ["Refresh", "Silence notifications", "Snooze notifications", "-", "Settings"], "menu entries")
      check(!body.pair.showsMenuButton && body.pair.settingsButton.visible && visibleButtons(body.pair) === 3, "two actions + Settings: no ⋯")
      check(body.withMenu.showsMenuButton && !body.withMenu.overflowing && body.withMenu.settingsButton.visible
            && visibleButtons(body.withMenu) === 3, "one action + menu items + Settings: ⋯ beside Settings")
      eq(names(body.withMenu.menu.entries), ["Open"], "menu of a non-overflowing header has only its items")
      check(!body.noSettings.showsMenuButton && visibleButtons(body.noSettings) === 3, "three actions, no Settings: no ⋯")
      // RTL: the buttons sit on the left.
      var bx = nc.menuButton.mapToItem(nc, 0, 0).x
      if (shell.rtl) check(bx < nc.width / 2, "RTL: ⋯ on the left " + bx)
      else check(bx > nc.width / 2, "LTR: ⋯ on the right " + bx)
      // A hidden action frees its slot: the next one comes back.
      shell.showSearch = false
      step2.start()
    }
  }

  Timer {
    id: step2
    interval: 200
    onTriggered: {
      var nc = popup.bodyItem.nc
      eq(nc.shownTrailing.map(function(a) { return a.objectName }), ["clear", "refresh"], "hidden action frees its slot")
      eq(names(nc.menu.entries), ["Silence notifications", "Snooze notifications", "-", "Settings"], "menu after the change")
      shell.showSearch = true
      step3.start()
    }
  }

  Timer {
    id: step3
    interval: 200
    onTriggered: {
      var body = popup.bodyItem
      var nc = body.nc
      var search = nc.shownTrailing[0]
      eq(search ? search.objectName : "", "search", "shown again")
      check(search && search.visible && search.parent === nc.menuButton.parent && search.width > 0
            && search.mapToItem(nc, 0, 0).x !== nc.shownTrailing[1].mapToItem(nc, 0, 0).x,
            "a re-shown action is laid out in the row " + (search ? [search.parent, search.visible, search.x, nc.shownTrailing[1].x] : ""))
      step3b.start()
    }
  }

  // The re-shown action is drawn (software renderer: shown + reparented in
  // one frame used to drop it).
  Timer {
    id: step3b
    interval: 100
    onTriggered: {
      var nc = popup.bodyItem.nc
      var search = nc.shownTrailing[0]
      search.grabToImage(function(result) {
        result.saveToFile(Quickshell.env("FOAMY_OUT") + "/check-search.png")
        console.log("FOAMY PNGCHECK check-search.png")
        step3c.start()
      })
    }
  }

  Timer {
    id: step3c
    interval: 50
    onTriggered: {
      var body = popup.bodyItem
      var nc = body.nc
      body.catcher.forceActiveFocus()
      nc.openMenu(true)
      var card = popup.cardItem
      var menu = nc.menu
      check(menu.opened && nc.menuOpen, "menu opens")
      check(menu.overlayItem.parent === card, "the menu lives in the popup card")
      check(menu.currentIndex === 0, "keyboard open selects the first entry " + menu.currentIndex)
      var p = menu.panel.mapToItem(card, 0, 0)
      var b = nc.menuButton.mapToItem(card, 0, 0)
      check(p.x >= 0 && p.y >= 0 && p.x + menu.panel.width <= card.width && p.y + menu.panel.height <= card.height,
            "panel inside the card " + JSON.stringify([p.x, p.y, menu.panel.width, menu.panel.height, card.width, card.height]))
      if (shell.rtl) check(near(p.x, b.x), "RTL: panel's left edge on the button's left edge " + p.x + " vs " + b.x)
      else check(near(p.x + menu.panel.width, b.x + nc.menuButton.width), "LTR: panel's right edge on the button's right edge "
                 + (p.x + menu.panel.width) + " vs " + (b.x + nc.menuButton.width))
      check(p.y >= b.y + nc.menuButton.height && p.y <= b.y + nc.menuButton.height + FoamyStyle.gap, "panel drops from the button " + p.y)
      check(near(menu.panel.height, menu.overlayItem.naturalHeight), "panel fits its entries")
      check(menu.overlayItem.activeFocus || menu.overlayItem.focus, "menu has the keys")
      // Keys: Down, disabled entries skipped, separators skipped.
      shell.silenceEnabled = false
      ev.keyClick(Qt.Key_Down, Qt.NoModifier, -1)
      eq(menu.currentIndex, 2, "Down skips the disabled entry")
      ev.keyClick(Qt.Key_Down, Qt.NoModifier, -1)
      eq(menu.currentIndex, 4, "Down skips the separator")
      ev.keyClick(Qt.Key_Down, Qt.NoModifier, -1)
      eq(menu.currentIndex, 4, "Down stops at the end")
      ev.keyClick(Qt.Key_Up, Qt.NoModifier, -1)
      eq(menu.currentIndex, 2, "Up")
      // Submenu: Right (Left in RTL) opens it in place with a Back entry.
      ev.keyClick(shell.rtl ? Qt.Key_Left : Qt.Key_Right, Qt.NoModifier, -1)
      check(menu.inSubmenu, "forward arrow opens the submenu")
      eq(names(menu.entries), ["Snooze notifications", "30 minutes", "1 hour"], "submenu entries with a Back row")
      eq(menu.currentIndex, 1, "submenu selects its first item")
      ev.keyClick(Qt.Key_Escape, Qt.NoModifier, -1)
      check(menu.opened && !menu.inSubmenu && menu.currentIndex === 2, "Esc leaves the submenu, cursor back on its entry")
      ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
      ev.keyClick(Qt.Key_Down, Qt.NoModifier, -1)
      ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
      check(!menu.opened && shell.snoozed === 60, "Enter triggers a submenu item and closes " + shell.snoozed)
      check(body.catcher.activeFocus, "focus returns to the panel")
      shell.silenceEnabled = true
      // Overflowed action and Settings keep working from the menu.
      nc.openMenu(true)
      ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
      eq(shell.refreshClicks, 1, "moved action runs its clicked()")
      nc.openMenu(true)
      ev.keyClick(Qt.Key_End, Qt.NoModifier, -1)
      ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
      eq(shell.settingsClicks, 1, "Settings entry emits settingsClicked")
      nc.openMenu(true)
      ev.keyClick(Qt.Key_Escape, Qt.NoModifier, -1)
      check(!menu.opened, "Esc closes")
      // Pointer: open from a click selects nothing; hover moves the one cursor.
      ev.mouseClick(nc.menuButton, nc.menuButton.width / 2, nc.menuButton.height / 2, Qt.LeftButton, Qt.NoModifier, -1)
      check(menu.opened && menu.currentIndex === -1, "click opens without a highlight")
      menu.hover(2)
      step4.start()
    }
  }

  Timer {
    id: step4
    interval: 300
    onTriggered: {
      var body = popup.bodyItem
      var nc = body.nc
      var menu = nc.menu
      var card = popup.cardItem
      // Capture the open menu for screenshots (Snooze under the pointer).
      card.grabToImage(function(result) {
        result.saveToFile(Quickshell.env("FOAMY_OUT") + "/menu.png")
        // A press outside the menu closes it and doesn't reach the row below.
        var presses = body.rowBelow.children[0].presses
        ev.mouseClick(body.rowBelow, 10, body.rowBelow.height - 10, Qt.LeftButton, Qt.NoModifier, -1)
        check(!menu.opened, "press outside closes")
        eq(body.rowBelow.children[0].presses, presses, "the press doesn't reach what is under the menu")
        // A click on ⋯ while open closes it (toggle).
        nc.openMenu(false)
        ev.mouseClick(nc.menuButton, nc.menuButton.width / 2, nc.menuButton.height / 2, Qt.LeftButton, Qt.NoModifier, -1)
        check(!menu.opened, "⋯ toggles the menu closed")
        // Closing the popup body (hidden header) closes the menu.
        nc.openMenu(true)
        nc.visible = false
        check(!menu.opened, "hiding the header closes the menu")
        nc.visible = true
        // Short card: grows for the menu, shrinks after.
        shell.shortBefore = shortPopup.cardItem.height
        shortPopup.bodyItem.openMenu(true)
        step5.start()
      })
    }
  }

  property real shortBefore: 0
  Timer {
    id: step5
    interval: 600
    onTriggered: {
      var band = shortPopup.bodyItem
      var menu = band.menu
      var card = shortPopup.cardItem
      check(card.height > shell.shortBefore + 40, "a short card grows for the menu " + shell.shortBefore + " -> " + card.height)
      check(near(menu.panel.height, menu.overlayItem.naturalHeight), "the menu fits without scrolling " + menu.panel.height + " / " + menu.overlayItem.naturalHeight)
      var p = menu.panel.mapToItem(card, 0, 0)
      check(p.y + menu.panel.height <= card.height, "and stays inside the card")
      card.grabToImage(function(result) {
        result.saveToFile(Quickshell.env("FOAMY_OUT") + "/menu-short.png")
        band.closeMenu()
        step6.start()
      })
    }
  }
  Timer {
    id: step6
    interval: 600
    onTriggered: {
      check(near(shortPopup.cardItem.height, shell.shortBefore), "the card shrinks back after " + shortPopup.cardItem.height)
      {
        console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
        console.log("FOAMY DONE")
        Qt.quit()
      }
    }
  }
}
