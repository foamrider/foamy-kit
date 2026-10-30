import QtQuick
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin" as Demo
import "plugin/kit"
import "plugin/kit/FoamyPrefs.js" as Prefs
import "plugin/kit/FoamyIpcResolver.js" as IpcResolver

// Runtime checks for FoamyI18n, FoamyMotion, FoamyPalette, FoamyStyle,
// FoamyPrefs, FoamyCursor, FoamyShared/FoamyMember and FoamyIpc, and the
// demo Panel (3 instances, as on 3 monitors). FOAMY_LANG picks the
// language-dependent expectations.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property string lang: Quickshell.env("FOAMY_LANG") || "en"
  readonly property bool v45: host === "4.5"
  property int checks: 0
  property int failures: 0

  function check(ok, label) {
    checks++
    if (!ok) { failures++; console.log("FOAMY FAIL " + host + "/" + lang + " " + label) }
  }
  function eq(actual, expected, label) {
    check(actual === expected, label + ": got " + JSON.stringify(actual) + ", expected " + JSON.stringify(expected))
  }

  FloatingWindow {
    id: window
    implicitWidth: 1920
    implicitHeight: 1080
    color: "black"
    ScreenSim { id: sim }
    Row {
      id: barRow
      y: 4
      x: 1200
      spacing: 40
      Repeater {
        id: panels
        model: 3
        Demo.Panel {
          bar: mockBar
          moduleName: "foamy.kit-demo"
          settings: ({ id: "foamy.kit-demo", showCount: true, refreshSeconds: 60, layout: "list", extra: "kept" })
        }
      }
    }
  }

  MockBar { id: mockBar; moduleName: "foamy.kit-demo" }
  QtObject { id: shellLessBar; property var shell: null }

  FoamyCursor { id: cursor; count: 3 }

  Component.onCompleted: Qt.callLater(stepOne)

  function stepOne() {
    // --- FoamyI18n ------------------------------------------------------------
    eq(FoamyI18n.translationsAvailable, v45, "translations backend on " + host)
    if (!v45 || lang === "en") {
      eq(FoamyI18n.t("Devices"), "Devices", "t English")
      eq(FoamyI18n.tn("%1 devices", 1), "1 device", "tn one (English)")
      eq(FoamyI18n.tn("%1 devices", 3), "3 devices", "tn other (English)")
      eq(FoamyI18n.number(13.14, 1), "13.1", "number English")
    }
    if (!v45) {
      eq(FoamyI18n.formatLocale, Qt.locale().name, "4.0 keeps the system calendar locale")
      eq(FoamyI18n.rightToLeft, false, "4.0 left-to-right")
    }
    if (v45 && lang === "da") {
      eq(FoamyI18n.language, "da", "language follows the picker")
      eq(FoamyI18n.t("Devices"), "Enheder", "t Danish")
      eq(FoamyI18n.tn("%1 devices", 1), "1 enhed", "tn one (Danish)")
      eq(FoamyI18n.tn("%1 devices", 3), "3 enheder", "tn other (Danish)")
      eq(FoamyI18n.t("Battery %1%", 13.5), "Batteri 13,5%", "numeric hole uses the Danish decimal")
      eq(FoamyI18n.t("Battery %1%", 8080), "Batteri 8080%", "numbers are ungrouped")
      eq(FoamyI18n.t("Name filter"), "Name filter", "missing Danish string falls back to English")
      eq(FoamyI18n.number(13.14, 1), "13,1", "number Danish")
      eq(FoamyI18n.formatLocale, "da-DK", "format locale from the registry")
      eq(FoamyI18n.rightToLeft, false, "Danish is left-to-right")
    }
    if (v45 && lang === "ar") {
      eq(FoamyI18n.rightToLeft, true, "Arabic mirrors")
      eq(FoamyI18n.tn("%1 devices", 2), "جهازان", "tn dual (Arabic)")
      eq(FoamyI18n.tn("%1 devices", 5), FoamyI18n.number(5) + " أجهزة", "tn few (Arabic), count in the language's digits")
    }
    eq(FoamyI18n.t("%1 and {name}", ["%2{name}"]), "%2{name} and {name}", "values substitute once (user text stays literal)")
    eq(FoamyI18n.t("Hello {name}", { name: "$&" }), "Hello $&", "replacement patterns stay literal")

    // --- FoamyMotion ------------------------------------------------------------
    eq(FoamyMotion.duration(180), 180, "duration passes through with motion on")
    eq(FoamyMotion.hover, 100, "hover token")
    eq(FoamyMotion.reduceMotion, false, "motion on by default")
    eq(FoamyMotion.easeOut.length, 6, "easeOut curve")
    check(FoamyMotion.loopAllowed(true), "loops allowed with motion on")
    if (v45) {
      Style.reduceMotion = true
      eq(FoamyMotion.reduceMotion, true, "reduceMotion follows Style.reduceMotion")
      eq(FoamyMotion.duration(180), 0, "durations collapse under reduced motion")
      eq(FoamyMotion.fadeIn, 0, "named tokens collapse under reduced motion")
      check(!FoamyMotion.loopAllowed(true), "loops stop under reduced motion")
      Style.reduceMotion = false
      eq(FoamyMotion.fadeIn, 180, "tokens recover")
    }

    // --- FoamyStyle / FoamyPalette -------------------------------------------------
    Style.cornerRadius = 6
    eq(FoamyStyle.radius, 12, "radius is 2x Hyprland rounding")
    eq(FoamyStyle.font.body, Style.space(12), "body size maps to space(12)")
    eq(FoamyStyle.fontFamily, "sans-serif", "foamy body font")
    eq(FoamyStyle.popupWidth, Style.space(420), "standard width")
    eq(FoamyStyle.popupWidthWide, Style.space(560), "wide width")
    check(Qt.colorEqual(FoamyPalette.warning, "#f9e2af"), "warning from theme yellow: " + FoamyPalette.warning)
    check(Qt.colorEqual(FoamyPalette.success, "#a6e3a1"), "success from theme green")
    check(Qt.colorEqual(FoamyPalette.error, "#f38ba8"), "error from theme red")
    check(Qt.colorEqual(FoamyPalette.info, "#94e2d5"), "info from theme cyan")
    eq(FoamyPalette.lightTheme, false, "dark theme mode")
    eq(FoamyPalette.pick(["nope"], "fallback"), "fallback", "status colour fallback")
    eq(FoamyPalette.parse('mode = "light"\n[x]\nred = "#ff0000" # c').red, "#ff0000", "colors.toml parse")
    check(Qt.colorEqual(FoamyPalette.border, Qt.alpha(Commons.Color.popups.text, 0.15)), "border is alpha(popups.text, .15)")

    // --- FoamyCursor ------------------------------------------------------------------
    eq(cursor.index, -1, "cursor starts hidden")
    cursor.move(1); eq(cursor.index, 0, "first move lands on the first stop")
    cursor.move(1); cursor.move(1); cursor.move(1); eq(cursor.index, 2, "cursor clamps at the end")
    cursor.hover(1); eq(cursor.index, 1, "hover moves the same cursor")
    cursor.count = 1; eq(cursor.index, 0, "cursor clamps when the list shrinks")

    // --- FoamyPrefs (QML engine) ---------------------------------------------------------
    var settings = { id: "foamy.kit-demo", showCount: true, refreshSeconds: 60, extra: "kept" }
    var fields = [{ key: "showCount", type: "boolean", defaultValue: true }, { key: "refreshSeconds", type: "integer", min: 30, max: 3600, defaultValue: 60 }]
    var unchanged = Prefs.save(mockBar, "foamy.kit-demo", fields, settings, "showCount", true)
    check(unchanged.ok && !unchanged.changed && unchanged.command.length === 0 && mockBar.saved.length === 0, "unchanged value is not written")
    var inline = Prefs.save(mockBar, "foamy.kit-demo", fields, settings, "showCount", false)
    check(inline.ok && inline.inline && inline.command.length === 0, "saves inline through bar.shell.updateEntryInline")
    eq(JSON.stringify(mockBar.saved[0]), JSON.stringify({ id: "foamy.kit-demo", settings: { showCount: false, refreshSeconds: 60, extra: "kept" } }), "inline save passes the full merged entry")
    var cli = Prefs.save(shellLessBar, "foamy.kit-demo", fields, settings, "refreshSeconds", 300)
    eq(cli.command.join(" "), "omarchy bar set foamy.kit-demo refreshSeconds 300 --json", "falls back to omarchy bar set")
    var bad = Prefs.save(mockBar, "foamy.kit-demo", fields, settings, "refreshSeconds", 5)
    check(!bad.ok && bad.error !== "", "out-of-range value is refused")

    stepTwo.start()
  }

  readonly property var members: {
    var out = []
    for (var i = 0; i < panels.count; i++) if (panels.itemAt(i)) out.push(panels.itemAt(i))
    return out
  }

  function memberOf(panel) {
    for (var i = 0; i < panel.data.length; i++)
      if (panel.data[i] && panel.data[i].scope === "poller" && "isLeader" in panel.data[i]) return panel.data[i]
    return null
  }

  function leaders() {
    var count = 0
    for (var i = 0; i < members.length; i++) if (memberOf(members[i]).isLeader) count++
    return count
  }

  Timer {
    id: stepTwo
    interval: 300
    onTriggered: {
      // --- FoamyShared: one leader for three bar instances ------------------------------
      eq(panels.count, 3, "three bar instances")
      eq(FoamyShared.memberCount("poller"), 3, "the plugin-local singleton is shared by every instance")
      eq(leaders(), 1, "exactly one leader")
      eq(memberOf(members[0]).isLeader, true, "first instance leads")
      eq(memberOf(members[2]).demanded, false, "no demand while every popup is closed")
      members[2].open()
      eq(memberOf(members[0]).demanded, true, "an open popup on another monitor raises demand for the leader")

      // --- FoamyIpc ---------------------------------------------------------------------
      var registry = IpcResolver.registry(shell)
      eq(registry !== null, v45, "IpcRegistry fast path present only on 4.5")
      if (registry) {
        var reply = registry.call("foamy.kit-demo", "status", [])
        check(reply.ran === true, "omarchy-shell socket path answers the plugin target")
        if (reply.ran) eq(JSON.parse(reply.output).leader, true, "the leader's handler answers")
        eq(registry.call("foamy.kit-demo", "destroy", []).ran, false, "undeclared functions are refused")
      }
      stepThree.start()
    }
  }

  Timer {
    id: stepThree
    interval: 500
    onTriggered: {
      // --- demo Panel: lazy body, settings save -------------------------------------------
      var panel = members[2]
      var popup = panel.popup
      check(popup !== null, "demo panel has a FoamyPopup")
      check(popup && popup.bodyItem !== null, "body built on open")
      check(popup && popup.cardItem !== null && popup.cardItem.radius === 12, "foamy radius on the demo popup")
      var lazy = members[1].popup
      check(lazy && lazy.bodyItem === null, "closed panels never build their body")
      mockBar.saved = []
      panel.save("refreshSeconds", 300)
      eq(mockBar.saved.length, 1, "panel save goes inline")
      if (mockBar.saved.length)
        eq(JSON.stringify(mockBar.saved[0].settings), JSON.stringify({ showCount: true, refreshSeconds: 300, layout: "list", extra: "kept" }), "panel save keeps every other key")
      panel.close()
      // Unplug the leader's monitor: leadership moves on.
      panels.model = 2
      stepFour.start()
    }
  }

  Timer {
    id: stepFour
    interval: 300
    onTriggered: {
      eq(FoamyShared.memberCount("poller"), 2, "members leave with their instance")
      eq(leaders(), 1, "a new leader takes over")
      var registry = IpcResolver.registry(shell)
      if (registry) eq(registry.call("foamy.kit-demo", "status", []).ran, true, "IPC follows the new leader")
      console.log("FOAMY READY")
      finish.start()
    }
  }

  // The python runner calls `qs ipc` while we wait here.
  Timer {
    id: finish
    interval: Number(Quickshell.env("FOAMY_HOLD_MS") || 200)
    onTriggered: {
      console.log("FOAMY RESULT " + host + "/" + lang + " checks=" + checks + " failures=" + failures)
      console.log("FOAMY DONE")
      Qt.quit()
    }
  }
}
