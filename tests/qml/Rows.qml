import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"

// kit 0.4.2 settings rows in a real FoamyPopup on the simulated screen: a
// page mixing FoamyToggle rows, compact FoamyNumberFields and compact
// FoamyDropdowns reads as one list (same row height, trailing controls on
// the row's end, mirrored in RTL); the compact dropdown is sized to its
// widest option, capped at half the row (eliding), and its list grows
// toward the label; a full-width dropdown is unchanged; a section title
// with an (i) is as far from its description as a plain title (note
// closed). FOAMY_RTL=1 mirrors. Cards are saved to FOAMY_OUT.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property bool rtl: Quickshell.env("FOAMY_RTL") === "1"
  readonly property string tag: host + "/" + (rtl ? "rtl" : "ltr") + "@" + Quickshell.env("FOAMY_SCALE")
  property int checks: 0
  property int failures: 0
  function check(ok, label) { checks++; if (!ok) { failures++; console.log("FOAMY FAIL " + tag + " " + label) } }
  function near(a, b, t) { return Math.abs(a - b) <= (t === undefined ? 1.01 : t) }

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
  readonly property Item anchorButton: shell.host === "4.5" ? sim.anchor : stripAnchor

  property string wheel: "track"
  property var wheelChanges: []

  readonly property var wheelOptions: [
    { value: "track", label: "Previous/next track" },
    { value: "volume", label: "Volume" },
    { value: "none", label: "Nothing" }
  ]

  FoamyPopup {
    id: formPopup
    anchorItem: shell.anchorButton
    bar: bar
    open: true
    body: Component {
      FoamySettingsPage {
        property alias toggleA: toggleA
        property alias toggleB: toggleB
        property alias mouseWheel: mouseWheel
        property alias labelWidth: labelWidth
        property alias accent: accent
        property alias interval: interval
        property alias longChoice: longChoice
        property alias fullWidth: fullWidth
        property alias lfs: lfs
        property alias folders: folders
        LayoutMirroring.enabled: shell.rtl
        FoamySettingsSection {
          id: folders
          width: parent.width
          title: "Repository folders"
          description: "Folders to search for Git repositories."
          FoamyToggle { id: toggleA; width: parent.width; label: "Left-click plays/pauses"; description: "Left-click opens the popup." }
          FoamyDropdown {
            id: mouseWheel
            objectName: "rowsMouseWheel"
            width: parent.width
            compact: true
            label: "Mouse wheel"
            value: shell.wheel
            options: shell.wheelOptions
            onChanged: function(v) { shell.wheelChanges = shell.wheelChanges.concat([v]) }
          }
          FoamyToggle { id: toggleB; width: parent.width; label: "Hide when stopped"; checked: true }
          FoamyNumberField { id: labelWidth; width: parent.width; compact: true; label: "Label width"; unit: "px"; value: 300; from: 60; to: 600; stepSize: 10 }
          FoamyDropdown {
            id: accent
            width: parent.width
            compact: true
            label: "Accent"
            description: "The colour of the progress bar and the playing icon."
            value: "source"
            options: [{ value: "source", label: "Source color" }, { value: "art", label: "Album art" },
                      { value: "theme", label: "Theme accent" }, { value: "bar", label: "Bar foreground" }]
          }
          FoamyDropdown {
            id: interval
            width: parent.width
            compact: true
            label: "Fetch remotes every"
            value: "15"
            options: [{ value: "5", label: "5 minutes" }, { value: "15", label: "15 minutes" },
                      { value: "30", label: "30 minutes" }, { value: "60", label: "1 hour" }]
          }
          FoamyDropdown {
            id: longChoice
            width: parent.width
            compact: true
            label: "Open Teams window"
            value: "a"
            options: [{ value: "a", label: "com.microsoft.teams.progressive-web-app-instance" }, { value: "b", label: "Manual" }]
          }
        }
        FoamySettingsSection {
          id: lfs
          width: parent.width
          title: "Git LFS"
          description: "Turn on for repositories you trust."
          info: "Automatic checks run Git without a repository's own settings, filters and hooks."
          FoamyDropdown {
            id: fullWidth
            width: parent.width
            label: "Calendar app"
            value: "track"
            options: shell.wheelOptions
          }
        }
      }
    }
  }

  Timer {
    interval: 900; running: true
    onTriggered: {
      Style.cornerRadius = 6
      var w = formPopup.cardItem.Window.window
      if (w && !w.active) w.requestActivate()
      settle.start()
    }
  }

  // Trailing edge of a control in its row's coordinates: the end of the row
  // (right in LTR, left in RTL) should be flush with it.
  function endGap(item, row) {
    var p = item.mapToItem(row, 0, 0)
    return shell.rtl ? p.x : row.width - (p.x + item.width)
  }
  function midY(item, ref) { return item.mapToItem(ref, 0, item.height / 2).y }

  Timer {
    id: settle
    interval: 500
    onTriggered: {
      var page = formPopup.bodyItem
      var rowH = FoamyStyle.rowHeight + FoamyStyle.gapSmall
      var mw = page.mouseWheel, lw = page.labelWidth, ta = page.toggleA, tb = page.toggleB
      // One list: the same row height.
      check(near(tb.height, rowH) && near(mw.height, rowH) && near(lw.height, rowH) && near(page.interval.height, rowH),
            "toggle, compact number and compact dropdown rows share a height " + [tb.height, mw.height, lw.height, page.interval.height, rowH])
      var at = findByName(page.accent, "foamyDropdownRowText")
      check(near(page.accent.height, Math.max(rowH, at.implicitHeight + FoamyStyle.gap * 2)) && near(ta.height, Math.max(rowH, ta.children[1].implicitHeight + FoamyStyle.gap * 2)),
            "rows with a description grow as toggle rows do " + page.accent.height + " / " + ta.height)
      // Trailing controls on the row's end.
      check(near(endGap(tb.switchItem, tb), 0), "switch on the end " + endGap(tb.switchItem, tb))
      check(near(endGap(mw.triggerItem, mw), 0), "compact dropdown on the end " + endGap(mw.triggerItem, mw))
      check(near(endGap(page.accent.triggerItem, page.accent), 0), "described dropdown on the end")
      // The number field's unit column ends the row (field + unit block).
      var unitEnd = shell.rtl ? lw.field.mapToItem(lw, 0, 0).x - FoamyStyle.gap - FoamyStyle.unitWidthCompact
                              : lw.width - (lw.field.mapToItem(lw, 0, 0).x + lw.field.width + FoamyStyle.gap + FoamyStyle.unitWidthCompact)
      check(near(unitEnd, 0, 1.5), "number field + unit end the row " + unitEnd)
      var unit = findText(lw, "px")
      var ux = unit.mapToItem(lw, 0, 0).x
      check(shell.rtl ? near(ux, 0) && unit.effectiveHorizontalAlignment === Text.AlignLeft
                      : near(ux + unit.width, lw.width) && unit.effectiveHorizontalAlignment === Text.AlignRight,
            "unit text ends on the row's end " + ux + " " + unit.effectiveHorizontalAlignment)
      // Controls centred on their row, labels on the start.
      check(near(midY(mw.triggerItem, mw), mw.height / 2) && near(midY(tb.switchItem, tb), tb.height / 2) && near(midY(lw.field, lw), lw.height / 2),
            "controls vertically centred " + [midY(mw.triggerItem, mw), midY(tb.switchItem, tb), midY(lw.field, lw)])
      var rt = findByName(mw, "foamyDropdownRowText")
      var rtx = rt.mapToItem(mw, 0, 0).x
      if (shell.rtl) check(near(rtx + rt.width, mw.width) && rtx >= mw.triggerItem.width + FoamyStyle.gapLarge - 1, "RTL: label on the right " + rtx)
      else check(near(rtx, 0) && rtx + rt.width <= mw.triggerItem.mapToItem(mw, 0, 0).x - FoamyStyle.gapLarge + 1, "label on the start " + rtx)
      check(near(midY(rt, mw), mw.height / 2, 1.5), "label vertically centred")
      check(rt.children[0].font.pixelSize === FoamyStyle.font.subtitle && rt.children[0].font.weight < Font.DemiBold, "label in the toggle row style")
      var nt = findByName(lw, "foamyNumberRowText")
      check(nt && nt.visible && near(nt.children[0].mapToItem(lw, 0, 0).x, shell.rtl ? lw.width - nt.children[0].width : 0, 1.5), "number label on the start")
      // Sized to the widest option; capped at half the row and eliding.
      check(near(mw.triggerItem.width, mw.compactNaturalWidth) && mw.triggerItem.width < mw.width / 2,
            "dropdown fits its widest option " + mw.triggerItem.width + " natural " + mw.compactNaturalWidth)
      var metrics = Qt.createQmlObject('import QtQuick; FontMetrics { font.family: "' + FoamyStyle.fontFamily + '"; font.pixelSize: ' + FoamyStyle.font.body + ' }', shell)
      check(mw.compactNaturalWidth >= metrics.advanceWidth("Previous/next track") + FoamyStyle.iconSize, "natural width covers the widest label and chevron")
      var lc = page.longChoice
      check(near(lc.triggerItem.width, Math.floor(lc.width * 0.5)), "long options cap at half the row " + lc.triggerItem.width + " of " + lc.width)
      var plain = findText(lc.triggerItem, "com.microsoft.teams.progressive-web-app-instance")
      check(plain && plain.truncated, "capped label elides")
      // Full-width dropdown unchanged: label above, trigger full width.
      var fw = page.fullWidth
      check(near(fw.triggerItem.width, fw.width) && fw.triggerItem.mapToItem(fw, 0, 0).y > 8, "full-width dropdown keeps the label above")
      check(!findByName(fw, "foamyDropdownRowText").visible, "no row label outside compact")
      // Section titles: an (i) title is as far from its description as a plain one.
      var dp = findByName(page.folders, "foamySectionDescription"), dl = findByName(page.lfs, "foamySectionDescription")
      var tp = findByName(page.folders, "foamySectionTitle")
      check(near(dp.y, dl.y, 0.5), "description as far below an (i) title as below a plain title " + dl.y + " vs " + dp.y)
      var btn = page.lfs.infoNote.infoButton
      var bTop = btn.mapToItem(page.lfs, 0, 0).y
      check(bTop + btn.height <= dl.y + 1, "(i) button clear of the description " + (bTop + btn.height) + " / " + dl.y)
      var gapAbove = page.lfs.mapToItem(page, 0, 0).y - (page.folders.mapToItem(page, 0, 0).y + page.folders.height)
      check(gapAbove >= 0 && page.lfs.infoNote.height <= tp.height + 0.5, "heading line as tall as a title " + page.lfs.infoNote.height + " / " + tp.height)
      shot.queue = [["rows", step2]]
      shot.start()
    }
  }

  // Open the compact dropdown: the list grows toward the label, keys pick.
  Timer {
    id: step2
    interval: 50
    onTriggered: {
      var page = formPopup.bodyItem
      var lc = page.longChoice
      lc.triggerItem.forceActiveFocus()
      ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
      openCheck.start()
    }
  }
  Timer {
    id: openCheck
    interval: 400
    onTriggered: {
      var page = formPopup.bodyItem
      var lc = page.longChoice
      check(lc.popupOpen, "Enter opens the compact dropdown")
      var list = findPopupList(lc)
      if (list) {
        var t = lc.triggerItem
        var lp = list.mapToItem(lc, 0, 0)
        var pw = list.width
        check(pw > t.width + 10 && pw <= lc.width + 1, "open list wider than the capped trigger, within the row " + pw + " / " + t.width)
        var tx = t.mapToItem(lc, 0, 0).x
        if (shell.rtl) check(near(lp.x, tx, 4), "RTL: list starts at the trigger's left edge " + lp.x + " / " + tx)
        else check(near(lp.x + pw, tx + t.width, 4), "list ends at the trigger's right edge " + (lp.x + pw) + " / " + (tx + t.width))
      } else check(false, "popup list found")
      shot.queue = [["rows-open", step3, true]]
      shot.start()
    }
  }
  Timer {
    id: step3
    interval: 50
    onTriggered: {
      var page = formPopup.bodyItem
      page.longChoice.close()
      var mw = page.mouseWheel
      mw.triggerItem.forceActiveFocus()
      ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
      pick.start()
    }
  }
  Timer {
    id: pick
    interval: 300
    onTriggered: {
      var mw = formPopup.bodyItem.mouseWheel
      ev.keyClick(Qt.Key_Down, Qt.NoModifier, -1)
      ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
      check(JSON.stringify(shell.wheelChanges) === '["volume"]', "pick emits changed " + JSON.stringify(shell.wheelChanges))
      check(mw.value === "track" && mw.currentLabel() === "Volume", "value stays the caller's; the pick shows")
      // The info note opened sits clear of the (i).
      var lfs = formPopup.bodyItem.lfs
      lfs.infoNote.open()
      noteCheck.start()
    }
  }
  Timer {
    id: noteCheck
    interval: 300
    onTriggered: {
      var lfs = formPopup.bodyItem.lfs
      var btn = lfs.infoNote.infoButton
      var n = lfs.infoNote.note
      check(n.visible && n.mapToItem(lfs, 0, 0).y >= btn.mapToItem(lfs, 0, 0).y + btn.height - 0.5, "open note under the (i) button")
      shot.queue = [["rows-note", done]]
      shot.start()
    }
  }
  Timer {
    id: done
    interval: 10
    onTriggered: {
      console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
      console.log("FOAMY DONE")
      Qt.quit()
    }
  }

  Timer {
    id: shot
    interval: 300
    property var queue: []
    onTriggered: {
      var item = queue.shift()
      // An open dropdown list is an overlay outside the card: grab it too.
      if (item[2]) {
        var list = findPopupList(null)
        if (list && list.parent) {
          var at = list.parent.mapToItem(formPopup.cardItem, 0, 0)
          console.log("FOAMY NOTE list-at " + at.x + " " + at.y)
        }
        if (list && list.parent) list.parent.grabToImage(function(r) { r.saveToFile(Quickshell.env("FOAMY_OUT") + "/" + item[0] + "-list.png") })
      }
      formPopup.cardItem.grabToImage(function(result) {
        result.saveToFile(Quickshell.env("FOAMY_OUT") + "/" + item[0] + ".png")
        item[1].start()
      })
    }
  }

  function findByName(item, name) {
    if (!item) return null
    if (item.objectName === name) return item
    for (var i = 0; i < item.children.length; i++) {
      var found = findByName(item.children[i], name)
      if (found) return found
    }
    return null
  }
  function findText(item, text) {
    if (!item) return null
    if (item.text === text && item.truncated !== undefined && item.visible) return item
    for (var i = 0; i < item.children.length; i++) {
      var found = findText(item.children[i], text)
      if (found) return found
    }
    return null
  }
  // The open popup's ListView (the popup is an overlay, not a child item).
  function findPopupList(dropdown) {
    var root = formPopup.cardItem.Window.window ? formPopup.cardItem.Window.window.contentItem : null
    return findList(root)
  }
  function findList(item) {
    if (!item) return null
    if (item.currentIndex !== undefined && item.model !== undefined && item.contentHeight !== undefined && item.visible && item.count === 2) return item
    for (var i = 0; i < item.children.length; i++) {
      var found = findList(item.children[i])
      if (found) return found
    }
    return null
  }

  Item { parent: formPopup.bodyItem; TestEvent { id: ev } }
}
