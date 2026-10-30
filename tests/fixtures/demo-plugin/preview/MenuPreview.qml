import QtQuick
import "../kit"

// A FoamyPopupCard (menu) preview: `popup` is declared `var` because a
// PopupCard is a window, not an Item. The harness copies its card onto the
// simulated screen at its anchor.
Item {
  id: preview
  required property QtObject bar
  required property Item anchorItem
  property var previewStates: ["menu"]
  property string previewState: "menu"
  readonly property var popup: menu

  FoamyPopupCard {
    id: menu
    anchorItem: preview.anchorItem
    bar: preview.bar
    open: true
    body: Component {
      Column {
        spacing: FoamyStyle.gapTiny
        Repeater {
          model: ["Open", "Pause syncing", "Quit"]
          FoamyCursorSurface {
            required property string modelData
            width: FoamyStyle.menuWidth - FoamyStyle.menuPadding * 2
            height: FoamyStyle.controlHeight
            Text {
              anchors.verticalCenter: parent.verticalCenter
              x: FoamyStyle.rowPadding
              text: modelData
              textFormat: Text.PlainText
              color: FoamyPalette.text
              font.family: FoamyStyle.fontFamily
              font.pixelSize: FoamyStyle.font.body
            }
          }
        }
      }
    }
  }
}
