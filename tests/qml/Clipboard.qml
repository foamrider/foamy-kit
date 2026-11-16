import QtQuick
import Quickshell
import Quickshell.Io
import "plugin/kit"

// FoamyClipboard (kit/FoamyClipboard.qml) against hostenv.clipboard_fakes()
// (tests/test_clipboard_reader.py): each case sets what the stand-in
// wl-paste does, starts a read and checks the one signal that follows.
ShellRoot {
  id: shell
  property int checks: 0
  property int failures: 0

  function check(ok, label) {
    checks++
    if (!ok) {
      failures++
      console.log("FOAMY FAIL " + label)
    }
  }

  readonly property string tooLarge: "Clipboard text is too large or contains invalid characters."
  readonly property string timedOut: "Clipboard paste timed out. Copy the text again."
  readonly property string couldNot: "Could not paste clipboard text. Copy plain text and try again."

  // One read each: the stand-in's mode, the selection, and the signal that
  // must follow ({read: text} or {failed: message}).
  readonly property var cases: [
    {
      mode: "normal",
      primary: false,
      expect: {
        read: "folder"
      }
    },
    {
      mode: "unicode",
      primary: true,
      expect: {
        read: "/home/test/Blåbær 📁"
      }
    },
    {
      mode: "empty",
      primary: false,
      expect: {
        read: ""
      }
    },
    {
      mode: "lines",
      primary: false,
      expect: {
        read: "one  two three"
      }
    },
    {
      mode: "limit",
      primary: false,
      expect: {
        read: "x".repeat(16384)
      }
    },
    {
      mode: "large",
      primary: false,
      expect: {
        failed: shell.tooLarge
      }
    },
    {
      mode: "nul",
      primary: false,
      expect: {
        failed: shell.tooLarge
      }
    },
    {
      mode: "stream",
      primary: false,
      expect: {
        failed: shell.tooLarge
      }
    },
    {
      mode: "failure",
      primary: false,
      expect: {
        failed: shell.couldNot
      }
    },
    {
      mode: "stall",
      primary: false,
      expect: {
        failed: shell.timedOut
      }
    }
  ]

  property var outcomes: []
  property int stage: 0
  property int caseIndex: 0
  property double since: 0
  property string cancelledPid: ""

  FoamyClipboard {
    id: clipboard
    onRead: function (text) {
      shell.outcomes = shell.outcomes.concat([
        {
          read: text
        }
      ])
    }
    onFailed: function (message) {
      shell.outcomes = shell.outcomes.concat([
        {
          failed: message
        }
      ])
    }
  }

  // Sets what the stand-in wl-paste does next.
  Process {
    id: fixture
    property bool done: false
    onExited: fixture.done = true
  }
  function setMode(mode) {
    fixture.done = false
    fixture.command = ["clipboard-fixture", mode]
    fixture.running = true
  }

  // The stand-in writes each paste's argv and pid next to its mode file,
  // read here synchronously (QML_XHR_ALLOW_FILE_READ=1): a FileView reload
  // can still return the previous paste's contents.
  readonly property string state: Quickshell.env("TEST_CLIPBOARD_STATE")
  function readFile(path) {
    var request = new XMLHttpRequest()
    request.open("GET", "file://" + path, false)
    request.send(null)
    return String(request.responseText || "")
  }

  function elapsed() {
    return Date.now() - shell.since
  }
  function same(a, b) {
    return JSON.stringify(a) === JSON.stringify(b)
  }
  function finish() {
    console.log("FOAMY RESULT " + shell.checks + " checks, " + shell.failures + " failed")
    console.log("FOAMY DONE")
    Qt.quit()
  }

  // Each tick runs the current stage; a stage that waits returns early and
  // runs again on the next tick (at most 15 s for any wait).
  Timer {
    interval: 50
    repeat: true
    running: true
    onTriggered: {
      if (shell.since && shell.elapsed() > 15000) {
        shell.check(false, "timed out at stage " + shell.stage + ", case " + shell.caseIndex)
        shell.finish()
        stop()
        return
      }
      shell.tick()
    }
  }

  function next() {
    stage++
    since = Date.now()
  }

  function tick() {
    var c = cases[caseIndex]
    switch (stage) {
    case 0:
      // The table of cases: set the mode, read, check the one signal.
      if (caseIndex >= cases.length) {
        stage = 10
        since = Date.now()
        return
      }
      setMode(c.mode)
      next()
      return
    case 1:
      if (!fixture.done)
        return
      outcomes = []
      check(clipboard.start(c.primary) === true && clipboard.busy, c.mode + ": a read starts")
      next()
      return
    case 2:
      if (outcomes.length === 0 || clipboard.busy)
        return
      var took = elapsed()
      check(outcomes.length === 1 && same(outcomes[0], c.expect), c.mode + ": " + JSON.stringify(outcomes).slice(0, 120))
      if (c.mode === "stall")
        check(took < 4000, "stall: ends at the 2 s deadline, after " + took + " ms")
      var argv = JSON.parse(readFile(state + ".args") || "[]")
      check((argv.indexOf("--primary") >= 0) === c.primary, c.mode + ": wl-paste argv " + JSON.stringify(argv))
      caseIndex++
      stage = 0
      return
    case 10:
      // One read at a time: a second start while one runs is refused, and
      // only the first read's signal follows.
      setMode("delayed")
      next()
      return
    case 11:
      if (!fixture.done)
        return
      outcomes = []
      check(clipboard.start(false) && !clipboard.start(false), "a second start while a read runs is refused")
      next()
      return
    case 12:
      if (outcomes.length === 0)
        return
      if (elapsed() < 600)
        return
      check(same(outcomes, [
        {
          read: "later"
        }
      ]), "busy: exactly one signal, the first read's: " + JSON.stringify(outcomes))
      setMode("ignore")
      next()
      return
    case 13:
      // Cancel mid-read: wl-paste here ignores TERM. Nothing follows, the
      // reader stays busy until the stopped read has exited, then reads again.
      if (!fixture.done)
        return
      shell.cancelledPid = readFile(state + ".pid")
      outcomes = []
      check(clipboard.start(false), "ignore: a read starts")
      next()
      return
    case 14:
      var pid = readFile(state + ".pid")
      if (pid === shell.cancelledPid)
        return
      shell.cancelledPid = pid
      clipboard.cancel()
      check(!clipboard.start(false), "a start right after cancel() is refused while the stopped read ends")
      next()
      return
    case 15:
      if (clipboard.busy)
        return
      check(elapsed() < 3000, "the stopped read ends, after " + elapsed() + " ms")
      check(outcomes.length === 0, "cancel(): no signal follows: " + JSON.stringify(outcomes))
      console.log("FOAMY PASTE PID " + shell.cancelledPid)
      setMode("normal")
      next()
      return
    case 16:
      if (!fixture.done)
        return
      check(clipboard.start(false), "after the stopped read ends, a new read starts")
      next()
      return
    case 17:
      if (outcomes.length === 0)
        return
      check(same(outcomes, [
        {
          read: "folder"
        }
      ]), "the new read gets its own result: " + JSON.stringify(outcomes))
      shell.finish()
      return
    }
  }
}
