import QtQuick
import Quickshell.Io
import qs.Commons

Rectangle {
  color: Color.popups.background
  radius: Style.cornerRadius * 2
  border.color: "#ff6b6b"
  Text { font.family: "sans-serif" }
  Behavior on opacity { NumberAnimation { duration: 140 } }
  RotationAnimation on rotation { running: true; from: 0; to: 360; duration: FoamyMotion.spin; loops: Animation.Infinite }
  IpcHandler { target: "foamy.bad" }
  // foamy-lint: allow hex-colour
  property color noReason: "#123456"
  OpticalGlyph { width: 16; text: ""; color: "white" }
  OpticalGlyph {
    width: 16
    Text { text: "inner" }
    text: ''
  }
}
