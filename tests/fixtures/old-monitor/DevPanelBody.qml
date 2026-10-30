import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Commons

// Reduced from foamy-monitor `dev` Panel.qml: ordinary items with grouped
// `anchors { … }` blocks, plus a Variants delegate that is a layer-shell
// PanelWindow (the Identify overlay). The trio's dev rewrite must swap only
// the window, not the items' anchors blocks (kit 0.3.0 broke this file).
Item {
  id: root
  property bool identifyVisible: false
  property string label: ""
  implicitWidth: 400
  implicitHeight: 160

  Rectangle {
    anchors {
      left: parent.left
      right: parent.right
      top: parent.top
      bottom: parent.bottom
    }
    color: Color.popups.background
    Text {
      anchors {
        centerIn: parent
      }
      text: root.label
      color: Color.popups.text
    }
  }

  Variants {
    model: Quickshell.screens
    delegate: PanelWindow {
      id: identifyWindow
      required property var modelData
      screen: modelData
      visible: root.identifyVisible
      exclusionMode: ExclusionMode.Ignore
      implicitWidth: 300
      implicitHeight: 120
      color: "transparent"
      WlrLayershell.layer: WlrLayer.Overlay
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
      WlrLayershell.namespace: "foamy-monitor-identify"
      mask: Region {}
      anchors {
        top: true
        left: true
      }
      Rectangle { anchors.fill: parent; color: Color.accent }
    }
  }
}
