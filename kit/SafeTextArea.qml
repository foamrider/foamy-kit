import QtQuick
import QtQuick.Controls as Controls
import qs.Commons
import qs.Commons as Commons
import qs.Ui

// A multi-line text field that never lets Qt read the clipboard itself: the
// multi-line sibling of SafeTextField, with the same safety rules.
//
// Paste (Ctrl+V, Shift+Insert, the context menu, middle-click) goes through
// FoamyClipboard (kit/clipboard.sh `multiline`): bounded to 16 KiB, NUL-free,
// 2 s deadline, line breaks kept as "\n", and a late result never overwrites
// newer typing, navigation or a closed form.
//
//   SafeTextArea {
//     width: parent.width
//     text: root.description
//     placeholderText: FoamyI18n.t("Description")
//     Accessible.name: FoamyI18n.t("Description")
//     translate: FoamyI18n.t                 // context menu labels
//     maximumLength: 16384
//     onTextEdited: root.description = text
//     onEditingFinished: root.save()         // focus left the field
//     onKeyPressed: function(event) {         // Ctrl+Enter saves
//       if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && (event.modifiers & Qt.ControlModifier)) {
//         root.save()
//         event.accepted = true
//       }
//     }
//   }
//
// - Enter and Shift+Enter insert a newline; keyPressed sees every key first
//   (accept the event to keep it from the editor). Tab and Shift+Tab move
//   the focus, as in SafeTextField.
// - The field grows with its text from minimumHeight to maximumHeight, then
//   scrolls (wheel through FoamyWheelScroll, and to keep the caret in view).
//   Lines wrap at word boundaries (`wrapMode`, TextEdit's).
// - maximumLength counts UTF-16 units, like SafeTextField's. Typing or a
//   newline that would pass it is dropped; a paste is cut to fit; a longer
//   `text` given by the caller, or a lower maximumLength, cuts the end. No
//   cut splits a surrogate pair.
// - textEdited fires on every change the user makes (typing, paste, cut,
//   undo, redo); editingFinished when the field loses the focus (to
//   anything but its own context menu: then when the menu closes without
//   giving the focus back).
// - Styled like SafeTextField (foamy radius, control fill and border), with
//   its `quiet` mode for text edited in place.
//   clipboardScript resolves relative to FoamyClipboard.qml unless absolute.

Flickable {
  id: root

  property color foreground: Commons.Color.foreground
  property color accent: Commons.Color.accent
  property string clipboardScript: "clipboard.sh"
  // Longest text the field keeps (typing and paste), in UTF-16 units.
  property int maximumLength: 32767
  // The field's height follows its text between these two (it scrolls past
  // maximumHeight).
  property real minimumHeight: FoamyStyle.controlHeight * 2
  property real maximumHeight: FoamyStyle.controlHeight * 5
  property real cornerRadius: FoamyStyle.radius
  property color selectionTint: Style.selectionFillFor(foreground, accent)
  property bool hasCursor: false
  readonly property bool _focused: editor.activeFocus
  readonly property bool _hot: editor.hovered || hasCursor
  readonly property var _borderSpec: Border.controlSpec(_focused ? "focus" : (_hot ? "hover-cursor" : "normal"), foreground, accent)
  // Quiet: text edited in place (a title that reads as text). At rest it
  // has no fill and no border; hover, the cursor or the focus show the
  // usual field. The border keeps its width, so the text never moves.
  property bool quiet: false
  readonly property bool _resting: quiet && !_focused && !_hot
  readonly property var _restingBorder: ({
      "color": "transparent",
      "widths": _borderSpec.widths,
      "gradient": {
        "colors": [],
        "angle": 0,
        "enabled": false
      }
    })
  property alias background: editor.background
  property bool editorReady: false
  // A scroll view around the field (FoamySettingsPage's focus follow)
  // shows the field's box, not its inner editor: the field scrolls its
  // own text to the caret.
  readonly property bool scrollsItself: true
  property alias color: editor.color
  property alias cursorPosition: editor.cursorPosition
  property alias font: editor.font
  property alias horizontalAlignment: editor.horizontalAlignment
  // An alias (see SafeTextField): current inside editingFinished.
  readonly property alias inputActiveFocus: editor.activeFocus
  // The editor itself (tests, glyph geometry).
  readonly property Item editorItem: editor
  readonly property int length: editor.length
  property alias padding: editor.padding
  property alias leftPadding: editor.leftPadding
  property alias rightPadding: editor.rightPadding
  property alias topPadding: editor.topPadding
  property alias bottomPadding: editor.bottomPadding
  property alias placeholderText: editor.placeholderText
  property alias placeholderTextColor: editor.placeholderTextColor
  property alias selectedTextColor: editor.selectedTextColor
  property alias selectionColor: editor.selectionColor
  property alias selectionEnd: editor.selectionEnd
  property alias selectionStart: editor.selectionStart
  property alias text: editor.text
  property alias wrapMode: editor.wrapMode
  property var translate: function (key) {
    return key
  }

  // Paste bookkeeping: the edit a running paste belongs to. A result lands
  // only while the text (revision), selection and caret are what they were.
  property int revision: 0
  property int pasteRevision: -1
  property int pasteStart: 0
  property int pasteEnd: 0
  property int pasteCursor: 0
  property string pasteError: ""
  readonly property bool pasteRunning: pasteRevision >= 0 || clipboard.busy

  signal keyPressed(var event)
  signal editingFinished
  signal textEdited

  // The focus went into the field's own context menu: the edit goes on
  // until the menu closes without giving the focus back.
  property bool _finishAfterMenu: false

  function cancelPaste() {
    pasteRevision = -1
    clipboard.cancel()
  }
  function _finishEditing() {
    cancelPaste()
    editingFinished()
  }
  // Empties the text. No textEdited: the caller made the change.
  function clear() {
    cancelPaste()
    editor.clear()
  }
  function cut() {
    var before = editor.text
    editor.cut()
    if (editor.text !== before)
      root.textEdited()
  }
  function focusInput() {
    editor.forceActiveFocus()
  }
  function redo() {
    // Programmatic TextEdit actions do not emit textEdited; menu edits must.
    var before = editor.text
    editor.redo()
    if (editor.text !== before)
      root.textEdited()
  }
  function undo() {
    var before = editor.text
    editor.undo()
    if (editor.text !== before)
      root.textEdited()
  }
  function select(start, end) {
    editor.select(start, end)
  }
  function selectAll() {
    editor.selectAll()
  }
  function requestPaste(primary) {
    if (!enabled || !visible || pasteRunning)
      return
    pasteError = ""
    pasteRevision = revision
    pasteStart = editor.selectionStart
    pasteEnd = editor.selectionEnd
    pasteCursor = editor.cursorPosition
    if (!clipboard.start(primary))
      pasteRevision = -1
  }
  // Whether a running paste still belongs to the field as it is now.
  function _pasteCurrent() {
    return pasteRevision >= 0 && enabled && visible && editor.activeFocus && pasteRevision === revision && pasteStart === editor.selectionStart && pasteEnd === editor.selectionEnd && pasteCursor === editor.cursorPosition
  }
  function _finishPaste(value) {
    var current = _pasteCurrent()
    pasteRevision = -1
    if (!current)
      return
    // Keep maximumLength (with repeated pastes), never cutting a surrogate pair.
    value = value.slice(0, _cutAt(value, Math.max(0, _limit() - editor.length + pasteEnd - pasteStart)))
    if (value === "" && pasteStart === pasteEnd)
      return
    // Not file-backed: reset the modified marker at each boundary so Qt keeps
    // the paste its own undo step instead of merging it with typing.
    editor.textDocument.modified = false
    editor.cursorSelection.text = value
    editor.cursorPosition = pasteStart + value.length
    editor.textDocument.modified = false
    root.textEdited()
  }
  function _failPaste(message) {
    var current = _pasteCurrent()
    pasteRevision = -1
    if (current)
      pasteError = message
  }
  function _limit() {
    return maximumLength > 32767 ? 32767 : (maximumLength > 0 ? maximumLength : 0)
  }
  // Where to cut `text` so it keeps at most `limit` UTF-16 units without
  // splitting a surrogate pair. No JS globals (see onMaximumLengthChanged).
  function _cutAt(text, limit) {
    if (limit >= text.length)
      return text.length
    if (limit <= 0)
      return 0
    var code = text.charCodeAt(limit - 1)
    return code >= 0xd800 && code < 0xdc00 ? limit - 1 : limit
  }
  // Whether a typed key (text or a newline) would pass maximumLength, as
  // QInputControl::isAcceptableInput reads it: Ctrl and Ctrl+Shift
  // combinations are shortcuts, control characters never type.
  function _overflows(event) {
    var newline = event.key === Qt.Key_Return || event.key === Qt.Key_Enter
    var text = newline ? "\n" : event.text
    var modifiers = event.modifiers & ~Qt.KeypadModifier
    if (text === "" || modifiers === Qt.ControlModifier || modifiers === (Qt.ControlModifier | Qt.ShiftModifier))
      return false
    for (let i = 0; !newline && i < text.length; i++) {
      let code = text.charCodeAt(i)
      if (code < 0x20 || (code >= 0x7f && code < 0xa0))
        return false
    }
    return editor.length - (editor.selectionEnd - editor.selectionStart) + text.length > _limit()
  }
  // Scroll the least amount that shows the caret line.
  function _followCursor() {
    if (!editorReady)
      return
    var top = editor.cursorRectangle.y
    var bottom = top + editor.cursorRectangle.height + editor.bottomPadding
    top -= editor.topPadding
    var max = Math.max(0, contentHeight - height)
    if (top < contentY)
      contentY = Math.max(0, top)
    else if (bottom > contentY + height)
      contentY = Math.min(max, bottom - height)
  }

  // Expose the native editable control, with the caller's field label.
  Accessible.ignored: true
  boundsBehavior: Flickable.StopAtBounds
  clip: true
  flickableDirection: Flickable.VerticalFlick
  implicitHeight: Math.max(minimumHeight, Math.min(maximumHeight, editor.contentHeight + editor.topPadding + editor.bottomPadding))
  // Explicit, so it follows LayoutMirroring (see SafeTextField).
  horizontalAlignment: TextEdit.AlignLeft
  font.family: FoamyStyle.fontFamily
  font.pixelSize: FoamyStyle.font.body
  color: foreground
  selectionColor: selectionTint
  selectedTextColor: foreground
  // A hint: the palette's muted text (as SafeTextField).
  placeholderTextColor: FoamyPalette.mutedText
  wrapMode: TextEdit.Wrap
  leftPadding: FoamyStyle.controlPaddingX + Border.left(_borderSpec)
  rightPadding: FoamyStyle.controlPaddingX + Border.right(_borderSpec)
  topPadding: FoamyStyle.controlPaddingY + Border.top(_borderSpec)
  bottomPadding: FoamyStyle.controlPaddingY + Border.bottom(_borderSpec)
  background: BorderSurface {
    color: root._resting ? "transparent" : Style.controlFill(root._focused, root._hot, root.foreground, root.accent)
    borderSpec: root._resting ? root._restingBorder : root._borderSpec
    radius: root.cornerRadius
  }

  // A TextArea checks the clipboard's formats only, never its text (a
  // TextField reads the whole text even on dataChanged).
  Controls.TextArea.flickable: Controls.TextArea {
    id: editor
    objectName: "safeEditor"

    Accessible.name: root.Accessible.name
    Accessible.role: Accessible.EditableText
    Accessible.multiLine: true
    activeFocusOnTab: true
    persistentSelection: true
    selectByMouse: true
    textFormat: TextEdit.PlainText

    // Our own menu: no entry calls the native paste or reads canPaste.
    Controls.ContextMenu.menu: Controls.Menu {
      id: editMenu
      objectName: "clipboardMenu"
      onClosed: if (root._finishAfterMenu) {
        root._finishAfterMenu = false
        if (!editor.activeFocus)
          root._finishEditing()
      }

      Controls.MenuItem {
        enabled: editor.canUndo
        text: root.translate("Undo")
        onTriggered: root.undo()
      }
      Controls.MenuItem {
        enabled: editor.canRedo
        text: root.translate("Redo")
        onTriggered: root.redo()
      }
      Controls.MenuSeparator {}
      Controls.MenuItem {
        enabled: editor.selectedText !== ""
        text: root.translate("Cut")
        onTriggered: root.cut()
      }
      Controls.MenuItem {
        enabled: editor.selectedText !== ""
        text: root.translate("Copy")
        onTriggered: editor.copy()
      }
      Controls.MenuItem {
        enabled: !root.pasteRunning
        text: root.translate("Paste")
        onTriggered: {
          editMenu.close()
          root.focusInput()
          root.requestPaste(false)
        }
      }
      Controls.MenuItem {
        text: root.translate("Select all")
        onTriggered: editor.selectAll()
      }
    }

    Keys.onPressed: function (event) {
      // The caller sees every key first (Ctrl+Enter to save, Escape).
      event.accepted = false
      root.keyPressed(event)
      if (event.accepted)
        return
      if (event.matches(StandardKey.Paste)) {
        event.accepted = true
        root.requestPaste(false)
      } else if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
        event.accepted = true
        let backwards = event.key === Qt.Key_Backtab || (event.modifiers & Qt.ShiftModifier)
        nextItemInFocusChain(!backwards).forceActiveFocus(Qt.TabFocusReason)
      } else if (root._overflows(event)) {
        // At maximumLength: drop the key rather than cut the text's end.
        event.accepted = true
      }
    }
    // Opening the context menu moves the focus into it. That is not the end
    // of the edit: the caller must not save or hide the field then (the
    // menu's Paste needs it shown); editingFinished waits for the menu.
    onActiveFocusChanged: if (activeFocus)
      root._finishAfterMenu = false
    else if (editMenu.visible)
      root._finishAfterMenu = true
    else
      root._finishEditing()
    onCursorRectangleChanged: root._followCursor()
    onTextChanged: {
      // A longer text from elsewhere (the caller's `text`, an input method)
      // is cut at the end.
      var limit = root._limit()
      if (length > limit)
        remove(root._cutAt(text, limit), length)
      root.revision++
      root.pasteError = ""
    }
    onTextEdited: root.textEdited()

    // Consume the primary-selection paste: Qt's own would read the selection.
    MouseArea {
      acceptedButtons: Qt.MiddleButton
      anchors.fill: parent

      onClicked: root.requestPaste(true)
      onPressed: function (mouse) {
        editor.forceActiveFocus()
        editor.cursorPosition = editor.positionAt(mouse.x, mouse.y)
      }
    }
  }

  FoamyWheelScroll {
    target: root
    // The field is the Flickable: a click in it is the field's own.
    clickAway: false
    // A notch scrolls the platform's wheel lines of this field's text.
    notch: Math.max(1, Application.styleHints.wheelScrollLines) * Math.max(1, editor.cursorRectangle.height)
  }

  FoamyClipboard {
    id: clipboard
    clipboardScript: root.clipboardScript
    multiline: true
    onRead: function (text) {
      root._finishPaste(text)
    }
    onFailed: function (message) {
      root._failPaste(message)
    }
  }

  onHeightChanged: _followCursor()
  Component.onCompleted: {
    editorReady = true
    if (editor.length > _limit())
      editor.remove(_cutAt(editor.text, _limit()), editor.length)
  }
  // Runs when maximumLength changes after creation (see SafeTextField: no
  // JS globals here).
  onMaximumLengthChanged: {
    if (!editorReady)
      return
    var limit = _limit()
    if (editor.length > limit)
      editor.remove(_cutAt(editor.text, limit), editor.length)
  }
  Component.onDestruction: cancelPaste()
  onActiveFocusChanged: if (activeFocus)
    editor.forceActiveFocus()
  onEnabledChanged: if (!enabled)
    cancelPaste()
  onVisibleChanged: if (!visible) {
    cancelPaste()
    pasteError = ""
  }
}
