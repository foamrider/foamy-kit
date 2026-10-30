import QtQuick
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"

// FoamyHeroBand inside a real FoamyPopup on the simulated screen: geometry
// against the card, compact form, picture background. FOAMY_RTL=1 mirrors
// the body. Captures go to FOAMY_OUT for pixel checks in test_band.py.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property bool rtl: Quickshell.env("FOAMY_RTL") === "1"
  readonly property string tag: Quickshell.env("FOAMY_TAG")
  property int checks: 0
  property int failures: 0
  function check(ok, label) { checks++; if (!ok) { failures++; console.log("FOAMY FAIL " + tag + " " + label) } }
  function near(a, b) { return Math.abs(a - b) <= 1 }

  FloatingWindow {
    implicitWidth: 1920
    implicitHeight: 1080
    color: "black"
    ScreenSim { id: sim; fullScreenBar: shell.host === "4.5" }
  }
  // 4.0 bars are strip windows (4.5 bars span the screen): as in the real hosts.
  FloatingWindow {
    visible: shell.host !== "4.5"
    implicitWidth: 1920
    implicitHeight: 34
    color: "black"
    Item { id: stripAnchor; x: sim.anchor.x; y: 6; width: 22; height: 22 }
  }
  MockBar { id: bar }

  FoamyPopup {
    id: popup
    anchorItem: shell.host === "4.5" ? sim.anchor : stripAnchor
    bar: bar
    open: true
    body: Component {
      Column {
        property alias band: band
        property alias compactBand: compactBand
        property alias pictureBand: pictureBand
        LayoutMirroring.enabled: shell.rtl
        LayoutMirroring.childrenInherit: true
        FoamyHeroBand {
          id: band
          width: parent.width
          iconName: "battery-charging"
          title: "Power"
          meta: "41% · Charging"
          Text { objectName: "heroValue"; text: "41%"; color: FoamyPalette.text; font.pixelSize: FoamyStyle.font.numeralCompact }
        }
        Item { width: 1; height: 120 }
        FoamyHeroBand { id: compactBand; width: parent.width; compact: true; topRadius: 0 }
        Item { width: 1; height: 20 }
        FoamyHeroBand { id: pictureBand; width: parent.width; title: "Artwork"; imageSource: Qt.resolvedUrl("plugin/preview/artwork.png") }
      }
    }
  }

  // A band-only popup (empty states): the band ends the card.
  FoamyPopup {
    id: bandOnly
    anchorItem: shell.host === "4.5" ? sim.anchor : stripAnchor
    bar: bar
    open: true
    centerOnBar: true
    body: Component {
      FoamyHeroBand {
        LayoutMirroring.enabled: shell.rtl
        title: "Nothing yet"
        meta: "No stations"
      }
    }
  }

  Timer {
    interval: 900
    running: true
    onTriggered: {
      Style.cornerRadius = 6
      settle.start()
    }
  }
  Timer {
    id: settle
    interval: 500
    onTriggered: {
      var card = popup.cardItem
      var band = popup.bodyItem.band
      var p = band.mapToItem(card, 0, 0)
      check(near(p.x, 1) && near(p.y, 1), "band starts at the card's inner edge " + p.x + "," + p.y)
      check(near(band.width, card.width - 2), "band is full bleed " + band.width + " of " + card.width)
      check(near(band.topRadius, card.radius - 1) && card.radius === 12, "band corners follow the popup radius " + band.topRadius)
      check(band.hasHero && band.height > popup.bodyItem.compactBand.height, "hero band is taller than the compact form")
      check(popup.bodyItem.compactBand.height >= FoamyStyle.settingsButtonSize + FoamyStyle.bandPaddingTop + FoamyStyle.bandPaddingBottom - 1, "compact band fits the back button")
      var icon = band.titleRow.children[0].children[0]
      var settings = band.settingsButton.mapToItem(band, 0, 0).x
      if (rtl) check(settings < band.width / 2, "RTL: settings button on the left " + settings)
      else check(settings > band.width / 2, "LTR: settings button on the right " + settings)
      check(band.mirrored === rtl, "band knows its direction")
      var hero = null
      for (var i = 0; i < band.hero.length; i++) if (band.hero[i].objectName === "heroValue") hero = band.hero[i]
      var heroX = hero ? hero.mapToItem(band, 0, 0).x : -1
      if (rtl) check(heroX + hero.width > band.width - FoamyStyle.padding - 2, "RTL: hero content starts on the right " + heroX)
      else check(near(heroX, FoamyStyle.padding), "LTR: hero content starts at the padding " + heroX)
      check(near(card.height, popup.bodyImplicitHeight + 2), "card fits the body " + card.height)
      console.log("FOAMY BAND " + JSON.stringify({ height: Math.round(band.height), y: Math.round(p.y), pictureY: Math.round(popup.bodyItem.pictureBand.mapToItem(card, 0, 0).y) }))
      check(!band.roundBottom && band.separator, "a band followed by content keeps a square bottom and the hairline")
      var only = bandOnly.bodyItem
      check(only && only.endsCard && only.roundBottom && !only.separator, "a band that ends the card rounds its bottom, no hairline")
      bandOnly.cardItem.grabToImage(function(r2) { r2.saveToFile(Quickshell.env("FOAMY_OUT") + "/band-only.png") })
      card.grabToImage(function(result) {
        if (!result.saveToFile(Quickshell.env("FOAMY_OUT") + "/band.png")) console.log("FOAMY FAIL save")
        console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
        console.log("FOAMY DONE")
        Qt.quit()
      })
    }
  }
}
