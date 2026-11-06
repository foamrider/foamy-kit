import QtQuick
import Quickshell
import Quickshell.Io
import "plugin/kit/FoamyNative.js" as FoamyNative

// FoamyNative.command in Quickshell's Process: the fixture plugin's built
// helper runs with its arguments verbatim, and a missing helper reports a
// normal exit 127 (Process gives no exit at all for a missing executable).
ShellRoot {
  id: root
  property int checks: 0
  property string pluginDir: FoamyNative.localPath(Quickshell.env("FOAMY_PLUGIN_URL"))
  property int stage: 0
  property var exitCode: null
  property var text: null

  function check(ok, label) {
    checks++
    if (!ok) console.log("FOAMY FAIL " + label)
  }

  function start(name, args) {
    exitCode = null
    text = null
    proc.command = FoamyNative.command(pluginDir, name, args)
    proc.running = true
  }

  function settle() {
    if (exitCode === null || text === null) return
    if (stage === 0) {
      check(exitCode === 0, "helper exits 0 (got " + exitCode + ")")
      var reply = {}
      try { reply = JSON.parse(text) } catch (error) { check(false, "helper reply is JSON: " + text) }
      check(reply.ok === true && JSON.stringify(reply.args) === JSON.stringify(["two words", "", "$HOME"]),
            "arguments arrive verbatim: " + text)
      check(!FoamyNative.unavailable(exitCode), "a running helper is available")
      stage = 1
      start("foamy-missing-helper", ["x"])
    } else if (stage === 1) {
      check(exitCode === 127, "a missing helper exits 127 (got " + exitCode + ")")
      check(FoamyNative.unavailable(exitCode), "unavailable() for a missing helper")
      stage = 2
      console.log("FOAMY RESULT checks=" + checks)
      console.log("FOAMY DONE")
      Qt.quit()
    }
  }

  Process {
    id: proc
    stdout: StdioCollector { onStreamFinished: { root.text = this.text; root.settle() } }
    onExited: function(exitCode) { root.exitCode = exitCode; root.settle() }
  }

  Timer {
    interval: 20000
    running: true
    onTriggered: {
      check(false, "timed out in stage " + root.stage)
      console.log("FOAMY RESULT checks=" + checks)
      console.log("FOAMY DONE")
      Qt.quit()
    }
  }

  Component.onCompleted: start("foamy-native-demo-helper", ["args", "two words", "", "$HOME"])
}
