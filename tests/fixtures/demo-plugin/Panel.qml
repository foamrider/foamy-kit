import QtQuick
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "kit"
import "kit/FoamyPrefs.js" as Prefs
import "Preferences.js" as Schema

// Reference foamy bar widget built only from foamy-kit parts: FoamyPopup
// with a lazy body, single-cursor keyboard model, settings page, inline
// settings saving, one shared poller and one IPC target per shell.
Panel {
  id: root
  ipcTarget: "foamy.kit-demo"
  manageIpc: false

  property bool editingSettings: false
  property bool saving: false
  property string settingsError: ""
  property var lastSave: null
  readonly property alias popup: popup
  readonly property bool showCount: Prefs.value(Schema.fields, settings, "showCount")
  readonly property int refreshSeconds: Prefs.value(Schema.fields, settings, "refreshSeconds")

  // Once per shell: only the leader polls, faster while any popup is open.
  FoamyMember { id: member; scope: "poller"; demanding: root.opened }
  Timer {
    running: member.isLeader
    repeat: true
    interval: (member.demanded ? 5 : root.refreshSeconds) * 1000
    onTriggered: DemoService.refresh()
  }

  FoamyIpc {
    target: "foamy.kit-demo"
    enabled: member.isLeader
    function toggle(): void { root.toggle() }
    function settings(): void { root.openSettings() }
    function status(): string { return JSON.stringify({ open: root.opened, devices: DemoService.devices.length, leader: member.isLeader }) }
  }

  function openSettings() { editingSettings = true; open() }
  function closeSettings() { editingSettings = false }

  function save(key, next) {
    settingsError = ""
    var result = Prefs.save(root.bar, root.moduleName, Schema.fields, root.settings, key, next)
    lastSave = { key: key, value: next }
    if (!result.ok) { settingsError = FoamyI18n.t(result.error); return }
    if (result.command.length === 0) return
    saving = true
    saveProcess.command = result.command
    saveProcess.running = true
  }

  Process {
    id: saveProcess
    onExited: function(code) {
      root.saving = false
      root.settingsError = code === 0 ? "" : FoamyI18n.t("Couldn't save the setting.")
    }
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.showCount ? String(DemoService.devices.length) : ""
    onPressed: function(b) { root.toggle() }
  }

  FoamyPopup {
    id: popup
    anchorItem: button
    bar: root.bar
    owner: root
    open: root.opened
    body: Component {
      DemoView {
        devices: DemoService.devices
        settings: root.settings
        editingSettings: root.editingSettings
        saving: root.saving
        settingsError: root.settingsError
        onCloseRequestedByView: root.editingSettings ? root.closeSettings() : root.close()
        onSettingsRequested: root.openSettings()
        onSettingsClosed: root.closeSettings()
        onRefreshRequested: DemoService.refresh()
        onSaveRequested: function(key, value) { root.save(key, value) }
        onSwitchPanelRequested: function(direction) { root.switchPanel(direction) }
      }
    }
  }
}
