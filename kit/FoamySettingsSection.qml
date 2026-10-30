import QtQuick

// A titled group of settings rows. Titles are sentence case ("Bar", "Refresh").
//
//   FoamySettingsSection {
//     title: FoamyI18n.t("Bar")
//     Toggle { width: parent.width; label: FoamyI18n.t("Show percentage in the bar"); … }
//   }
Column {
  id: root

  property string title: ""
  property string description: ""
  default property alias content: rows.data

  spacing: FoamyStyle.gap

  Text {
    visible: root.title !== ""
    width: parent.width
    text: root.title
    textFormat: Text.PlainText
    horizontalAlignment: Text.AlignLeft
    wrapMode: Text.WordWrap
    color: FoamyPalette.secondaryText
    font.family: FoamyStyle.fontFamily
    font.pixelSize: FoamyStyle.font.bodySmall
    font.weight: Font.DemiBold
    Accessible.role: Accessible.Heading
  }
  Text {
    visible: root.description !== ""
    width: parent.width
    text: root.description
    textFormat: Text.PlainText
    horizontalAlignment: Text.AlignLeft
    wrapMode: Text.WordWrap
    color: FoamyPalette.mutedText
    font.family: FoamyStyle.fontFamily
    font.pixelSize: FoamyStyle.font.bodySmall
  }
  Column {
    id: rows
    width: parent.width
    spacing: FoamyStyle.gap
  }
}
