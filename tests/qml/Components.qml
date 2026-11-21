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
// FoamyInfoNote in a settings page, and FoamyPopupCard's height following
// the screen (no fixed 640 cap). FOAMY_RTL=1 mirrors. Cards are saved to
// FOAMY_OUT for screenshots.
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
  function near(a, b, t) {
    return Math.abs(a - b) <= (t === undefined ? 1.01 : t)
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
  readonly property Item anchorButton: sim.anchor

  property int refreshes: 0
  property int weatherRefreshes: 0
  property bool weatherRefreshing: true
  property int calendarClicks: 0
  property int applies: 0
  property int verifies: 0
  property bool verifying: false
  property int toggleClicks: 0

  FoamyWait {
    id: wait
  }

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
        property alias glyphBand: glyphBand
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
            Text {
              text: "20:32"
              color: FoamyPalette.text
              font.family: FoamyStyle.fontFamily
              font.pixelSize: FoamyStyle.font.numeral
              font.weight: Font.Light
            }
            Text {
              text: ":10"
              color: FoamyPalette.secondaryText
              font.family: FoamyStyle.fontFamily
              font.pixelSize: FoamyStyle.font.display
              Layout.alignment: Qt.AlignBaseline
            }
          }
        }
        Item {
          width: parent.width
          height: 120
          Text {
            x: FoamyStyle.padding
            text: "oktober 2026"
            color: FoamyPalette.text
            font.family: FoamyStyle.fontFamily
            font.pixelSize: FoamyStyle.font.subtitle
          }
        }
        FoamyHeroBand {
          id: hiddenHeroBand
          visible: false
          width: parent.width
          title: "Paused"
          Text {
            id: hiddenHero
            visible: false
            text: "Outside your schedule"
          }
        }
        FoamyHeroBand {
          id: glyphBand
          width: parent.width
          iconName: "calendar"
          iconGlyph: "\u{f02bb}"
          title: "Teams"
          showSettings: false
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
            Text {
              text: "7"
              color: FoamyPalette.text
              font.family: FoamyStyle.fontFamily
              font.pixelSize: FoamyStyle.font.numeral
              font.weight: Font.Light
            }
            Text {
              text: "°C"
              color: FoamyPalette.secondaryText
              font.family: FoamyStyle.fontFamily
              font.pixelSize: FoamyStyle.font.display
              Layout.alignment: Qt.AlignTop
            }
            FoamyIcon {
              name: "cloud"
              Layout.preferredWidth: 28
              Layout.preferredHeight: 28
              Layout.alignment: Qt.AlignVCenter
            }
            Text {
              text: "Cloudy"
              color: FoamyPalette.text
              font.family: FoamyStyle.fontFamily
              font.pixelSize: FoamyStyle.font.heading
              Layout.alignment: Qt.AlignVCenter
            }
          }
        }
        Item {
          width: parent.width
          height: 80
        }
        FoamyPanelFooter {
          id: footer
          x: FoamyStyle.padding
          width: parent.width - FoamyStyle.padding * 2
          source: "MET Norway"
          status: "Updated 13 min ago"
          refreshing: shell.weatherRefreshing
          onRefreshClicked: shell.weatherRefreshes++
        }
      }
    }
  }

  // --- a tall card: height follows the screen, not 640 -------------------------------
  FoamyPopupCard {
    id: tallCard
    anchorItem: shell.anchorButton
    bar: bar
    open: true
    body: Component {
      Rectangle {
        implicitHeight: 1500
        color: "transparent"
      }
    }
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
          FoamyToggle {
            id: toggleA
            width: parent.width
            label: "Kvale/arca"
            description: "/home/tomas/GitHub/Kvale/arca"
            divider: true
            onClicked: shell.toggleClicks++
          }
          FoamyToggle {
            id: toggleB
            width: parent.width
            label: "Compact view"
            checked: true
          }
        }
        FoamySettingsSection {
          width: parent.width
          title: "Usage warnings"
          description: "Warns at or above these percentages."
          FoamyNumberField {
            id: cpu
            width: parent.width
            compact: true
            label: "CPU"
            unit: "%"
            value: 95
            from: 1
            to: 100
          }
          FoamyNumberField {
            id: ram
            width: parent.width
            compact: true
            label: "RAM"
            unit: "%"
            value: 90
            from: 1
            to: 100
          }
          FoamyNumberField {
            id: margin
            width: parent.width
            compact: true
            label: "CPU temperature margin"
            unit: "°C"
            value: 15
            from: 0
            to: 40
          }
        }
        FoamySettingsSection {
          width: parent.width
          title: "Wireless headset"
          RowLayout {
            width: parent.width
            spacing: FoamyStyle.gap
            FoamyButton {
              id: secondary
              text: "Verify"
              iconName: "check"
              focusable: true
              busy: shell.verifying
              onClicked: shell.verifies++
            }
            FoamyButton {
              id: primary
              text: "Apply"
              kind: "primary"
              focusable: true
              onClicked: shell.applies++
            }
            Item {
              Layout.fillWidth: true
            }
            FoamyButton {
              id: destructive
              text: "Remove"
              iconName: "trash"
              kind: "destructive"
              focusable: true
            }
          }
        }
      }
    }
  }

  Timer {
    interval: 900
    running: true
    onTriggered: {
      Style.cornerRadius = 6
      var w = formPopup.cardItem.Window.window
      if (w && !w.active)
        w.requestActivate()
      settle.start()
    }
  }

  function centerX(item, ref) {
    return item.mapToItem(ref, 0, 0).x + item.width / 2
  }

  Timer {
    id: settle
    interval: 500
    onTriggered: {
      // Centred band (clock).
      var clock = clockPopup.bodyItem
      var band = clock.band
      check(band.centered && !band.titleRow.showTitle, "centred band hides the title row's icon and text")
      check(near(centerX(clock.time, band), band.width / 2, 2), "hero centred " + centerX(clock.time, band) + " of " + band.width)
      var g = findByName(clock.glyphBand, "foamyHeaderGlyph")
      check(g && g.visible && g.children[0].text === "\u{f02bb}", "iconGlyph draws the font glyph in the title row")
      check(g && g.children[0].font.family === FoamyStyle.monoFamily, "iconGlyph defaults to the mono font")
      var gi = findByName(clock.glyphBand, "foamyHeaderIcon")
      check(gi && gi.visible === false, "iconGlyph hides the Lucide icon")
      var t = findByName(band, "foamyHeroBandCenteredTitle")
      check(t && t.visible, "centred title shown")
      if (t) {
        check(near(t.x + t.width / 2, band.width / 2, 1), "title column centred")
        check(t.mapToItem(band, 0, 0).y > clock.time.mapToItem(band, 0, 0).y + clock.time.height - 1, "big time above the date")
      }
      var s = band.settingsButton.mapToItem(band, 0, 0)
      if (shell.rtl)
        check(s.x < FoamyStyle.padding + 2, "RTL: settings in the top left corner " + s.x)
      else
        check(s.x + band.settingsButton.width > band.width - FoamyStyle.padding - 2, "LTR: settings in the top right corner " + s.x)
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
      var line = r.y
      check(near(line - 1, footer.height - line - footer.refreshButton.height), "footer: row centred between hairline and bottom " + (line - 1) + " / " + (footer.height - line - footer.refreshButton.height))
      check(st.text === "Updated 3 minutes ago", "footer status text")

      // Buttons.
      var page = formPopup.bodyItem
      check(!Qt.colorEqual(page.primary.color, page.secondary.color) && !Qt.colorEqual(page.destructive.color, page.secondary.color), "kinds have their own fill")
      check(page.secondary.border.width >= 1 && page.destructive.border.width >= 1, "secondary/destructive are bordered")
      page.secondary.forceActiveFocus()
      ev.keyClick(Qt.Key_Tab, Qt.NoModifier, -1)
      check(page.primary.activeFocus && page.primary.border.width > page.destructive.border.width, "Tab moves to the next button, which shows a focus ring " + [page.primary.activeFocus, page.primary.border.width, page.destructive.border.width])
      page.primary.forceActiveFocus()
      ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
      check(shell.applies === 1, "Enter activates the focused button " + shell.applies)
      // A busy button takes no key; it stays busy until the pointer check.
      shell.verifying = true
      page.secondary.forceActiveFocus()
      ev.keyClick(Qt.Key_Space, Qt.NoModifier, -1)
      ev.keyClick(Qt.Key_Return, Qt.NoModifier, -1)
      check(page.secondary.activeFocus && shell.verifies === 0, "a busy button ignores Space and Enter " + shell.verifies)
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
      check(findByName(ta, "foamyToggleDivider").visible && !findByName(page.toggleB, "foamyToggleDivider").visible, "divider only where asked")
      // Compact number fields: one row, narrow field, units lined up.
      var cpu = page.cpu, margin = page.margin
      var cf = cpu.field.mapToItem(page, 0, 0), mf = margin.field.mapToItem(page, 0, 0)
      check(cpu.field.width < cpu.width / 3 && cpu.field.width >= cpu.compactFieldWidth - 1, "compact field is narrow " + cpu.field.width + " of " + cpu.width)
      if (shell.rtl)
        check(near(cf.x, mf.x), "RTL: stacked compact fields line up at their unit side " + cf.x + " / " + mf.x)
      else
        check(near(cf.x + cpu.field.width, mf.x + margin.field.width), "stacked compact fields line up at their unit side " + (cf.x + cpu.field.width) + " / " + (mf.x + margin.field.width))
      if (shell.rtl)
        check(cf.x < cpu.mapToItem(page, 0, 0).x + cpu.width / 2, "RTL: field toward the left")
      else
        check(cf.x > cpu.mapToItem(page, 0, 0).x + cpu.width / 2, "field toward the end")
      // hasHero counts shown hero items only.
      var hb = clock.hiddenHeroBand
      hb.visible = true
      check(!hb.hasHero, "a hidden hero item is no hero")
      clock.hiddenHero.visible = true
      check(hb.hasHero, "shown again, it is")
      // A closed popup or an open settings page hides the band: it still
      // answers whether it has hero items (plugins read it then).
      hb.visible = false
      check(hb.hasHero, "a hidden band still answers that it has hero items")

      // FoamyPopupCard's height follows the screen.
      check(tallCard.availableCardHeight > FoamyStyle.popupMaxHeight, "screen allows more than 640 " + tallCard.availableCardHeight)
      check(tallCard.cardItem.height > FoamyStyle.popupMaxHeight && tallCard.cardItem.height <= tallCard.availableCardHeight + 2, "FoamyPopupCard follows the screen " + tallCard.cardItem.height + " of " + tallCard.availableCardHeight)
      capture.start()
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

  // Screenshots (one popup at a time on top).
  Timer {
    id: capture
    interval: 400
    property var queue: [["clock", clockPopup], ["weather", weatherPopup], ["form", formPopup]]
    onTriggered: {
      if (queue.length === 0) {
        // The popups share one window: a pointer check needs its card
        // alone on top, so the others close first.
        weatherPopup.open = false
        formPopup.open = false
        tallCard.open = false
        clockPointer.start()
        return
      }
      var item = queue.shift()
      item[1].cardItem.grabToImage(function (result) {
        result.saveToFile(Quickshell.env("FOAMY_OUT") + "/" + item[0] + ".png")
        capture.start()
      })
    }
  }

  function clickCentre(item) {
    ev.mouseClick(item, item.width / 2, item.height / 2, Qt.LeftButton, Qt.NoModifier, -1)
  }

  Timer {
    id: clockPointer
    interval: 600
    onTriggered: {
      clickCentre(clockPopup.bodyItem.footer.refreshButton)
      check(shell.refreshes === 1, "a click on refresh emits refreshClicked " + shell.refreshes)
      clockPopup.open = false
      weatherPopup.open = true
      weatherPointer.start()
    }
  }

  Timer {
    id: weatherPointer
    interval: 600
    onTriggered: {
      var refresh = weatherPopup.bodyItem.footer.refreshButton
      clickCentre(refresh)
      check(refresh.spinning && shell.weatherRefreshes === 0, "refreshing: the spinning refresh button ignores a click " + shell.weatherRefreshes)
      shell.weatherRefreshing = false
      clickCentre(refresh)
      check(shell.weatherRefreshes === 1, "done refreshing, the same click refreshes " + shell.weatherRefreshes)
      weatherPopup.open = false
      formPopup.open = true
      pointerStep.start()
    }
  }

  Timer {
    id: pointerStep
    interval: 600
    onTriggered: {
      var page = formPopup.bodyItem
      var ta = page.toggleA
      var fill = findByName(ta, "foamyToggleFill")
      // Hover first, before any click lands on the row: it lights up under
      // the pointer (the colour animates).
      wait.waitFor(function () {
        return fill.color.a === 0
      }, 1000, function () {
        ev.mouseMove(ta, ta.width / 2, ta.height / 2, -1, Qt.NoButton, Qt.NoModifier)
        wait.waitFor(function () {
          return fill.color.a > 0
        }, 1000, function () {
          shell.clicks()
        }, tag + " hover lights the row")
      }, tag + " the row is unlit before the pointer reaches it")
    }
  }

  function clicks() {
    var page = formPopup.bodyItem
    var ta = page.toggleA
    ev.mouseClick(ta, ta.width / 2, ta.height / 2, Qt.LeftButton, Qt.NoModifier, -1)
    check(shell.toggleClicks === 1 && !ta.checked, "click emits clicked, never flips checked " + shell.toggleClicks)
    clickCentre(page.secondary)
    check(shell.verifies === 0, "a busy button ignores a click " + shell.verifies)
    shell.verifying = false
    clickCentre(page.secondary)
    check(shell.verifies === 1, "no longer busy, the same click verifies " + shell.verifies)
    console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
    console.log("FOAMY DONE")
    Qt.quit()
  }

  Item {
    parent: formPopup.bodyItem
    TestEvent {
      id: ev
    }
  }
}
