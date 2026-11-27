import QtQuick
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"

// The kit's UI font (FoamyStyle.fontFamily) as Qt resolves it: the family
// asked for, what a FoamyHeroBand's DemiBold title draws with (QFontInfo
// through Text.fontInfo), and the width of one text in Normal, DemiBold and
// Bold, in the kit's font and in the system's "sans-serif" (the kit's font
// before 0.17.0). One FOAMY FONT line of JSON for test_ui_font.py, which knows what
// this run's fontconfig offers; both sample texts are saved to FOAMY_OUT.
ShellRoot {
  id: shell
  readonly property string tag: Quickshell.env("FOAMY_TAG")
  readonly property string sample: "Settings and sync · Wednesday 27 November"

  function findTitle(item, text) {
    if (!item)
      return null
    if (item.text === text && item.font !== undefined && item.fontInfo !== undefined)
      return item
    for (var i = 0; i < item.children.length; i++) {
      var found = findTitle(item.children[i], text)
      if (found)
        return found
    }
    return null
  }
  function info(text) {
    return {
      "family": text.fontInfo.family,
      "style": text.fontInfo.styleName,
      "weight": text.fontInfo.weight,
      "width": text.advance.width
    }
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
        property alias kit: kit
        property alias system: system
        FoamyHeroBand {
          id: band
          width: parent.width
          iconName: "battery-charging"
          title: "Power"
          meta: "41% · Charging"
        }
        Repeater {
          id: kit
          model: [Font.Normal, Font.DemiBold, Font.Bold]
          Text {
            required property int modelData
            text: shell.sample
            color: FoamyPalette.text
            font.family: FoamyStyle.fontFamily
            font.pixelSize: FoamyStyle.font.title
            font.weight: modelData
          }
        }
        Repeater {
          id: system
          model: [Font.Normal, Font.DemiBold, Font.Bold]
          Text {
            required property int modelData
            text: shell.sample
            color: FoamyPalette.text
            font.family: "sans-serif"
            font.pixelSize: FoamyStyle.font.title
            font.weight: modelData
          }
        }
      }
    }
  }

  Timer {
    interval: 400
    running: true
    onTriggered: {
      var body = popup.bodyItem
      var title = shell.findTitle(body.band, "Power")
      var kit = [], system = []
      for (var i = 0; i < 3; i++) {
        kit.push(shell.info(body.kit.itemAt(i)))
        system.push(shell.info(body.system.itemAt(i)))
      }
      console.log("FOAMY FONT " + JSON.stringify({
        "fontFamily": FoamyStyle.fontFamily,
        "title": title ? shell.info(title) : null,
        "titleWeight": title ? title.font.weight : null,
        "kit": kit,
        "system": system
      }))
      shell.save(body.kit.itemAt(1), "kit", function () {
        shell.save(body.system.itemAt(1), "system", function () {
          console.log("FOAMY RESULT " + tag)
          console.log("FOAMY DONE")
          Qt.quit()
        })
      })
    }
  }
  function save(item, name, next) {
    item.grabToImage(function (result) {
      if (!result.saveToFile(Quickshell.env("FOAMY_OUT") + "/" + name + ".png"))
        console.log("FOAMY FAIL " + tag + " saved " + name)
      next()
    })
  }
}
