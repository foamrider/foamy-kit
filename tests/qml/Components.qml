import QtQuick
import QtQuick.Layouts
import QtTest
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"

// kit 0.4.0 components in real FoamyPopups on the simulated screen:
// FoamyHeroBand `centered` (clock, weather), FoamyPanelFooter, FoamyButton,
// FoamyInfoNote in a settings page, and popup height following the screen
// (FoamyPopup and FoamyPopupCard, no fixed 640 cap). FOAMY_RTL=1 mirrors.
// Cards are saved to FOAMY_OUT for screenshots.
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

  property int refreshes: 0
  property int calendarClicks: 0
  property int applies: 0
  property bool verifying: false
  property int toggleClicks: 0
  property var cpuCommits: []

  // --- clock: centred band, footer with a leading action -----------------------
  FoamyPopup {
    id: clockPopup
    anchorItem: shell.anchorButton
    bar: bar
    open: true
    body: Component {
      Column {
        property alias band: band
        property alias time: time
        property alias footer: footer
        property alias calendarButton: calendarButton
        property alias hiddenHeroBand: hiddenHeroBand
        property alias hiddenHero: hiddenHero
        LayoutMirroring.enabled: shell.rtl
        LayoutMirroring.childrenInherit: true
        spacing: FoamyStyle.gapLarge
        FoamyHeroBand {
          id: band
          width: parent.width
          centered: true
          iconName: "calendar"
          title: "lørdag 31. oktober"
          meta: "Week 44 · 2026"
          RowLayout {
            id: time
            objectName: "clockTime"
            Layout.alignment: Qt.AlignHCenter
            spacing: FoamyStyle.gapSmall
            Text { text: "20:32"; color: FoamyPalette.text; font.family: FoamyStyle.fontFamily; font.pixelSize: FoamyStyle.font.numeral; font.weight: Font.Light }
            Text { text: ":10"; color: FoamyPalette.secondaryText; font.family: FoamyStyle.fontFamily; font.pixelSize: FoamyStyle.font.display; Layout.alignment: Qt.AlignBaseline }
          }
        }
        Item { width: parent.width; height: 120
          Text { x: FoamyStyle.padding; text: "oktober 2026"; color: FoamyPalette.text; font.family: FoamyStyle.fontFamily; font.pixelSize: FoamyStyle.font.subtitle } }
        FoamyHeroBand {
          id: hiddenHeroBand
          visible: false
          width: parent.width
          title: "Paused"
          Text { id: hiddenHero; visible: false; text: "Outside your schedule" }
        }
        FoamyPanelFooter {
          id: footer
          x: FoamyStyle.padding
          width: parent.width - FoamyStyle.padding * 2
          status: "Updated 3 minutes ago"
          refreshing: false
          onRefreshClicked: shell.refreshes++
          FoamyAction {
            id: calendarButton
            iconName: "calendar"
            label: "Calendar"
            foreground: FoamyPalette.secondaryText
            onClicked: shell.calendarClicks++
          }
        }
      }
    }
  }

  // --- weather: centred hero row, footer with a source ----------------------------
  FoamyPopup {
    id: weatherPopup
    anchorItem: shell.anchorButton
    bar: bar
    open: true
    wide: true
    body: Component {
      Column {
        property alias band: band
        property alias footer: footer
        LayoutMirroring.enabled: shell.rtl
        LayoutMirroring.childrenInherit: true
        spacing: FoamyStyle.gapLarge
        FoamyHeroBand {
          id: band
          width: parent.width
          centered: true
          title: "Mjøndalen"
          meta: "High 7° · Low 6°"
          RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: FoamyStyle.gapLarge
            Text { text: "7"; color: FoamyPalette.text; font.family: FoamyStyle.fontFamily; font.pixelSize: FoamyStyle.font.numeral; font.weight: Font.Light }
            Text { text: "°C"; color: FoamyPalette.secondaryText; font.family: FoamyStyle.fontFamily; font.pixelSize: FoamyStyle.font.display; Layout.alignment: Qt.AlignTop }
            FoamyIcon { name: "cloud"; Layout.preferredWidth: 28; Layout.preferredHeight: 28; Layout.alignment: Qt.AlignVCenter }
            Text { text: "Cloudy"; color: FoamyPalette.text; font.family: FoamyStyle.fontFamily; font.pixelSize: FoamyStyle.font.heading; Layout.alignment: Qt.AlignVCenter }
          }
        }
        Item { width: parent.width; height: 80 }
        FoamyPanelFooter {
          id: footer
          x: FoamyStyle.padding
          width: parent.width - FoamyStyle.padding * 2
          source: "MET Norway"
          status: "Updated 13 min ago"
          refreshing: true
        }
      }
    }
  }

  // --- a tall panel: height follows the screen, not 640 ------------------------------
  FoamyPopup {
    id: tallPopup
    anchorItem: shell.anchorButton
    bar: bar
    open: true
    body: Component { Rectangle { implicitHeight: 1500; color: "transparent" } }
  }
  FoamyPopup {
    id: cappedPopup
    anchorItem: shell.anchorButton
    bar: bar
    open: true
    maxHeight: FoamyStyle.popupMaxHeight
    body: Component { Rectangle { implicitHeight: 1500; color: "transparent" } }
  }
  FoamyPopupCard {
    id: tallCard
    anchorItem: shell.anchorButton
    bar: bar
    open: true
    body: Component { Rectangle { implicitHeight: 1500; color: "transparent" } }
  }

  // --- settings form: buttons and an info note --------------------------------------
  FoamyPopup {
    id: formPopup
    anchorItem: shell.anchorButton
    bar: bar
    open: true
    body: Component {
      FoamySettingsPage {
        id: page
        property alias primary: primary
        property alias secondary: secondary
        property alias destructive: destructive
        property alias lfs: lfs
        property alias toggleA: toggleA
        property alias toggleB: toggleB
        property alias cpu: cpu
        property alias ram: ram
        property alias margin: margin
        implicitHeight: 900
        LayoutMirroring.enabled: shell.rtl
        FoamySettingsSection {
          id: lfs
          width: parent.width
          title: "Git LFS"
          info: "Automatic checks run Git without a repository's own settings, filters and hooks, so nothing in a repository can run code just by being in these folders. For Git LFS that means files you edited may show as changed until Git refreshes. A trusted repository runs its own Git settings, including LFS, during automatic checks and fetches, so its counts are exact."
          FoamyToggle { id: toggleA; width: parent.width; label: "Kvale/arca"; description: "/home/tomas/GitHub/Kvale/arca"; divider: true; onClicked: shell.toggleClicks++ }
          FoamyToggle { id: toggleB; width: parent.width; label: "Compact view"; checked: true }
        }
        FoamySettingsSection {
          width: parent.width
          title: "Usage warnings"
          description: "Warns at or above these percentages."
          FoamyNumberField { id: cpu; width: parent.width; compact: true; label: "CPU"; unit: "%"; value: 95; from: 1; to: 100; onCommitted: function(v) { shell.cpuCommits = shell.cpuCommits.concat([v]) } }
          FoamyNumberField { id: ram; width: parent.width; compact: true; label: "RAM"; unit: "%"; value: 90; from: 1; to: 100 }
          FoamyNumberField { id: margin; width: parent.width; compact: true; label: "CPU temperature margin"; unit: "°C"; value: 15; from: 0; to: 40 }
        }
        FoamySettingsSection {
          width: parent.width
          title: "Wireless headset"
          RowLayout {
            width: parent.width
            spacing: FoamyStyle.gap
            FoamyButton { id: secondary; text: "Verify"; iconName: "check"; focusable: true; busy: shell.verifying }
            FoamyButton { id: primary; text: "Apply"; kind: "primary"; focusable: true; onClicked: shell.applies++ }
            Item { Layout.fillWidth: true }
            FoamyButton { id: destructive; text: "Remove"; iconName: "trash"; kind: "destructive"; focusable: true }
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

  function centerX(item, ref) { return item.mapToItem(ref, 0, 0).x + item.width / 2 }

  Timer {
    id: settle
    interval: 500
    onTriggered: {
      // Centred band (clock).
      var clock = clockPopup.bodyItem
      var band = clock.band
      check(band.centered && !band.titleRow.showTitle, "centred band hides the title row's icon and text")
      check(near(centerX(clock.time, band), band.width / 2, 2), "hero centred " + centerX(clock.time, band) + " of " + band.width)
      var t = findByName(band, "foamyHeroBandCenteredTitle")
      check(t && t.visible, "centred title shown")
      if (t) {
        check(near(t.x + t.width / 2, band.width / 2, 1), "title column centred")
        check(t.mapToItem(band, 0, 0).y > clock.time.mapToItem(band, 0, 0).y + clock.time.height - 1, "big time above the date")
        check(t.children[0].horizontalAlignment === Text.AlignHCenter, "title text centred")
      }
      var s = band.settingsButton.mapToItem(band, 0, 0)
      if (shell.rtl) check(s.x < FoamyStyle.padding + 2, "RTL: settings in the top left corner " + s.x)
      else check(s.x + band.settingsButton.width > band.width - FoamyStyle.padding - 2, "LTR: settings in the top right corner " + s.x)
      check(s.y <= FoamyStyle.bandPaddingTop + 1, "settings pinned to the top " + s.y)
      var heroLeft = clock.time.mapToItem(band, 0, 0).x
      check(heroLeft + clock.time.width < s.x || heroLeft > s.x + band.settingsButton.width, "hero keeps clear of the corner buttons")
      // Footer (clock): leading action, status, refresh on the end.
      var footer = clock.footer
      var r = footer.refreshButton.mapToItem(footer, 0, 0)
      var c = clock.calendarButton.mapToItem(footer, 0, 0)
      var st = findByName(footer, "foamyFooterStatus")
      var sp = st.mapToItem(footer, 0, 0)
      if (shell.rtl) {
        check(near(r.x, 0) && near(c.x + clock.calendarButton.width, footer.width), "RTL footer: refresh left, calendar right")
        check(sp.x + st.width <= c.x + 1 && sp.x >= r.x + footer.refreshButton.width - 1, "RTL footer: status between")
      } else {
        check(near(r.x + footer.refreshButton.width, footer.width) && near(c.x, 0), "footer: calendar at the start, refresh at the end")
        check(near(sp.x + st.width, r.x - FoamyStyle.gapSmall, 1.5), "footer: status ends at the refresh button")
      }
      check(st.text === "Updated 3 minutes ago" && st.font.pixelSize === FoamyStyle.font.bodySmall, "footer status text")
      footer.refreshButton.clicked()
      check(shell.refreshes === 1, "refresh emits refreshClicked")
      var wfooter = weatherPopup.bodyItem.footer
      check(wfooter.refreshButton.spinning && !wfooter.refreshButton.active, "refreshing: spinning and inert")
      // Weather band centred.
      var wband = weatherPopup.bodyItem.band
      check(wband.hasHero && wband.centered, "weather band centred with hero")

      // Buttons.
      var page = formPopup.bodyItem
      check(page.primary.color !== page.secondary.color && page.destructive.color !== page.secondary.color, "kinds have their own fill")
      check(page.secondary.border.width >= 1 && page.destructive.border.width >= 1, "secondary/destructive are bordered")
      check(page.primary.height === FoamyStyle.controlHeight && page.primary.activeFocusOnTab, "button height and Tab")
      page.primary.forceActiveFocus()
      ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
      check(shell.applies === 1, "Enter activates the focused button " + shell.applies)
      check(page.primary.border.width === 2, "focus ring on the focused button")
      shell.verifying = true
      check(!page.secondary.active, "busy button is inert")
      // Info note: the (i) is beside the title and the note opens under it.
      var info = page.lfs.infoNote
      check(info.visible && !info.note.visible, "section with info: (i) shown, note folded")
      info.infoButton.forceActiveFocus()
      ev.keyClick(Qt.Key_Space, Qt.NoModifier, -1)
      check(info.expanded && info.note.visible, "Space on the (i) opens the note")

      // Toggle rows: plain, not boxed.
      var ta = page.toggleA
      var fill = findByName(ta, "foamyToggleFill")
      check(fill && fill.border.width === 0 && fill.color.a === 0, "toggle row has no box at rest")
      check(ta.height >= FoamyStyle.rowHeight && near(page.toggleB.height, FoamyStyle.rowHeight + FoamyStyle.gapSmall, 1), "toggle row heights " + ta.height + " / " + page.toggleB.height)
      check(findByName(ta, "foamyToggleDivider").visible && !findByName(page.toggleB, "foamyToggleDivider").visible, "divider only where asked")
      var sw = ta.switchItem.mapToItem(ta, 0, 0)
      if (shell.rtl) check(sw.x < 2, "RTL: switch on the left " + sw.x)
      else check(near(sw.x + ta.switchItem.width, ta.width), "switch on the end " + sw.x)
      check(ta.children[1].children[0].font.weight !== Font.Bold && ta.children[1].children[0].font.weight < Font.DemiBold, "label in normal weight")
      // Compact number fields: one row, narrow field, units lined up.
      var cpu = page.cpu, margin = page.margin
      var cf = cpu.field.mapToItem(page, 0, 0), mf = margin.field.mapToItem(page, 0, 0)
      check(cpu.field.width < cpu.width / 3 && cpu.field.width >= cpu.compactFieldWidth - 1, "compact field is narrow " + cpu.field.width + " of " + cpu.width)
      if (shell.rtl) check(near(cf.x, mf.x), "RTL: stacked compact fields line up at their unit side " + cf.x + " / " + mf.x)
      else check(near(cf.x + cpu.field.width, mf.x + margin.field.width), "stacked compact fields line up at their unit side "
                 + (cf.x + cpu.field.width) + " / " + (mf.x + margin.field.width))
      check(cpu.height < FoamyStyle.controlHeight + 8, "label, field and unit on one row " + cpu.height)
      if (shell.rtl) check(cf.x < cpu.mapToItem(page, 0, 0).x + cpu.width / 2, "RTL: field toward the left")
      else check(cf.x > cpu.mapToItem(page, 0, 0).x + cpu.width / 2, "field toward the end")
      cpu.field.text = "80"
      cpu.dirty = true
      cpu.commitEdit(false)
      check(JSON.stringify(shell.cpuCommits) === "[80]", "compact field commits " + JSON.stringify(shell.cpuCommits))
      // hasHero counts shown hero items only.
      var hb = clock.hiddenHeroBand
      hb.visible = true
      check(!hb.hasHero, "a hidden hero item is no hero")
      clock.hiddenHero.visible = true
      check(hb.hasHero, "shown again, it is")
      hb.visible = false

      // Popup height follows the screen.
      var avail = tallPopup.availableCardHeight
      check(avail > FoamyStyle.popupMaxHeight, "screen allows more than 640 " + avail)
      check(near(tallPopup.cardItem.height, avail, 2), "tall popup grows to the available height " + tallPopup.cardItem.height + " of " + avail)
      check(near(cappedPopup.cardItem.height, FoamyStyle.popupMaxHeight, 2), "maxHeight still caps when set " + cappedPopup.cardItem.height)
      check(tallCard.cardItem.height > FoamyStyle.popupMaxHeight && tallCard.cardItem.height <= tallCard.availableCardHeight + 2,
            "FoamyPopupCard follows the screen " + tallCard.cardItem.height + " of " + tallCard.availableCardHeight)
      shell.verifying = false
      capture.start()
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

  // Screenshots (one popup at a time on top).
  Timer {
    id: capture
    interval: 400
    property var queue: [["clock", clockPopup], ["weather", weatherPopup], ["form", formPopup]]
    onTriggered: {
      if (queue.length === 0) {
        // Pointer checks need the form card on top: close the others first.
        clockPopup.open = false; weatherPopup.open = false; tallPopup.open = false
        cappedPopup.open = false; tallCard.open = false
        pointerStep.start()
        return
      }
      var item = queue.shift()
      item[1].cardItem.grabToImage(function(result) {
        result.saveToFile(Quickshell.env("FOAMY_OUT") + "/" + item[0] + ".png")
        capture.start()
      })
    }
  }

  Timer {
    id: pointerStep
    interval: 600
    onTriggered: {
      var info = formPopup.bodyItem.lfs.infoNote
      check(info.note.mapToItem(formPopup.bodyItem.lfs, 0, 0).y > info.infoButton.mapToItem(formPopup.bodyItem.lfs, 0, 0).y + info.infoButton.height - 1,
            "note under the title (once laid out)")
      var ta = formPopup.bodyItem.toggleA
      var fill = findByName(ta, "foamyToggleFill")
      ev.mouseClick(ta, ta.width / 2, ta.height / 2, Qt.LeftButton, Qt.NoModifier, -1)
      check(shell.toggleClicks === 1 && !ta.checked, "click emits clicked, never flips checked " + shell.toggleClicks)
      ev.mouseMove(ta, ta.width / 2, ta.height / 2 + 1, -1, Qt.NoButton, Qt.NoModifier)
      check(ta.hot, "hover lights the row")
      console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
      console.log("FOAMY DONE")
      Qt.quit()
    }
  }

  Item { parent: formPopup.bodyItem; TestEvent { id: ev } }
}
