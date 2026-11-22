import QtQuick
import Quickshell
import Quickshell.Io
import "plugin/kit"

// FoamyBoundedCollector on a real child's stdout and stderr, read in the
// Process's exited handler: a short stream kept whole; a stream far longer
// than the bound and than a pipe (many reads) cut to the bound's start;
// a long stream under the bound kept whole and in order across its reads;
// a cut that would split a surrogate pair; clear() in the started handler.
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
  function eq(actual, expected, label) {
    check(JSON.stringify(actual) === JSON.stringify(expected), label + ": got " + JSON.stringify(actual).slice(0, 300) + ", expected " + JSON.stringify(expected).slice(0, 300))
  }

  Process {
    id: child
    property var then: null
    stdout: FoamyBoundedCollector {
      id: out
      limit: 4096
    }
    stderr: FoamyBoundedCollector {
      id: err
      limit: 64
    }
    onStarted: {
      out.clear()
      err.clear()
    }
    onExited: function (code) {
      var next = child.then
      child.then = null
      next(code)
    }
  }
  // Runs `script` under bash, then `then(exitCode)` from the exited handler.
  function run(script, then) {
    child.then = then
    child.command = ["bash", "-c", script]
    child.running = true
  }

  Component.onCompleted: short()

  function short() {
    run("printf 'hostname: laptop\\n'; printf 'one warning\\n' >&2", function (code) {
      eq([code, out.text, out.truncated, err.text, err.truncated], [0, "hostname: laptop\n", false, "one warning\n", false], "a short stream is kept whole")
      long()
    })
  }

  function long() {
    // 4 MiB on stdout and 100 kB on stderr: many reads of the pipe.
    run("head -c 4194304 /dev/zero | tr '\\0' x; head -c 100000 /dev/zero | tr '\\0' e >&2", function (code) {
      eq([code, out.text.length, out.truncated, out.text === "x".repeat(4096)], [0, 4096, true, true], "4 MiB of stdout keeps its first 4096 characters and says it cut")
      eq([err.text, err.truncated], ["e".repeat(64), true], "stderr keeps its own bound")
      inOrder()
    })
  }

  function inOrder() {
    // About 590 kB under a larger bound: every read is kept, in order.
    var expected = ""
    for (var i = 1; i <= 100000; i++)
      expected += i + "\n"
    out.limit = expected.length + 10
    run("seq 1 100000", function (code) {
      eq([code, out.truncated, out.text.length], [0, false, expected.length], "a long stream under the bound is kept whole")
      check(out.text === expected, "and in order, across its reads")
      pair()
    })
  }

  function pair() {
    // The bound falls between the two halves of U+1F600.
    out.limit = 4
    run("printf 'abc\\xf0\\x9f\\x98\\x80def'", function (code) {
      eq([code, out.text, out.truncated], [0, "abc", true], "a cut never keeps half of a surrogate pair")
      out.limit = 4096
      cleared()
    })
  }

  function cleared() {
    run("printf 'first\\n'", function () {
      run("printf 'second\\n'", function (code) {
        eq([code, out.text, out.truncated, err.text], [0, "second\n", false, ""], "clear() in the started handler starts each run's text afresh")
        console.log("FOAMY RESULT checks=" + checks + " failures=" + failures)
        console.log("FOAMY DONE")
        Qt.quit()
      })
    })
  }
}
