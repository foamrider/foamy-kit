import QtQuick
import Quickshell.Io
import "kit/FoamyNative.js" as FoamyNative

// The smallest FoamyNative consumer: runs the bundled helper once and keeps
// its reply, or notes that no helper exists for this CPU.
Item {
  id: root
  property string reply: ""
  property bool unavailable: false

  Process {
    running: true
    command: FoamyNative.command(FoamyNative.localPath(Qt.resolvedUrl(".")), "foamy-native-demo-helper", ["version"])
    stdout: StdioCollector { onStreamFinished: root.reply = this.text }
    onExited: function(exitCode) { root.unavailable = FoamyNative.unavailable(exitCode) }
  }
}
