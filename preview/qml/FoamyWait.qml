import QtQuick

// Event-driven waits for runtime tests (copied into every harness run as
// harness/FoamyWait.qml). A step that waits for a condition instead of a fixed
// after(ms) chain is neither flaky on a loaded machine nor slow on an idle one.
//
//   import "harness"
//   FoamyWait { id: wait }
//   wait.waitFor(function() { return service.ready }, 10000, function(ok) {
//     check(ok, "the service became ready")             // false: timed out
//     …next step…
//   })
//   wait.waitFor(function() { return !proc.running }, 5000, next, "the save ends")
//   wait.after(500, next)                               // when the step really is time
//
// waitFor(condition, timeoutMs, then[, label]): polls condition() every
// `interval` ms (a throw counts as false) and calls then(ok) once, always
// later, never from inside waitFor(). With a label, a timeout also logs
// "FOAMY FAIL <label>: not true after <timeoutMs> ms", which fails the run.
// `pending` counts the waits in flight.
QtObject {
  id: root

  property int interval: 50
  property int pending: 0

  property Component timer: Component {
    Timer {
      repeat: true
    }
  }

  function waitFor(condition, timeoutMs, then, label) {
    var deadline = Date.now() + Math.max(0, Number(timeoutMs) || 0)
    var lastError = ""
    var holds = function () {
      try {
        return !!condition()
      } catch (error) {
        lastError = String(error)
        return false
      }
    }
    var poll = root.timer.createObject(root, {
      interval: Math.max(1, root.interval)
    })
    var done = false
    root.pending++
    var finish = function (ok) {
      if (done)
        return
      done = true
      poll.stop()
      poll.destroy()
      root.pending = Math.max(0, root.pending - 1)
      if (!ok && label)
        console.log("FOAMY FAIL " + label + ": not true after " + timeoutMs + " ms" + (lastError ? " (" + lastError + ")" : ""))
      if (then)
        then(ok)
    }
    poll.triggered.connect(function () {
      if (holds())
        finish(true)
      else if (Date.now() >= deadline)
        finish(false)
    })
    poll.start()
  }

  function after(ms, then) {
    var once = root.timer.createObject(root, {
      interval: Math.max(1, Number(ms) || 0),
      repeat: false
    })
    once.triggered.connect(function () {
      once.destroy()
      if (then)
        then()
    })
    once.start()
  }
}
