import QtQuick
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"

// FoamyHeroBand inside a real FoamyPopup on the simulated screen: geometry
// against the card, compact form (with a trailing action), picture background. FOAMY_RTL=1 mirrors
// the body. Captures go to FOAMY_OUT for pixel checks in test_band.py.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property bool rtl: Quickshell.env("FOAMY_RTL") === "1"
  readonly property string tag: Quickshell.env("FOAMY_TAG")
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
    return Math.abs(a - b) <= 1
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
  FoamyWait {
    id: wait
  }

  FloatingWindow {
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

  FoamyPopup {
    id: popup
    anchorItem: sim.anchor
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
          Text {
            objectName: "heroValue"
            text: "41%"
            color: FoamyPalette.text
            font.pixelSize: FoamyStyle.font.numeralCompact
          }
        }
        Item {
          width: 1
          height: 120
        }
        FoamyHeroBand {
          id: compactBand
          width: parent.width
          compact: true
          topRadius: 0
          saving: true
          compactTrailing: [
            FoamyAction {
              objectName: "compactOpen"
              iconName: "external-link"
              tooltipText: "Open"
            }
          ]
        }
        Item {
          width: 1
          height: 20
        }
        FoamyHeroBand {
          id: pictureBand
          width: parent.width
          title: "Artwork"
          imageSource: Qt.resolvedUrl("plugin/preview/artwork.png")
        }
      }
    }
  }

  // A band-only popup (empty states): the band ends the card.
  FoamyPopup {
    id: bandOnly
    anchorItem: sim.anchor
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
      // compactTrailing: the action at the trailing end, after "Saving…",
      // centred on the back button; the band no taller for it.
      var compact = popup.bodyItem.compactBand
      var open = compact.compactTrailing[0]
      var back = compact.backButton
      var openX = open.mapToItem(compact, 0, 0).x
      var backX = back.mapToItem(compact, 0, 0).x
      check(open.visible && open.objectName === "compactOpen", "the compact band shows its trailing action")
      if (rtl)
        check(near(openX, FoamyStyle.padding) && backX > compact.width / 2, "RTL: the trailing action on the left, Back on the right " + openX + " / " + backX)
      else
        check(near(openX + open.width, compact.width - FoamyStyle.padding) && backX < compact.width / 2, "LTR: the trailing action on the right, Back on the left " + openX + " / " + backX)
      check(near(open.mapToItem(compact, 0, open.height / 2).y, back.mapToItem(compact, 0, back.height / 2).y), "the trailing action centred on Back")
      check(near(compact.height, FoamyStyle.settingsButtonSize + FoamyStyle.bandPaddingTop + FoamyStyle.bandPaddingBottom), "the trailing action keeps the compact height " + compact.height)
      var settings = band.settingsButton.mapToItem(band, 0, 0).x
      if (rtl)
        check(settings < band.width / 2, "RTL: settings button on the left " + settings)
      else
        check(settings > band.width / 2, "LTR: settings button on the right " + settings)
      var hero = null
      for (var i = 0; i < band.hero.length; i++)
        if (band.hero[i].objectName === "heroValue")
          hero = band.hero[i]
      var heroX = hero ? hero.mapToItem(band, 0, 0).x : -1
      if (rtl)
        check(heroX + hero.width > band.width - FoamyStyle.padding - 2, "RTL: hero content starts on the right " + heroX)
      else
        check(near(heroX, FoamyStyle.padding), "LTR: hero content starts at the padding " + heroX)
      check(near(card.height, popup.bodyImplicitHeight + 2), "card fits the body " + card.height)
      console.log("FOAMY BAND " + JSON.stringify({
        height: Math.round(band.height),
        y: Math.round(p.y),
        pictureY: Math.round(popup.bodyItem.pictureBand.mapToItem(card, 0, 0).y),
        pictureHeight: Math.round(popup.bodyItem.pictureBand.height)
      }))
      check(!band.roundBottom && band.separator, "a band followed by content keeps a square bottom and the hairline")
      var only = bandOnly.bodyItem
      check(only && only.endsCard && only.roundBottom && !only.separator, "a band that ends the card rounds its bottom, no hairline")
      bandOnly.cardItem.grabToImage(function (r2) {
        r2.saveToFile(Quickshell.env("FOAMY_OUT") + "/band-only.png")
      })
      // The band's Canvas loads its artwork asynchronously; test_band.py
      // reads the artwork's pixels from the shot.
      var picture = popup.bodyItem.pictureBand
      wait.waitFor(function () {
        return shell.findByName(picture, "foamyHeroBandSurface").isImageLoaded(picture.imageSource)
      }, 5000, shell.grabCard, "the picture band's artwork is loaded")
    }
  }
  function grabCard() {
    popup.cardItem.grabToImage(function (result) {
      if (!result.saveToFile(Quickshell.env("FOAMY_OUT") + "/band.png"))
        console.log("FOAMY FAIL save")
      console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
      console.log("FOAMY DONE")
      Qt.quit()
    })
  }
}
