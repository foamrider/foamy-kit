import QtQuick
import QtQuick.Layouts
import qs.Commons as Commons
import qs.Ui
import "FoamyText.js" as FoamyText

// Settings page header: back button, "Settings", and "Saving…" while a save
// is in flight. Part of FoamySettingsPage; use it alone only for a custom page.
// A sub-view built like the settings page (an editor page) may put icon
// actions (FoamyAction) at the trailing end with `trailing`, after "Saving…".
//
// Title action (off by default): with `titleAction: true` the title is a
// control that opens something about it (an editor page's place: the move
// menu). It shows `titleIconName` (in `titleIconColor`) before the title and
// a chevron after it, on a hover fill, with the keys' ring; it is the next
// Tab stop after Back. A click, Enter or Space emits
// `titleActivated(keyboard)` (true from the keys, for FoamyMenu.open).
// `titleAccessibleName` names the button (default: the title); a title cut
// with "…" shows whole in a tooltip on hover, wrapped, at most the header's
// width. `titleButton` is the control (give it the keys back with
// forceActiveFocus()); `titleMenuAnchor` is an item as wide as a FoamyMenu
// (FoamyStyle.menuWidth) at the control's start: a menu anchored to it
// hangs under the control from its start. Off, the title is the plain text
// it always was.
Item {
  id: root

  property string title: FoamyI18n.t("Settings")
  property bool saving: false
  property alias backButton: backButton
  property alias trailing: trailingRow.data
  property real horizontalPadding: FoamyStyle.padding
  property real topPadding: FoamyStyle.padding
  property real bottomPadding: FoamyStyle.padding

  property bool titleAction: false
  property string titleIconName: ""
  property color titleIconColor: FoamyPalette.secondaryText
  property string titleAccessibleName: title
  readonly property alias titleButton: titleButton
  readonly property alias titleMenuAnchor: titleMenuAnchor

  signal back
  signal titleActivated(bool keyboard)

  implicitHeight: Math.max(FoamyStyle.settingsButtonSize, titleText.implicitHeight) + topPadding + bottomPadding

  RowLayout {
    anchors.fill: parent
    anchors.leftMargin: root.horizontalPadding
    anchors.rightMargin: root.horizontalPadding
    anchors.topMargin: root.topPadding
    anchors.bottomMargin: root.bottomPadding
    spacing: FoamyStyle.gap

    FoamyAction {
      id: backButton
      settings: true
      focusable: true
      iconName: "arrow-left"
      foreground: FoamyPalette.secondaryText
      tooltipText: FoamyI18n.t("Back")
      Layout.alignment: Qt.AlignVCenter
      onClicked: root.back()
    }
    Text {
      id: titleText
      visible: !root.titleAction
      Layout.fillWidth: true
      Layout.alignment: Qt.AlignVCenter
      text: root.title
      textFormat: Text.PlainText
      horizontalAlignment: Text.AlignLeft
      elide: Text.ElideRight
      color: FoamyPalette.text
      font.family: FoamyStyle.fontFamily
      font.pixelSize: FoamyStyle.font.title
      font.weight: Font.DemiBold
    }
    // The title action: as wide as its content, at most the room left.
    Item {
      id: titleSlot
      visible: root.titleAction
      Layout.fillWidth: true
      Layout.alignment: Qt.AlignVCenter
      implicitHeight: titleButton.height

      Rectangle {
        id: titleButton
        objectName: "foamyTitleAction"
        readonly property real padding: FoamyStyle.gap
        readonly property bool hovered: titleMouse.containsMouse
        // Everything but the title's words: paddings, mark, chevron.
        readonly property real chrome: padding * 2 + (titleMark.visible ? titleMark.width + titleContent.spacing : 0) + titleContent.spacing + titleChevron.width
        // Anchored, so a mirrored header starts it at the right.
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        implicitWidth: chrome + titleLabel.implicitWidth
        width: Math.min(implicitWidth, titleSlot.width)
        height: FoamyStyle.settingsButtonSize
        radius: FoamyStyle.radius
        color: titleMouse.containsMouse || activeFocus ? FoamyPalette.hoverFill : "transparent"
        border.width: activeFocus ? 1 : 0
        border.color: Commons.Color.accent
        // Off, the slot is hidden: never a Tab stop. (Bound to titleAction,
        // Qt warns when it turns off while the control has the keys.)
        activeFocusOnTab: true

        Behavior on color {
          ColorAnimation {
            duration: FoamyMotion.hover
          }
        }

        Accessible.role: Accessible.Button
        Accessible.name: root.titleAccessibleName
        Accessible.onPressAction: root.titleActivated(false)
        Keys.onPressed: function (event) {
          if (event.key === Qt.Key_Space || event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            event.accepted = true
            root.titleActivated(true)
          }
        }

        Row {
          id: titleContent
          anchors.left: parent.left
          anchors.leftMargin: titleButton.padding
          anchors.verticalCenter: parent.verticalCenter
          spacing: FoamyStyle.gapSmall
          FoamyIcon {
            id: titleMark
            visible: root.titleIconName !== ""
            anchors.verticalCenter: parent.verticalCenter
            width: FoamyStyle.iconSize
            height: width
            name: root.titleIconName
            color: root.titleIconColor
          }
          Text {
            id: titleLabel
            objectName: "foamyTitleActionText"
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(0, titleButton.width - titleButton.chrome)
            text: root.title
            textFormat: Text.PlainText
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideRight
            color: FoamyPalette.text
            font.family: FoamyStyle.fontFamily
            font.pixelSize: FoamyStyle.font.title
            font.weight: Font.DemiBold
          }
          FoamyIcon {
            id: titleChevron
            anchors.verticalCenter: parent.verticalCenter
            width: FoamyStyle.iconSize
            height: width
            name: "chevron-down"
            color: FoamyPalette.secondaryText
          }
        }

        MouseArea {
          id: titleMouse
          anchors.fill: parent
          hoverEnabled: true
          cursorShape: Qt.PointingHandCursor
          onClicked: root.titleActivated(false)
        }

        // Cut: the whole title on hover, at most as wide as the header.
        PanelToolTip {
          id: titleTip
          objectName: "foamyTitleActionTip"
          visible: titleMouse.containsMouse && titleLabel.truncated
          implicitWidth: Math.min(implicitContentWidth + leftPadding + rightPadding, root.width)
          text: FoamyText.cap(root.title, 3, 200)
          // The host's text wraps at word boundaries only; a name typed
          // without spaces may break anywhere.
          Binding {
            target: titleTip.contentItem
            property: "wrapMode"
            value: Text.WrapAtWordBoundaryOrAnywhere
            when: titleTip.contentItem !== null
          }
        }
      }

      // A FoamyMenu's width at the control's start (the menu's trailing
      // edge goes on its anchor's): the menu hangs from the control's start.
      Item {
        id: titleMenuAnchor
        objectName: "foamyTitleMenuAnchor"
        anchors.left: titleButton.left
        anchors.top: titleButton.top
        width: FoamyStyle.menuWidth
        height: titleButton.height
      }
    }
    Text {
      visible: root.saving
      Layout.alignment: Qt.AlignVCenter
      text: FoamyI18n.t("Saving…")
      textFormat: Text.PlainText
      color: FoamyPalette.secondaryText
      font.family: FoamyStyle.fontFamily
      font.pixelSize: FoamyStyle.font.bodySmall
    }
    Row {
      id: trailingRow
      visible: children.length > 0
      Layout.alignment: Qt.AlignVCenter
      spacing: FoamyStyle.gapSmall
    }
  }
}
