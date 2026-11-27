import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "harness"
import "plugin" as Demo
import "plugin/kit"
import "plugin/kit/FoamyIpcResolver.js" as IpcResolver
import "plugin/kit/FoamyText.js" as FoamyText

// Runtime checks for FoamyI18n, FoamyMotion, FoamyPalette (with a live theme
// switch), FoamyStyle, FoamyCursor, FoamyIcon mirroring,
// FoamyShared/FoamyMember and FoamyIpc, and the demo Panel (3 instances, as
// on 3 monitors): unplugging the leader's monitor hands leadership and the
// IPC target to the next live instance, and an unplugged open popup takes
// its demand with it. FOAMY_LANG picks the language-dependent expectations.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property string lang: Quickshell.env("FOAMY_LANG") || "en"
  property int checks: 0
  property int failures: 0

  function check(ok, label) {
    checks++
    if (!ok) {
      failures++
      console.log("FOAMY FAIL " + host + "/" + lang + " " + label)
    }
  }
  function eq(actual, expected, label) {
    check(actual === expected, label + ": got " + JSON.stringify(actual) + ", expected " + JSON.stringify(expected))
  }

  FloatingWindow {
    id: window
    implicitWidth: 1920
    implicitHeight: 1080
    color: "black"
    ScreenSim {
      id: sim
    }
    Row {
      id: barRow
      y: 4
      x: 1200
      spacing: 40
      // One bar instance per monitor; removing an entry unplugs that monitor
      // and destroys only its instance.
      Repeater {
        id: panels
        model: ListModel {
          id: monitors
          ListElement {
            monitor: "DP-1"
          }
          ListElement {
            monitor: "DP-2"
          }
          ListElement {
            monitor: "DP-3"
          }
        }
        Demo.Panel {
          bar: mockBar
          moduleName: "foamy.kit-demo"
          settings: ({
              id: "foamy.kit-demo",
              showCount: true,
              refreshSeconds: 60,
              layout: "list",
              extra: "kept"
            })
        }
      }
    }
  }

  MockBar {
    id: mockBar
    moduleName: "foamy.kit-demo"
  }

  FoamyIcon {
    id: chevron
    name: "chevron-left"
  }
  FoamyIcon {
    id: transport
    name: "skip-back"
  }

  FoamyWait {
    id: wait
  }
  // Writes the run's own theme file for the live theme switch.
  FileView {
    id: themeFile
    path: (Commons.Color.currentThemePath || "") + "/colors.toml"
  }

  FoamyCursor {
    id: cursor
    count: 3
  }

  Component.onCompleted: Qt.callLater(stepOne)

  function stepOne() {
    // --- FoamyI18n (preview/i18n_runtime.py covers t(), the one form, the
    // fallback and the direction per language) ---------------------------------
    if (lang === "en") {
      eq(FoamyI18n.tn("%1 devices", 3), "3 devices", "tn other (English)")
      eq(FoamyI18n.number(13.14, 1), "13.1", "number English")
      var nowMs = 1800000000000
      eq(FoamyI18n.updatedAgo(0, nowMs), "", "updatedAgo without a time")
      eq(FoamyI18n.updatedAgo(nowMs - 30000, nowMs), "Updated just now", "updatedAgo just now")
      eq(FoamyI18n.updatedAgo(nowMs - 60000, nowMs), "Updated 1 minute ago", "updatedAgo one minute")
      eq(FoamyI18n.updatedAgo(nowMs - 59 * 60000, nowMs), "Updated 59 minutes ago", "updatedAgo minutes")
      eq(FoamyI18n.updatedAgo(nowMs - 1283 * 60000, nowMs), "Updated 21 hours ago", "updatedAgo hours")
      eq(FoamyI18n.updatedAgo(nowMs - 49 * 3600000, nowMs), "Updated 2 days ago", "updatedAgo days")
    }
    if (lang === "da") {
      eq(FoamyI18n.tn("%1 devices", 3), "3 enheder", "tn other (Danish)")
      eq(FoamyI18n.t("Battery %1%", 13.5), "Batteri 13,5%", "numeric hole uses the Danish decimal")
      eq(FoamyI18n.t("Battery %1%", 8080), "Batteri 8080%", "numbers are ungrouped")
      eq(FoamyI18n.number(13.14, 1), "13,1", "number Danish")
      eq(FoamyI18n.formatLocale, "da-DK", "format locale from the registry")
    }
    if (lang === "ar") {
      eq(FoamyI18n.tn("%1 devices", 2), "جهازان", "tn dual (Arabic)")
      eq(FoamyI18n.tn("%1 devices", 5), FoamyI18n.number(5) + " أجهزة", "tn few (Arabic) fills %1 through number()")
    }
    // Directional icons mirror under a right-to-left language only; media
    // transport never does.
    eq(chevron.mirror, lang === "ar", "directional icons mirror only in RTL")
    eq(transport.mirror, false, "media transport never mirrors")

    // --- FoamyText (the node tests' cases, in Qt's JavaScript engine) ---------------
    eq(FoamyText.cap("ab\ud83d\ude00cd", 1, 3), "ab\u2026", "cap never splits a surrogate pair")
    eq(FoamyText.cap("a\u2028b\r\nc", 2, 5), "a\nb\u2026", "cap counts every Qt line break")
    eq(FoamyText.tooltip("x".repeat(500)).length, 100, "tooltip caps a long line at the host's 100 characters")

    // --- FoamyMotion ------------------------------------------------------------
    eq(FoamyMotion.duration(180), 180, "duration passes through with motion on")
    eq(FoamyMotion.reduceMotion, false, "motion on by default")
    check(FoamyMotion.loopAllowed(true), "loops allowed with motion on")
    Style.reduceMotion = true
    eq(FoamyMotion.reduceMotion, true, "reduceMotion follows Style.reduceMotion")
    eq(FoamyMotion.duration(180), 0, "durations collapse under reduced motion")
    eq(FoamyMotion.fadeIn, 0, "named tokens collapse under reduced motion")
    check(!FoamyMotion.loopAllowed(true), "loops stop under reduced motion")
    Style.reduceMotion = false
    eq(FoamyMotion.fadeIn, 180, "tokens recover")

    // --- FoamyStyle / FoamyPalette -------------------------------------------------
    Style.cornerRadius = 0
    eq(FoamyStyle.radius, 0, "square corners stay square")
    check(!FoamyStyle.rounded && FoamyStyle.pillRadius(20) === 0, "no pill on a square theme")
    Style.cornerRadius = 6
    eq(FoamyStyle.radius, 12, "radius is 2x Hyprland rounding")
    // Sizes follow the theme's [spacing] scale.
    var body = FoamyStyle.font.body, width = FoamyStyle.popupWidth, wideWidth = FoamyStyle.popupWidthWide
    Style.spacingScale = 1.5
    check(FoamyStyle.font.body > body && FoamyStyle.font.body === Style.space(12), "body size follows the spacing scale: " + FoamyStyle.font.body)
    check(FoamyStyle.popupWidth > width && FoamyStyle.popupWidth === Style.space(420), "standard width follows the spacing scale: " + FoamyStyle.popupWidth)
    check(FoamyStyle.popupWidthWide > wideWidth && FoamyStyle.popupWidthWide === Style.space(560), "wide width follows the spacing scale: " + FoamyStyle.popupWidthWide)
    Style.spacingScale = 1.0
    eq(JSON.stringify([FoamyStyle.font.body, FoamyStyle.popupWidth, FoamyStyle.popupWidthWide]), JSON.stringify([body, width, wideWidth]), "sizes return with the scale")
    check(Qt.colorEqual(FoamyPalette.warning, "#f9e2af"), "warning from theme yellow: " + FoamyPalette.warning)
    check(Qt.colorEqual(FoamyPalette.success, "#a6e3a1"), "success from theme green")
    check(Qt.colorEqual(FoamyPalette.error, "#f38ba8"), "error from theme red")
    check(Qt.colorEqual(FoamyPalette.info, "#94e2d5"), "info from theme cyan")
    eq(FoamyPalette.lightTheme, false, "dark theme mode")
    eq(FoamyPalette.pick(["nope"], "fallback"), "fallback", "status colour fallback")
    eq(FoamyPalette.parse('mode = "light"\n[x]\nred = "#ff0000" # c').red, "#ff0000", "colors.toml parse")

    // --- FoamyCursor ------------------------------------------------------------------
    eq(cursor.index, -1, "cursor starts hidden")
    cursor.hover(7)
    eq(cursor.index, -1, "hover outside the list is ignored")
    cursor.move(1)
    eq(cursor.index, 0, "first move lands on the first stop")
    cursor.move(1)
    cursor.move(1)
    cursor.move(1)
    eq(cursor.index, 2, "cursor clamps at the end")
    cursor.wrap = true
    cursor.move(1)
    eq(cursor.index, 0, "a wrapping cursor goes from the last stop to the first")
    cursor.wrap = false
    cursor.hover(1)
    eq(cursor.index, 1, "hover moves the same cursor")
    cursor.reset()
    cursor.move(-1)
    eq(cursor.index, 2, "Up on open lands on the last stop")
    cursor.count = 1
    eq(cursor.index, 0, "cursor clamps when the list shrinks")

    wait.waitFor(function () {
      return panels.count === 3 && FoamyShared.memberCount("poller") === 3
    }, 5000, then("three bar instances join", stepTwo))
  }

  // Each step waits for what it needs (a 5 s bound), never a fixed delay.
  function then(label, next) {
    return function (ok) {
      check(ok, label)
      next()
    }
  }

  readonly property var members: {
    var out = []
    for (var i = 0; i < panels.count; i++)
      if (panels.itemAt(i))
        out.push(panels.itemAt(i))
    return out
  }

  function memberOf(panel) {
    for (var i = 0; i < panel.data.length; i++)
      if (panel.data[i] && panel.data[i].scope === "poller" && "isLeader" in panel.data[i])
        return panel.data[i]
    return null
  }

  function leaders() {
    var count = 0
    for (var i = 0; i < members.length; i++)
      if (memberOf(members[i]).isLeader)
        count++
    return count
  }

  function statusReply() {
    var registry = IpcResolver.registry(shell)
    var reply = registry ? registry.call("foamy.kit-demo", "status", []) : null
    return reply && reply.ran ? JSON.parse(reply.output) : null
  }

  // The demo's FoamyIpc handlers in the registry (the host Panel registers
  // its own, disabled ShellIpc for the same target; only FoamyIpc has status).
  function demoHandlers() {
    var registry = IpcResolver.registry(shell)
    return registry ? registry.handlers.filter(function (h) {
      return h && h.target === "foamy.kit-demo" && typeof h.status === "function"
    }).length : -1
  }

  // The instances that stay after the unplugs.
  property var survivor: null
  property var demander: null

  function stepTwo() {
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
    check(registry !== null, "IpcRegistry fast path present")
    if (registry) {
      var reply = registry.call("foamy.kit-demo", "status", [])
      check(reply.ran === true, "omarchy-shell socket path answers the plugin target")
      if (reply.ran)
        eq(JSON.parse(reply.output).leader, true, "the leader's handler answers")
      eq(demoHandlers(), 3, "every instance registers its handler")
    }
    // The open popup builds its body; closed ones never do.
    wait.waitFor(function () {
      return members[2].popup.bodyItem !== null
    }, 5000, then("the open popup builds its body", stepThree))
  }

  function stepThree() {
    check(members[1].popup.bodyItem === null, "closed panels never build their body")
    // Unplug the leader's monitor: the next live instance takes over.
    survivor = members[1]
    demander = members[2]
    monitors.remove(0)
    wait.waitFor(function () {
      return FoamyShared.memberCount("poller") === 2
    }, 5000, then("the unplugged instance leaves", stepFour))
  }

  function stepFour() {
    check(memberOf(survivor).isLeader, "the next live instance takes over")
    eq(leaders(), 1, "one leader after the handover")
    check(memberOf(survivor).demanded, "an open popup keeps demand across the handover")
    var status = statusReply()
    check(status !== null && status.leader === true, "IPC follows the new leader: " + JSON.stringify(status))
    // A destroyed handler left in the registry has no target any more.
    var registry = IpcResolver.registry(shell)
    check(demoHandlers() === 2 && registry && registry.handlers.every(function (h) {
      return h && typeof h.target === "string"
    }), "the destroyed instance's FoamyIpc unregistered")
    // Unplug the open popup's monitor: its demand goes with it.
    check(demander.opened, "the popup on the next monitor is still open")
    monitors.remove(1)
    wait.waitFor(function () {
      return FoamyShared.memberCount("poller") === 1
    }, 5000, then("the open popup's instance leaves", stepFive))
  }

  function stepFive() {
    check(!memberOf(survivor).demanded, "demand leaves with its instance")
    check(memberOf(survivor).isLeader, "the last instance leads")
    // The settings IPC on a closed popup lands on Settings (FoamySettingsState).
    check(!survivor.opened, "popup closed before openSettings()")
    survivor.openSettings()
    check(survivor.opened && survivor.editingSettings, "openSettings() on a closed popup shows Settings")
    survivor.close()
    check(!survivor.editingSettings, "closing the popup leaves Settings")

    // --- a live theme switch reaches FoamyPalette ---------------------------------
    // Only ever the run's own copy (the harness puts the theme under its temp
    // XDG_STATE_HOME); never write anything else.
    var stateHome = Quickshell.env("XDG_STATE_HOME")
    var own = stateHome !== "" && themeFile.path.indexOf(stateHome + "/") === 0
    check(own, "the theme file is the run's own: " + themeFile.path)
    if (!own) {
      ready()
      return
    }
    themeFile.setText('mode = "light"\naccent = "#1e66f5"\nbackground = "#eff1f5"\nforeground = "#4c4f69"\nred = "#d20f39"\nyellow = "#df8e1d"\ngreen = "#40a02b"\ncyan = "#179299"\n')
    wait.waitFor(function () {
      return FoamyPalette.lightTheme && Qt.colorEqual(FoamyPalette.warning, "#df8e1d")
    }, 5000, then("the palette follows a changed theme file", function () {
      check(Qt.colorEqual(FoamyPalette.error, "#d20f39"), "error from the new theme's red")
      // The popup surface of Catppuccin Latte: muted hints reach WCAG AA
      // (tint .55 gave 2.53:1) and stay lighter than the text.
      Commons.Color.background = "#eff1f5"
      Commons.Color.foreground = "#4c4f69"
      // Status text reads at 4.5:1 there: the yellow (2.3:1) darkens, the
      // red (4.8:1) keeps the theme's colour.
      var warningRatio = wcagContrast(FoamyPalette.onSurface(FoamyPalette.warning), FoamyPalette.background)
      check(warningRatio >= 4.5 && !Qt.colorEqual(FoamyPalette.onSurface(FoamyPalette.warning), FoamyPalette.warning), "a faint status colour darkens to 4.5:1 on the popup surface: " + warningRatio.toFixed(3))
      check(Qt.colorEqual(FoamyPalette.onSurface(FoamyPalette.error), FoamyPalette.error) && Qt.colorEqual(FoamyPalette.onSurface("#d20f39"), FoamyPalette.error), "a status colour that reads keeps its hue, also given as text")
      var mutedRatio = wcagContrast(FoamyPalette.mutedText, "#eff1f5")
      check(mutedRatio >= 4.5, "muted text has 4.5:1 on a light surface: " + mutedRatio.toFixed(2))
      var secondaryRatio = wcagContrast(FoamyPalette.secondaryText, "#eff1f5")
      check(secondaryRatio >= 5.5 && mutedRatio < secondaryRatio && secondaryRatio < wcagContrast("#4c4f69", "#eff1f5"), "secondary text has 5.5:1 on a light surface, between muted and the text: " + secondaryRatio.toFixed(2))
      // A theme whose text itself is weak (2.8:1): the tones stop at their
      // ceilings and stay three, muted below .85 of the way to the text.
      Commons.Color.foreground = "#8c8fa1"
      var way = function (c) {
        return (Qt.color(c).g - Qt.color("#eff1f5").g) / (Qt.color("#8c8fa1").g - Qt.color("#eff1f5").g)
      }
      var weakMuted = way(FoamyPalette.mutedText), weakSecondary = way(FoamyPalette.secondaryText)
      check(weakMuted > 0.3 && weakMuted < 0.85 && weakMuted < weakSecondary && weakSecondary < 0.99, "weak text keeps three tones, muted under .85: " + weakMuted.toFixed(2) + ", " + weakSecondary.toFixed(2))
      Commons.Color.foreground = "#4c4f69"
      surfaceSweep("light")
      darkThemeStep()
    }))
  }

  // A dark theme with a dim red (Nord's: 3.05:1 on its background): status
  // text lightens until it reads at 4.5:1, as the light path darkens.
  function darkThemeStep() {
    themeFile.setText('mode = "dark"\naccent = "#88c0d0"\nbackground = "#2e3440"\nforeground = "#d8dee9"\nred = "#bf616a"\nyellow = "#ebcb8b"\ngreen = "#a3be8c"\ncyan = "#8fbcbb"\n')
    wait.waitFor(function () {
      return !FoamyPalette.lightTheme && Qt.colorEqual(FoamyPalette.error, "#bf616a")
    }, 5000, then("the palette follows a changed dark theme file", function () {
      Commons.Color.background = "#2e3440"
      Commons.Color.foreground = "#d8dee9"
      var shown = FoamyPalette.onSurface(FoamyPalette.error)
      var ratio = wcagContrast(shown, "#2e3440")
      check(ratio >= 4.5 && !Qt.colorEqual(shown, "#bf616a"), "a dim red lightens to 4.5:1 on a dark surface: #bf616a " + wcagContrast("#bf616a", "#2e3440").toFixed(2) + " -> " + shown + " " + ratio.toFixed(2))
      surfaceSweep("dark")
      ready()
    }))
  }

  // onSurface(c, surface) on any opaque surface, in the current theme:
  // greys from black to white (a light surface in a dark theme and the
  // reverse), the popup's own tints (a hero band's glow under the pointer,
  // as foamy-audio draws it; the destructive press tint; a selected row;
  // a menu) and, as colours, the theme's status colours, black and white.
  // Every result reads at 4.5:1; a colour that reads is returned as it is;
  // one that doesn't moves only about as far as it must (under 5.25:1) and
  // keeps its hue while it still has one. Before 0.16.1 it stepped by the
  // theme's light or dark, at most 1.7 times: 1.00:1 for the status colours
  // on white in a dark theme, a dim red at 3.54:1 on the band's glow.
  function surfaceSweep(theme) {
    const P = FoamyPalette
    const shown = c => Qt.color(Qt.tint(P.background, c).toString())
    const surfaces = [Qt.color(Qt.tint(Qt.tint(P.bandFill, P.bandGlow), P.hoverFill).toString()), shown(Qt.alpha(P.urgent, 0.26)), shown(P.selectedFill), shown(P.menuFill)]
    for (let v = 0; v <= 255; v += 17)
      surfaces.push(Qt.rgba(v / 255, v / 255, v / 255, 1))
    const colours = [P.error, P.warning, P.success, P.info, P.urgent, Qt.color("#000000"), Qt.color("#ffffff")]
    const hue = c => Qt.color(c).hsvHue
    const short = [], moved = [], kept = [], lost = []
    let most = 0
    for (const s of surfaces)
      for (const c of colours) {
        const out = P.onSurface(c, s)
        const ratio = wcagContrast(out, s)
        const what = c + " on " + s + " -> " + out + " " + ratio.toFixed(2)
        if (ratio < 4.5)
          short.push(what)
        if (wcagContrast(c, s) >= 4.5) {
          if (!Qt.colorEqual(out, c))
            kept.push(what)
          continue
        }
        most = Math.max(most, ratio)
        if (ratio >= 5.25)
          moved.push(what)
        // A hue is still there when the result has colour and light
        // enough for 8 bits a channel to hold it.
        const o = Qt.color(out), base = Qt.color(c)
        if (base.hsvSaturation >= 0.1 && o.hsvSaturation >= 0.1 && o.hsvValue >= 0.25) {
          const turn = Math.abs(hue(o) - hue(base))
          if (Math.min(turn, 1 - turn) > 0.02)
            lost.push(what)
        }
      }
    check(short.length === 0, theme + ": onSurface reads at 4.5:1 on every surface (" + short.length + " short: " + short.slice(0, 4).join(", ") + ")")
    check(kept.length === 0, theme + ": onSurface returns a colour that reads unchanged, on every surface (" + kept.slice(0, 4).join(", ") + ")")
    check(moved.length === 0, theme + ": onSurface moves a colour only as far as it must, the most " + most.toFixed(2) + " (" + moved.slice(0, 4).join(", ") + ")")
    check(lost.length === 0, theme + ": onSurface keeps the hue (" + lost.slice(0, 4).join(", ") + ")")
  }

  // WCAG 2 contrast ratio, written out here so the palette's own
  // contrastRatio() is not what checks it.
  function wcagContrast(a, b) {
    function relative(c) {
      var rgb = [Qt.color(c).r, Qt.color(c).g, Qt.color(c).b].map(function (v) {
        return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)
      })
      return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    }
    var la = relative(a), lb = relative(b)
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
  }

  // test_runtime.py calls `qs ipc call foamy.kit-demo status` after READY,
  // then `qs ipc call foamy.test-runtime finish`. FOAMY_HOLD_MS bounds the hold.
  function ready() {
    console.log("FOAMY READY")
    hold.start()
  }
  property bool finished: false
  // `by` names the path that ended the run; test_runtime.py requires the
  // finish call.
  function finishNow(by) {
    if (finished)
      return
    finished = true
    console.log("FOAMY END by " + by)
    console.log("FOAMY RESULT " + host + "/" + lang + " checks=" + checks + " failures=" + failures)
    console.log("FOAMY DONE")
    Qt.quit()
  }
  IpcHandler {
    target: "foamy.test-runtime"
    function finish(): void {
      shell.finishNow("the finish call")
    }
  }
  Timer {
    id: hold
    interval: Number(Quickshell.env("FOAMY_HOLD_MS") || 200)
    onTriggered: shell.finishNow("the hold bound")
  }
}
