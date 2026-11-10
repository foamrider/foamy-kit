import QtQuick
import Quickshell
import Quickshell.Io
import "plugin/kit"

// How the kit's Process users end (tests/test_lifecycle.py; fake omarchy and
// omarchy-shell on PATH, never the real ones). FoamyPrefsQueue's CLI save:
// success, failure with rollback, a command that can't start, one that hangs
// past the deadline, oversized stderr, a stopped command, the queue destroyed
// mid-save, and a save that succeeds after each of them. FoamyPeerIpc: a CLI
// call that can't start still calls done().
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property string calls: Quickshell.env("FOAMY_CALLS")
  readonly property string base: Quickshell.env("FOAMY_BASE")
  property int checks: 0
  property int failures: 0
  property var events: []

  function check(ok, label) {
    checks++
    if (!ok) { failures++; console.log("FOAMY FAIL " + host + " " + label) }
  }
  function eq(actual, expected, label) {
    check(JSON.stringify(actual) === JSON.stringify(expected), label + ": got " + JSON.stringify(actual) + ", expected " + JSON.stringify(expected))
  }
  function callLines() {
    var request = new XMLHttpRequest()
    request.open("GET", "file://" + calls, false)
    request.send(null)
    return String(request.responseText || "").split("\n").filter(function(line) { return line !== "" })
  }
  function ran(value) {
    return callLines().some(function(line) { return line.indexOf(JSON.stringify(value)) >= 0 })
  }

  readonly property var fields: [
    { key: "a", type: "string", defaultValue: "" },
    { key: "b", type: "string", defaultValue: "" }
  ]
  QtObject { id: cliBar; property var shell: null }
  FoamyPrefsQueue {
    id: q
    bar: cliBar
    moduleName: "foamy.test"
    fields: shell.fields
    settings: ({})
    saveTimeoutMs: 1500
    reflectTimeoutMs: 600000
    onSaved: function(key, value) { shell.events = shell.events.concat([["saved", key, value]]) }
    onFailed: function(key, value, error) { shell.events = shell.events.concat([["failed", key, value, q.stderrHead.length]]) }
  }
  Component {
    id: doomedQueue
    FoamyPrefsQueue { bar: cliBar; moduleName: "foamy.test"; fields: shell.fields; settings: ({}); saveTimeoutMs: 60000 }
  }
  property var doomed: null
  FoamyPeerIpc { id: peer }
  property var peerResult: null
  property string defaultDirectory: ""

  // Exits 0 when none of the hanging fake commands is still alive (2: none ran).
  Process {
    id: alive
    property var done: null
    command: ["bash", "-c", '[ -s "$1/hang.pids" ] || exit 2; for p in $(cat "$1/hang.pids"); do kill -0 "$p" 2>/dev/null && exit 1; done; exit 0', "alive", shell.base]
    onExited: function(code) { if (done) done(code) }
  }

  // --- a small step runner --------------------------------------------------------
  property var steps: []
  property double started: 0
  property var cond: null
  property int limit: 0
  property string label: ""
  function next() {
    if (steps.length === 0) { finishAll(); return }
    var step = steps[0]
    steps = steps.slice(1)
    step()
  }
  // Run the step, then wait for `until` (at most `ms`), then the next step.
  function waitFor(text, until, ms) {
    label = text; cond = until; limit = ms; started = Date.now(); poll.start()
  }
  Timer {
    id: poll
    interval: 20
    repeat: true
    onTriggered: {
      if (shell.cond()) { stop(); shell.next(); return }
      if (Date.now() - shell.started > shell.limit) {
        stop()
        shell.check(false, shell.label + ": not within " + shell.limit + " ms")
        shell.finishAll()
      }
    }
  }
  function idle() { return !q.busy && !q.saving }
  function since() { return Date.now() - started }

  Component.onCompleted: {
    defaultDirectory = q.proc.workingDirectory
    // omarchy-shell here is a file whose interpreter doesn't exist: exec fails.
    peer.call("foamy.absent", "status", [], function(ok, output) { shell.peerResult = { ok: ok, output: output } })
    steps = [
      // --- success --------------------------------------------------------------------
      function() {
        check(q.save("a", "one"), "save a")
        check(q.saving && q.busy && !q.canRetry, "CLI save in flight")
        waitFor("first save", idle, 3000)
      },
      function() {
        eq(events, [["saved", "a", "one"]], "saved signal")
        eq(q.value("a"), "one", "saved value shows")
        eq(q.error, "", "no error")

        // --- failure: rolled back to the previous pending value, error, retryable ----
        events = []
        q.save("a", "boom")
        waitFor("failing save", idle, 3000)
      },
      function() {
        eq(events, [["failed", "a", "boom", "fake failure\n".length]], "failed signal (stderr kept)")
        eq(q.value("a"), "one", "a failed value rolls back to the value saved before it")
        eq(q.error, "Couldn't save the setting.", "error message")
        check(q.canRetry, "retryable")

        // --- the command can't start: no exited(), only running -> false ---------------
        events = []
        q.proc.workingDirectory = "/nonexistent-foamy-kit-dir"
        q.save("a", "nostart")
        waitFor("save that can't start", idle, 1000)   // well before the 1500 ms deadline
      },
      function() {
        check(since() < 1000, "a failed start ends at once, not at the deadline (" + since() + " ms)")
        eq(events, [["failed", "a", "nostart", 0]], "failed start reports failure")
        eq(q.value("a"), "one", "failed start rolls back")
        check(q.canRetry && !q.inFlight, "failed start leaves the queue free and retryable")
        check(!ran("nostart"), "the command never ran")
        // Retry once the command can start again.
        events = []
        q.proc.workingDirectory = defaultDirectory
        check(q.retry(), "retry()")
        waitFor("retry", idle, 3000)
      },
      function() {
        eq(events, [["saved", "a", "nostart"]], "retry succeeds")
        eq(q.value("a"), "nostart", "retried value shows")
        eq(q.error, "", "retry clears the error")

        // --- a command that hangs (ignoring SIGTERM) hits the deadline -----------------
        events = []
        q.save("a", "hang")
        q.save("b", "after")   // waits behind it
        eq(q.waiting.length, 1, "a later save waits behind the hanging one")
        waitFor("hanging save", function() { return events.length > 0 }, 4000)
      },
      function() {
        check(since() >= 1400 && since() < 3000, "hang fails at the deadline (" + since() + " ms)")
        eq(events[0], ["failed", "a", "hang", "partial\n".length], "hang reports failure with the stderr so far")
        check(!q.inFlight, "inFlight clears at the deadline")
        eq(q.value("a"), "nostart", "hang rolls back")
        waitFor("save queued behind the hang", idle, 3000)
      },
      function() {
        eq(events.slice(1), [["saved", "b", "after"]], "the waiting save runs after the hang is killed")
        check(ran("after"), "and its command ran")
        check(q.canRetry && q.lastFailed.key === "a" && q.lastFailed.value === "hang", "the hung save is retryable")
        alive.done = function(code) { shell.eq(code, 0, "the hung command was killed"); shell.next() }
        alive.running = true
      },
      function() {
        // --- oversized stderr is capped -----------------------------------------------
        events = []
        q.save("b", "bigerr")
        waitFor("save with 1 MB of stderr", idle, 5000)
      },
      function() {
        eq(events, [["failed", "b", "bigerr", q.stderrLimit]], "stderr kept is capped at stderrLimit")
        eq(q.value("b"), "after", "rolled back")

        // --- a stopped command (Quickshell's running = false: SIGTERM) -----------------
        events = []
        q.save("a", "slow")
        waitFor("slow save starts", function() { return ran("slow") }, 3000)
      },
      function() {
        started = Date.now()
        q.proc.running = false
        waitFor("stopped save", idle, 1000)
      },
      function() {
        eq(events, [["failed", "a", "slow", 0]], "a stopped save fails")
        eq(q.value("a"), "nostart", "stopped save rolls back")
        check(q.canRetry, "stopped save is retryable")

        // --- and a later save succeeds -------------------------------------------------
        events = []
        q.save("a", "final")
        waitFor("save after all that", idle, 3000)
      },
      function() {
        eq(events, [["saved", "a", "final"]], "a following save succeeds")
        eq(q.value("a"), "final", "and shows")
        eq(q.error, "", "no error left")

        // --- a queue destroyed mid-save (its panel closed) kills the command -----------
        doomed = doomedQueue.createObject(shell)
        doomed.save("a", "hang-doomed")
        doomed.save("b", "never")
        waitFor("doomed save starts", function() { return ran("hang-doomed") }, 3000)
      },
      function() {
        doomed.destroy()
        doomed = null
        waitFor("destruction settles", function() { return Date.now() - started > 500 }, 2000)
      },
      function() {
        check(!ran("never"), "a destroyed queue runs nothing more")
        alive.done = function(code) { shell.eq(code, 0, "destroying the queue killed its command"); shell.next() }
        alive.running = true
      },
      function() {
        eq(peerResult, { ok: false, output: "" }, "FoamyPeerIpc: a call whose command can't start still calls done()")
        eq(peer.running, 0, "and no longer counts as running")
        next()
      }
    ]
    Qt.callLater(next)
  }

  function finishAll() {
    console.log("FOAMY RESULT " + host + " checks=" + checks + " failures=" + failures)
    console.log("FOAMY DONE")
    Qt.quit()
  }
}
