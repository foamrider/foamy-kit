import QtQuick
import "../kit"

// A pill; used by DemoTag by bare name (same-directory type, no qmldir).
Rectangle {
  property alias text: label.text
  implicitWidth: label.implicitWidth + FoamyStyle.gap * 2
  implicitHeight: label.implicitHeight + FoamyStyle.gapSmall
  radius: FoamyStyle.pillRadius(implicitHeight)
  color: FoamyPalette.hoverFill
  Text {
    id: label
    anchors.centerIn: parent
    textFormat: Text.PlainText
    color: FoamyPalette.secondaryText
    font.family: FoamyStyle.fontFamily
    font.pixelSize: FoamyStyle.font.caption
  }
}
