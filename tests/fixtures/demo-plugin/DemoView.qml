import QtQuick
import qs.Ui
import "kit"
import "components"

// The demo popup body: header, a cursor-driven device list, and the
// settings page, all from foamy-kit. Data comes in through properties so the
// preview can feed mock states; the Panel owns polling and saving.
PanelKeyCatcher {
  id: root

  property var devices: []
  property var settings: ({})
  property bool editingSettings: false
  property bool saving: false
  property string settingsError: ""
  property bool loading: false
  property bool canRetry: false
  property url artwork: ""
  readonly property int lowestBattery: devices.length ? Math.min.apply(null, devices.map(function(d) { return d.battery })) : 0

  signal closeRequestedByView()
  signal settingsRequested()
  signal settingsClosed()
  signal refreshRequested()
  signal saveRequested(string key, var value)
  signal switchPanelRequested(int direction)
  signal retryRequested()

  implicitWidth: FoamyStyle.popupWidth
  implicitHeight: editingSettings ? settingsPage.implicitHeight : list.implicitHeight
  blocked: editingSettings

  FoamyCursor { id: cursor; count: root.devices.length + 1 }   // rows, then settings

  onMoveRequested: function(dx, dy) { cursor.move(dy !== 0 ? dy : dx) }
  onActivateRequested: if (cursor.index === root.devices.length) root.settingsRequested()
  onCloseRequested: root.closeRequestedByView()
  onTabRequested: function(direction) { root.switchPanelRequested(direction) }
  onTextKey: function(text, modifiers) {
    if (!cursor.plain(modifiers)) return
    if (text === "s") root.settingsRequested()
    else if (text === "r") root.refreshRequested()
  }

  Column {
    id: list
    visible: !root.editingSettings
    width: parent.width
    bottomPadding: FoamyStyle.padding

    FoamyHeroBand {
      id: band
      width: parent.width
      iconName: "laptop"
      title: FoamyI18n.t("Devices")
      meta: FoamyI18n.tn("%1 devices", root.devices.length)
      imageSource: root.artwork
      settingsHasCursor: cursor.at(root.devices.length)
      onSettingsClicked: root.settingsRequested()
      onSettingsHovered: function(hovered) { if (hovered) cursor.hover(root.devices.length) }
      trailing: [
        FoamyAction {
          iconName: "refresh-cw"
          tooltipText: FoamyI18n.t("Refresh")
          spinning: root.loading
          onClicked: root.refreshRequested()
        }
      ]

      // Hero: the one number this panel is about, and its context.
      Row {
        visible: root.devices.length > 0
        spacing: FoamyStyle.gapLarge
        Text {
          text: FoamyI18n.number(root.lowestBattery)
          textFormat: Text.PlainText
          color: FoamyPalette.text
          font.family: FoamyStyle.fontFamily
          font.pixelSize: FoamyStyle.font.numeralCompact
          font.weight: Font.Light
        }
        Column {
          anchors.verticalCenter: parent.verticalCenter
          spacing: FoamyStyle.gapTiny
          Text {
            text: FoamyI18n.t("Lowest battery")
            textFormat: Text.PlainText
            color: FoamyPalette.text
            font.family: FoamyStyle.fontFamily
            font.pixelSize: FoamyStyle.font.subtitle
          }
          Text {
            text: FoamyI18n.t("%1% left", root.lowestBattery)
            textFormat: Text.PlainText
            color: FoamyPalette.secondaryText
            font.family: FoamyStyle.fontFamily
            font.pixelSize: FoamyStyle.font.bodySmall
          }
        }
      }
    }

    Item { width: 1; height: FoamyStyle.gap }

    Text {
      visible: root.devices.length === 0
      x: FoamyStyle.padding
      width: parent.width - FoamyStyle.padding * 2
      text: FoamyI18n.t("No devices")
      textFormat: Text.PlainText
      horizontalAlignment: Text.AlignLeft
      color: FoamyPalette.mutedText
      font.family: FoamyStyle.fontFamily
      font.pixelSize: FoamyStyle.font.bodySmall
    }

    Repeater {
      model: root.devices
      FoamyCursorSurface {
        required property var modelData
        required property int index
        x: FoamyStyle.gapLarge
        width: list.width - FoamyStyle.gapLarge * 2
        height: FoamyStyle.rowHeight + FoamyStyle.gap
        hasCursor: cursor.at(index)
        onHovered: cursor.hover(index)
        Row {
          anchors.verticalCenter: parent.verticalCenter
          x: FoamyStyle.rowPadding
          spacing: FoamyStyle.rowPadding
          FoamyIcon { name: modelData.icon; width: FoamyStyle.iconSize; height: width; anchors.verticalCenter: parent.verticalCenter }
          Column {
            anchors.verticalCenter: parent.verticalCenter
            Text {
              text: modelData.name
              textFormat: Text.PlainText
              color: FoamyPalette.text
              font.family: FoamyStyle.fontFamily
              font.pixelSize: FoamyStyle.font.body
            }
            Text {
              text: FoamyI18n.t("Battery %1%", modelData.battery)
              textFormat: Text.PlainText
              color: modelData.battery < 20 ? FoamyPalette.onSurface(FoamyPalette.warning) : FoamyPalette.secondaryText
              font.family: FoamyStyle.fontFamily
              font.pixelSize: FoamyStyle.font.caption
            }
          }
          DemoTag { battery: modelData.battery; anchors.verticalCenter: parent.verticalCenter }
        }
      }
    }
  }

  FoamySettingsPage {
    id: settingsPage
    visible: root.editingSettings
    width: parent.width
    height: parent.height
    saving: root.saving
    error: root.settingsError
    retryable: root.canRetry
    onBack: root.settingsClosed()
    onRetry: root.retryRequested()

    FoamySettingsSection {
      width: parent.width
      title: FoamyI18n.t("Bar")
      FoamyToggle {
        width: parent.width
        label: FoamyI18n.t("Show the count in the bar")
        checked: root.settings.showCount !== false
        onClicked: root.saveRequested("showCount", !checked)
      }
    }
    FoamySettingsSection {
      width: parent.width
      title: FoamyI18n.t("Refresh")
      FoamyDropdown {
        width: parent.width
        label: FoamyI18n.t("Refresh every")
        value: String(root.settings.refreshSeconds || 60)
        options: [{ value: "30", label: FoamyI18n.t("30 seconds") }, { value: "60", label: FoamyI18n.t("1 minute") }, { value: "300", label: FoamyI18n.t("5 minutes") }]
        onChanged: function(v) { root.saveRequested("refreshSeconds", Number(v)) }
      }
      FoamyNumberField {
        width: parent.width
        label: FoamyI18n.t("Warn below")
        unit: "%"
        value: root.settings.lowBattery !== undefined ? root.settings.lowBattery : 20
        from: 1; to: 100; stepSize: 5
        onCommitted: function(v) { root.saveRequested("lowBattery", v) }
      }
      SafeTextField {
        width: parent.width
        placeholderText: FoamyI18n.t("Name filter")
        translate: FoamyI18n.t
      }
    }
  }
}
