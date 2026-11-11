import QtQuick
import Quickshell

// Offscreen stand-in for Quickshell's PanelWindow, used only by the preview
// and test harness (offscreen Qt has no layer-shell backend). The host's
// KeyboardPanel.qml is loaded with its window type swapped for this item;
// everything else in it (geometry, motion, content) is the host's real code.
// The surface is drawn into FakeDisplay.overlay, which stands for the screen.
Item {
  id: root
  property var screen: null
  property color color: "transparent"
  property int exclusionMode: 0
  property QtObject mask: null
  property string layerNamespace: ""
  readonly property bool backingWindowVisible: visible
  readonly property FakeAnchors windowAnchors: FakeAnchors {}
  parent: FakeDisplay.overlay
  x: 0
  y: 0
  width: screen ? screen.width : 0
  height: screen ? screen.height : 0
  z: 100
}
