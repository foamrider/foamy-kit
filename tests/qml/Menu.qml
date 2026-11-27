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
// keyboard navigation, submenus, Esc, press outside, focus restore; a menu
// taller than its room keeps the keyboard's entry in view (the least
// scroll), while the wheel and hover leave the scroll and the entry alone.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property bool rtl: Quickshell.env("FOAMY_RTL") === "1"
  readonly property string tag: host + "/" + (rtl ? "rtl" : "ltr") + "@" + Quickshell.env("FOAMY_SCALE")
  property int checks: 0
  property int failures: 0
  function check(ok, label) {
    checks++
    if (!ok) {
      failures++
      console.log("FOAMY FAIL " + tag + " " + label)
    }
  }
  function eq(actual, expected, label) {
    check(JSON.stringify(actual) === JSON.stringify(expected), label + ": got " + JSON.stringify(actual) + ", expected " + JSON.stringify(expected))
  }
  function near(a, b) {
    return Math.abs(a - b) <= 1.01
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

  property int searchClicks: 0
  property int clearClicks: 0
  property int refreshClicks: 0
  property int settingsClicks: 0
  property int snoozed: 0
  property bool silenceEnabled: true
  property bool showSearch: true

  FoamyPopup {
    id: popup
    anchorItem: sim.anchor
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
        property alias longMenu: longMenu
        property alias longButton: longButton
        property alias rowMenu: rowMenu
        // Synthetic keys and clicks go to the window the card is in.
        property alias ev: bodyEvent
        TestEvent {
          id: bodyEvent
        }
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
              FoamyAction {
                objectName: "search"
                visible: shell.showSearch
                iconName: "search"
                tooltipText: "Search"
                onClicked: shell.searchClicks++
              },
              FoamyAction {
                objectName: "clear"
                iconName: "trash"
                destructive: true
                tooltipText: "Clear all"
                onClicked: shell.clearClicks++
              },
              FoamyAction {
                objectName: "refresh"
                iconName: "refresh-cw"
                tooltipText: "Refresh"
                onClicked: shell.refreshClicks++
              }
            ]
            menuItems: [
              FoamyMenuItem {
                objectName: "silence"
                text: "Silence notifications"
                iconName: "bell-off"
                enabled: shell.silenceEnabled
              },
              FoamyMenuItem {
                objectName: "snooze"
                text: "Snooze notifications"
                iconName: "alarm-clock"
                FoamyMenuItem {
                  text: "30 minutes"
                  iconName: "clock"
                  onTriggered: shell.snoozed = 30
                }
                FoamyMenuItem {
                  text: "1 hour"
                  iconName: "clock"
                  onTriggered: shell.snoozed = 60
                }
              }
            ]
            Text {
              text: "3"
              color: FoamyPalette.text
              font.pixelSize: FoamyStyle.font.numeralCompact
            }
          }
          // Room under the band so the menu drops inside the card.
          Rectangle {
            id: rowBelow
            width: parent.width
            height: 220
            color: "transparent"
            MouseArea {
              anchors.fill: parent
              hoverEnabled: true
              property int presses: 0
              onPressed: presses++
            }
          }
          FoamyHeader {
            id: pair
            width: parent.width
            title: "Pair"
            FoamyAction {
              iconName: "volume-2"
            }
            FoamyAction {
              iconName: "mic"
            }
          }
          FoamyHeader {
            id: withMenu
            width: parent.width
            title: "With menu"
            FoamyAction {
              iconName: "refresh-cw"
            }
            menuItems: [
              FoamyMenuItem {
                text: "Open"
                iconName: "external-link"
              }
            ]
          }
          FoamyHeader {
            id: noSettings
            width: parent.width
            title: "No settings"
            showSettings: false
            FoamyAction {
              iconName: "play"
            }
            FoamyAction {
              iconName: "globe"
            }
            FoamyAction {
              iconName: "download"
            }
          }
          FocusScope {
            id: catcher
            width: 10
            height: 10
            focus: true
          }
          // A row's ⋯ inside a cursor surface, which is a bordered surface
          // of its own: its menu still belongs to the card.
          FoamyCursorSurface {
            width: parent.width
            height: 40
            FoamyAction {
              id: rowButton
              anchors.right: parent.right
              iconName: "ellipsis"
            }
          }
          // A fixed room, shorter than the long menu: the menu scrolls.
          Item {
            id: longHost
            width: parent.width
            height: 220
            FoamyAction {
              id: longButton
              anchors.right: parent.right
              iconName: "ellipsis"
            }
          }
        }
        FoamyMenu {
          id: rowMenu
          anchorItem: rowButton
          FoamyMenuItem {
            text: "Row entry"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "The current choice"
            iconName: "check"
            checked: true
          }
          FoamyMenuItem {
            text: "Pick one"
            iconName: "check"
            FoamyMenuItem {
              objectName: "subFirst"
              text: "First"
              iconName: "check"
            }
            FoamyMenuItem {
              text: "Second"
              iconName: "check"
              checked: true
            }
          }
        }
        FoamyMenu {
          id: longMenu
          anchorItem: longButton
          host: longHost
          FoamyMenuItem {
            text: "Entry 1"
            iconName: "check"
          }
          FoamyMenuItem {
            separator: true
          }
          FoamyMenuItem {
            text: "Entry 2"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "Entry 3"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "Entry 4"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "Entry 5"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "Entry 6"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "Entry 7"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "Entry 8"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "Entry 9"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "Entry 10"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "Entry 11"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "Entry 12"
            iconName: "check"
          }
        }
      }
    }
  }

  readonly property var ev: popup.bodyItem ? popup.bodyItem.ev : null

  // A short popup (band only): the card grows while the menu is open.
  FoamyPopup {
    id: shortPopup
    anchorItem: sim.anchor
    bar: bar
    open: true
    centerOnBar: true
    body: Component {
      FoamyHeroBand {
        LayoutMirroring.enabled: shell.rtl
        LayoutMirroring.childrenInherit: true
        title: "Nothing here"
        FoamyAction {
          iconName: "search"
        }
        menuItems: [
          FoamyMenuItem {
            text: "One"
            iconName: "check"
          },
          FoamyMenuItem {
            text: "Two"
            iconName: "check"
          },
          FoamyMenuItem {
            text: "Three"
            iconName: "check"
          },
          FoamyMenuItem {
            text: "Four"
            iconName: "check"
          },
          FoamyMenuItem {
            text: "More"
            iconName: "check"
            FoamyMenuItem {
              text: "Only"
              iconName: "check"
            }
          }
        ]
      }
    }
  }

  // A button low in its card, with room above for its menu but not below:
  // the menu opens above and the card keeps its height.
  FoamyPopup {
    id: lowPopup
    anchorItem: sim.anchor
    bar: bar
    open: false
    centerOnBar: true
    body: Component {
      Column {
        property alias menu: lowMenu
        width: FoamyStyle.popupWidth
        Item {
          width: parent.width
          height: FoamyStyle.rowHeight * 12
        }
        FoamyAction {
          id: lowButton
          iconName: "ellipsis"
        }
        FoamyMenu {
          id: lowMenu
          anchorItem: lowButton
          FoamyMenuItem {
            text: "One"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "Two"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "Three"
            iconName: "check"
          }
          FoamyMenuItem {
            text: "Four"
            iconName: "check"
          }
        }
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
      if (item.visible && x >= 0 && x < header.width)
        n++
    }
    return n + (header.settingsButton.visible ? 1 : 0)
  }
  function names(entries) {
    return entries.map(function (e) {
      return e.separator ? "-" : e.text
    })
  }

  Timer {
    interval: 900
    running: true
    onTriggered: {
      Style.cornerRadius = 6
      // The live panel has the keyboard while open; the harness's offscreen
      // stand-in window isn't activated by itself.
      var w = popup.cardItem.Window.window
      if (w && !w.active)
        w.requestActivate()
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
      eq(header.shownTrailing.map(function (a) {
        return a.objectName
      }), ["search", "clear"], "first two actions stay")
      eq(header.overflowTrailing.map(function (a) {
        return a.objectName
      }), ["refresh"], "the least important action moves")
      check(!nc.settingsButton.visible && nc.menuButton.visible, "⋯ shown, settings button hidden")
      eq(visibleButtons(header), 3, "three buttons top right")
      var mx = nc.menuButton.mapToItem(nc, 0, 0).x
      var outer = true
      for (var i = 0; i < header.shownTrailing.length; i++) {
        var ax = header.shownTrailing[i].mapToItem(nc, 0, 0).x
        if (shell.rtl ? ax < mx : ax > mx)
          outer = false
      }
      check(outer, "⋯ is the last button of the row")
      check(header.shownTrailing[0].mapToItem(nc, 0, 0).x < header.shownTrailing[1].mapToItem(nc, 0, 0).x !== shell.rtl, "actions keep their order in reading direction")
      eq(names(nc.menu.entries), ["Refresh", "Silence notifications", "Snooze notifications", "-", "Settings"], "menu entries")
      check(!body.pair.showsMenuButton && body.pair.settingsButton.visible && visibleButtons(body.pair) === 3, "two actions + Settings: no ⋯")
      check(body.withMenu.showsMenuButton && !body.withMenu.overflowing && body.withMenu.settingsButton.visible && visibleButtons(body.withMenu) === 3, "one action + menu items + Settings: ⋯ beside Settings")
      eq(names(body.withMenu.menu.entries), ["Open"], "menu of a non-overflowing header has only its items")
      check(!body.noSettings.showsMenuButton && visibleButtons(body.noSettings) === 3, "three actions, no Settings: no ⋯")
      // RTL: the buttons sit on the left.
      var bx = nc.menuButton.mapToItem(nc, 0, 0).x
      if (shell.rtl)
        check(bx < nc.width / 2, "RTL: ⋯ on the left " + bx)
      else
        check(bx > nc.width / 2, "LTR: ⋯ on the right " + bx)
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
      eq(nc.shownTrailing.map(function (a) {
        return a.objectName
      }), ["clear", "refresh"], "hidden action frees its slot")
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
      check(search && search.visible && search.parent === nc.menuButton.parent && search.width > 0 && search.mapToItem(nc, 0, 0).x !== nc.shownTrailing[1].mapToItem(nc, 0, 0).x, "a re-shown action is laid out in the row " + (search ? [search.parent, search.visible, search.x, nc.shownTrailing[1].x] : ""))
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
      search.grabToImage(function (result) {
        result.saveToFile(Quickshell.env("FOAMY_OUT") + "/check-search.png")
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
      check(p.x >= 0 && p.y >= 0 && p.x + menu.panel.width <= card.width && p.y + menu.panel.height <= card.height, "panel inside the card " + JSON.stringify([p.x, p.y, menu.panel.width, menu.panel.height, card.width, card.height]))
      if (shell.rtl)
        check(near(p.x, b.x), "RTL: panel's left edge on the button's left edge " + p.x + " vs " + b.x)
      else
        check(near(p.x + menu.panel.width, b.x + nc.menuButton.width), "LTR: panel's right edge on the button's right edge " + (p.x + menu.panel.width) + " vs " + (b.x + nc.menuButton.width))
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
      // j and k move like Down and Up, Tab leaves the menu, Space activates.
      body.catcher.forceActiveFocus()
      nc.openMenu(true)
      ev.keyClick(Qt.Key_J, Qt.NoModifier, -1)
      eq(menu.currentIndex, 1, "j moves down like Down")
      ev.keyClick(Qt.Key_K, Qt.NoModifier, -1)
      eq(menu.currentIndex, 0, "k moves up like Up")
      ev.keyClick(Qt.Key_Tab, Qt.NoModifier, -1)
      eq([menu.opened, body.catcher.activeFocus], [false, true], "Tab closes the menu and gives the focus back (opened, catcher focus)")
      nc.openMenu(true)
      ev.keyClick(Qt.Key_End, Qt.NoModifier, -1)
      ev.keyClick(Qt.Key_Space, Qt.NoModifier, -1)
      eq(shell.settingsClicks, 2, "Space activates the entry like Enter")
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
      card.grabToImage(function (result) {
        result.saveToFile(Quickshell.env("FOAMY_OUT") + "/menu.png")
        // Raised: the same menu over a shadow on a clearer fill (the
        // Python side compares the two shots around the panel's box).
        menu.raised = true
        var p = menu.panel.mapToItem(card, 0, 0)
        console.log("FOAMY NOTE panel " + JSON.stringify([p.x, p.y, menu.panel.width, menu.panel.height, card.width]))
        card.grabToImage(function (raised) {
          raised.saveToFile(Quickshell.env("FOAMY_OUT") + "/menu-raised.png")
          menu.raised = false
          shell.afterRaised()
        })
      })
    }
  }
  function afterRaised() {
    var body = popup.bodyItem
    var nc = body.nc
    var menu = nc.menu
    var card = popup.cardItem
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
    // Short card: grows for the menu, shrinks after. The card's height
    // follows the menu's reserve over a few frames: wait for the end state.
    shell.shortBefore = shortPopup.cardItem.height
    var band = shortPopup.bodyItem
    var shortMenu = band.menu
    var shortCard = shortPopup.cardItem
    var grown = function () {
      return shortCard.height > shell.shortBefore + 40
    }
    var fits = function () {
      return near(shortMenu.panel.height, shortMenu.overlayItem.naturalHeight)
    }
    var inside = function () {
      return shortMenu.panel.mapToItem(shortCard, 0, 0).y + shortMenu.panel.height <= shortCard.height
    }
    band.openMenu(true)
    wait.waitFor(function () {
      return grown() && fits() && inside()
    }, 5000, function () {
      check(grown(), "a short card grows for the menu " + shell.shortBefore + " -> " + shortCard.height)
      check(fits(), "the menu fits without scrolling " + shortMenu.panel.height + " / " + shortMenu.overlayItem.naturalHeight)
      check(inside(), "and stays inside the card")
      // A shorter level (a submenu) doesn't shrink the grown card under
      // the open menu (a shrink would show within half a second).
      var grownHeight = shortCard.height
      shortMenu.activate(shortMenu.entries.length - 1)
      check(shortMenu.inSubmenu, "the short menu's submenu opened")
      wait.waitFor(function () {
        return shortCard.height < grownHeight - 1
      }, 500, function (shrank) {
        check(!shrank, "a shorter submenu keeps the grown card " + [grownHeight, shortCard.height])
        shortMenu.leaveSubmenu()
        shortCard.grabToImage(function (shot) {
          shot.saveToFile(Quickshell.env("FOAMY_OUT") + "/menu-short.png")
          band.closeMenu()
          wait.waitFor(function () {
            return near(shortCard.height, shell.shortBefore)
          }, 5000, function (ok) {
            check(ok, "the card shrinks back after " + shortCard.height)
            // Capped: the card grows by at most maxGrowHeight of menu,
            // and the rest of the menu scrolls.
            shortMenu.maxGrowHeight = FoamyStyle.rowHeight * 3
            band.openMenu(true)
            // Wait for the end state: the card grown and no longer moving.
            var lastHeight = -1
            wait.waitFor(function () {
              var settled = shortCard.height > shell.shortBefore + 10 && Math.abs(shortCard.height - lastHeight) < 0.5
              lastHeight = shortCard.height
              return settled
            }, 5000, function (grewSome) {
              check(grewSome && shortCard.height < shell.shortBefore + shortMenu.overlayItem.naturalHeight - 20 && shortMenu.panel.height < shortMenu.overlayItem.naturalHeight - 1, "a capped growth: the card grows less, the menu scrolls " + [shortCard.height, shell.shortBefore, shortMenu.panel.height, shortMenu.overlayItem.naturalHeight])
              band.closeMenu()
              shortMenu.maxGrowHeight = FoamyStyle.rowHeight * 9
              wait.waitFor(function () {
                return near(shortCard.height, shell.shortBefore)
              }, 5000, function () {
                // Room above, none below: above, and no growth.
                shortPopup.open = false
                lowPopup.open = true
                wait.waitFor(function () {
                  return lowPopup.bodyItem && lowPopup.cardItem && lowPopup.cardItem.height > FoamyStyle.rowHeight * 12
                }, 5000, function () {
                  var lowCard = lowPopup.cardItem
                  var lowBefore = lowCard.height
                  var low = lowPopup.bodyItem.menu
                  low.open(true)
                  wait.waitFor(function () {
                    return low.opened && low.panel.height > 0
                  }, 5000, function () {
                    var button = low.anchorItem.mapToItem(lowCard, 0, 0)
                    var panel = low.panel.mapToItem(lowCard, 0, 0)
                    check(near(lowCard.height, lowBefore) && panel.y + low.panel.height <= button.y + 1 && near(low.panel.height, low.overlayItem.naturalHeight), "room above: the menu opens above, the card keeps its height " + [lowBefore, lowCard.height, panel.y, low.panel.height, button.y])
                    low.close()
                    lowPopup.open = false
                    shortPopup.open = true
                    step7.start()
                  })
                })
              })
            })
          })
        })
      })
    })
  }

  property real shortBefore: 0

  // The long menu's Flickable and the shown row of entry i.
  function scrollerOf(menu) {
    for (var i = 0; i < menu.panel.children.length; i++)
      if (menu.panel.children[i].objectName === "foamyMenuScroller")
        return menu.panel.children[i]
    return null
  }
  function rowOf(menu, index) {
    var list = scrollerOf(menu).contentItem.children[0]
    for (var i = 0; i < list.children.length; i++) {
      var row = list.children[i]
      if (row.objectName === "foamyMenuRow" && row.index === index)
        return row
    }
    return null
  }
  // "" when entry i shows whole in the menu's view; else where it is.
  function shown(menu, index) {
    var view = scrollerOf(menu)
    var row = rowOf(menu, index)
    if (!row)
      return "no row " + index
    var top = row.mapToItem(view, 0, 0).y
    return top >= -0.5 && top + row.height <= view.height + 0.5 ? "" : "row " + index + " at " + top + ".." + (top + row.height) + " of " + view.height
  }
  // Entry i's bottom on the view's bottom edge: the least scroll down.
  function onBottom(menu, index) {
    var view = scrollerOf(menu)
    var row = rowOf(menu, index)
    return near(row.mapToItem(view, 0, row.height).y, view.height)
  }

  // A menu taller than its room: each keyboard move keeps its entry in
  // view, with the least scroll; the wheel and hover don't fight it.
  Timer {
    id: step7
    interval: 100
    onTriggered: {
      var body = popup.bodyItem
      body.rowMenu.open(false)
      check(body.rowMenu.opened && body.rowMenu.overlayItem.parent === popup.cardItem && body.rowMenu.panel.height > 0, "a menu anchored inside a row's surface lives in the popup card " + body.rowMenu.overlayItem.parent)
      body.rowMenu.close()
      // From the keys it starts on the current choice, so Enter keeps it.
      body.rowMenu.open(true)
      check(body.rowMenu.currentIndex === 1, "keyboard open selects the checked entry " + body.rowMenu.currentIndex)
      // A submenu too starts on its checked entry (after Back, First).
      body.rowMenu.activate(2)
      check(body.rowMenu.inSubmenu && body.rowMenu.currentIndex === 2, "a submenu starts on its checked entry " + body.rowMenu.currentIndex)
      // Two checked (a multi-select set): the first entry, not a checked one.
      body.rowMenu.leaveSubmenu()
      body.rowMenu.items[2].items[0].checked = true
      body.rowMenu.activate(2)
      check(body.rowMenu.currentIndex === 1, "two checked: the first entry " + body.rowMenu.currentIndex)
      body.rowMenu.items[2].items[0].checked = false
      body.rowMenu.close()
      var menu = body.longMenu
      body.catcher.forceActiveFocus()
      menu.open(true)
      var view = scrollerOf(menu)
      check(menu.opened && menu.panel.height + 1 < menu.overlayItem.naturalHeight && view.contentHeight > view.height + 1, "the long menu scrolls " + [menu.panel.height, menu.overlayItem.naturalHeight])
      eq([menu.currentIndex, shown(menu, 0), view.contentY], [0, "", 0], "opens on the first entry, at the top")
      var last = menu.entries.length - 1
      ev.keyClick(Qt.Key_End, Qt.NoModifier, -1)
      eq([menu.currentIndex, shown(menu, last)], [last, ""], "End: the last entry, in view")
      check(onBottom(menu, last), "End: the least scroll (the last entry on the bottom edge)")
      ev.keyClick(Qt.Key_Home, Qt.NoModifier, -1)
      eq([menu.currentIndex, shown(menu, 0), view.contentY], [0, "", 0], "Home: the first entry, back at the top")
      // Down through the menu: past the fold each entry lands on the bottom edge.
      var hidden = []
      var pushed = false
      for (var i = 0; i < last; i++) {
        var before = view.contentY
        ev.keyClick(Qt.Key_Down, Qt.NoModifier, -1)
        var where = shown(menu, menu.currentIndex)
        if (where !== "")
          hidden.push(where)
        if (view.contentY !== before && !onBottom(menu, menu.currentIndex))
          hidden.push("not the least scroll at " + menu.currentIndex)
        pushed = pushed || view.contentY > before
      }
      eq([menu.currentIndex, hidden], [last, []], "Down keeps each entry in view")
      check(pushed, "Down scrolled the menu")
      // Up from the bottom: an entry above the view lands on its top edge.
      var upHidden = []
      for (i = 0; i < last; i++) {
        var was = view.contentY
        ev.keyClick(Qt.Key_Up, Qt.NoModifier, -1)
        var at = shown(menu, menu.currentIndex)
        if (at !== "")
          upHidden.push(at)
        if (view.contentY !== was && !near(rowOf(menu, menu.currentIndex).mapToItem(view, 0, 0).y, 0))
          upHidden.push("not the least scroll at " + menu.currentIndex)
      }
      eq([menu.currentIndex, upHidden, view.contentY], [0, [], 0], "Up keeps each entry in view, back to the top")
      // The wheel scrolls without moving the entry; hover doesn't scroll back.
      ev.mouseWheel(menu.panel, menu.panel.width / 2, menu.panel.height / 2, Qt.NoButton, Qt.NoModifier, 0, -120, -1)
      step8.start()
    }
  }
  Timer {
    id: step8
    interval: 500
    onTriggered: {
      var menu = popup.bodyItem.longMenu
      var view = scrollerOf(menu)
      var scrolled = view.contentY
      check(scrolled > 1 && menu.currentIndex === 0, "the wheel scrolls, the entry stays " + [scrolled, menu.currentIndex])
      menu.hover(menu.entries.length - 1)
      eq([menu.currentIndex, view.contentY], [menu.entries.length - 1, scrolled], "hover moves the entry, not the scroll")
      // The pointer rests on the menu while End scrolls rows under it: the
      // keys' entry stays once the hover events settle.
      menu.close()
      popup.bodyItem.catcher.forceActiveFocus()
      menu.open(true)
      ev.mouseMove(menu.panel, menu.panel.width / 2, menu.panel.height / 2, -1, Qt.NoButton, Qt.NoModifier)
      check(menu.currentIndex > 0, "a moved pointer takes the highlight " + menu.currentIndex)
      ev.keyClick(Qt.Key_End, Qt.NoModifier, -1)
      step9.start()
    }
  }
  Timer {
    id: step9
    interval: 300
    onTriggered: {
      var menu = popup.bodyItem.longMenu
      var last = menu.entries.length - 1
      eq([menu.currentIndex, shown(menu, last)], [last, ""], "End under a resting pointer keeps the last entry")
      ev.mouseMove(menu.panel, menu.panel.width / 2, menu.panel.height / 2 + 2, -1, Qt.NoButton, Qt.NoModifier)
      check(menu.currentIndex !== last, "moving the pointer again takes the highlight " + menu.currentIndex)
      menu.close()
      {
        console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
        console.log("FOAMY DONE")
        Qt.quit()
      }
    }
  }
}
