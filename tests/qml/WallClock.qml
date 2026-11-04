import QtQuick
import Quickshell
import "plugin/kit" as Kit

ShellRoot {
  property int checks: 0
  property int changes: 0
  property int pausedChanges: 0
  property real pausedDate: 0
  function check(ok, label) {
    checks++
    if (!ok) console.log("FOAMY FAIL " + label)
  }
  Kit.FoamyWallClock {
    id: clock
    enabled: false
    onDateChanged: changes++
  }
  Component.onCompleted: {
    var first = Date.parse("2026-10-25T00:30:00Z")
    var second = Date.parse("2026-10-25T01:30:00Z")
    check(new Date(first).getHours() === new Date(second).getHours(), "fixture repeats the local hour")
    check(new Date(first).getTimezoneOffset() !== new Date(second).getTimezoneOffset(), "fixture crosses DST fallback")
    for (var step of [1000, 60000]) {
      clock.step = step
      var bounded = true
      for (var now = first - 1800000; now <= second + 1800000; now += 997) {
        var delay = clock.msUntilNextTick(now)
        if (delay <= 0 || delay > step || (now + delay) % step !== 0) bounded = false
      }
      check(bounded, "positive epoch-aligned delays across fallback, step " + step)
      check(clock.msUntilNextTick(first) === step, "whole tick waits one full step")
    }
    check(!clock.running, "disabled clock stays stopped after cadence changes")
    clock.step = 1000
    pausedDate = clock.date.getTime()
    pausedChanges = changes
    phase.start()
  }
  Timer {
    id: phase
    interval: 1200
    repeat: true
    property int stage: 0
    onTriggered: {
      if (stage === 0) {
        check(changes === pausedChanges && clock.date.getTime() === pausedDate, "disabled clock does not tick")
        clock.enabled = true
        check(clock.running && Date.now() - clock.date.getTime() < 100, "enabling refreshes immediately")
        pausedChanges = changes
      } else if (stage === 1) {
        check(changes > pausedChanges, "second ticks advance the clock")
        clock.step = 60000
        check(clock.running && clock.interval > 0 && clock.interval <= 60000, "cadence changes rearm")
        clock.enabled = false
        check(!clock.running, "hiding stops the timer")
        pausedChanges = changes
        pausedDate = clock.date.getTime()
      } else {
        check(changes === pausedChanges && clock.date.getTime() === pausedDate, "hidden clock remains paused")
        clock.enabled = true
        check(clock.running && clock.date.getTime() > pausedDate, "resume refreshes stale date")
        clock.enabled = false
        console.log("FOAMY RESULT " + checks + " checks")
        console.log("FOAMY DONE")
        Qt.quit()
      }
      stage++
    }
  }
}
