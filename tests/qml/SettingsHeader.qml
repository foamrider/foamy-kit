import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Commons as Commons
import "harness"
import "plugin/kit"

// kit 0.16.0: the compact band's title action (FoamySettingsHeader's
// titleAction through FoamyHeroBand) in a real FoamyPopup, and a wide
// FoamySettingsPage's column (columnWidth).
// - Off (the default): no title control, Tab goes from Back to the trailing
//   action; with the action's other properties set while off the band
//   draws the same pixels (band-off.png, band-off-set.png).
// - On: its mark, title and chevron; a click, Enter and Space emit
//   compactTitleActivated(keyboard) with false, true, true; Tab from Back
//   reaches it first, with the hover fill and the accent ring; role Button
//   and its accessible name; a menu anchored to compactTitleMenuAnchor
//   hangs under it from its start; Esc gives the keys back to it; a long
//   title elides within the room left, with a tooltip on hover no wider
//   than the header.
// - The column: on a wide page Back and the title, the error line and its
//   Retry, and the sections keep to the centred column while the band runs
//   to the page's edges; a page of the settings width keeps its padding.
// FOAMY_RTL=1 mirrors the bands (a settings page mirrors with the language).
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
  function near(a, b) {
    return Math.abs(a - b) <= 1.01
  }
  function box(item, to) {
    var p = item.mapToItem(to, 0, 0)
    return {
      left: p.x,
      right: p.x + item.width,
      top: p.y,
      bottom: p.y + item.height
    }
  }
  function find(item, name) {
    if (!item)
      return null
    if (item.objectName === name)
      return item
    // data: a tooltip (a Popup) is not among the children.
    var kids = item.data || item.children || []
    for (var i = 0; i < kids.length; i++) {
      var found = find(kids[i], name)
      if (found)
        return found
    }
    return null
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

  // Each compactTitleActivated: its `keyboard` argument.
  property var activations: []
  readonly property string place: "Work › Review"
  readonly property string longPlace: "A project with a long name › And a section with an even longer name that cannot fit"

  FoamyPopup {
    id: popup
    anchorItem: sim.anchor
    bar: bar
    open: true
    body: Component {
      FocusScope {
        id: bodyRoot
        property alias offBand: offBand
        property alias offSetBand: offSetBand
        property alias offOpen: offOpen
        property alias actionBand: actionBand
        property alias actionOpen: actionOpen
        property alias longBand: longBand
        property alias menu: placeMenu
        property alias ev: bodyEvent
        // Takes the keys from the bands (the body, a FocusScope, would give
        // them back to its focused child).
        property alias catcher: catcher
        FocusScope {
          id: catcher
          width: 1
          height: 1
        }
        TestEvent {
          id: bodyEvent
        }
        implicitHeight: column.implicitHeight
        LayoutMirroring.enabled: shell.rtl
        LayoutMirroring.childrenInherit: true
        Column {
          id: column
          width: parent.width
          // Off: an editor page's band as every plugin has it.
          FoamyHeroBand {
            id: offBand
            compact: true
            width: parent.width
            compactTitle: shell.place
            compactTrailing: [
              FoamyAction {
                id: offOpen
                focusable: true
                iconName: "external-link"
                tooltipText: "Open"
              }
            ]
          }
          // Off, the action's other properties set: nothing changes.
          FoamyHeroBand {
            id: offSetBand
            compact: true
            width: parent.width
            compactTitle: shell.place
            compactTitleIconName: "hash"
            compactTitleIconColor: "red"
            compactTitleAccessibleName: "Project: " + shell.place
            compactTrailing: [
              FoamyAction {
                focusable: true
                iconName: "external-link"
                tooltipText: "Open"
              }
            ]
          }
          FoamyHeroBand {
            id: actionBand
            compact: true
            width: parent.width
            compactTitle: shell.place
            compactTitleAction: true
            compactTitleIconName: "hash"
            compactTitleAccessibleName: "Project: " + shell.place
            onCompactTitleActivated: function (keyboard) {
              shell.activations = shell.activations.concat([keyboard])
            }
            compactTrailing: [
              FoamyAction {
                id: actionOpen
                focusable: true
                iconName: "external-link"
                tooltipText: "Open"
              }
            ]
          }
          FoamyHeroBand {
            id: longBand
            compact: true
            width: parent.width
            compactTitle: shell.longPlace
            compactTitleAction: true
            saving: true
            compactTrailing: [
              FoamyAction {
                focusable: true
                iconName: "external-link"
                tooltipText: "Open"
              }
            ]
          }
          // Room for the menu below the bands.
          Item {
            width: parent.width
            height: FoamyStyle.rowHeight * 6
          }
        }
        FoamyMenu {
          id: placeMenu
          anchorItem: actionBand.compactTitleMenuAnchor
          FoamyMenuItem {
            text: "Inbox"
            iconName: "hash"
          }
          FoamyMenuItem {
            text: "Work"
            iconName: "hash"
            checked: true
          }
        }
      }
    }
  }

  // A wide page (a Wide popup's 880) with a settings-wide column, and one
  // of the settings width with the default column; both with an error and
  // Retry.
  FloatingWindow {
    id: pages
    implicitWidth: 1400
    implicitHeight: 500
    color: "black"
    Item {
      anchors.fill: parent
      LayoutMirroring.enabled: shell.rtl
      LayoutMirroring.childrenInherit: true
      FoamySettingsPage {
        id: widePage
        width: 880
        height: 400
        columnWidth: 400
        error: "Couldn't save the setting."
        retryable: true
        FoamySettingsSection {
          id: wideSection
          width: parent.width
          title: "Panel"
          FoamyToggle {
            width: parent.width
            label: "A toggle"
          }
        }
      }
      FoamySettingsPage {
        id: narrowPage
        x: 900
        width: 420
        height: 400
        error: "Couldn't save the setting."
        retryable: true
        FoamySettingsSection {
          id: narrowSection
          width: parent.width
          title: "Panel"
          FoamyToggle {
            width: parent.width
            label: "A toggle"
          }
        }
      }
    }
  }

  readonly property var body: popup.bodyItem
  readonly property var ev: body ? body.ev : null

  // The start and end of an item along the reading direction, from the
  // page's start edge.
  // (A settings page mirrors with the language, FoamyI18n.rightToLeft,
  // not with FOAMY_RTL.)
  function span(item, page) {
    var b = box(item, page)
    return page.LayoutMirroring.enabled ? {
      start: page.width - b.right,
      end: page.width - b.left
    } : {
      start: b.left,
      end: b.right
    }
  }

  function grab(item, name, then) {
    item.grabToImage(function (result) {
      result.saveToFile(Quickshell.env("FOAMY_OUT") + "/" + name + ".png")
      then()
    })
  }

  function finish() {
    console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
    console.log("FOAMY DONE")
    Qt.quit()
  }

  Timer {
    interval: 900
    running: true
    onTriggered: {
      Style.cornerRadius = 6
      var w = popup.cardItem.Window.window
      if (w && !w.active)
        w.requestActivate()
      wait.waitFor(function () {
        return shell.body && shell.body.width > 0 && shell.body.actionBand.height > 0
      }, 5000, function (ok) {
        shell.check(ok, "the popup is laid out")
        shell.offChecks()
      })
    }
  }

  // --- off -----------------------------------------------------------------------
  function offChecks() {
    var band = body.offBand
    check(!band.compactTitleButton.visible && !band.compactTitleMenuAnchor.visible, "off: no title control")
    band.backButton.forceActiveFocus()
    ev.keyClick(Qt.Key_Tab, Qt.NoModifier, -1)
    check(body.offOpen.activeFocus, "off: Tab goes from Back to the trailing action")
    ev.keyClick(Qt.Key_Backtab, Qt.ShiftModifier, -1)
    check(band.backButton.activeFocus, "off: Shift+Tab back to Back")
    // Nothing has the keys while the bands are grabbed.
    body.catcher.forceActiveFocus()
    wait.after(100, function () {
      shell.grab(body.offBand, "band-off", function () {
        shell.grab(body.offSetBand, "band-off-set", shell.onChecks)
      })
    })
  }

  // --- on ------------------------------------------------------------------------
  function onChecks() {
    var band = body.actionBand
    var button = band.compactTitleButton
    var text = find(button, "foamyTitleActionText")
    check(button.visible && text && text.text === place && !text.truncated, "on: the title in the control, whole")
    check(button.Accessible.role === Accessible.Button && button.Accessible.name === "Project: " + place, "on: role Button, named " + button.Accessible.name)
    // Mark, title, chevron in reading order.
    var icons = []
    for (var i = 0; i < text.parent.children.length; i++) {
      var child = text.parent.children[i]
      if (child.visible)
        icons.push(child === text ? "text" : child.name)
    }
    check(JSON.stringify(icons) === JSON.stringify(["hash", "text", "chevron-down"]), "on: mark, title, chevron " + JSON.stringify(icons))
    var bb = span(band.backButton, band)
    var tb = span(button, band)
    check(tb.start > bb.end && tb.start - bb.end <= FoamyStyle.gap + 1, "on: the control follows Back " + JSON.stringify([bb, tb]))
    // Tab: Back, the control, the trailing action.
    band.backButton.forceActiveFocus()
    ev.keyClick(Qt.Key_Tab, Qt.NoModifier, -1)
    check(button.activeFocus, "on: Tab from Back reaches the control")
    check(button.border.width === 1 && Qt.colorEqual(button.border.color, Commons.Color.accent), "on: the keys' ring")
    wait.waitFor(function () {
      return Qt.colorEqual(button.color, FoamyPalette.hoverFill)
    }, 2000, function (ok) {
      shell.check(ok, "on: the keys' fill " + button.color)
      shell.ev.keyClick(Qt.Key_Tab, Qt.NoModifier, -1)
      shell.check(shell.body.actionOpen.activeFocus && button.border.width === 0, "on: Tab goes on to the trailing action")
      shell.ev.keyClick(Qt.Key_Backtab, Qt.ShiftModifier, -1)
      shell.check(button.activeFocus, "on: Shift+Tab back to the control")
      shell.keyChecks()
    })
  }

  function keyChecks() {
    var band = body.actionBand
    var button = band.compactTitleButton
    activations = []
    ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
    ev.keyClick(Qt.Key_Enter, Qt.KeypadModifier, -1)
    ev.keyClick(Qt.Key_Space, Qt.NoModifier, -1)
    check(JSON.stringify(activations) === JSON.stringify([true, true, true]), "on: Return, Enter and Space activate from the keys " + JSON.stringify(activations))
    ev.keyClick(Qt.Key_A, Qt.NoModifier, -1)
    check(activations.length === 3, "on: another key does nothing")
    button.Accessible.pressAction()
    check(JSON.stringify(activations.slice(3)) === JSON.stringify([false]), "on: the accessible press activates " + JSON.stringify(activations))
    // A click: from the pointer; the pointer over it lights it.
    activations = []
    body.catcher.forceActiveFocus()
    ev.mouseMove(button, button.width / 2, button.height / 2, -1, Qt.NoButton, Qt.NoModifier)
    wait.waitFor(function () {
      return Qt.colorEqual(button.color, FoamyPalette.hoverFill)
    }, 2000, function (ok) {
      shell.check(ok && button.border.width === 0, "on: hover fill, no ring without the keys " + button.color)
      shell.ev.mouseClick(button, button.width / 2, button.height / 2, Qt.LeftButton, Qt.NoModifier, -1)
      shell.check(JSON.stringify(shell.activations) === JSON.stringify([false]), "on: a click activates from the pointer " + JSON.stringify(shell.activations))
      shell.ev.mouseMove(shell.body, 2, shell.body.height - 2, -1, Qt.NoButton, Qt.NoModifier)
      shell.menuChecks()
    })
  }

  function menuChecks() {
    var band = body.actionBand
    var button = band.compactTitleButton
    var menu = body.menu
    var card = popup.cardItem
    button.forceActiveFocus()
    menu.open(true)
    wait.waitFor(function () {
      return menu.opened && menu.panel.width > 0
    }, 2000, function (ok) {
      shell.check(ok, "the menu opens")
      var m = shell.box(menu.panel, card)
      var b = shell.box(button, card)
      // It hangs under the control from its start.
      var start = shell.rtl ? shell.near(m.right, b.right) : shell.near(m.left, b.left)
      shell.check(start && m.top >= b.bottom && m.top - b.bottom <= FoamyStyle.gapSmall + 1, "the menu hangs under the control from its start " + JSON.stringify([m, b]))
      shell.ev.keyClick(Qt.Key_Escape, Qt.NoModifier, -1)
      shell.check(!menu.opened && button.activeFocus, "Esc closes the menu and gives the keys back to the control")
      // Turned off while it has the keys (an editor's task went): the
      // control hidden; on again, a Tab stop again. (test_settings_header.py
      // fails on Qt's warning if the Tab stop is bound to the option.)
      band.compactTitleAction = false
      shell.check(!button.visible && shell.find(band, "foamyTitleActionText") !== null, "off while it had the keys: hidden")
      band.compactTitleAction = true
      band.backButton.forceActiveFocus()
      shell.ev.keyClick(Qt.Key_Tab, Qt.NoModifier, -1)
      shell.check(button.activeFocus, "on again: Tab from Back reaches it")
      shell.elideChecks()
    })
  }

  function elideChecks() {
    var band = body.longBand
    var button = band.compactTitleButton
    var text = find(button, "foamyTitleActionText")
    var slot = button.parent
    var trailing = band.compactTrailing[0]
    check(text.truncated && near(button.width, slot.width) && button.width < button.implicitWidth, "a long title elides in the room left " + JSON.stringify([button.width, slot.width, button.implicitWidth]))
    // "Saving…" and the trailing action stay in the band.
    var t = span(trailing, band)
    var s = span(button, band)
    check(trailing.visible && t.end <= band.width - FoamyStyle.padding + 1 && s.end < t.start, "the trailing action stays " + JSON.stringify([s, t]))
    var tip = find(button, "foamyTitleActionTip")
    ev.mouseMove(button, button.width / 2, button.height / 2, -1, Qt.NoButton, Qt.NoModifier)
    wait.waitFor(function () {
      return tip.visible
    }, 3000, function (ok) {
      shell.check(ok && tip.text === shell.longPlace, "the whole title in a tooltip on hover")
      shell.check(tip.implicitWidth <= band.width + 0.5 && tip.contentItem.wrapMode === Text.WrapAtWordBoundaryOrAnywhere, "the tooltip at most the header's width, wrapped " + JSON.stringify([tip.implicitWidth, band.width]))
      // A title that fits: no tooltip.
      var short = shell.body.actionBand.compactTitleButton
      shell.ev.mouseMove(short, short.width / 2, short.height / 2, -1, Qt.NoButton, Qt.NoModifier)
      wait.after(300, function () {
        shell.check(!shell.find(short, "foamyTitleActionTip").visible, "no tooltip for a title that fits")
        shell.ev.mouseMove(shell.body, 2, shell.body.height - 2, -1, Qt.NoButton, Qt.NoModifier)
        shell.columnChecks()
      })
    })
  }

  // --- the column ----------------------------------------------------------------
  // The shown Text item under `item` that says `text`.
  function shownText(item, text) {
    if (item.text === text && item.visible && item.font !== undefined)
      return item
    for (var i = 0; i < item.children.length; i++) {
      var found = shownText(item.children[i], text)
      if (found)
        return found
    }
    return null
  }
  function columnChecks() {
    var inset = (widePage.width - widePage.columnWidth) / 2
    var band = find(widePage, "foamyHeroBandSurface").parent
    var back = widePage.backTarget
    var title = shownText(band, widePage.title)
    var errorText = find(widePage, "settingsErrorText")
    var retry = errorText.parent.children[1]
    var b = span(band, widePage)
    check(near(b.start, 0) && near(b.end, widePage.width), "wide: the band runs to the page's edges " + JSON.stringify(b))
    check(near(span(back, widePage).start, inset), "wide: Back starts at the column's edge " + JSON.stringify([span(back, widePage), inset]))
    check(title && span(title, widePage).end <= widePage.width - inset + 1, "wide: the title ends in the column")
    var e = span(errorText, widePage)
    var r = span(retry, widePage)
    check(errorText.visible && near(e.start, inset), "wide: the error starts at the column's edge " + JSON.stringify([e, inset]))
    check(retry.visible && near(r.end, widePage.width - inset), "wide: Retry ends at the column's edge " + JSON.stringify([r, widePage.width - inset]))
    var w = span(wideSection, widePage)
    check(near(w.start, inset) && near(w.end, widePage.width - inset), "wide: the section fills the column " + JSON.stringify(w))
    // A settings-width page: the padding, as before.
    var pad = FoamyStyle.padding
    var nb = narrowPage.backTarget
    var ne = find(narrowPage, "settingsErrorText")
    var nr = ne.parent.children[1]
    check(near(narrowPage.columnInset, pad) && near(span(nb, narrowPage).start, pad) && near(span(ne, narrowPage).start, pad) && near(span(nr, narrowPage).end, narrowPage.width - pad), "narrow: Back, the error and Retry at the padding")
    var ns = span(narrowSection, narrowPage)
    check(near(ns.start, pad) && near(ns.end, narrowPage.width - pad), "narrow: the section at the padding " + JSON.stringify(ns))
    // A column wider than the page: the padding, never less.
    widePage.columnWidth = 2000
    wait.waitFor(function () {
      return shell.near(shell.span(wideSection, widePage).start, pad)
    }, 2000, function (ok) {
      shell.check(ok && shell.near(widePage.columnInset, pad), "a column wider than the page keeps the padding")
      widePage.columnWidth = 400
      wait.after(100, function () {
        shell.grab(widePage, "wide-page", shell.finish)
      })
    })
  }
}
