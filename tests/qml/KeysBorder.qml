import QtQuick
import QtTest
import Quickshell
import qs.Commons as Commons
import "harness"
import "plugin/kit"

// The keys' cursor border on every kit control that takes the cursor, in a
// real FoamyPopup: FoamyAction and FoamyButton (each kind) active, inert
// and disabled, FoamyToggle, FoamyDropdown, FoamyNumberField,
// FoamyTextSettingField, SafeTextField, SafeTextArea, and the buttons that
// FoamyHeroBand, FoamyHeader, FoamyPanelFooter and FoamyInfoNote own (they
// get `cursorByKeys` from the component). The card is drawn in four modes:
// rest (no cursor, no flag), elsewhere (the flag, the cursor on no
// control), pointer (the cursor, no flag) and keys (both), each saved to
// FOAMY_OUT/<mode>.png. FOAMY KEYS <json> says where each control's
// outline is on the card, per mode, which colour its keys' border is to be
// drawn in ("accent", or "ink" on an accent fill: the text or the
// background colour) and at what strength
// (the control's own fading); test_keys_border.py reads the pixels.
//
// Then the pointer, per control that reports it (each report clears the
// keys' look, as a panel's cursor.hover(i) does): with the pointer resting
// inside, the keys come to the control; the pointer reported again at the
// same place and the body moving 2 px under the still pointer (Qt re-sends
// hover, seen by a probe) report nothing, a real 3 px move inside
// reports the pointer and clears the keys' look, and with the pointer's
// look a move reports nothing.
ShellRoot {
  id: shell
  readonly property string host: Quickshell.env("FOAMY_HOST")
  readonly property string tag: host + "@" + Quickshell.env("FOAMY_SCALE")
  property int checks: 0
  property int failures: 0
  function check(ok, label) {
    checks++
    if (!ok) {
      failures++
      console.log("FOAMY FAIL " + tag + " " + label)
    }
  }

  readonly property var modes: ["rest", "elsewhere", "pointer", "keys"]
  property string mode: "rest"
  readonly property bool cursorOn: mode === "pointer" || mode === "keys"
  // A pointer report takes the cursor from the keys (FoamyCursor.hover()).
  property bool pointerTook: false
  readonly property bool byKeys: (mode === "elsewhere" || mode === "keys") && !pointerTook
  property var reports: []
  function pointer(name) {
    reports = reports.concat([name])
    pointerTook = true
  }
  // The body's shift under a still pointer, and the hover Qt re-sends then.
  property real shift: 0
  property int probeMoves: 0
  property int frames: 0
  FrameAnimation {
    running: true
    onTriggered: shell.frames++
  }

  FloatingWindow {
    id: window
    implicitWidth: 1920
    implicitHeight: 1080
    color: "black"
    ScreenSim {
      id: sim
    }
  }
  MockBar {
    id: bar
  }
  FoamyWait {
    id: wait
  }

  readonly property var kinds: ["primary", "secondary", "destructive"]
  readonly property var states: ["active", "inert", "disabled"]
  readonly property var labels: ({
      primary: "Save",
      secondary: "Verify",
      destructive: "Remove"
    })

  FoamyPopup {
    id: popup
    anchorItem: sim.anchor
    bar: bar
    open: true
    body: Component {
      Column {
        id: bodyColumn
        property alias band: band
        property alias header: header
        property alias actions: actions
        property alias buttons: buttons
        property alias toggle: toggle
        property alias dropdown: dropdown
        property alias number: number
        property alias textSetting: textSetting
        property alias textField: textField
        property alias textArea: textArea
        property alias note: note
        property alias footer: footer
        property alias surface: surface
        property alias tabs: tabs
        spacing: FoamyStyle.gap
        transform: Translate {
          x: shell.shift
        }
        // A probe: Qt's hover under the still pointer as the body moves.
        HoverHandler {
          onPointChanged: if (hovered)
            shell.probeMoves++
        }

        FoamyHeroBand {
          id: band
          width: parent.width
          iconName: "keyboard"
          title: "Keys"
          meta: "The band's buttons"
          menuItems: [
            FoamyMenuItem {
              text: "One"
            }
          ]
          settingsHasCursor: shell.cursorOn
          menuHasCursor: shell.cursorOn
          cursorByKeys: shell.byKeys
          onSettingsHovered: function (hovered) {
            if (hovered)
              shell.pointer("band-settings")
          }
          onMenuHovered: function (hovered) {
            if (hovered)
              shell.pointer("band-menu")
          }
        }
        FoamyHeader {
          id: header
          width: parent.width
          iconName: "keyboard"
          title: "Header"
          menuItems: [
            FoamyMenuItem {
              text: "One"
            }
          ]
          settingsHasCursor: shell.cursorOn
          menuHasCursor: shell.cursorOn
          cursorByKeys: shell.byKeys
          onSettingsHovered: function (hovered) {
            if (hovered)
              shell.pointer("header-settings")
          }
          onMenuHovered: function (hovered) {
            if (hovered)
              shell.pointer("header-menu")
          }
        }
        FoamyTabs {
          id: tabs
          width: parent.width
          value: "one"
          model: [
            {
              value: "one",
              text: "One"
            },
            {
              value: "two",
              text: "Two"
            }
          ]
          hasCursor: shell.cursorOn
          cursorByKeys: shell.byKeys
          onHovered: shell.pointer("tabs")
        }
        Column {
          x: FoamyStyle.padding
          width: parent.width - FoamyStyle.padding * 2
          spacing: FoamyStyle.gap

          Row {
            id: actions
            spacing: FoamyStyle.gap
            Repeater {
              model: shell.states
              FoamyAction {
                required property string modelData
                objectName: "action-" + modelData
                iconName: "refresh-cw"
                tooltipText: "Refresh"
                actionEnabled: modelData !== "inert"
                enabled: modelData !== "disabled"
                hasCursor: shell.cursorOn
                cursorByKeys: shell.byKeys
                onHoveredChanged: if (hovered)
                  shell.pointer(objectName)
              }
            }
          }
          Grid {
            id: buttons
            columns: shell.states.length
            spacing: FoamyStyle.gap
            Repeater {
              model: shell.kinds.length * shell.states.length
              FoamyButton {
                required property int index
                readonly property string stateName: shell.states[index % shell.states.length]
                kind: shell.kinds[Math.floor(index / shell.states.length)]
                objectName: kind + "-" + stateName
                text: shell.labels[kind]
                actionEnabled: stateName !== "inert"
                enabled: stateName !== "disabled"
                hasCursor: shell.cursorOn
                cursorByKeys: shell.byKeys
                onHoveredChanged: if (hovered)
                  shell.pointer("button-" + objectName)
              }
            }
          }
          FoamyCursorSurface {
            id: surface
            width: parent.width
            height: FoamyStyle.rowHeight
            hasCursor: shell.cursorOn
            byKeys: shell.byKeys
            onHovered: shell.pointer("surface")
          }
          FoamyToggle {
            id: toggle
            width: parent.width
            label: "Show in the bar"
            checked: true
            hasCursor: shell.cursorOn
            cursorByKeys: shell.byKeys
            onHovered: function (isHovered) {
              if (isHovered)
                shell.pointer("toggle")
            }
          }
          FoamyDropdown {
            id: dropdown
            width: parent.width
            compact: true
            label: "Mode"
            value: "auto"
            options: [
              {
                value: "auto",
                label: "Automatic"
              },
              {
                value: "manual",
                label: "Manual"
              }
            ]
            hasCursor: shell.cursorOn
            cursorByKeys: shell.byKeys
            onHovered: function (isHovered) {
              if (isHovered)
                shell.pointer("dropdown")
            }
          }
          FoamyNumberField {
            id: number
            width: parent.width
            compact: true
            label: "Margin"
            unit: "%"
            value: 12
            hasCursor: shell.cursorOn
            cursorByKeys: shell.byKeys
          }
          FoamyTextSettingField {
            id: textSetting
            width: parent.width
            label: "Display name"
            placeholderText: "Your name"
            hasCursor: shell.cursorOn
            cursorByKeys: shell.byKeys
          }
          SafeTextField {
            id: textField
            width: parent.width
            placeholderText: "Search"
            hasCursor: shell.cursorOn
            cursorByKeys: shell.byKeys
          }
          SafeTextArea {
            id: textArea
            width: parent.width
            placeholderText: "Notes"
            hasCursor: shell.cursorOn
            cursorByKeys: shell.byKeys
          }
          FoamyInfoNote {
            id: note
            width: parent.width
            focusable: false
            title: "About keys"
            text: "The keys' cursor has an accent border."
            buttonHasCursor: shell.cursorOn
            cursorByKeys: shell.byKeys
            onButtonHovered: function (hovered) {
              if (hovered)
                shell.pointer("note-button")
            }
          }
          FoamyPanelFooter {
            id: footer
            width: parent.width
            source: "Kit"
            status: "Updated now"
            refreshHasCursor: shell.cursorOn
            cursorByKeys: shell.byKeys
            onRefreshHovered: function (hovered) {
              if (hovered)
                shell.pointer("footer-refresh")
            }
          }
        }
      }
    }
  }

  function find(item, name) {
    if (!item)
      return null
    if (item.objectName === name)
      return item
    for (var i = 0; i < item.children.length; i++) {
      var hit = find(item.children[i], name)
      if (hit)
        return hit
    }
    return null
  }
  function rect(item) {
    var p = item.mapToItem(popup.cardItem, 0, 0)
    return [p.x, p.y, item.width, item.height]
  }

  // name: [outline item (draws the border), the item whose fill animates,
  // the keys' border colour, its strength, inert or disabled].
  function cases() {
    var body = popup.bodyItem
    var out = {}
    var strength = {
      active: 1,
      inert: 0.7,
      disabled: FoamyStyle.disabledOpacity
    }
    for (var s = 0; s < states.length; s++) {
      var a = find(body.actions, "action-" + states[s])
      // FoamyAction fades as a whole while inert or disabled.
      out["action-" + states[s]] = [a, a, "accent", strength[states[s]], states[s] !== "active"]
      for (var k = 0; k < kinds.length; k++) {
        var b = find(body.buttons, kinds[k] + "-" + states[s])
        // A button draws its border at full strength in every state.
        out["button-" + kinds[k] + "-" + states[s]] = [b, b, kinds[k] === "primary" ? "ink" : "accent", 1, states[s] !== "active"]
      }
    }
    var fill = find(body.toggle, "foamyToggleFill")
    out["toggle"] = [fill, fill, "accent", 1, false]
    out["dropdown"] = [body.dropdown.triggerItem, body.dropdown.triggerItem, "accent", 1, false]
    out["number-field"] = [body.number.field, body.number.field.background, "accent", 1, false]
    out["text-setting-field"] = [body.textSetting.field, body.textSetting.field.background, "accent", 1, false]
    out["text-field"] = [body.textField, body.textField.background, "accent", 1, false]
    out["text-area"] = [body.textArea, body.textArea.background, "accent", 1, false]
    out["band-settings"] = [body.band.settingsButton, body.band.settingsButton, "accent", 1, false]
    out["band-menu"] = [body.band.menuButton, body.band.menuButton, "accent", 1, false]
    out["header-settings"] = [body.header.settingsButton, body.header.settingsButton, "accent", 1, false]
    out["header-menu"] = [body.header.menuButton, body.header.menuButton, "accent", 1, false]
    out["note-button"] = [body.note.infoButton, body.note.infoButton, "accent", 1, false]
    out["footer-refresh"] = [body.footer.refreshButton, body.footer.refreshButton, "accent", 1, false]
    return out
  }

  // The fills animate (FoamyMotion.hover): a mode is drawn once they stop
  // changing for three polls in a row.
  function fills() {
    var all = cases()
    var out = []
    for (var name in all)
      out.push(String(all[name][1].color))
    return out.join()
  }

  property var info: ({})
  function show(i) {
    if (i >= modes.length) {
      console.log("FOAMY KEYS " + JSON.stringify(info))
      mode = "keys"
      pointerTook = true
      moves(moveCases(), 0)
      return
    }
    mode = modes[i]
    var last = "", same = 0
    wait.waitFor(function () {
      var now = fills()
      same = now === last ? same + 1 : 0
      last = now
      return same >= 2
    }, 5000, function (settled) {
      check(settled, mode + ": the fills settle")
      var all = cases()
      for (var name in all) {
        var c = all[name]
        if (!info.cases[name])
          info.cases[name] = {
            ring: c[2],
            strength: c[3],
            quiet: c[4],
            radius: FoamyStyle.radius,
            rects: {}
          }
        info.cases[name].rects[mode] = rect(c[0])
      }
      popup.cardItem.grabToImage(function (result) {
        check(result.saveToFile(Quickshell.env("FOAMY_OUT") + "/" + mode + ".png"), mode + ": saved")
        shell.show(i + 1)
      })
    }, tag + " " + modes[i] + " drawn")
  }

  // name: the item the pointer moves in. A disabled control takes no
  // pointer at all, so it reports nothing either way.
  function moveCases() {
    var body = popup.bodyItem
    var out = []
    for (var s = 0; s < 2; s++) {
      out.push(["action-" + states[s], find(body.actions, "action-" + states[s])])
      for (var k = 0; k < kinds.length; k++)
        out.push(["button-" + kinds[k] + "-" + states[s], find(body.buttons, kinds[k] + "-" + states[s])])
    }
    out.push(["surface", body.surface], ["tabs", find(body.tabs, "foamyTab1")], ["toggle", body.toggle], ["dropdown", body.dropdown.triggerItem], ["band-settings", body.band.settingsButton], ["band-menu", body.band.menuButton], ["header-settings", body.header.settingsButton], ["header-menu", body.header.menuButton], ["note-button", body.note.infoButton], ["footer-refresh", body.footer.refreshButton])
    return out
  }
  // Waits `count` frames, then calls then().
  function frameWait(count, then) {
    var until = frames + count
    wait.waitFor(function () {
      return frames >= until
    }, 5000, then, "frames drawn")
  }
  function moves(list, i) {
    if (i >= list.length) {
      finish()
      return
    }
    var name = list[i][0], item = list[i][1]
    var next = function () {
      shell.shift = 0
      // Off every control, to enter the next one afresh.
      ev.mouseMove(popup.cardItem, 1, popup.cardItem.height - 1, -1, Qt.NoButton, Qt.NoModifier)
      frameWait(2, function () {
        shell.moves(list, i + 1)
      })
    }
    pointerTook = true
    reports = []
    ev.mouseMove(item, item.width / 2, item.height / 2, -1, Qt.NoButton, Qt.NoModifier)
    var at = item.mapToItem(null, item.width / 2, item.height / 2)
    wait.waitFor(function () {
      return reports.indexOf(name) >= 0
    }, 2000, function (entered) {
      check(entered, name + ": entering reports the pointer " + JSON.stringify(reports))
      // The keys come here, the pointer resting inside.
      pointerTook = false
      reports = []
      frameWait(2, function () {
        // The pointer reported again where it rests: no move.
        ev.mouseMove(item, item.width / 2, item.height / 2, -1, Qt.NoButton, Qt.NoModifier)
        frameWait(3, function () {
          check(reports.length === 0 && byKeys, name + ": the pointer at the same place keeps the keys' look " + JSON.stringify(reports))
          probeMoves = 0
          shift = 2
          wait.waitFor(function () {
            return probeMoves > 0
          }, 2000, function (resent) {
            check(resent, name + ": Qt re-sends hover as the body moves under the pointer")
            frameWait(3, function () {
              check(reports.length === 0 && byKeys, name + ": the body moving under a still pointer keeps the keys' look " + JSON.stringify(reports))
              var here = item.mapFromItem(null, at.x, at.y)
              ev.mouseMove(item, here.x + 3, here.y, -1, Qt.NoButton, Qt.NoModifier)
              wait.waitFor(function () {
                return !byKeys
              }, 2000, function (cleared) {
                check(cleared && reports.length === 1 && reports[0] === name, name + ": a move inside reports the pointer and clears the keys' look " + JSON.stringify(reports))
                // The pointer's look: a move reports nothing more.
                reports = []
                ev.mouseMove(item, here.x + 5, here.y, -1, Qt.NoButton, Qt.NoModifier)
                frameWait(3, function () {
                  check(reports.length === 0, name + ": with the pointer's look a move reports nothing " + JSON.stringify(reports))
                  next()
                })
              })
            })
          })
        })
      })
    }, tag + " " + name + " entered")
  }

  Component.onCompleted: wait.waitFor(function () {
    return popup.bodyItem && popup.cardItem.opacity === 1 && popup.bodyItem.band.menuButton.visible
  }, 5000, function (ok) {
    check(ok, "the popup shows with the band's ⋯ button")
    info = {
      card: [popup.cardItem.width, popup.cardItem.height],
      accent: String(Commons.Color.accent),
      text: String(FoamyPalette.text),
      background: String(FoamyPalette.background),
      cases: {}
    }
    var all = cases()
    for (var name in all)
      check(all[name][0] && all[name][0].visible, name + ": shown")
    show(0)
  })

  function finish() {
    console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
    console.log("FOAMY DONE")
    Qt.quit()
  }

  Item {
    parent: popup.bodyItem
    TestEvent {
      id: ev
    }
  }
}
