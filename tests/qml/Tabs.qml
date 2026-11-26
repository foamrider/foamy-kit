import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"

// FoamyTabs in a real FoamyPopup's body, directly under the hero band, on
// the simulated screen, wired to a FoamyCursor through the stock
// PanelKeyCatcher: three content-width tabs from the reading start with
// icons and counts, the first icon on the rows' content inset, the accent
// underline under the open tab only, the hairline across the row, the urgent
// count colour, labels eliding from the last tab inward with icons and
// counts whole, a press emits activated() without assigning `value`, hover
// moves the one cursor, ←/→ (h/l) move between tabs in reading order and
// Enter/Space activate, RTL order, and the tab-list accessibility.
// FOAMY_RTL=1 mirrors, FOAMY_WIDE=1 uses the wide popup. Cards are saved to
// FOAMY_OUT.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property bool rtl: Quickshell.env("FOAMY_RTL") === "1"
  readonly property bool wide: Quickshell.env("FOAMY_WIDE") === "1"
  readonly property string tag: host + "/" + (rtl ? "rtl" : "ltr") + (wide ? "/wide" : "") + "@" + Quickshell.env("FOAMY_SCALE")
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
  function near(a, b, t) {
    return Math.abs(a - b) <= (t === undefined ? 1.01 : t)
  }
  // Within one 8-bit step per channel: Text stores its colour in 8 bits,
  // Qt.tint() results are finer.
  function sameColor(a, b) {
    var x = Qt.color(a), y = Qt.color(b)
    var step = 1 / 255 + 1e-6
    return Math.abs(x.r - y.r) <= step && Math.abs(x.g - y.g) <= step && Math.abs(x.b - y.b) <= step && Math.abs(x.a - y.a) <= step
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

  // The caller's state: the row never changes it; the handler records.
  property string view: "inbox"
  property var activations: []
  property int presetActivations: 0
  property var views: [
    {
      value: "inbox",
      text: "Inbox",
      iconName: "inbox",
      count: 12
    },
    {
      value: "today",
      text: "Today",
      iconName: "calendar-days",
      count: 3,
      countUrgent: true
    },
    {
      value: "upcoming",
      text: "Upcoming",
      iconName: "calendar",
      count: -1
    }
  ]
  // Long labels for the eliding row; its width is set from their natural sizes.
  readonly property var longViews: [
    {
      value: "a",
      text: "Everything",
      iconName: "inbox",
      count: 1234
    },
    {
      value: "b",
      text: "Overdue and urgent",
      iconName: "hash",
      count: 88,
      countUrgent: true
    },
    {
      value: "c",
      text: "Scheduled later",
      iconName: "calendar",
      count: 7
    }
  ]

  FoamyCursor {
    id: cursor
    count: 3 // the tabs, then two rows
  }

  FoamyPopup {
    id: popup
    anchorItem: sim.anchor
    bar: bar
    open: true
    wide: shell.wide
    body: Component {
      FocusScope {
        id: bodyRoot
        property alias tabs: tabs
        property alias narrow: narrow
        property alias preset: preset
        property alias catcher: catcher
        property alias ev: bodyEvent
        // The first row's icon, set by that row.
        property var rowIcon: null
        implicitHeight: catcher.implicitHeight
        LayoutMirroring.enabled: shell.rtl
        LayoutMirroring.childrenInherit: true
        TestEvent {
          id: bodyEvent
        }
        PanelKeyCatcher {
          id: catcher
          width: parent.width
          implicitHeight: column.implicitHeight
          onMoveRequested: function (dx, dy) {
            if (dy === 0 && cursor.at(0))
              tabs.moveCursor(dx)
            else
              cursor.move(dy !== 0 ? dy : dx)
          }
          onActivateRequested: if (cursor.at(0))
            tabs.activateCursor()
          Column {
            id: column
            width: parent.width
            FoamyHeroBand {
              width: parent.width
              iconName: "calendar"
              title: "Todoist"
              meta: "15 tasks"
            }
            FoamyTabs {
              id: tabs
              width: parent.width
              value: shell.view
              model: shell.views
              hasCursor: cursor.at(0)
              cursorByKeys: cursor.byKeys
              onHovered: cursor.hover(0)
              onActivated: function (v) {
                shell.activations = shell.activations.concat([v])
              }
            }
            // Rows as a plugin insets them: the surface at gapLarge, its
            // content at rowPadding inside.
            Repeater {
              model: 2
              Item {
                id: rowItem
                required property int index
                width: parent.width
                height: FoamyStyle.rowHeight
                FoamyCursorSurface {
                  objectName: "rowSurface" + rowItem.index
                  anchors.left: parent.left
                  anchors.leftMargin: FoamyStyle.gapLarge
                  anchors.right: parent.right
                  anchors.rightMargin: FoamyStyle.gapLarge
                  height: parent.height
                  hasCursor: cursor.at(rowItem.index + 1)
                  byKeys: cursor.byKeys
                  // The second row is the selected one, with its bar.
                  current: rowItem.index === 1
                  currentBar: true
                  onHovered: cursor.hover(rowItem.index + 1)
                  FoamyIcon {
                    id: rowIconItem
                    anchors.left: parent.left
                    anchors.leftMargin: FoamyStyle.rowPadding
                    anchors.verticalCenter: parent.verticalCenter
                    width: FoamyStyle.iconSize
                    height: FoamyStyle.iconSize
                    name: "hash"
                    color: FoamyPalette.secondaryText
                    Component.onCompleted: if (rowItem.index === 0)
                      bodyRoot.rowIcon = rowIconItem
                  }
                }
              }
            }
            Item {
              width: parent.width
              height: FoamyStyle.gap
            }
            // Long labels in a row too narrow for them: they elide from the
            // last tab inward, icons and counts stay whole.
            FoamyTabs {
              id: narrow
              width: parent.width
              value: "a"
              model: shell.longViews
            }
            // Created with the cursor already on it; disabled.
            FoamyTabs {
              id: preset
              visible: false
              width: 240
              hasCursor: true
              enabled: false
              value: "b"
              model: [
                {
                  value: "a",
                  text: "A"
                },
                {
                  value: "b",
                  text: "B"
                }
              ]
              onActivated: function (v) {
                shell.presetActivations++
              }
            }
          }
        }
      }
    }
  }

  readonly property var body: popup.bodyItem
  readonly property var ev: body ? body.ev : null

  function tab(s, i) {
    return findByName(s, "foamyTab" + i)
  }
  function part(s, i, name) {
    return findByName(tab(s, i), name)
  }
  // An item lies wholly inside its tab (nothing clipped).
  function inside(item, t) {
    var p = item.mapToItem(t, 0, 0)
    return p.x >= -0.5 && p.y >= -0.5 && p.x + item.width <= t.width + 0.5 && p.y + item.height <= t.height + 0.5
  }
  // x of an item's reading-start edge, measured from the reading start of `s`.
  function startOf(item, s) {
    var x = item.mapToItem(s, 0, 0).x
    return shell.rtl ? s.width - (x + item.width) : x
  }
  function naturalTotal(s) {
    var total = s.inset * 2
    for (var i = 0; i < s.count; i++)
      total += tab(s, i).fixedWidth + tab(s, i).naturalLabel
    return total
  }
  // As wide as its content: the label is whole and the tab ends rowPadding
  // after its last part (the count, or the label without one).
  function contentWidth(s, i) {
    var label = part(s, i, "foamyTabLabel"), count = part(s, i, "foamyTabCount")
    var last = count.visible ? count : label
    return !label.truncated && near(tab(s, i).width - (startOf(last, tab(s, i)) + last.width), FoamyStyle.rowPadding, 1)
  }

  FoamyWait {
    id: wait
  }
  // Each step waits for what it needs (a 5 s bound), never a fixed delay.
  function step(label, next) {
    return function (ok) {
      check(ok, label)
      next()
    }
  }
  Component.onCompleted: wait.waitFor(function () {
    return body && body.tabs && body.tabs.width > 0 && tab(body.tabs, 2) && popup.cardItem.Window.window
  }, 5000, step("the popup shows its body", activate))
  function activate() {
    Style.cornerRadius = 6
    var w = popup.cardItem.Window.window
    if (!w.active)
      w.requestActivate()
    // Keys reach the focused item only in the active window.
    wait.waitFor(function () {
      return w.active
    }, 5000, step("the popup's window is active", settle))
  }
  // Saves the card after the current changes are drawn, then goes on.
  function shot(name, next) {
    Qt.callLater(function () {
      popup.cardItem.grabToImage(function (result) {
        result.saveToFile(Quickshell.env("FOAMY_OUT") + "/" + name + ".png")
        next()
      })
    })
  }

  function settle() {
    var s = body.tabs
    var popupWidth = shell.wide ? FoamyStyle.popupWidthWide : FoamyStyle.popupWidth
    check(near(s.width, s.parent.width) && near(s.width, popupWidth, 2), "full popup width " + s.width + " / " + popupWidth)
    check(near(s.height, FoamyStyle.controlHeight + FoamyStyle.gap, 0.01), "height controlHeight + gap " + s.height)
    eq(s.count, 3, "three tabs")
    var tabs = [tab(s, 0), tab(s, 1), tab(s, 2)]
    check(tabs[0] && tabs[1] && tabs[2] && !tab(s, 3), "three tab items")
    // Content width, not equal shares: each tab is its padding, icon,
    // label and count; "Inbox" and "Upcoming" differ.
    for (var k = 0; k < 3; k++)
      check(contentWidth(s, k), "tab " + k + " is content-width " + tabs[k].width)
    var share = (s.width - s.inset * 2) / 3
    check(tabs.every(function (g) {
      return g.width < share - 20
    }) && tabs[0].width !== tabs[1].width, "tabs are not equal shares of " + share + ": " + tabs.map(function (g) {
      return g.width
    }))
    // From the reading start: the first at the inset, the rest abutting,
    // the leftover space at the reading end.
    check(near(startOf(tabs[0], s), FoamyStyle.gapLarge, 0.01), "first tab at the gapLarge inset " + startOf(tabs[0], s))
    check(near(startOf(tabs[1], s), startOf(tabs[0], s) + tabs[0].width, 0.01) && near(startOf(tabs[2], s), startOf(tabs[1], s) + tabs[1].width, 0.01), "tabs follow each other")
    check(startOf(tabs[2], s) + tabs[2].width < s.width - FoamyStyle.gapLarge - 20, "space left at the reading end")
    var xs = tabs.map(function (g) {
      return g.mapToItem(s, 0, 0).x
    })
    if (shell.rtl)
      check(xs[0] > xs[1] && xs[1] > xs[2], "RTL: first tab on the right " + xs)
    else
      check(xs[0] < xs[1] && xs[1] < xs[2], "LTR: first tab on the left " + xs)
    // The first icon sits on the rows' content inset, in line with a row's icon.
    var icon0 = part(s, 0, "foamyTabIcon")
    var rowX = body.rowIcon.mapToItem(body, 0, 0).x, tabX = icon0.mapToItem(body, 0, 0).x
    check(near(rowX, tabX, 0.01), "first icon in line with the row icon below " + tabX + " / " + rowX)
    // Icons, labels and counts.
    var names = ["inbox", "calendar-days", "calendar"]
    for (var i = 0; i < 3; i++) {
      var icon = part(s, i, "foamyTabIcon")
      check(icon.visible && icon.name === names[i] && icon.known && near(icon.width, FoamyStyle.iconSize), "tab " + i + " icon " + icon.name)
      check(inside(icon, tabs[i]), "tab " + i + " icon not clipped")
      var label = part(s, i, "foamyTabLabel")
      check(!label.truncated && label.font.pixelSize === FoamyStyle.font.body && label.font.family === FoamyStyle.fontFamily, "tab " + i + " label whole, body font " + [label.truncated, label.width, label.implicitWidth, label.font.pixelSize, label.font.family])
      check(inside(label, tabs[i]), "tab " + i + " label inside its tab")
      var ix = icon.mapToItem(s, 0, 0).x, lx = label.mapToItem(s, 0, 0).x
      check(shell.rtl ? ix > lx : ix < lx, "tab " + i + " icon on the reading start of its label")
      // The trailing padding mirrors the leading one.
      var c = part(s, i, "foamyTabCount")
      var last = c.visible ? c : label
      var lastEnd = startOf(last, tabs[i]) + last.width
      check(near(tabs[i].width - lastEnd, FoamyStyle.rowPadding, 1), "tab " + i + " ends rowPadding after its content " + (tabs[i].width - lastEnd))
    }
    eq([part(s, 0, "foamyTabCount").text, part(s, 1, "foamyTabCount").text], ["12", "3"], "counts")
    check(!part(s, 2, "foamyTabCount").visible, "a count below 0 shows nothing")
    check(inside(part(s, 0, "foamyTabCount"), tabs[0]) && inside(part(s, 1, "foamyTabCount"), tabs[1]), "counts not clipped")
    // Three looks: the selected row in selectedFill with its bar; the
    // pointer's cursor without a border of its own; the keys' cursor with
    // an accent border.
    var row0 = findByName(body, "rowSurface0"), row1 = findByName(body, "rowSurface1")
    var saved = cursor.index
    cursor.reset()
    check(sameColor(row1.color, FoamyPalette.selectedFill) && findByName(row1, "foamyCurrentBar").visible && !findByName(row0, "foamyCurrentBar").visible, "the selected row: selectedFill and its bar")
    // The tab row: the keys' cursor has the accent border, the pointer's not.
    cursor.hover(0)
    var tabCursor = part(body.tabs, body.tabs.cursorIndex, "foamyTabCursor")
    var pointerTab = tabCursor.border.width
    cursor.index = 1
    cursor.move(-1)
    check(pointerTab === 0 && tabCursor.border.width === FoamyStyle.borderWidth, "a tab's keys' cursor has the accent border " + [pointerTab, tabCursor.border.width])
    cursor.hover(1)
    check(!cursor.byKeys && row0.hasCursor && !(row0.borderTop > 0 && sameColor(row0.borderSpec.color, row0.accent)), "the pointer's cursor: no accent border " + [row0.borderTop, row0.borderSpec.color])
    cursor.index = 0
    cursor.move(1)
    check(cursor.byKeys && row0.hasCursor && row0.borderTop === FoamyStyle.borderWidth && sameColor(row0.borderSpec.color, row0.accent), "the keys' cursor: an accent border " + [row0.borderTop, row0.borderSpec.color])
    cursor.byKeys = false
    cursor.index = saved
    // A destructive label on its strongest tint reads at 4.5:1 in light
    // and dark themes (the preview's dark red drew 4.32:1 there before
    // 0.15.1). A primary label takes whichever of text and background
    // reads better.
    var urgentTint = Qt.tint(FoamyPalette.background, Qt.alpha(Commons.Color.urgent, 0.26))
    var inkOther = Qt.colorEqual(FoamyPalette.accentInk, FoamyPalette.text) ? FoamyPalette.background : FoamyPalette.text
    check(FoamyPalette.contrastRatio(FoamyPalette.onSurface(Commons.Color.urgent, urgentTint), urgentTint) >= 4.5 && FoamyPalette.contrastRatio(FoamyPalette.accentInk, FoamyPalette.accent) >= FoamyPalette.contrastRatio(inkOther, FoamyPalette.accent), "the destructive label and the primary ink read " + [FoamyPalette.contrastRatio(FoamyPalette.onSurface(Commons.Color.urgent, urgentTint), urgentTint).toFixed(2), FoamyPalette.contrastRatio(FoamyPalette.accentInk, FoamyPalette.accent).toFixed(2)])
    // The palette in this theme: status marks and secondary text read at
    // 4.5:1 (light themes darken only as far as that), muted hints at 4:1.
    var minimum = function (c) {
      return FoamyPalette.contrastRatio(c, FoamyPalette.background)
    }
    check(["error", "warning", "success", "info"].every(function (k) {
      return minimum(FoamyPalette.onSurface(FoamyPalette[k])) >= 4.5
    }) && minimum(FoamyPalette.secondaryText) >= 4.5 && minimum(FoamyPalette.mutedText) >= 4, "status marks and text tones read (" + ["error", "warning", "success", "info"].map(function (k) {
      return minimum(FoamyPalette.onSurface(FoamyPalette[k])).toFixed(2)
    }) + ", " + minimum(FoamyPalette.secondaryText).toFixed(2) + ", " + minimum(FoamyPalette.mutedText).toFixed(2) + ")")
    // A status colour that already reads comes back unchanged, so a theme
    // keeps its look wherever it read before (light or dark).
    check(["error", "warning", "success", "info"].every(function (k) {
      return minimum(FoamyPalette[k]) < 4.5 || Qt.colorEqual(FoamyPalette.onSurface(FoamyPalette[k]), FoamyPalette[k])
    }), "a status colour that reads is returned unchanged " + ["error", "warning", "success", "info"].map(function (k) {
      return FoamyPalette[k] + "->" + FoamyPalette.onSurface(FoamyPalette[k])
    }))
    check(part(s, 0, "foamyTabCount").font.family === FoamyStyle.monoFamily && part(s, 0, "foamyTabCount").font.pixelSize === FoamyStyle.font.bodySmall, "count in the mono bodySmall")
    // The open tab: DemiBold text label, accent icon, count and underline.
    check(part(s, 0, "foamyTabLabel").font.weight === Font.DemiBold && part(s, 2, "foamyTabLabel").font.weight === Font.Normal, "open label DemiBold, others normal")
    check(sameColor(part(s, 0, "foamyTabLabel").color, FoamyPalette.text) && sameColor(part(s, 2, "foamyTabLabel").color, FoamyPalette.secondaryText), "label colours")
    check(sameColor(part(s, 0, "foamyTabIcon").color, FoamyPalette.accent) && sameColor(part(s, 2, "foamyTabIcon").color, FoamyPalette.secondaryText), "icon colours")
    check(sameColor(part(s, 0, "foamyTabCount").color, FoamyPalette.accent), "open count in accent")
    check(sameColor(part(body.narrow, 2, "foamyTabCount").color, FoamyPalette.secondaryText), "a count on another tab in secondaryText")
    check(sameColor(part(s, 1, "foamyTabCount").color, FoamyPalette.onSurface(FoamyPalette.error)), "urgent count in the error colour " + part(s, 1, "foamyTabCount").color)
    // The underline: 2px accent across the open tab only, on the row's bottom.
    var u0 = part(s, 0, "foamyTabUnderline")
    check(sameColor(u0.color, FoamyPalette.accent) && u0.height === 2 && near(u0.width, tabs[0].width, 0.01) && near(u0.mapToItem(s, 0, 0).x, xs[0], 0.01), "underline across the open tab " + [u0.color, u0.height, u0.width])
    check(near(u0.mapToItem(s, 0, 0).y + u0.height, s.height, 0.01), "underline on the row's bottom edge")
    check(sameColor(part(s, 1, "foamyTabUnderline").color, "transparent") && sameColor(part(s, 2, "foamyTabUnderline").color, "transparent"), "no underline under the other tabs")
    // The hairline: 1px divider across the whole row at its bottom, under
    // the underline (drawn first).
    var hair = findByName(s, "foamyTabsHairline")
    check(hair.x === 0 && near(hair.width, s.width, 0.01) && hair.height === 1 && near(hair.y, s.height - 1, 0.01) && sameColor(hair.color, FoamyPalette.divider), "hairline spans the row " + [hair.x, hair.width, hair.y, hair.height])
    check(s.children[0] === hair, "the hairline is drawn under the tabs")
    // Accessibility: a tab list of named page tabs with the selected state.
    check(s.Accessible.role === Accessible.PageTabList, "tab-list role")
    check(tabs[0].Accessible.role === Accessible.PageTab && tabs[0].Accessible.name === "Inbox, 12" && tabs[2].Accessible.name === "Upcoming", "page tabs named with their count " + tabs[0].Accessible.name)
    check(tabs[0].Accessible.selected && !tabs[1].Accessible.selected, "selected state")
    // Created with the cursor: on the open tab. Disabled: inert.
    eq(body.preset.cursorIndex, 1, "a row created with the cursor starts on the open tab")
    body.preset.activateCursor()
    eq(shell.presetActivations, 0, "a disabled row does not activate")
    // No cursor highlight before the cursor arrives.
    check(s.cursorIndex === -1 && !s.hasCursor, "no cursor on open")
    // A little short: only the last label gives way.
    var n = body.narrow
    n.width = naturalTotal(n) - 20
    wait.waitFor(function () {
      return part(n, 2, "foamyTabLabel").truncated
    }, 5000, step("a little short: the last label elides", eliding))
  }
  function eliding() {
    var n = body.narrow
    check(contentWidth(n, 0) && contentWidth(n, 1) && part(n, 2, "foamyTabLabel").truncated, "a little short: only the last label elides " + n.labelWidths)
    elidingCheck(n, "a little short")
    // Shorter than the whole last label: it goes, then the middle one elides.
    n.width = naturalTotal(n) - tab(n, 2).naturalLabel - 30
    wait.waitFor(function () {
      return part(n, 1, "foamyTabLabel").truncated
    }, 5000, step("much shorter: the middle label elides", deeper))
  }
  function deeper() {
    var n = body.narrow
    check(contentWidth(n, 0) && part(n, 1, "foamyTabLabel").truncated && tab(n, 2).labelWidth === 0, "much shorter: the last label gone, the middle one elides " + n.labelWidths)
    elidingCheck(n, "much shorter")
    eq(part(n, 0, "foamyTabCount").text, "1234", "counts through FoamyI18n.number (ungrouped)")
    shot("tabs", pointer)
  }
  // Icons and counts whole, the tabs inside the row, the row unscrolled.
  function elidingCheck(n, what) {
    for (var j = 0; j < 3; j++) {
      var t = tab(n, j)
      var ic = part(n, j, "foamyTabIcon"), c = part(n, j, "foamyTabCount")
      check(inside(ic, t) && near(ic.width, FoamyStyle.iconSize) && inside(c, t) && c.width >= c.implicitWidth - 0.5, what + ": tab " + j + " icon and count whole")
    }
    var end = startOf(tab(n, 2), n) + tab(n, 2).width
    check(near(end, n.width - n.inset, 1), what + ": the tabs end at the trailing inset " + end + " / " + (n.width - n.inset))
    check(near(startOf(tab(n, 0), n), n.inset, 0.01), what + ": the first tab stays at the inset")
  }

  // Pointer: hover moves the one cursor, a press emits without assigning.
  function pointer() {
    var s = body.tabs
    var g = tab(s, 2)
    ev.mouseMove(g, g.width / 2, g.height / 2, -1, Qt.NoButton, Qt.NoModifier)
    // The fill fades in (FoamyMotion.hover).
    wait.waitFor(function () {
      return cursor.index === 0 && s.cursorIndex === 2 && sameColor(part(s, 2, "foamyTabCursor").color, FoamyPalette.hoverFill)
    }, 5000, step("hover reaches the third tab", hoverCheck))
  }
  function hoverCheck() {
    var s = body.tabs
    var before = [tab(s, 0).width, tab(s, 1).width, tab(s, 2).width, tab(s, 2).mapToItem(s, 0, 0).x]
    check(cursor.index === 0 && s.hasCursor && s.cursorIndex === 2, "hover moves the panel cursor to the row, on that tab " + cursor.index + " " + s.cursorIndex)
    check(sameColor(part(s, 2, "foamyTabCursor").color, FoamyPalette.hoverFill), "hovered tab shows the cursor fill")
    check(sameColor(part(s, 0, "foamyTabCursor").color, "transparent"), "one highlight")
    var fill = part(s, 2, "foamyTabCursor")
    check(fill.mapToItem(s, 0, 0).y + fill.height <= s.height - 2, "the hover fill stays clear of the underline " + (fill.mapToItem(s, 0, 0).y + fill.height) + " of " + s.height)
    var g = tab(s, 2)
    ev.mouseClick(g, g.width / 2, g.height / 2, Qt.LeftButton, Qt.NoModifier, -1)
    eq(shell.activations, ["upcoming"], "a press emits activated with its value")
    check(s.value === "inbox" && s.selectedIndex === 0 && shell.view === "inbox", "the press does not change value")
    eq([tab(s, 0).width, tab(s, 1).width, tab(s, 2).width, tab(s, 2).mapToItem(s, 0, 0).x], before, "hover and press never move the layout")
    shot("tabs-hover", keys)
  }

  function forward() {
    return shell.rtl ? Qt.Key_Left : Qt.Key_Right
  }
  function back() {
    return shell.rtl ? Qt.Key_Right : Qt.Key_Left
  }
  // Keyboard through the real PanelKeyCatcher.
  function keys() {
    var s = body.tabs
    // Move the pointer off the popup so it no longer drives the cursor.
    ev.mouseMove(popup.cardItem, 1, popup.cardItem.height - 1, -1, Qt.NoButton, Qt.NoModifier)
    body.catcher.forceActiveFocus()
    cursor.index = 1
    check(!s.hasCursor && s.cursorIndex === -1, "cursor leaving the row clears its tab")
    ev.keyClick(Qt.Key_Up, Qt.NoModifier, -1)
    check(cursor.index === 0 && s.cursorIndex === 0, "keyboard arrival lands on the open tab " + s.cursorIndex)
    ev.keyClick(forward(), Qt.NoModifier, -1)
    eq(s.cursorIndex, 1, (shell.rtl ? "←" : "→") + " moves forward in reading order")
    ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
    eq(shell.activations, ["upcoming", "today"], "Enter activates the tab under the cursor")
    ev.keyClick(forward(), Qt.NoModifier, -1)
    ev.keyClick(forward(), Qt.NoModifier, -1)
    eq(s.cursorIndex, 2, "stops at the last tab")
    ev.keyClick(Qt.Key_Space, Qt.NoModifier, -1)
    eq(shell.activations, ["upcoming", "today", "upcoming"], "Space activates")
    ev.keyClick(back(), Qt.NoModifier, -1)
    eq(s.cursorIndex, 1, "back one")
    ev.keyClick(shell.rtl ? Qt.Key_L : Qt.Key_H, Qt.NoModifier, -1)
    eq(s.cursorIndex, 0, "h/l move too")
    ev.keyClick(back(), Qt.NoModifier, -1)
    eq(s.cursorIndex, 0, "stops at the first tab")
    check(cursor.index === 0, "←/→ stay on the row")
    check(s.value === "inbox" && s.selectedIndex === 0, "keys never change value")
    // The caller changes its state: the open tab follows.
    shell.view = "today"
    check(s.selectedIndex === 1 && part(s, 1, "foamyTabLabel").font.weight === Font.DemiBold, "the open tab follows the caller's value")
    check(sameColor(part(s, 1, "foamyTabCount").color, FoamyPalette.onSurface(FoamyPalette.error)), "urgent count keeps the error colour when open")
    // The tab's content row lays out on the next polish.
    wait.waitFor(function () {
      return contentWidth(s, 1)
    }, 5000, step("the DemiBold label is not cut and its tab fits it", openTabCursor))
  }
  function openTabCursor() {
    var s = body.tabs
    ev.keyClick(forward(), Qt.NoModifier, -1)
    eq(s.cursorIndex, 1, "cursor on the open tab")
    // The underline fades over to the new open tab (FoamyMotion.hover).
    wait.waitFor(function () {
      return sameColor(part(s, 1, "foamyTabUnderline").color, FoamyPalette.accent) && sameColor(part(s, 0, "foamyTabUnderline").color, "transparent")
    }, 5000, step("the underline moved with the value", function () {
      shot("tabs-cursor", rest)
    }))
  }
  function rest() {
    var s = body.tabs
    ev.keyClick(Qt.Key_Down, Qt.NoModifier, -1)
    check(cursor.index === 1 && !s.hasCursor && s.cursorIndex === -1, "Down leaves the row")
    ev.keyClick(Qt.Key_Up, Qt.NoModifier, -1)
    eq(s.cursorIndex, 1, "back on the row, on the open tab")
    ev.keyClick(forward(), Qt.NoModifier, -1)
    // A shorter model clamps the cursor.
    var full = shell.views
    shell.views = shell.views.slice(0, 2)
    check(s.count === 2 && s.cursorIndex === 1 && !tab(s, 2), "a shorter model clamps the cursor " + s.cursorIndex)
    shell.views = shell.views.slice(0, 1)
    eq(s.cursorIndex, 0, "clamped again")
    // Emptied and refilled while the row has the cursor: back on the open tab.
    shell.views = []
    check(s.hasCursor && s.cursorIndex === -1, "an empty model has no cursor tab " + s.cursorIndex)
    shell.views = full
    eq(s.cursorIndex, s.selectedIndex, "a refilled model puts the cursor on the open tab")
    wait.waitFor(function () {
      return tab(s, 2) && contentWidth(s, 0) && contentWidth(s, 1) && contentWidth(s, 2)
    }, 5000, step("refilled tabs are content-width again", refilledEnter))
  }
  function refilledEnter() {
    var s = body.tabs
    var before = shell.activations.length
    ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
    eq(shell.activations.slice(before), ["today"], "Enter works again after the refill")
    // The selected row under the cursor keeps its tint, lit (its colour
    // animates, so this waits for it).
    var row1 = findByName(body, "rowSurface1")
    // Lit: the selected tint (same hue as selectedFill), stronger than it.
    var plain = FoamyPalette.selectedFill
    var lit = function () {
      var c = row1.color
      return Math.abs(c.r - plain.r) < 0.02 && Math.abs(c.g - plain.g) < 0.02 && Math.abs(c.b - plain.b) < 0.02 && c.a > plain.a + 0.02
    }
    cursor.hover(2)
    wait.waitFor(lit, 5000, function (ok) {
      check(ok && findByName(row1, "foamyCurrentBar").visible, "the selected row under the cursor: its tint, lit, and its bar " + row1.color)
      console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
      console.log("FOAMY DONE")
      Qt.quit()
    })
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
}
