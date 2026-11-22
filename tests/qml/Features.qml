import QtQuick
import QtQuick.Layouts
import QtTest
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin/kit"
import "plugin/kit/FoamyIpcResolver.js" as Resolver

// kit 0.2.0 features on every host: icons, textKey arity,
// SafeTextField.maximumLength, FoamyPrefsQueue (inline and CLI),
// FoamyIpcResolver.prefer/others/call, FoamyIpcPreference, FoamyPeerIpc and
// FoamySettingsState.holdOnClose, the pending-value expiry and peer-call
// failures.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property string calls: Quickshell.env("FOAMY_CALLS")
  property int checks: 0
  property int failures: 0
  // The checks that end later; the run reports only after all of them ran.
  readonly property var laterChecks: ["dropdown", "tooltip", "long field", "unit stack", "state switches", "covers", "expiry"]
  property var finished: []
  function done(name) {
    finished = finished.concat([name])
  }

  function check(ok, label) {
    checks++
    if (!ok) {
      failures++
      console.log("FOAMY FAIL " + host + " " + label)
    }
  }
  function eq(actual, expected, label) {
    check(JSON.stringify(actual) === JSON.stringify(expected), label + ": got " + JSON.stringify(actual) + ", expected " + JSON.stringify(expected))
  }
  // Real key events to the focused item, through the window.
  function key(k) {
    ev.keyClick(k, Qt.NoModifier, -1)
  }
  function type(text) {
    for (var i = 0; i < text.length; i++)
      ev.keyClickChar(text.charAt(i), Qt.NoModifier, -1)
  }

  FloatingWindow {
    id: window
    implicitWidth: 800
    implicitHeight: 600
    color: "black"
    Column {
      PanelKeyCatcher {
        id: catcher
        width: 100
        height: 20
        property var lastText: null
        property var lastModifiers: "unset"
        onTextKey: function (text, modifiers) {
          lastText = text
          lastModifiers = modifiers
        }
      }
      SafeTextField {
        id: field
        width: 200
        maximumLength: 5
      }
      SafeTextField {
        id: createdField
        width: 200
        text: "abcdefgh"
        maximumLength: shell.createdLimit
      }
      FoamyIcon {
        id: icon
        width: 16
        height: 16
      }
      FoamyHeroBand {
        id: coverBand
        width: 400
        title: "Covers"
      }
      Item {
        width: 1
        height: 1
        TestEvent {
          id: ev
        }
      }
      // On a settings page, as in a plugin: Escape that a field leaves
      // unhandled would go back.
      FoamySettingsPage {
        width: 300
        height: 300
        onBack: shell.pageBacks++
        FoamySettingsSection {
          width: parent.width
          FoamyNumberField {
            id: numberField
            width: parent.width
            label: "Refresh every"
            value: shell.numberSetting
            from: 1
            to: 100
            stepSize: 5
            onCommitted: function (v) {
              shell.numberCommits = shell.numberCommits.concat([v])
            }
          }
          FoamyTextSettingField {
            id: textSetting
            width: parent.width
            value: shell.textSetting
            validate: function (text) {
              return text.length <= 5 || "Too long"
            }
            onCommitted: function (v) {
              shell.textCommits = shell.textCommits.concat([v])
            }
          }
        }
      }
      Column {
        id: unitStack
        width: 300
        FoamyNumberField {
          id: percentField
          width: parent.width
          unit: "%"
          value: 95
        }
        FoamyNumberField {
          id: celsiusField
          width: parent.width
          unit: "°C"
          value: 15
        }
        FoamyNumberField {
          id: plainField
          width: parent.width
          reserveUnit: true
          value: 3
        }
      }
      FoamyNumberField {
        id: retryField
        width: 300
        value: 20
        from: 1
        to: 100
        onCommitted: function (v) {
          shell.retryCommits = shell.retryCommits.concat([v])
        }
        onPasteFailed: function (message) {
          shell.pasteMessage = message
        }
      }
      // Real pastes through kit/clipboard.sh (refusedPastes()).
      FoamyNumberField {
        id: pasteNumber
        width: 300
        value: 20
        from: 1
        to: 100
      }
      FoamyTextSettingField {
        id: pasteText
        width: 300
        value: "short"
        validate: function (text) {
          return text.length <= 5 || "Too long"
        }
        onPasteFailed: function (message) {
          shell.textPasteMessages = shell.textPasteMessages.concat([message])
        }
      }
      FoamyNumberField {
        id: decimalField
        width: 300
        value: 2.5
        from: 0
        to: 10
        decimals: 1
      }
      // Text inset must not depend on how a field is sized (Column `width:`
      // vs RowLayout fillWidth), in LTR and RTL; kit fields included.
      Repeater {
        id: insetRepeater
        model: 2
        Column {
          id: insetCase
          required property int index
          property alias byWidth: byWidth
          property alias byLayout: byLayout
          property alias textSetting: textSettingInset
          property alias numberSetting: numberInset
          width: 300
          LayoutMirroring.enabled: index === 1
          LayoutMirroring.childrenInherit: true
          SafeTextField {
            id: byWidth
            width: parent.width
            text: "Calendar app"
          }
          RowLayout {
            width: parent.width
            SafeTextField {
              id: byLayout
              Layout.fillWidth: true
              text: "Calendar app"
            }
          }
          FoamyTextSettingField {
            id: textSettingInset
            width: parent.width
            value: "Calendar app"
          }
          FoamyNumberField {
            id: numberInset
            width: parent.width
            value: 30
            reserveUnit: true
          }
        }
      }
      SafeTextField {
        id: longField
        width: 120
        text: "a long value that cannot fit in the field at all"
      }
      // A caller that shows its value whenever the field has no focus
      // (foamy-lock's step field) still reads the typed text when the edit
      // ends.
      SafeTextField {
        id: idleShown
        property string seen: ""
        width: 120
        Binding on text {
          value: "shown"
          when: !idleShown.inputActiveFocus
        }
        onEditingFinished: seen = text
      }
      // Switching between settings states (train: settings -> settings-schedule)
      // destroys and builds pages with text and number fields.
      Loader {
        id: stateSwitcher
        width: 300
        property int flips: 0
        asynchronous: flips % 4 >= 2
        sourceComponent: flips % 2 === 0 ? pageA : pageB
      }
      FoamyDropdown {
        id: dropdown
        width: 200
        pickHoldMs: 400
        value: shell.dropdownSetting
        options: ["a", "b", "c"]
        onChanged: function (v) {
          shell.dropdownChanges = shell.dropdownChanges.concat([v])
        }
      }
      // Linked to a FoamyPrefsQueue key (linkedDropdowns()): the queue's
      // refusals of the key end the pick's hold.
      FoamyDropdown {
        id: refusedDropdown
        width: 160
        value: linkQueue.value("mode")
        options: ["x", "y", "z"]
        onChanged: function (v) {
          linkQueue.save("mode", v)
        }
      }
      FoamyDropdown {
        id: queuedDropdown
        width: 160
        value: linkCliQueue.value("mode")
        options: ["x", "y", "z"]
        onChanged: function (v) {
          linkCliQueue.save("mode", v)
        }
      }
      // Quick picks whose saves end one by one (serialPicks()).
      FoamyDropdown {
        id: serialDropdown
        width: 200
        value: "c"
        options: ["a", "b", "c"]
        onChanged: function (v, serial) {
          shell.serialChanges = shell.serialChanges.concat([[v, serial]])
        }
      }
    }
    // A dropdown disabled while its list is open, itself or through its
    // parent (disabledDropdown()); nothing lies under its list.
    Item {
      id: lockHolder
      x: 560
      y: 300
      width: 160
      height: 40
      FoamyDropdown {
        id: lockDropdown
        width: 160
        value: "x"
        options: ["x", "y", "z"]
        onChanged: function (v) {
          shell.lockPicks = shell.lockPicks.concat([v])
        }
      }
    }
    // An action whose tooltip is app text of any length (a folder's name).
    FoamyAction {
      id: tipAction
      x: 700
      y: 540
      iconName: "folder"
      tooltipText: "Pause synchronization for " + "A folder name with words ".repeat(20)
    }
    // A form button and a footer status whose tooltips are app text too.
    FoamyButton {
      id: tipButton
      x: 620
      y: 540
      text: "Open"
      tooltipText: "Open"
    }
    FoamyPanelFooter {
      id: tipFooter
      x: 380
      y: 530
      width: 220
      divider: false
      showRefresh: false
      status: "Sync failed"
      statusTooltip: "Sync failed"
    }
  }

  FoamyCursor {
    id: cursor
    count: 2
  }
  FoamyWait {
    id: wait
  }
  property string dropdownSetting: "a"
  Component {
    id: pageA
    FoamySettingsPage {
      height: 300
      FoamySettingsSection {
        width: parent.width
        FoamyNumberField {
          width: parent.width
          unit: "%"
          value: 50
        }
        SafeTextField {
          width: parent.width
          maximumLength: 5
          text: "abcdefgh"
        }
      }
    }
  }
  Component {
    id: pageB
    FoamySettingsPage {
      height: 300
      FoamySettingsSection {
        width: parent.width
        FoamyTextSettingField {
          width: parent.width
          value: "schedule"
        }
        SafeTextField {
          width: parent.width
          maximumLength: 3
          text: "06:00-18:00"
        }
        Repeater {
          model: 7
          SafeTextField {
            required property int index
            width: 80
            maximumLength: 5
            text: "06:00"
          }
        }
      }
    }
  }
  property real numberSetting: 5
  property int pageBacks: 0
  property var numberCommits: []
  property string textSetting: "abc"
  property var textCommits: []
  function coverUrl(i) {
    return Qt.resolvedUrl("plugin/preview/covers/cover-" + i + ".png")
  }
  function coverSurface() {
    for (var i = 0; i < coverBand.children.length; i++)
      if (coverBand.children[i].objectName === "foamyHeroBandSurface")
        return coverBand.children[i]
    return null
  }
  property var dropdownChanges: []

  // --- prefs fixtures -------------------------------------------------------------
  readonly property var fields: [
    {
      key: "a",
      type: "string",
      defaultValue: ""
    },
    {
      key: "b",
      type: "string",
      defaultValue: ""
    },
    {
      key: "list",
      type: "array",
      maxItems: 3,
      defaultValue: []
    }
  ]
  QtObject {
    id: inlineBar
    property var saved: []
    property QtObject shell: QtObject {
      function updateEntryInline(id, settings) {
        inlineBar.saved = inlineBar.saved.concat([JSON.parse(JSON.stringify(settings))])
        return true
      }
    }
  }
  QtObject {
    id: cliBar
    property var shell: null
  }
  FoamyPrefsQueue {
    id: inlineQueue
    bar: inlineBar
    moduleName: "foamy.test"
    fields: shell.fields
    settings: ({
        id: "foamy.test",
        a: "",
        b: "",
        keep: 1
      })
  }
  FoamyPrefsQueue {
    id: cliQueue
    bar: cliBar
    moduleName: "foamy.test"
    fields: shell.fields
    settings: ({})
  }
  // The stored list has four items (maxItems 3): user data the schema rejects.
  QtObject {
    id: storedBar
    property var saved: []
    property QtObject shell: QtObject {
      function updateEntryInline(id, settings) {
        storedBar.saved = storedBar.saved.concat([JSON.parse(JSON.stringify(settings))])
        return true
      }
    }
  }
  FoamyPrefsQueue {
    id: storedQueue
    bar: storedBar
    moduleName: "foamy.stored"
    fields: shell.fields
    settings: ({
        id: "foamy.stored",
        list: [1, 2, 3, 4],
        a: ""
      })
  }
  // A panel handed its settings through createObject (as the bar and the
  // plugin tests do) sees each list as a QML sequence wrapper, which fails
  // Array.isArray.
  Component {
    id: wrappedQueueComponent
    FoamyPrefsQueue {
      bar: storedBar
      fields: shell.fields
    }
  }
  Component {
    id: settingsHolder
    QtObject {
      property var settings: ({})
    }
  }
  function wrappedSettings(settings) {
    return settingsHolder.createObject(shell, {
      settings: settings
    }).settings
  }
  property var storedFailures: []
  property var inlineFailures: []
  Connections {
    target: inlineQueue
    function onFailed(key, value, error) {
      shell.inlineFailures = shell.inlineFailures.concat([error])
    }
  }
  // The documented bindings: both follow the queue's settings.
  readonly property string storedListProblem: storedQueue.storedProblems.list || ""
  readonly property string storedListProblemCall: storedQueue.storedProblem("list")
  Connections {
    target: storedQueue
    function onFailed(key, value, error) {
      shell.storedFailures = shell.storedFailures.concat([error])
    }
  }

  // --- IPC fixtures -----------------------------------------------------------------
  FoamyIpc {
    id: first
    target: "foamy.shared-target"
    function who(): string {
      return "first"
    }
  }
  FoamyIpc {
    id: mine
    target: "foamy.shared-target"
    function who(): string {
      return "mine"
    }
  }
  FoamyIpcPreference {
    id: preference
    handler: mine
    interval: 300
  }
  Component {
    id: lateHandler
    FoamyIpc {
      target: "foamy.shared-target"
      function who(): string {
        return "late"
      }
    }
  }
  FoamyPeerIpc {
    id: peer
  }
  FoamyPeerIpc {
    id: narrow
    limit: 1
  }
  // foamy-lock's scenario: the rival arrives after the preference settled.
  FoamyIpc {
    id: guarded
    target: "foamy.guarded"
    function who(): string {
      return "guarded"
    }
  }
  FoamyIpcPreference {
    id: guardPreference
    handler: guarded
    interval: 300
  }
  Component {
    id: rivalHandler
    FoamyIpc {
      target: "foamy.guarded"
      function who(): string {
        return "rival"
      }
    }
  }
  property var rival: null

  // 4.5 reflects inline saves synchronously (persistShellConfig -> settings).
  QtObject {
    id: syncBar
    property var written: []
    property QtObject shell: QtObject {
      function updateEntryInline(id, settings) {
        syncBar.written = syncBar.written.concat([JSON.parse(JSON.stringify(settings))])
        var next = JSON.parse(JSON.stringify(settings))
        next.id = id
        syncQueue.settings = next
        return true
      }
    }
  }
  FoamyPrefsQueue {
    id: syncQueue
    bar: syncBar
    moduleName: "foamy.sync"
    fields: shell.fields
    settings: ({
        id: "foamy.sync",
        a: "",
        b: ""
      })
  }
  // A host that takes inline saves but never reflects them.
  QtObject {
    id: expiringBar
    property var saved: []
    property QtObject shell: QtObject {
      function updateEntryInline(id, settings) {
        expiringBar.saved = expiringBar.saved.concat([JSON.parse(JSON.stringify(settings))])
        return true
      }
    }
  }
  FoamyPrefsQueue {
    id: expiringQueue
    bar: expiringBar
    moduleName: "foamy.expiring"
    fields: shell.fields
    reflectTimeoutMs: 300
    settings: ({
        id: "foamy.expiring",
        a: "stored"
      })
  }
  property var retryCommits: []
  property string pasteMessage: ""
  property var textPasteMessages: []
  property var lockPicks: []
  property var serialChanges: []

  // The queues of the linked dropdowns: one that saves inline, whose schema
  // refuses "z", and one that saves through the fake CLI (0.3 s a save).
  QtObject {
    id: linkBar
    property QtObject shell: QtObject {
      function updateEntryInline(id, settings) {
        return true
      }
    }
  }
  FoamyPrefsQueue {
    id: linkQueue
    bar: linkBar
    moduleName: "foamy.link"
    fields: [
      {
        key: "mode",
        type: "enum",
        options: ["x", "y"],
        defaultValue: "x"
      }
    ]
    settings: ({
        id: "foamy.link",
        mode: "x"
      })
  }
  FoamyPrefsQueue {
    id: linkCliQueue
    bar: cliBar
    moduleName: "foamy.link-cli"
    fields: [
      {
        key: "mode",
        type: "enum",
        options: ["x", "y", "z"],
        defaultValue: "x"
      }
    ]
    settings: ({
        id: "foamy.link-cli",
        mode: "x"
      })
  }
  // A dropdown linked to a queue and a key gives way when the queue
  // refuses that key: at once when save() refuses the pick (it returns
  // false), and when a pick that waited behind a running save is refused
  // as it runs; a refusal of another key leaves it.
  function linkedDropdowns(then) {
    refusedDropdown.queue = linkQueue
    refusedDropdown.queueKey = "mode"
    queuedDropdown.queue = linkCliQueue
    queuedDropdown.queueKey = "mode"
    refusedDropdown.select("z")
    eq([refusedDropdown.value, refusedDropdown.shownValue], ["x", "x"], "a pick the linked queue's save() refuses gives way at once")
    queuedDropdown.select("y")
    queuedDropdown.select("z")
    eq([linkCliQueue.saving, linkCliQueue.waiting.length, queuedDropdown.value, queuedDropdown.shownValue], [true, 1, "y", "z"], "a second pick waits behind the running save and shows")
    linkCliQueue.save("bogus", 1)
    eq(queuedDropdown.shownValue, "z", "a refusal of another key leaves the pick on show")
    // The widget loses its bar entry while the pick waits: its save is refused when it runs.
    linkCliQueue.moduleName = ""
    wait.waitFor(function () {
      return !linkCliQueue.busy
    }, 5000, function (drained) {
      eq([drained, linkCliQueue.error, queuedDropdown.value, queuedDropdown.shownValue], [true, "Settings can't be saved: this widget has no bar entry.", "y", "y"], "a queued pick the linked queue refuses as it runs gives way at once")
      then()
    })
  }

  // Picks A, B, A, each saved on its own: changed() names each pick with a
  // serial, and saveFailed(serial) drops only that pick, so the refusal of
  // the first A leaves the second A on show (its value alone can't tell).
  function serialPicks() {
    serialDropdown.select("a")
    serialDropdown.select("b")
    serialDropdown.select("a")
    var serials = serialChanges.map(function (change) {
      return change[1]
    })
    eq(serialChanges.map(function (change) {
      return change[0]
    }), ["a", "b", "a"], "each pick emits changed() once")
    check(serials.length === 3 && serials[0] < serials[1] && serials[1] < serials[2], "changed() gives each pick a newer serial: " + JSON.stringify(serials))
    serialDropdown.saveFailed(serials[0])
    eq([serialDropdown.shownValue, serialDropdown.pickHeld], ["a", true], "a refusal of the first A leaves the second A on show")
    serialDropdown.saveFailed(serials[1])
    eq(serialDropdown.shownValue, "a", "a refusal of B, no longer on show, changes nothing")
    serialDropdown.saveFailed(serials[2])
    eq([serialDropdown.shownValue, serialDropdown.pickHeld], ["c", false], "a refusal of the pick on show shows the saved value again")
    serialDropdown.select("b")
    serialDropdown.saveFailed()
    eq(serialDropdown.shownValue, "c", "saveFailed() without a serial still drops whatever pick is on show")
  }

  // A dropdown disabled while its list is open (a settings page that starts
  // saving) closes the list, and nothing there picks: a key or a click on the
  // list would reach onChanged. A panel's open() on a disabled dropdown opens
  // no list either.
  function disabledDropdown(then) {
    var trigger = lockDropdown.triggerItem
    // Open the list, disable `target` (the dropdown or its parent), then
    // `act` on where the list was.
    function attempt(label, target, act, next) {
      target.enabled = true
      lockDropdown.open()
      wait.waitFor(function () {
        return lockDropdown.popupOpen
      }, 3000, function (opened) {
        check(opened, label + ": the dropdown's list opens")
        target.enabled = false
        wait.waitFor(function () {
          return !lockDropdown.popupOpen
        }, 3000, function (closed) {
          check(closed, label + ": a dropdown disabled while its list is open closes the list")
          act()
          eq(shell.lockPicks, [], label + ": a dropdown disabled while its list is open takes no pick")
          target.enabled = true
          next()
        })
      })
    }
    attempt("keys, the dropdown disabled", lockDropdown, function () {
      key(Qt.Key_Down)
      key(Qt.Key_Return)
    }, function () {
      attempt("click, its parent disabled", lockHolder, function () {
        // The list's first row, where it showed.
        ev.mouseClick(trigger, 20, trigger.height + 12, Qt.LeftButton, Qt.NoModifier, -1)
      }, function () {
        lockDropdown.enabled = false
        lockDropdown.open()
        check(!lockDropdown.popupOpen, "open() on a disabled dropdown opens no list")
        lockDropdown.enabled = true
        then()
      })
    })
  }

  // What the stand-in wl-paste does on the next paste (hostenv.clipboard_fakes()).
  Process {
    id: fixture
  }
  function setClipboard(mode, then) {
    fixture.command = ["clipboard-fixture", mode]
    fixture.running = true
    wait.waitFor(function () {
      return !fixture.running
    }, 5000, then, "clipboard-fixture " + mode)
  }
  // Ctrl+V into `input` (a SafeTextField), then `then` once the paste has ended.
  function paste(input, then) {
    input.focusInput()
    ev.keyClick(Qt.Key_V, Qt.ControlModifier, -1)
    check(input.pasteRunning, "the paste runs out of process")
    wait.waitFor(function () {
      return !input.pasteRunning
    }, 10000, then, "the paste ends")
  }
  // A refused paste is the field's newest news: it replaces the error the
  // field shows for its draft (a number out of range, a text too long).
  function refusedPastes(then) {
    var tooLarge = "Clipboard text is too large or contains invalid characters."
    var numberLine = findNamed(pasteNumber, "foamyFieldError")
    var textLine = findNamed(pasteText, "foamyFieldError")
    pasteNumber.field.focusInput()
    pasteNumber.field.selectAll()
    type("500")
    key(Qt.Key_Return)
    check(numberLine !== null && numberLine.visible && numberLine.text === pasteNumber.invalidText, "an out-of-range number says why: " + (numberLine ? numberLine.text : "no error line"))
    setClipboard("large", function () {
      paste(pasteNumber.field, function () {
        check(numberLine !== null && numberLine.visible && numberLine.text === tooLarge, "a refused paste into a number field replaces its range error: " + (numberLine ? numberLine.text : "no error line"))
        pasteText.field.focusInput()
        pasteText.field.selectAll()
        type("toolong")
        key(Qt.Key_Return)
        check(textLine !== null && textLine.visible && textLine.text === "Too long", "a text too long says why: " + (textLine ? textLine.text : "no error line"))
        paste(pasteText.field, function () {
          check(textLine !== null && textLine.visible && textLine.text === tooLarge, "a refused paste into a text field replaces its validation error: " + (textLine ? textLine.text : "no error line"))
          eq(shell.textPasteMessages, [tooLarge], "a text field reports a refused paste (pasteFailed)")
          longField.focusInput()
          then()
        })
      })
    })
  }

  QtObject {
    id: fakePanel
    property bool opened: false
    function open() {
      opened = true
    }
    function close() {
      opened = false
    }
  }
  FoamySettingsState {
    id: settingsState
    panel: fakePanel
  }

  // A maximumLength lowered while the page is created: this root's
  // Component.onCompleted runs before the field's own (Qt completes in
  // reverse creation order), so only the field's completion can cut then.
  property int createdLimit: 32767
  Component.onCompleted: {
    createdLimit = 5
    Qt.callLater(stepOne)
  }

  function stepOne() {
    // --- icons -----------------------------------------------------------------------------
    var wanted = ["github", "git-branch", "arrow-up", "arrow-down", "eye", "chevron-left", "calendar", "bell", "bell-off", "search", "x", "ellipsis", "mouse", "keyboard", "message-square", "message", "chat", "users", "battery", "battery-low", "battery-medium", "battery-full", "battery-charging", "plug", "zap", "skip-back", "skip-forward", "play", "pause", "shuffle", "repeat", "repeat-1", "music", "megaphone", "info", "user", "inbox", "calendar-days", "hash"]
    var missing = wanted.filter(function (name) {
      return !icon.paths.hasOwnProperty(name)
    })
    eq(missing, [], "requested Lucide icons present")
    eq(icon.paths.info, '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>', "info is Lucide info, not a megaphone")
    icon.name = "chevron-left"
    check(icon.known, "chevron-left is known")
    // Brand marks (Simple Icons) are solid shapes: drawn filled, not stroked.
    var marks = ["zendesk", "todoist"]
    marks.forEach(function (mark) {
      icon.name = mark
      var svg = decodeURIComponent(String(icon.source))
      check(icon.known && svg.indexOf('<g fill="' + icon.color.toString() + '" stroke="none">' + icon.paths[mark] + '</g>') !== -1, mark + " is a known mark, drawn filled")
    })

    // --- textKey arity ---------------------------------------------------------------------
    cursor.emitTextKey(catcher, "s")
    eq(catcher.lastText, "s", "emitTextKey reaches a (text, modifiers) handler")
    check(cursor.plain(catcher.lastModifiers), "a plain letter is plain on " + host)
    cursor.emitTextKey(catcher, "s", Qt.AltModifier)
    check(!cursor.plain(catcher.lastModifiers), "Alt+S is not plain")
    check(cursor.plain(Qt.ShiftModifier) && !cursor.plain(Qt.ControlModifier), "plain() ignores Shift only")

    // --- SafeTextField.maximumLength ---------------------------------------------------
    eq([createdField.maximumLength, createdField.text], [5, "abcde"], "a maximumLength lowered while the field is created cuts its text")
    field.text = "abcdefgh"
    eq(field.text, "abcde", "maximumLength trims typed text")
    field.maximumLength = 3
    eq(field.text, "abc", "lowering maximumLength trims")
    idleShown.focusInput()
    idleShown.selectAll()
    type("typed")
    longField.focusInput()
    eq([idleShown.seen, idleShown.text], ["typed", "shown"], "editingFinished reads the typed text before a focus-bound Binding shows the value again")
    // A cut never keeps half of a surrogate pair (the emoji is two units).
    field.maximumLength = 5
    field.text = "abcd\uD83D\uDE00"
    eq([field.text, field.text.length], ["abcd", 4], "a longer text is cut by whole code point (text, UTF-16 units)")
    field.text = "abc\uD83D\uDE00"
    field.maximumLength = 4
    eq([field.text, field.text.length], ["abc", 3], "lowering maximumLength cuts by whole code point (text, UTF-16 units)")
    // Typing in a full field drops the key wherever the caret is, as Qt's
    // TextInput does: the end of the text stays ("09:00" never becomes "089:0").
    field.maximumLength = 5
    field.text = "09:00"
    field.focusInput()
    field.cursorPosition = 1
    type("8")
    eq(field.text, "09:00", "a key typed inside a full field is dropped, and the end of the text stays")
    field.select(0, 1)
    type("1")
    eq(field.text, "19:00", "a key typed over a selection in a full field replaces it")
    longField.focusInput()
    field.maximumLength = 3

    // --- FoamyDropdown keeps the caller's value binding ----------------------------------
    dropdown.select("b")
    eq(shell.dropdownChanges, ["b"], "selection emits changed()")
    eq(dropdown.shownValue, "b", "the pick shows until the setting catches up")
    eq(dropdown.value, "a", "selection does not assign value")
    shell.dropdownSetting = "b"
    eq([dropdown.value, dropdown.shownValue], ["b", "b"], "the binding follows the setting")
    shell.dropdownSetting = "c"
    eq([dropdown.value, dropdown.shownValue], ["c", "c"], "a later external change still shows (binding intact)")
    // a save that failed: the caller says so, and the saved value shows at once
    dropdown.select("b")
    dropdown.saveFailed()
    eq([dropdown.value, dropdown.shownValue], ["c", "c"], "saveFailed() drops the unsaved pick at once")
    // a save that never lands
    dropdown.select("a")
    dropdownRevert.start()
    serialPicks()

    // --- FoamyAction: a long tooltip wraps in a capped width ---------------------------
    wait.waitFor(function () {
      if (window.visible && !tipAction.hovered)
        ev.mouseMove(tipAction, 5, 5, -1, Qt.NoButton, Qt.NoModifier)
      var tip = shell.toolTipOf(tipAction)
      return tip !== null && tip.opened
    }, 3000, function (ok) {
      var tip = shell.toolTipOf(tipAction)
      var cap = Style.space(320)
      shell.check(ok && tip.width <= cap + 0.5 && tip.height < window.height / 2, "a long tooltip wraps within " + cap + " px instead of covering the window: " + (tip ? tip.width + "x" + tip.height : "none"))
      // A name typed without spaces has no word break, and still stays in the box.
      tipAction.tooltipText = "Pause synchronization for " + "X".repeat(512)
      var fits = function () {
        var text = tip.contentItem
        return tip.width <= cap + 0.5 && text.contentWidth + text.leftPadding + text.rightPadding <= tip.width + 0.5
      }
      wait.waitFor(fits, 2000, function (inside) {
        shell.check(inside, "an unbreakable word wraps inside the tooltip: " + tip.contentItem.contentWidth + " px of text in " + tip.width + " px")
        // A path of any length keeps the tooltip a few lines high, cut with a "…".
        tipAction.tooltipText = "Open /home/test/" + "Sync/Folder-with-a-long-name/".repeat(140) + "\nFolder ID: abcde-fghij"
        wait.waitFor(function () {
          return tip.height < window.height / 3 && fits()
        }, 2000, function (short) {
          var lines = String(tip.text).split("\n")
          shell.check(short && lines.length === 2 && lines[0].slice(-1) === "\u2026" && lines[1] === "Folder ID: abcde-fghij", "a long path is cut so the tooltip stays short and shows its last line: " + tip.width + "x" + tip.height + ", " + lines.length + " lines")
          tipAction.tooltipText = "Refresh"
          wait.waitFor(function () {
            return tip.width < cap / 2
          }, 2000, function () {
            shell.check(Math.abs(tip.width - (tip.implicitContentWidth + tip.leftPadding + tip.rightPadding)) < 0.5 && tip.text === "Refresh", "a short tooltip keeps its own width and text: " + tip.width)
            shell.longTip(tipButton, function (text) {
              tipButton.tooltipText = text
            }, "FoamyButton", function () {
              shell.longTip(shell.findNamed(tipFooter, "foamyFooterStatus"), function (text) {
                tipFooter.statusTooltip = text
              }, "FoamyPanelFooter status", function () {
                shell.done("tooltip")
              })
            })
          }, "a short tooltip is narrow")
        })
      })
    }, "the action's tooltip opens")

    // --- FoamyNumberField: binding-safe numeric settings ------------------------------------
    eq(numberField.field.text, "5", "shows the bound value")
    shell.numberSetting = 7
    eq(numberField.field.text, "7", "follows an external change while not editing")
    numberField.field.text = "9"
    numberField.field.textEdited()
    check(numberField.editing, "typing starts a draft")
    shell.numberSetting = 8
    eq(numberField.field.text, "9", "an external change doesn't overwrite the draft")
    numberField.field.focusInput()
    key(Qt.Key_Return)
    eq(shell.numberCommits, [9], "Enter commits a valid changed draft once")
    // The focus goes to a plain field, not to another settings field, so the
    // text field's own focus-out checks below still start without the focus.
    longField.focusInput()
    eq(shell.numberCommits, [9], "focus-out after Enter doesn't commit twice")
    shell.numberSetting = 9
    eq(numberField.field.text, "9", "shows the saved value")
    shell.numberSetting = 12
    eq(numberField.field.text, "12", "binding still drives the field after a commit")
    numberField.field.text = "12"
    numberField.field.textEdited()
    numberField.commitEdit(false)
    eq(shell.numberCommits, [9], "an unchanged draft doesn't commit")
    numberField.field.text = "abc"
    numberField.field.textEdited()
    check(!numberField.commitEdit(false) && numberField.error !== "" && numberField.field.text === "abc", "Enter on invalid input keeps the draft and says why")
    numberField.field.text = "500"
    numberField.field.textEdited()
    check(numberField.commitEdit(true) && numberField.field.text === "12" && numberField.error !== "", "focus-out on an out-of-range draft restores the value")
    eq(shell.numberCommits, [9], "invalid drafts never commit")
    numberField.field.focusInput()
    type("33")
    check(numberField.editing && numberField.field.text.indexOf("33") !== -1, "typed digits reach the field and start a draft: " + numberField.field.text)
    var numberBacks = shell.pageBacks
    key(Qt.Key_Escape)
    check(numberField.field.text === "12" && !numberField.editing && shell.pageBacks === numberBacks, "Escape restores the value and the page stays: " + [numberField.field.text, numberField.editing, shell.pageBacks - numberBacks])
    key(Qt.Key_Up)
    check(numberField.field.text === "17" && numberField.editing, "Up steps the draft by stepSize: " + numberField.field.text)
    key(Qt.Key_Return)
    eq(shell.numberCommits, [9, 17], "Enter commits the stepped draft once")
    longField.focusInput()
    eq(shell.numberCommits, [9, 17], "focus-out after Enter doesn't commit it again")
    numberField.field.focusInput()
    key(Qt.Key_Up)
    longField.focusInput()
    check(!numberField.editing && numberField.field.text === "22", "focus-out ends the stepped draft: " + [numberField.editing, numberField.field.text])
    eq(shell.numberCommits, [9, 17, 22], "focus-out commits a valid changed draft once")
    numberField.field.focusInput()
    numberField.field.selectAll()
    type("500")
    longField.focusInput()
    check(numberField.field.text === "12" && !numberField.editing && numberField.error !== "", "focus-out on an out-of-range draft restores the value and says why: " + [numberField.field.text, numberField.editing, numberField.error])
    eq(shell.numberCommits, [9, 17, 22], "an out-of-range draft never commits on focus-out")
    // The field hides (its settings page closes) during an invalid draft:
    // shown again, it looks as if nothing was typed.
    numberField.field.focusInput()
    numberField.field.selectAll()
    type("500")
    numberField.visible = false
    numberField.visible = true
    check(numberField.field.text === "12" && !numberField.editing && numberField.error === "", "an out-of-range draft ended by hiding the field is gone when it shows again, with no error: " + [numberField.field.text, numberField.editing, numberField.error])
    numberField.field.focusInput()
    numberField.field.selectAll()
    type("500")
    longField.focusInput()
    check(numberField.error !== "", "after a focus-out on an out-of-range draft the error shows: " + numberField.error)
    numberField.visible = false
    numberField.visible = true
    eq(numberField.error, "", "and is gone when the field shows again")
    eq(shell.numberCommits, [9, 17, 22], "a hidden out-of-range draft never commits")
    numberField.cancelEdit()
    eq([numberField.parse("٤٢"), numberField.parse("42"), numberField.parse("1.5")], [42, 42, NaN], "language digits parse; integers only when decimals is 0")
    eq([decimalField.parse("2,5"), decimalField.parse("2.56")], [2.5, 2.6], "decimal comma accepted, rounded to decimals")

    // --- FoamyNumberField: mixed units stack flush (LTR and RTL) ---------------------------
    checkInsets()
    checkUnitStack("LTR")
    unitStack.LayoutMirroring.childrenInherit = true
    unitStack.LayoutMirroring.enabled = true
    wait.waitFor(function () {
      return percentField.field.mapToItem(unitStack, 0, 0).x > 0
    }, 2000, function () {
      shell.checkUnitStack("RTL")
      unitStack.LayoutMirroring.enabled = false
      shell.done("unit stack")
    }, "the unit stack mirrors")

    // --- FoamyTextSettingField: the same rules for free text --------------------------------
    eq(textSetting.field.text, "abc", "text field shows the bound value")
    shell.textSetting = "xyz"
    eq(textSetting.field.text, "xyz", "text field follows an external change")
    textSetting.field.text = " new "
    textSetting.field.textEdited()
    shell.textSetting = "other"
    eq(textSetting.field.text, " new ", "draft survives an external change")
    check(textSetting.commitEdit(false) && JSON.stringify(shell.textCommits) === JSON.stringify(["new"]), "commits the trimmed draft once")
    textSetting.field.editingFinished()
    eq(shell.textCommits, ["new"], "no second commit on focus-out")
    textSetting.field.text = "toolong"
    textSetting.field.textEdited()
    check(!textSetting.commitEdit(false) && textSetting.error === "Too long", "validate() message on Enter")
    textSetting.field.focusInput()
    type("x")
    var textBacks = shell.pageBacks
    key(Qt.Key_Escape)
    check(textSetting.field.text === "other" && !textSetting.editing && shell.pageBacks === textBacks, "Escape restores the bound value and the page stays: " + [textSetting.field.text, textSetting.editing, shell.pageBacks - textBacks])
    shell.textSetting = "later"
    eq(textSetting.field.text, "later", "binding intact after Escape")
    textSetting.field.focusInput()
    textSetting.field.selectAll()
    type("new2")
    longField.focusInput()
    check(!textSetting.editing && textSetting.field.text === "new2", "focus-out ends the text draft: " + [textSetting.editing, textSetting.field.text])
    eq(shell.textCommits, ["new", "new2"], "focus-out commits a valid changed text draft once")
    shell.textSetting = "new2"
    textSetting.field.focusInput()
    textSetting.field.selectAll()
    type("toolong")
    longField.focusInput()
    check(textSetting.field.text === "new2" && !textSetting.editing && textSetting.error === "Too long", "focus-out on an invalid text draft restores the value and says why: " + [textSetting.field.text, textSetting.editing, textSetting.error])
    eq(shell.textCommits, ["new", "new2"], "an invalid text draft never commits on focus-out")
    textSetting.visible = false
    textSetting.visible = true
    eq(textSetting.error, "", "the focus-out error is gone when the text field shows again")
    textSetting.field.focusInput()
    textSetting.field.selectAll()
    type("toolong")
    textSetting.visible = false
    textSetting.visible = true
    check(textSetting.field.text === "new2" && !textSetting.editing && textSetting.error === "", "an invalid text draft ended by hiding the field is gone when it shows again, with no error: " + [textSetting.field.text, textSetting.editing, textSetting.error])
    eq(shell.textCommits, ["new", "new2"], "a hidden invalid text draft never commits")
    textSetting.cancelEdit()

    // --- FoamyPrefsQueue with a synchronously reflecting host (4.5) ---------------------------
    syncQueue.save("a", "one")
    eq(Object.keys(syncQueue.pending), [], "a save the host reflects at once doesn't stay pending")
    syncQueue.settings = ({
        id: "foamy.sync",
        a: "external",
        b: ""
      // another monitor changes a
      })
    eq(syncQueue.value("a"), "external", "an outside change after the save shows")
    syncQueue.save("b", "two")
    eq(syncBar.written[1], {
      a: "external",
      b: "two"
    }, "the next save keeps the outside change (no stale write-back)")

    // --- FoamyNumberField: retry after a failed save; paste errors ------------------------------
    retryField.field.text = "30"
    retryField.field.textEdited()
    retryField.commitEdit(false)
    retryField.field.text = "30"
    retryField.field.textEdited()
    retryField.commitEdit(false)
    eq(shell.retryCommits, [30, 30], "retyping the same value after a failed save commits again")
    retryField.saveFailed()
    eq(retryField.field.text, "20", "saveFailed() shows the saved value again")
    retryField.field.text = "30"
    retryField.field.textEdited()
    retryField.commitEdit(false)
    eq(shell.retryCommits, [30, 30, 30], "and the same input can be committed after saveFailed()")
    retryField.field.pasteError = "Clipboard paste timed out. Copy the text again."
    eq(shell.pasteMessage, "Clipboard paste timed out. Copy the text again.", "a refused paste is reported (pasteFailed)")
    retryField.field.pasteError = ""

    // --- state switches build and destroy fields (no TypeError in the log) ----------------
    stateFlip.start()

    // --- FoamyHeroBand keeps at most one cover decoded ----------------------------------------
    showCover(0)

    // --- FoamyPrefsQueue: inline, two saves before the host reflects the first -------
    check(inlineQueue.save("a", "one"), "inline save a")
    check(inlineQueue.save("b", "two"), "inline save b")
    eq(inlineBar.saved.length, 2, "two inline writes")
    eq(inlineBar.saved[1], {
      a: "one",
      b: "two",
      keep: 1
    }, "second save merges over the pending first, not the stale entry")
    eq(inlineQueue.value("a"), "one", "effective settings show the pending value")
    inlineQueue.settings = ({
        id: "foamy.test",
        a: "one",
        b: "two",
        keep: 1
      })
    eq(Object.keys(inlineQueue.pending), [], "pending settles once the host reflects it")
    check(!inlineQueue.save("list", [1, 2, 3, 4]), "array maxItems is enforced")
    eq(inlineQueue.error, "That value isn't allowed.", "error message for the catalog")
    eq(inlineBar.saved.length, 2, "an invalid value writes nothing")
    eq(shell.inlineFailures, ["That value isn't allowed."], "failed() reports it")

    // --- FoamyPrefsQueue: a value the host never reflects expires ----------------------
    check(expiringQueue.save("a", "x") && expiringBar.saved.length === 1, "a save the host never reflects is written")
    eq(expiringQueue.value("a"), "x", "and shows while it is pending")
    // The expiry timer ticks every 1000 ms.
    wait.waitFor(function () {
      return Object.keys(expiringQueue.pending).length === 0
    }, 3000, function () {
      shell.eq(expiringQueue.value("a"), "stored", "the host's value wins after reflectTimeoutMs")
      shell.done("expiry")
    }, "an unreflected pending value expires")

    // --- FoamyPrefsQueue: an invalid stored array is kept, not replaced ----------------
    eq([storedListProblem, storedListProblemCall], ["That value isn't allowed.", "That value isn't allowed."], "bindings on storedProblems.list and storedProblem(\"list\") name it")
    check(!storedQueue.save("list", [9]), "a save over the invalid stored list is refused")
    eq(storedQueue.error, "The saved list in shell.json isn't valid, so it wasn't replaced.", "with its own message")
    eq(storedFailures, ["The saved list in shell.json isn't valid, so it wasn't replaced."], "failed() reports it")
    check(!storedQueue.saving && !storedQueue.canRetry, "nothing runs and nothing to retry")
    eq(storedBar.saved.length, 0, "nothing was written")
    check(storedQueue.save("a", "x"), "another key still saves")
    eq(storedBar.saved[0], {
      list: [1, 2, 3, 4],
      a: "x"
    }, "carrying the stored list over verbatim")
    check(storedQueue.save("list", [9], true), "a forced save replaces it")
    eq(storedBar.saved[1], {
      list: [9],
      a: "x"
    }, "the forced value is written")
    eq([storedListProblem, storedListProblemCall], ["", ""], "and both bindings clear once the forced list is in effect")

    // --- FoamyPrefsQueue: a list passed in as a QML sequence wrapper -----------------
    var wrappedList = shell.wrappedSettings({
      list: [1, 2]
    }).list
    check(!Array.isArray(wrappedList) && wrappedList.length === 2, "createObject hands a list over as a sequence wrapper")
    var wrappedQueue = wrappedQueueComponent.createObject(shell, {
      moduleName: "foamy.wrapped",
      settings: {
        id: "foamy.wrapped",
        list: [1, 2],
        a: ""
      }
    })
    eq(wrappedQueue.storedProblem("list"), "", "a wrapped valid list has no stored problem")
    eq(wrappedQueue.storedProblems, {}, "storedProblems is empty")
    eq(wrappedQueue.value("list"), [1, 2], "it reads as stored, not as the default")
    check(Array.isArray(wrappedQueue.value("list")), "as a real Array")
    var savedBefore = storedBar.saved.length
    check(wrappedQueue.save("list", [1, 2, 3]), "a save of the wrapped list isn't refused")
    eq(wrappedQueue.error, "", "and sets no error")
    var wrappedWrite = storedBar.saved[savedBefore] || {}
    eq([wrappedWrite.list, wrappedWrite.a], [[1, 2, 3], ""], "the new list is written")
    // No list stored yet, so the save goes through either way; the host then
    // reflects it as a wrapper.
    var wrappedNew = wrappedQueueComponent.createObject(shell, {
      moduleName: "foamy.wrapped-new",
      settings: {
        id: "foamy.wrapped-new",
        a: ""
      }
    })
    check(wrappedNew.save("list", [5]), "a first list saves")
    check("list" in wrappedNew.pending, "and is pending until the host reflects it")
    wrappedNew.settings = shell.wrappedSettings({
      id: "foamy.wrapped-new",
      list: [5],
      a: ""
    })
    eq(Object.keys(wrappedNew.pending), [], "pending settles when the host reflects the list as a wrapper")
    eq(wrappedNew.storedProblems, {}, "and the reflected list is no stored problem")
    var wrappedInvalid = wrappedQueueComponent.createObject(shell, {
      moduleName: "foamy.wrapped-invalid",
      settings: {
        id: "foamy.wrapped-invalid",
        list: [1, 2, 3, 4],
        a: ""
      }
    })
    eq(wrappedInvalid.storedProblem("list"), "That value isn't allowed.", "a wrapped invalid list is still a stored problem")
    check(!wrappedInvalid.save("list", [9]), "and a save over it is still refused")
    eq(wrappedInvalid.error, "The saved list in shell.json isn't valid, so it wasn't replaced.", "with the stored-invalid message")
    eq(storedBar.saved.length, savedBefore + 2, "nothing more was written")

    // --- FoamyPrefsQueue: CLI, one save at a time, newest value per key ---------------
    cliQueue.save("a", "first")
    cliQueue.save("a", "second")
    cliQueue.save("b", "other")
    cliQueue.save("a", "third")
    check(cliQueue.saving, "CLI save in flight")
    eq(cliQueue.waiting.length, 2, "waiting saves keep the newest value per key")
    // The fake omarchy takes 0.3 s per call: three calls run.
    wait.waitFor(function () {
      return !cliQueue.busy && callLog.lines().length >= 3
    }, 6000, function () {
      shell.stepTwo()
    }, "the CLI queue drains")
  }

  FileViewProbe {
    id: callLog
    path: shell.calls
  }

  function glyphEdges(field) {
    var ed = field.editorItem
    var start = ed.mapToItem(field, ed.positionToRectangle(0).x, 0).x
    var end = ed.mapToItem(field, ed.positionToRectangle(ed.length).x, 0).x
    return [Math.round(start), Math.round(end)]
  }
  function checkInsets() {
    var ltr = insetRepeater.itemAt(0), rtl = insetRepeater.itemAt(1)
    var a = glyphEdges(ltr.byWidth), b = glyphEdges(ltr.byLayout)
    eq(a, b, "LTR: text starts at the same x whether the field is sized by width or by a layout")
    check(Math.abs(a[0] - (Style.spacing.controlPaddingX + 1)) <= 1, "LTR: text inset is padding + border " + a[0])
    eq(glyphEdges(ltr.textSetting.field)[0], a[0], "LTR: FoamyTextSettingField text lines up")
    var n = ltr.numberSetting.field
    eq(n.editorItem.mapToItem(n, n.editorItem.positionToRectangle(0).x, 0).x | 0, a[0], "LTR: FoamyNumberField text lines up")
    var c = glyphEdges(rtl.byWidth), d = glyphEdges(rtl.byLayout)
    eq(c, d, "RTL: text ends at the same x whether sized by width or by a layout")
    check(Math.abs(c[1] - (rtl.byWidth.width - Style.spacing.controlPaddingX - 1)) <= 2, "RTL: text sits against the right padding " + c)
    eq(glyphEdges(rtl.textSetting.field)[1], c[1], "RTL: FoamyTextSettingField text lines up")
    longField.editorItem.cursorPosition = longField.editorItem.length
    wait.waitFor(function () {
      return longField.contentX > 0
    }, 2000, function () {
      var ed = longField.editorItem
      var cursor = ed.mapToItem(longField, ed.cursorRectangle.x, 0).x
      shell.check(longField.contentX > 0 && cursor > 0 && cursor <= longField.width, "long text still scrolls to keep the cursor visible " + longField.contentX + " " + cursor)
      shell.done("long field")
    }, "long text scrolls to the caret")
  }

  // Gives the tooltip of `item` a long path whose last name has no break,
  // hovers `item` and checks that the tooltip stays in its box, a few lines
  // high, and keeps the text's last line.
  function longTip(item, setText, label, then) {
    setText("Open /home/test/" + "Sync/Folder-with-a-long-name/".repeat(140) + "X".repeat(512) + "\nFolder ID: abcde-fghij")
    wait.waitFor(function () {
      if (window.visible)
        ev.mouseMove(item, 5, 5, -1, Qt.NoButton, Qt.NoModifier)
      var tip = shell.toolTipOf(item)
      return tip !== null && tip.opened
    }, 3000, function (opened) {
      var tip = shell.toolTipOf(item)
      var cap = Style.space(320)
      wait.waitFor(function () {
        var text = tip.contentItem
        return tip.width <= cap + 0.5 && text.contentWidth + text.leftPadding + text.rightPadding <= tip.width + 0.5 && tip.height < window.height / 3
      }, 2000, function (inside) {
        var lines = tip ? String(tip.text).split("\n") : []
        shell.check(opened && inside && lines.length === 2 && lines[0].slice(-1) === "\u2026" && lines[1] === "Folder ID: abcde-fghij", label + ": a long tooltip stays in its " + cap + " px box, a few lines high, with its last line: " + (tip ? tip.width + "x" + tip.height + ", " + tip.contentItem.contentWidth + " px of text, " + lines.length + " lines" : "none"))
        then()
      })
    }, label + ": the tooltip opens")
  }
  // The first item named `name` under `item`, depth first.
  function findNamed(item, name) {
    for (var i = 0; i < item.children.length; i++) {
      var child = item.children[i]
      if (child.objectName === name)
        return child
      var found = shell.findNamed(child, name)
      if (found)
        return found
    }
    return null
  }

  // The PanelToolTip inside a FoamyAction (a Popup, so not among its children).
  function toolTipOf(action) {
    for (var i = 0; i < action.data.length; i++) {
      var d = action.data[i]
      if (d && d.delay !== undefined && d.text !== undefined)
        return d
    }
    return null
  }

  function checkUnitStack(label) {
    var fields = [percentField, celsiusField, plainField].map(function (f) {
      var p = f.field.mapToItem(unitStack, 0, 0)
      return [Math.round(p.x), Math.round(f.field.width)]
    })
    eq(fields[1], fields[0], label + ": % and °C fields have the same x and width")
    eq(fields[2], fields[0], label + ": a unitless field with reserveUnit lines up too")
    if (label === "RTL")
      check(fields[0][0] > 0, "RTL: the unit column is on the left, the field after it")
    else
      eq(fields[0][0], 0, "LTR: fields start at the row's start")
  }
  Timer {
    id: stateFlip
    interval: 40
    repeat: true
    onTriggered: {
      stateSwitcher.flips++
      if (stateSwitcher.flips >= 12) {
        stop()
        shell.check(stateSwitcher.item !== null, "settings states switch 12 times")
        shell.done("state switches")
      }
    }
  }

  // Shows covers 0, 1 and 2 in turn. Each one is decoded before the next
  // replaces it, so an earlier cover that is still loaded was never unloaded.
  readonly property int coverCount: 3
  function showCover(i) {
    coverBand.imageSource = coverUrl(i)
    wait.waitFor(function () {
      return coverBand.loadedImage === String(shell.coverUrl(i)) && shell.coverSurface().isImageLoaded(shell.coverUrl(i))
    }, 3000, function (ok) {
      if (ok && i + 1 < shell.coverCount)
        shell.showCover(i + 1)
      else
        shell.checkCovers()
    }, "cover " + i + " is decoded")
  }
  function checkCovers() {
    var surface = coverSurface()
    var last = coverUrl(coverCount - 1)
    var stale = []
    for (var i = 0; i < coverCount - 1; i++)
      if (surface.isImageLoaded(coverUrl(i)))
        stale.push(i)
    eq(stale, [], coverCount + " covers cycled: no earlier cover stays decoded")
    check(coverBand.loadedImage === String(last) && surface.isImageLoaded(last), "only the current cover is loaded")
    coverBand.visible = false
    check(coverBand.loadedImage === "" && !surface.isImageLoaded(last), "a hidden band (closed popup) unloads its cover")
    coverBand.visible = true
    check(coverBand.loadedImage === String(last), "showing the band again reloads it")
    coverBand.imageSource = ""
    check(coverBand.loadedImage === "" && !surface.isImageLoaded(last), "clearing the source unloads the cover")
    done("covers")
  }

  Timer {
    id: dropdownRevert
    interval: 800
    onTriggered: {
      shell.eq(dropdown.shownValue, "c", "an unconfirmed pick gives way to the real value")
      shell.done("dropdown")
    }
  }

  function stepTwo() {
    var lines = callLog.lines()
    eq(lines, ["omarchy bar set foamy.test a \"first\" --json", "omarchy bar set foamy.test b \"other\" --json", "omarchy bar set foamy.test a \"third\" --json"], "CLI saves run one at a time, superseded values skipped")
    check(!cliQueue.busy && cliQueue.error === "", "queue drained without errors")
    stepThree()
  }

  function stepThree() {
    // --- IPC: prefer / others / call -----------------------------------------------------
    check(guardPreference.answering && guardPreference.others === 0, "guarded target settled with no rival")
    var registry = Resolver.registry(shell)
    rival = rivalHandler.createObject(shell)
    registry.handlers.splice(registry.handlers.indexOf(rival), 1)
    // a later service jumps ahead
    registry.handlers.unshift(rival)
    eq(Resolver.call(shell, "foamy.guarded", "who", []).output, "rival", "the rival took the route")
    eq(Resolver.call(shell, "foamy.shared-target", "who", []), {
      ran: true,
      output: "mine"
    }, "FoamyIpcPreference puts its handler first")
    check(preference.answering && preference.others === 1, "preference reports one other handler")
    late = lateHandler.createObject(shell)
    // someone else claims the target
    Resolver.prefer(shell, late)
    eq(Resolver.call(shell, "foamy.shared-target", "who", []).output, "late", "another prefer() takes over")
    eq(Resolver.call(shell, "foamy.shared-target", "nope", []), {
      ran: false
    }, "undeclared functions don't run")
    // destroy() is callable on every handler but not declared: only the
    // registry's list of declared functions refuses it.
    eq(Resolver.call(shell, "foamy.shared-target", "destroy", []), {
      ran: false
    }, "a handler's QObject methods don't run")
    peer.call("foamy.shared-target", "who", [], function (ok, output) {
      shell.peerResult = {
        ok: ok,
        output: output
      }
    })
    peer.call("foamy.absent", "status", ["[1]"], function (ok, output) {
      shell.peerFallback = {
        ok: ok,
        output: output
      }
    })
    // The fake omarchy-shell answers foamy.gone as the real one does for a
    // missing target: an error line and exit 0.
    peer.call("foamy.gone", "status", [], function (ok, output) {
      shell.peerGone = {
        ok: ok,
        output: output
      }
    })
    // limit: 1. The second call finds the one process slot taken.
    inNarrowCall = true
    narrow.call("foamy.limited", "status", [], function (ok, output) {
      shell.limitedFirst = {
        ok: ok,
        output: output
      }
    })
    narrow.call("foamy.limited", "status", [], function (ok, output) {
      shell.limitedSecond = {
        ok: ok,
        output: output,
        insideCall: shell.inNarrowCall
      }
    })
    inNarrowCall = false

    // --- FoamySettingsState ---------------------------------------------------------------
    settingsState.holdOnClose = true
    settingsState.show()
    fakePanel.close()
    check(settingsState.editing, "holdOnClose keeps Settings across a close")

    // The preferences re-claim every 300 ms; the peer calls answer later.
    wait.waitFor(function () {
      return shell.peerResult !== null && shell.peerFallback !== null && shell.peerGone !== null && shell.limitedFirst !== null && shell.limitedSecond !== null && Resolver.call(shell, "foamy.shared-target", "who", []).output === "mine" && Resolver.call(shell, "foamy.guarded", "who", []).output === "guarded"
    }, 3000, function () {
      shell.stepFour()
    }, "peer calls answer and the preferences re-claim")
  }

  property var late: null
  property var peerResult: null
  property var peerFallback: null
  property var peerGone: null
  property var limitedFirst: null
  property var limitedSecond: null
  property bool inNarrowCall: false

  function stepFour() {
    eq(shell.peerResult, {
      ok: true,
      output: "late"
    }, "FoamyPeerIpc answers in-process")
    // Re-claim within the preference interval.
    eq(Resolver.call(shell, "foamy.shared-target", "who", []).output, "mine", "FoamyIpcPreference re-claims the target")
    eq(Resolver.call(shell, "foamy.guarded", "who", []).output, "guarded", "a rival that arrived after the check settled is pushed back (lock route)")
    eq(shell.peerFallback, {
      ok: true,
      output: "cli: foamy.absent status [1]"
    }, "unknown in-process target uses the CLI")
    eq(shell.peerGone, {
      ok: false,
      output: "Target not found: foamy.gone"
    }, "a missing target fails although omarchy-shell exits 0")
    eq(shell.limitedSecond, {
      ok: false,
      output: "",
      insideCall: false
    }, "a call over the process limit fails, and later, not inside call()")
    eq(shell.limitedFirst, {
      ok: true,
      output: "cli: foamy.limited status"
    }, "the call within the limit runs")
    eq(callLog.lines().filter(function (line) {
      return line.indexOf("omarchy-shell foamy.limited") === 0
    }), ["omarchy-shell foamy.limited status"], "the limit starts one process")
    var unfinished = function () {
      return shell.laterChecks.filter(function (name) {
        return shell.finished.indexOf(name) === -1
      })
    }
    wait.waitFor(function () {
      return unfinished().length === 0
    }, 5000, function () {
      shell.eq(unfinished(), [], "every later check ran")
      // Last, so no other check types meanwhile.
      shell.refusedPastes(function () {
        shell.disabledDropdown(function () {
          shell.linkedDropdowns(function () {
            console.log("FOAMY RESULT " + host + " checks=" + checks + " failures=" + failures)
            console.log("FOAMY DONE")
            Qt.quit()
          })
        })
      })
    })
  }
}
