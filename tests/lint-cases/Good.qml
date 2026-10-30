import QtQuick
import qs.Commons as Commons
import "kit"

Rectangle {
  // Commons.Color.popups and "Color." in a string or comment are fine: Color.accent
  color: Commons.Color.popups.background
  property string doc: "use Color.accent"
  radius: FoamyStyle.radius
  property real twice: Style.cornerRadius * 2.5
  Text { font.family: FoamyStyle.fontFamily }
  Behavior on opacity { NumberAnimation { duration: FoamyMotion.fadeIn } }
  RotationAnimation on rotation {
    running: root.busy && !FoamyMotion.reduceMotion
    duration: FoamyMotion.spin
    loops: Animation.Infinite
  }
  SequentialAnimation {
    loops: Animation.Infinite
    running: FoamyMotion.loopAllowed(root.visible)
  }
  property color art: "#0b1d2a" // foamy-lint: allow hex-colour — lock-screen art surface
  // foamy-lint: allow bare-duration — shader clock, not UI motion
  NumberAnimation { duration: 60000 }
  property color textColor: "red"
  OpticalGlyph { width: 16; text: "\u{f0e7}" }
  OpticalGlyph { text: root.glyph; Text { text: "" } }
}
