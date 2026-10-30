import QtQuick
import Quickshell
import Quickshell.Services.Mpris
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"
import "plugin/kit/FoamyIpcResolver.js" as Resolver

// kit 0.2.0 features on both hosts: icons, numeral/menu tokens, cursor
// shape, textKey arity, SafeTextField.maximumLength, FoamyPrefsQueue (inline
// and CLI), FoamyIpcResolver.prefer/others/call, FoamyIpcPreference,
// FoamyPeerIpc, FoamySettingsState, and D-Bus isolation.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property bool v45: host === "4.5"
  readonly property string calls: Quickshell.env("FOAMY_CALLS")
  property int checks: 0
  property int failures: 0

  function check(ok, label) {
    checks++
    if (!ok) { failures++; console.log("FOAMY FAIL " + host + " " + label) }
  }
  function eq(actual, expected, label) {
    check(JSON.stringify(actual) === JSON.stringify(expected), label + ": got " + JSON.stringify(actual) + ", expected " + JSON.stringify(expected))
  }

  FloatingWindow {
    id: window
    implicitWidth: 800
    implicitHeight: 600
    color: "black"
    Column {
      PanelKeyCatcher {
        id: catcher
        width: 100; height: 20
        property var lastText: null
        property var lastModifiers: "unset"
        onTextKey: function(text, modifiers) { lastText = text; lastModifiers = modifiers }
      }
      SafeTextField { id: field; width: 200; maximumLength: 5 }
      FoamyCursorSurface { id: row; width: 100; height: 20 }
      FoamyIcon { id: icon; width: 16; height: 16 }
      FoamyHeroBand { id: coverBand; width: 400; title: "Covers" }
      FoamyNumberField {
        id: numberField
        width: 300
        label: "Refresh every"
        value: shell.numberSetting
        from: 1; to: 100; stepSize: 5
        onCommitted: function(v) { shell.numberCommits = shell.numberCommits.concat([v]) }
      }
      FoamyTextSettingField {
        id: textSetting
        width: 300
        value: shell.textSetting
        validate: function(text) { return text.length <= 5 || "Too long" }
        onCommitted: function(v) { shell.textCommits = shell.textCommits.concat([v]) }
      }
      FoamyNumberField { id: decimalField; width: 300; value: 2.5; from: 0; to: 10; decimals: 1 }
      FoamyDropdown {
        id: dropdown
        width: 200
        pickHoldMs: 400
        value: shell.dropdownSetting
        options: ["a", "b", "c"]
        onChanged: function(v) { shell.dropdownChanges = shell.dropdownChanges.concat([v]) }
      }
    }
  }

  FoamyCursor { id: cursor; count: 2 }
  property string dropdownSetting: "a"
  property real numberSetting: 5
  property var numberCommits: []
  property string textSetting: "abc"
  property var textCommits: []
  property int coverIndex: 0
  function coverUrl(i) { return Qt.resolvedUrl("plugin/preview/covers/cover-" + i + ".png") }
  function coverSurface() {
    for (var i = 0; i < coverBand.children.length; i++)
      if (coverBand.children[i].objectName === "foamyHeroBandSurface") return coverBand.children[i]
    return null
  }
  property var dropdownChanges: []

  // --- prefs fixtures -------------------------------------------------------------
  readonly property var fields: [
    { key: "a", type: "string", defaultValue: "" },
    { key: "b", type: "string", defaultValue: "" },
    { key: "list", type: "array", maxItems: 3, defaultValue: [] }
  ]
  QtObject {
    id: inlineBar
    property var saved: []
    property QtObject shell: QtObject {
      function updateEntryInline(id, settings) { inlineBar.saved = inlineBar.saved.concat([JSON.parse(JSON.stringify(settings))]); return true }
    }
  }
  QtObject { id: cliBar; property var shell: null }
  FoamyPrefsQueue { id: inlineQueue; bar: inlineBar; moduleName: "foamy.test"; fields: shell.fields; settings: ({ id: "foamy.test", a: "", b: "", keep: 1 }) }
  FoamyPrefsQueue { id: cliQueue; bar: cliBar; moduleName: "foamy.test"; fields: shell.fields; settings: ({}) }

  // --- IPC fixtures -----------------------------------------------------------------
  FoamyIpc { id: first; target: "foamy.shared-target"; function who(): string { return "first" } }
  FoamyIpc { id: mine; target: "foamy.shared-target"; function who(): string { return "mine" } }
  FoamyIpcPreference { id: preference; handler: mine; interval: 300 }
  Component { id: lateHandler; FoamyIpc { target: "foamy.shared-target"; function who(): string { return "late" } } }
  FoamyPeerIpc { id: peer }

  QtObject {
    id: fakePanel
    property bool opened: false
    function open() { opened = true }
    function close() { opened = false }
  }
  FoamySettingsState { id: settingsState; panel: fakePanel }

  Component.onCompleted: Qt.callLater(stepOne)

  function stepOne() {
    // --- icons -----------------------------------------------------------------------------
    var wanted = ["github", "git-branch", "arrow-up", "arrow-down", "eye", "chevron-left", "calendar", "bell", "bell-off",
                  "search", "x", "ellipsis", "mouse", "keyboard", "message-square", "message", "chat", "users", "battery",
                  "battery-low", "battery-medium", "battery-full", "battery-charging", "plug", "zap", "skip-back",
                  "skip-forward", "play", "pause", "shuffle", "repeat", "repeat-1", "music", "megaphone", "info"]
    var missing = wanted.filter(function(name) { return !icon.paths.hasOwnProperty(name) })
    eq(missing, [], "requested Lucide icons present")
    eq(icon.paths.info, '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>', "info is Lucide info, not a megaphone")
    icon.name = "chevron-left"
    check(icon.known, "chevron-left is known")
    check(icon.directional.indexOf("chevron-left") !== -1, "chevron-left mirrors in RTL")

    // --- tokens ----------------------------------------------------------------------------
    eq(FoamyStyle.font.numeral, Style.space(56), "numeral token")
    eq(FoamyStyle.font.numeralCompact, Style.space(40), "numeralCompact token")
    eq(FoamyStyle.menuPadding, Style.space(8), "menu padding token")
    eq(row.cursorShape, Qt.PointingHandCursor, "cursor rows show a pointing hand")

    // --- textKey arity ---------------------------------------------------------------------
    cursor.emitTextKey(catcher, "s")
    eq(catcher.lastText, "s", "emitTextKey reaches a (text, modifiers) handler")
    check(cursor.plain(catcher.lastModifiers), "a plain letter is plain on " + host)
    if (v45) {
      cursor.emitTextKey(catcher, "s", Qt.AltModifier)
      check(!cursor.plain(catcher.lastModifiers), "Alt+S is not plain on 4.5")
    } else {
      eq(catcher.lastModifiers, undefined, "4.0 textKey has no modifiers argument")
    }
    check(cursor.plain(Qt.ShiftModifier) && !cursor.plain(Qt.ControlModifier), "plain() ignores Shift only")

    // --- SafeTextField.maximumLength ---------------------------------------------------
    field.text = "abcdefgh"
    eq(field.text, "abcde", "maximumLength trims typed text")
    field.maximumLength = 3
    eq(field.text, "abc", "lowering maximumLength trims")

    // --- FoamyDropdown keeps the caller's value binding ----------------------------------
    dropdown.select("b")
    eq(shell.dropdownChanges, ["b"], "selection emits changed()")
    eq(dropdown.shownValue, "b", "the pick shows until the setting catches up")
    eq(dropdown.value, "a", "selection does not assign value")
    shell.dropdownSetting = "b"
    eq([dropdown.value, dropdown.shownValue], ["b", "b"], "the binding follows the setting")
    shell.dropdownSetting = "c"
    eq([dropdown.value, dropdown.shownValue], ["c", "c"], "a later external change still shows (binding intact)")
    dropdown.select("a")   // a save that never lands
    dropdownRevert.start()

    // --- FoamyNumberField: binding-safe numeric settings ------------------------------------
    eq(numberField.field.text, "5", "shows the bound value")
    shell.numberSetting = 7
    eq(numberField.field.text, "7", "follows an external change while not editing")
    numberField.field.text = "9"; numberField.field.textEdited()
    check(numberField.editing, "typing starts a draft")
    shell.numberSetting = 8
    eq(numberField.field.text, "9", "an external change doesn't overwrite the draft")
    check(numberField.commitEdit(false), "Enter commits")
    eq(shell.numberCommits, [9], "a valid changed draft commits once")
    numberField.commitEdit(false)
    numberField.field.editingFinished()
    eq(shell.numberCommits, [9], "focus-out after Enter doesn't commit twice")
    shell.numberSetting = 9
    eq(numberField.field.text, "9", "shows the saved value")
    shell.numberSetting = 12
    eq(numberField.field.text, "12", "binding still drives the field after a commit")
    numberField.field.text = "12"; numberField.field.textEdited(); numberField.commitEdit(false)
    eq(shell.numberCommits, [9], "an unchanged draft doesn't commit")
    numberField.field.text = "abc"; numberField.field.textEdited()
    check(!numberField.commitEdit(false) && numberField.error !== "" && numberField.field.text === "abc", "Enter on invalid input keeps the draft and says why")
    numberField.field.text = "500"; numberField.field.textEdited()
    check(numberField.commitEdit(true) && numberField.field.text === "12" && numberField.error !== "", "focus-out on an out-of-range draft restores the value")
    eq(shell.numberCommits, [9], "invalid drafts never commit")
    numberField.field.text = "33"; numberField.field.textEdited()
    check(numberField.handleKey(Qt.Key_Escape) && numberField.field.text === "12" && !numberField.editing, "Escape restores the value and is consumed (page stays)")
    check(numberField.handleKey(Qt.Key_Up) && numberField.field.text === "17" && numberField.editing, "Up steps the draft by stepSize")
    check(!numberField.handleKey(Qt.Key_A), "other keys pass through")
    numberField.cancelEdit()
    eq([numberField.parse("٤٢"), numberField.parse("42"), numberField.parse("1.5")], [42, 42, NaN], "language digits parse; integers only when decimals is 0")
    eq([decimalField.parse("2,5"), decimalField.parse("2.56")], [2.5, 2.6], "decimal comma accepted, rounded to decimals")

    // --- FoamyTextSettingField: the same rules for free text --------------------------------
    eq(textSetting.field.text, "abc", "text field shows the bound value")
    shell.textSetting = "xyz"
    eq(textSetting.field.text, "xyz", "text field follows an external change")
    textSetting.field.text = " new "; textSetting.field.textEdited()
    shell.textSetting = "other"
    eq(textSetting.field.text, " new ", "draft survives an external change")
    check(textSetting.commitEdit(false) && JSON.stringify(shell.textCommits) === JSON.stringify(["new"]), "commits the trimmed draft once")
    textSetting.field.editingFinished()
    eq(shell.textCommits, ["new"], "no second commit on focus-out")
    textSetting.field.text = "toolong"; textSetting.field.textEdited()
    check(!textSetting.commitEdit(false) && textSetting.error === "Too long", "validate() message on Enter")
    check(textSetting.handleKey(Qt.Key_Escape) && textSetting.field.text === "other" && !textSetting.editing, "Escape restores the bound value")
    shell.textSetting = "later"
    eq(textSetting.field.text, "later", "binding intact after Escape")

    // --- FoamyHeroBand keeps at most one cover decoded ----------------------------------------
    coverCycle.start()

    // --- FoamyPrefsQueue: inline, two saves before the host reflects the first -------
    check(inlineQueue.save("a", "one"), "inline save a")
    check(inlineQueue.save("b", "two"), "inline save b")
    eq(inlineBar.saved.length, 2, "two inline writes")
    eq(inlineBar.saved[1], { a: "one", b: "two", keep: 1 }, "second save merges over the pending first, not the stale entry")
    eq(inlineQueue.value("a"), "one", "effective settings show the pending value")
    inlineQueue.settings = ({ id: "foamy.test", a: "one", b: "two", keep: 1 })
    eq(Object.keys(inlineQueue.pending), [], "pending settles once the host reflects it")
    check(!inlineQueue.save("list", [1, 2, 3, 4]), "array maxItems is enforced")
    eq(inlineQueue.error, "That value isn't allowed.", "error message for the catalog")

    // --- FoamyPrefsQueue: CLI, newest value per key, failure + retry ------------------
    cliQueue.save("a", "first")
    cliQueue.save("a", "second")
    cliQueue.save("b", "other")
    cliQueue.save("a", "third")
    check(cliQueue.saving, "CLI save in flight")
    eq(cliQueue.waiting.length, 2, "waiting saves keep the newest value per key")
    stepTwo.start()
  }

  FileViewProbe { id: callLog; path: shell.calls }

  Timer {
    id: coverCycle
    interval: 15
    repeat: true
    onTriggered: {
      if (shell.coverIndex < 50) {
        coverBand.imageSource = shell.coverUrl(shell.coverIndex)
        shell.coverIndex++
        return
      }
      stop()
      coverCheck.start()
    }
  }
  Timer {
    id: coverCheck
    interval: 500
    onTriggered: {
      var surface = shell.coverSurface()
      var stale = 0
      for (var i = 0; i < 49; i++) if (surface.isImageLoaded(shell.coverUrl(i))) stale++
      shell.eq(stale, 0, "50 covers cycled: no earlier cover stays decoded")
      shell.check(coverBand.loadedImage === String(shell.coverUrl(49)) && surface.isImageLoaded(shell.coverUrl(49)), "only the current cover is loaded")
      coverBand.visible = false
      shell.check(coverBand.loadedImage === "" && !surface.isImageLoaded(shell.coverUrl(49)), "a hidden band (closed popup) unloads its cover")
      coverBand.visible = true
      shell.check(coverBand.loadedImage === String(shell.coverUrl(49)), "showing the band again reloads it")
      coverBand.imageSource = ""
      shell.check(coverBand.loadedImage === "" && !surface.isImageLoaded(shell.coverUrl(49)), "clearing the source unloads the cover")
    }
  }

  Timer {
    id: dropdownRevert
    interval: 800
    onTriggered: shell.eq(dropdown.shownValue, "c", "an unconfirmed pick gives way to the real value")
  }

  Timer {
    id: stepTwo
    interval: 2500
    onTriggered: {
      var lines = callLog.lines()
      eq(lines, ["omarchy bar set foamy.test a \"first\" --json", "omarchy bar set foamy.test b \"other\" --json",
                 "omarchy bar set foamy.test a \"third\" --json"], "CLI saves run one at a time, superseded values skipped")
      check(!cliQueue.busy && cliQueue.error === "", "queue drained without errors")
      // Array values go to setBarWidget with a leading space (qs ipc splits "[…]").
      cliQueue.save("list", [1, 2])
      failNext.start()
    }
  }

  Timer {
    id: failNext
    interval: 1500
    onTriggered: {
      var lines = callLog.lines()
      eq(lines[lines.length - 1], "omarchy-shell shell setBarWidget foamy.test list | [1,2]| {}", "arrays bypass qs ipc list parsing")
      cliQueue.save("b", "boom")   // the fake omarchy fails on "boom"
      afterFail.start()
    }
  }

  Timer {
    id: afterFail
    interval: 1500
    onTriggered: {
      eq(cliQueue.error, "Couldn't save the setting.", "failed CLI save reports an error")
      check(cliQueue.canRetry, "a failed save can be retried")
      eq(cliQueue.value("b"), "other", "a failed value is not shown as saved")
      stepThree()
    }
  }

  function stepThree() {
    // --- IPC: prefer / others / call -----------------------------------------------------
    if (v45) {
      eq(Resolver.call(shell, "foamy.shared-target", "who", []), { ran: true, output: "mine" }, "FoamyIpcPreference puts its handler first")
      check(preference.answering && preference.others === 1, "preference reports one other handler")
      late = lateHandler.createObject(shell)
      Resolver.prefer(shell, late)   // someone else claims the target
      eq(Resolver.call(shell, "foamy.shared-target", "who", []).output, "late", "another prefer() takes over")
      eq(Resolver.call(shell, "foamy.shared-target", "nope", []), { ran: false }, "undeclared functions don't run")
    } else {
      eq(Resolver.call(shell, "foamy.shared-target", "who", []), { ran: false }, "4.0: no in-process IPC")
      check(!preference.answering, "4.0: preference is inert")
    }
    peer.call("foamy.shared-target", "who", [], function(ok, output) { shell.peerResult = { ok: ok, output: output } })
    peer.call("foamy.absent", "status", ["[1]"], function(ok, output) { shell.peerFallback = { ok: ok, output: output } })

    // --- FoamySettingsState ---------------------------------------------------------------
    settingsState.show()
    check(fakePanel.opened && settingsState.editing, "show() on a closed panel opens it on Settings")
    fakePanel.close()
    check(!settingsState.editing, "closing resets Settings")
    settingsState.holdOnClose = true
    settingsState.show()
    fakePanel.close()
    check(settingsState.editing, "holdOnClose keeps Settings across a close")

    // --- D-Bus isolation -------------------------------------------------------------------
    var address = Quickshell.env("DBUS_SESSION_BUS_ADDRESS")
    check(address !== Quickshell.env("FOAMY_LIVE_BUS") && address.indexOf(Quickshell.env("FOAMY_BASE")) !== -1, "private session bus " + address)
    eq(Mpris.players.values.length, 0, "no desktop MPRIS players visible")
    stepFour.start()
  }

  property var late: null
  property var peerResult: null
  property var peerFallback: null

  Timer {
    id: stepFour
    interval: 1200
    onTriggered: {
      if (v45) {
        eq(shell.peerResult, { ok: true, output: "late" }, "FoamyPeerIpc answers in-process on 4.5")
        // Re-claim within the preference interval.
        eq(Resolver.call(shell, "foamy.shared-target", "who", []).output, "mine", "FoamyIpcPreference re-claims the target")
      } else {
        eq(shell.peerResult, { ok: true, output: "cli: foamy.shared-target who" }, "FoamyPeerIpc falls back to omarchy-shell on 4.0")
      }
      eq(shell.peerFallback, { ok: true, output: "cli: foamy.absent status [1]" }, "unknown in-process target uses the CLI")
      console.log("FOAMY RESULT " + host + " checks=" + checks + " failures=" + failures)
      console.log("FOAMY DONE")
      Qt.quit()
    }
  }
}
