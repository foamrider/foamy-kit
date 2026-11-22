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
      mode: "lines",
      primary: false,
      multiline: true,
      expect: {
        read: "one\ntwo\nthree"
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
  property var spare: null

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

  // A second reader, destroyed in the middle of a read.
  Component {
    id: spareReader
    FoamyClipboard {}
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

  // True once `pid` has exited (no /proc entry, or a zombie).
  function exited(pid) {
    var stat = readFile("/proc/" + pid + "/stat")
    return stat === "" || stat.slice(stat.lastIndexOf(")") + 2).charAt(0) === "Z"
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
      clipboard.multiline = c.multiline === true
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
      clipboard.multiline = false
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
      setMode("loaded")
      next()
      return
    case 13:
      // Cancel mid-read. The stand-in timeout gives a "loaded" paste 60 s
      // and its producer prints after 2.5 s, so only clipboard.sh's kill of
      // the whole read can end it at once. Nothing follows, the reader
      // stays busy until the stopped read has exited, then reads again.
      if (!fixture.done)
        return
      shell.cancelledPid = readFile(state + ".pid")
      outcomes = []
      check(clipboard.start(false), "loaded: a read starts")
      next()
      return
    case 14:
      // The stand-in empties the pid file before it writes its pid.
      var pid = readFile(state + ".pid")
      if (pid === "" || pid === shell.cancelledPid)
        return
      shell.cancelledPid = pid
      clipboard.cancel()
      check(!clipboard.start(false), "a start right after cancel() is refused while the stopped read ends")
      next()
      return
    case 15:
      if (clipboard.busy)
        return
      check(elapsed() < 1500, "the stopped read ends at once, before the 2.5 s producer would, after " + elapsed() + " ms")
      check(outcomes.length === 0, "cancel(): no signal follows: " + JSON.stringify(outcomes))
      next()
      return
    case 16:
      if (!exited(shell.cancelledPid) && elapsed() < 500)
        return
      check(exited(shell.cancelledPid), "cancel(): the read's producer is killed with it (pid " + shell.cancelledPid + ")")
      setMode("normal")
      next()
      return
    case 17:
      if (!fixture.done)
        return
      check(clipboard.start(false), "after the stopped read ends, a new read starts")
      next()
      return
    case 18:
      if (outcomes.length === 0)
        return
      check(same(outcomes, [
        {
          read: "folder"
        }
      ]), "the new read gets its own result: " + JSON.stringify(outcomes))
      setMode("loaded")
      next()
      return
    case 19:
      // A reader destroyed mid-read (a closed field, a reload): Quickshell
      // kills clipboard.sh with SIGKILL, which no trap sees, and the read
      // must still end at once, producer included: before the "loaded"
      // producer would end by itself at 2.5 s (the stand-in timeout gives
      // it 60 s).
      if (!fixture.done)
        return
      // The normal read above wrote its pid last; wait for this read's own.
      shell.cancelledPid = readFile(state + ".pid")
      shell.spare = spareReader.createObject(shell)
      check(shell.spare.start(false), "a second reader starts a read")
      next()
      return
    case 20:
      var spawned = readFile(state + ".pid")
      if (spawned === "" || spawned === shell.cancelledPid)
        return
      shell.cancelledPid = spawned
      shell.spare.destroy()
      shell.spare = null
      next()
      return
    case 21:
      if (!exited(shell.cancelledPid) && elapsed() < 4000)
        return
      check(exited(shell.cancelledPid) && elapsed() < 1500, "a destroyed reader's read ends at once (pid " + shell.cancelledPid + "), after " + elapsed() + " ms")
      shell.finish()
      return
    }
  }
}
