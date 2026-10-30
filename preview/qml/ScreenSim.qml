import QtQuick
import qs.Ui

// A simulated 1920x1080 screen: wallpaper, the bar strip on `position`, a
// few widget icons, and the overlay that FakePanelWindow surfaces draw into.
// `anchor` is the plugin's bar button. With `fullScreenBar` (4.5) this item
// lives in the bar's own full-screen window; otherwise (4.0) the button sits
// in a separate strip window and this only paints a copy for screenshots.
Item {
  id: root
  property string position: "top"
  property int thickness: 34
  property real anchorAlong: 0.78
  property bool fullScreenBar: true
  property color barColor: Qt.alpha(stripColor, 0.96)
  property color stripColor: "black"
  property color iconColor: "white"
  readonly property bool vertical: position === "left" || position === "right"
  readonly property alias overlay: overlay
  readonly property alias content: content
  readonly property alias anchor: anchorIcon

  width: 1920
  height: 1080
  clip: true

  Rectangle {
    anchors.fill: parent
    gradient: Gradient {
      GradientStop { position: 0; color: Qt.darker(root.iconColor, 6.5) }
      GradientStop { position: 1; color: Qt.darker(root.iconColor, 3.2) }
    }
  }

  Rectangle {
    id: strip
    color: root.barColor
    x: root.position === "right" ? root.width - root.thickness : 0
    y: root.position === "bottom" ? root.height - root.thickness : 0
    width: root.vertical ? root.thickness : root.width
    height: root.vertical ? root.height : root.thickness
    Repeater {
      model: 9
      Rectangle {
        required property int index
        readonly property real along: 0.05 + index * 0.032
        width: 14; height: 14; radius: 3
        color: Qt.alpha(root.iconColor, 0.55)
        x: root.vertical ? (root.thickness - width) / 2 : root.width * along
        y: root.vertical ? root.height * along : (root.thickness - height) / 2
      }
    }
  }

  // The plugin button. In 4.0 mode the real anchor lives in the strip window;
  // this one is painted so the screenshot shows where the popup hangs from.
  Rectangle {
    id: anchorIcon
    width: 22; height: 22; radius: 5
    color: Qt.alpha(root.iconColor, 0.9)
    x: root.vertical ? strip.x + (root.thickness - width) / 2 : root.width * root.anchorAlong
    y: root.vertical ? root.height * root.anchorAlong : strip.y + (root.thickness - height) / 2
  }

  // Preview items drawn in screen coordinates (service toasts, card copies).
  Item {
    id: content
    anchors.fill: parent
    z: 50
  }

  Item {
    id: overlay
    anchors.fill: parent
    z: 100
    Component.onCompleted: FakeDisplay.overlay = overlay
  }
}
