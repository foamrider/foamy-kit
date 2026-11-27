import QtQuick
import qs.Commons as Commons
import qs.Ui
import "FoamyText.js" as FoamyText

// A form button that reads as a button: a filled or bordered surface with a
// label and an optional icon. For actions in forms and settings ("Verify",
// "Apply", "Remove", "Add folder"); icon-only toolbar actions stay FoamyAction.
//
//   FoamyButton { text: FoamyI18n.t("Apply"); kind: "primary"; focusable: true; onClicked: root.apply() }
//   FoamyButton { text: FoamyI18n.t("Verify"); iconName: "check"; busy: root.verifying; onClicked: root.verify() }
//   FoamyButton { text: FoamyI18n.t("Remove"); iconName: "trash"; kind: "destructive"; onClicked: root.remove() }
//
// kind: "secondary" (default; field fill + border), "primary" (accent fill,
// one per form), "destructive" (urgent tint + border).
// Height FoamyStyle.controlHeight, foamy radius, label body size.
//
// Keyboard: like FoamyAction. In a PanelKeyCatcher panel set `hasCursor`
// from the panel's cursor and route `hovered` back; in a form (settings
// page) set `focusable: true` to join the Tab chain (focus ring in the
// accent). Enter/Space activate. `busy` spins the icon (or shows a spinner
// glyph when there is none) and keeps the button inert; actionEnabled: false
// keeps it visible but inert; enabled: false greys it out.
// Inert and disabled are drawn weaker, not faded: an opaque fill mixed
// toward the popup background and a label that still reads on it (inert
// 4.5:1, disabled 3:1). `foreground` is the label's colour in the current
// state, for a button that draws its own content.
// `tooltipText` only for a short hint; never for paragraphs (DESIGN.md).
Rectangle {
  id: root

  property string text: ""
  property string iconName: ""
  property string kind: "secondary"
  property string tooltipText: ""
  property bool busy: false
  property bool actionEnabled: true
  property bool hasCursor: false
  property bool focusable: false
  property Item keyTarget: null
  property string fontFamily: FoamyStyle.fontFamily
  readonly property bool hovered: mouse.containsMouse
  readonly property bool pressed: mouse.pressed
  readonly property bool active: enabled && actionEnabled && !busy
  readonly property bool primary: kind === "primary"
  readonly property bool destructive: kind === "destructive"
  readonly property bool hot: active && (hasCursor || mouse.containsMouse)

  signal clicked

  readonly property color foreground: _quiet ? _quiet.label : _ink

  // The kind's fill at rest and its label's ink. Destructive: readable on
  // its strongest (pressed) tint, so the label doesn't change on hover.
  readonly property color _restFill: primary ? Commons.Color.accent : destructive ? Qt.alpha(Commons.Color.urgent, 0.12) : FoamyPalette.fieldFill
  readonly property color _ink: primary ? FoamyPalette.accentInk : destructive ? FoamyPalette.onSurface(Commons.Color.urgent, Qt.tint(FoamyPalette.background, Qt.alpha(Commons.Color.urgent, 0.26))) : FoamyPalette.text
  // How strongly a state draws: active and busy 1, inert .7, disabled .45.
  readonly property real _strength: enabled ? (actionEnabled || busy ? 1 : 0.7) : FoamyStyle.disabledOpacity
  // Inert or disabled: { fill, label }, both opaque; null when active.
  readonly property var _quiet: _strength < 1 ? _quietLook() : null

  // Fading the whole item moved the fill toward the very colour a primary
  // label has (accentInk is often the background): 2.08:1 inert in the
  // light preview. Each state instead gets the kind's fill at its strength,
  // mixed toward the background, and a label measured on it, as drawn
  // (8 bits a channel). Where no ink reaches the state's ratio on that fill
  // (a primary in a light theme), the fill steps further toward the
  // background until one does; disabled starts no stronger than inert, so
  // it stays the weaker. The label is the faded ink (as before) where that
  // reads, else the faintest that does.
  function _quietLook() {
    const inert = 0.7
    const disabled = FoamyStyle.disabledOpacity
    const inks = [_ink, FoamyPalette.text, FoamyPalette.background]
    const fillAt = mix => Qt.color(Qt.tint(FoamyPalette.background, Qt.alpha(_restFill, _restFill.a * mix)).toString())
    // The strongest fill from `start` down on which an ink reaches `ratio`;
    // on the background itself, the ink that reads best.
    const pick = (start, ratio) => {
      for (let step = Math.round(start * 100); step > 0; step--) {
        const fill = fillAt(step / 100)
        const ink = inks.find(c => FoamyPalette.contrastRatio(c, fill) >= ratio)
        if (ink !== undefined)
          return {
            mix: step / 100,
            fill: fill,
            ink: ink
          }
      }
      const under = fillAt(0)
      const best = inks.reduce((a, b) => FoamyPalette.contrastRatio(b, under) > FoamyPalette.contrastRatio(a, under) ? b : a)
      return {
        mix: 0,
        fill: under,
        ink: best
      }
    }
    let look = pick(inert, 4.5)
    if (!enabled)
      look = pick(Math.min(disabled, look.mix * disabled / inert), 3)
    const ratio = enabled ? 4.5 : 3
    for (let step = Math.round(_strength * 100); step <= 100; step++) {
      const label = Qt.color(Qt.tint(look.fill, Qt.alpha(look.ink, step / 100)).toString())
      if (FoamyPalette.contrastRatio(label, look.fill) >= ratio)
        return {
          fill: look.fill,
          label: label
        }
    }
    return {
      fill: look.fill,
      label: look.ink
    }
  }

  implicitWidth: Math.max(FoamyStyle.controlHeight * 2, content.implicitWidth + FoamyStyle.gapLarge * 2 + border.width * 2)
  implicitHeight: FoamyStyle.controlHeight
  radius: FoamyStyle.radius
  color: {
    if (_quiet)
      return _quiet.fill
    if (primary) {
      var base = Commons.Color.accent
      return root.pressed && root.active ? Qt.darker(base, 1.12) : root.hot ? Qt.lighter(base, 1.1) : base
    }
    if (destructive)
      return Qt.alpha(Commons.Color.urgent, root.pressed && root.active ? 0.26 : root.hot ? 0.2 : 0.12)
    return root.pressed && root.active ? Qt.alpha(FoamyPalette.text, 0.14) : root.hot ? Qt.alpha(FoamyPalette.text, 0.1) : FoamyPalette.fieldFill
  }
  border.width: activeFocus && focusable ? 2 : FoamyStyle.borderWidth
  // Inert and disabled fade the border as the fill; the focus ring stays.
  border.color: {
    if (activeFocus && focusable)
      return primary ? FoamyPalette.text : Commons.Color.accent
    if (primary)
      return "transparent"
    const edge = destructive ? Qt.alpha(Commons.Color.urgent, root.hot ? 0.7 : 0.45) : Qt.alpha(FoamyPalette.text, root.hot ? 0.3 : 0.18)
    return _strength < 1 ? Qt.alpha(edge, edge.a * _strength) : edge
  }
  activeFocusOnTab: focusable && active

  Behavior on color {
    ColorAnimation {
      duration: FoamyMotion.hover
    }
  }

  Accessible.role: Accessible.Button
  Accessible.name: text || tooltipText
  Accessible.onPressAction: if (root.active)
    root.clicked()
  Keys.onReturnPressed: if (root.active)
    root.clicked()
  Keys.onEnterPressed: if (root.active)
    root.clicked()
  Keys.onSpacePressed: if (root.active)
    root.clicked()
  Keys.forwardTo: keyTarget ? [keyTarget] : []

  Row {
    id: content
    anchors.centerIn: parent
    spacing: FoamyStyle.gap
    FoamyIcon {
      id: icon
      visible: root.iconName !== "" || root.busy
      name: root.busy && root.iconName === "" ? "refresh-cw" : root.iconName
      width: FoamyStyle.iconSize
      height: width
      color: root.foreground
      anchors.verticalCenter: parent.verticalCenter
      RotationAnimation on rotation {
        running: root.busy && root.visible && !FoamyMotion.reduceMotion
        from: 0
        to: 360
        duration: FoamyMotion.spin
        loops: Animation.Infinite
        onStopped: icon.rotation = 0
      }
    }
    Text {
      visible: root.text !== ""
      text: root.text
      textFormat: Text.PlainText
      color: root.foreground
      font.family: root.fontFamily
      font.pixelSize: FoamyStyle.font.body
      font.weight: root.primary ? Font.DemiBold : Font.Medium
      anchors.verticalCenter: parent.verticalCenter
    }
  }

  MouseArea {
    id: mouse
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: root.active ? Qt.PointingHandCursor : Qt.ArrowCursor
    onClicked: if (root.active)
      root.clicked()
  }

  PanelToolTip {
    id: tip
    visible: mouse.containsMouse && root.tooltipText !== ""
    // The host's tooltip is as wide as its text and wraps only under a cap,
    // so a long label or path would cover the whole popup. Capped through
    // implicitWidth, which the tooltip centers itself by (as the host does).
    implicitWidth: Math.min(implicitContentWidth + leftPadding + rightPadding, Commons.Style.space(320))
    // The caller's text may be app text with no length bound (a path, an
    // error's detail): 3 lines of 200 characters keep an ordinary path whole
    // and the wrapped tooltip a few lines high, with a visible "…" beyond.
    text: FoamyText.cap(root.tooltipText, 3, 200)
    fontFamily: root.fontFamily

    // The host's text wraps at word boundaries only, so a name typed
    // without spaces would run past the capped width.
    Binding {
      target: tip.contentItem
      property: "wrapMode"
      value: Text.Wrap
    }
  }
}
