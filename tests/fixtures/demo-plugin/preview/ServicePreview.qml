import QtQuick
import "../kit"

// A service-only preview (toasts, no bar popup): no bar or anchorItem is
// declared; `popup` is any Item with a `cardItem`, drawn in screen
// coordinates.
Item {
  id: preview
  anchors.fill: parent
  property var previewStates: ["toast"]
  property string previewState: "toast"
  readonly property Item popup: toast

  Rectangle {
    id: toast
    readonly property Item cardItem: toast
    x: parent.width - width - 16
    y: 50
    width: FoamyStyle.popupWidth
    height: 72
    radius: FoamyStyle.radius
    color: FoamyPalette.background
    border.color: FoamyPalette.border
    Text {
      anchors.centerIn: parent
      text: "Toast from a service plugin"
      textFormat: Text.PlainText
      color: FoamyPalette.text
      font.family: FoamyStyle.fontFamily
      font.pixelSize: FoamyStyle.font.body
    }
  }
}
