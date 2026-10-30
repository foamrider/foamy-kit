import QtQuick
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "kit"
import "Preferences.js" as Schema

// Reference foamy bar widget built only from foamy-kit parts: FoamyPopup
// with a lazy body, single-cursor keyboard model, settings page
// (FoamySettingsState), queued settings saving (FoamyPrefsQueue), one
// shared poller and one IPC target per shell.
Panel {
  id: root
  ipcTarget: "foamy.kit-demo"
  manageIpc: false

  readonly property alias popup: popup
  readonly property alias prefs: prefs
  readonly property bool editingSettings: settingsState.editing
  readonly property bool showCount: prefs.value("showCount")
  readonly property int refreshSeconds: prefs.value("refreshSeconds")

  FoamySettingsState { id: settingsState; panel: root }
  FoamyPrefsQueue {
    id: prefs
    bar: root.bar
    moduleName: root.moduleName
    fields: Schema.fields
    settings: root.settings
  }

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

  function openSettings() { settingsState.show() }
  function closeSettings() { settingsState.hide() }
  function save(key, next) { return prefs.save(key, next) }

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
        settings: prefs.effectiveSettings
        editingSettings: root.editingSettings
        saving: prefs.saving
        settingsError: FoamyI18n.t(prefs.error)
        canRetry: prefs.canRetry
        onRetryRequested: prefs.retry()
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
