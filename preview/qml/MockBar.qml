import QtQuick

// The `bar` a third-party bar widget receives (Ui/PluginBarApi on 4.0 and
// 4.5): scalar state plus popout coordination. barSize only; no barSizeFor,
// exactly like the 4.5 plugin facade. MockFullBar adds barSizeFor.
QtObject {
  id: bar
  property string pluginId: "foamy.preview"
  property string moduleName: "foamy.preview"
  property string position: "top"
  readonly property bool vertical: position === "left" || position === "right"
  property int barSize: 34
  property color foreground: "white"
  property color barForeground: "white"
  property color background: "black"
  property color urgent: "red"
  property string fontFamily: "monospace"
  property bool transparent: false
  property bool foregroundAnimationEnabled: true
  property bool centerSectionRevealHeld: false
  property bool traySectionDragActive: false
  property bool traySectionPopoutOpen: false
  property var activePopout: null
  property var clickTargets: []
  property var layoutConfig: ({})
  property var lastCard: null
  property var saved: []
  property QtObject shell: QtObject {
    function updateEntryInline(id, settings) {
      bar.saved = bar.saved.concat([{ id: id, settings: settings }])
      return true
    }
  }
  function requestPopout(owner) { activePopout = owner }
  function releasePopout(owner) { if (activePopout === owner) activePopout = null }
  function notePopoutCard(card) { lastCard = card }
  function popoutCardFor(owner) { return null }
  function switchPanelFrom(owner, direction) { return false }
  function targetBelongsToWindow(target, window) { return false }
  function showTooltip(target, text) {}
  function hideTooltip(target) {}
  function registerClickTarget(target) {}
  function unregisterClickTarget(target) {}
  function moduleWidgets(id) { return [] }
  function run(command) {}
}
