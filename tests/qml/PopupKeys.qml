import QtQuick
import QtTest
import Quickshell
import qs.Ui
import "harness"
import "plugin/kit"

// Settings hides and FoamyPopup gives the keys back to its body (the key
// catcher), with no onHidden handler in the plugin: open Settings, close the
// popup, open it, Esc closes it; Esc on Settings goes back, the next Esc
// closes; a field on the page that hides with it; and a plugin that
// refocuses its own list in onHidden keeps that.
ShellRoot {
  id: shell
  readonly property string tag: Quickshell.env("FOAMY_TAG")
  property int checks: 0
  property int failures: 0
  // The plugin's own refocus (case 4).
  property bool ownRefocus: false

  function check(ok, label) {
    checks++
    if (!ok) {
      failures++
      console.log("FOAMY FAIL " + tag + " " + label)
    }
  }
  function focused() {
    var window = popup.bodyItem ? popup.bodyItem.Window.window : null
    return window ? window.activeFocusItem : null
  }
  function inside(item, ancestor) {
    for (var at = item; at; at = at.parent)
      if (at === ancestor)
        return true
    return false
  }
  function esc() {
    ev.keyClick(Qt.Key_Escape, Qt.NoModifier, -1)
  }

  FloatingWindow {
    implicitWidth: 1920
    implicitHeight: 1080
    color: "black"
    ScreenSim {
      id: sim
    }
    Item {
      TestEvent {
        id: ev
      }
    }
  }
  MockBar {
    id: bar
  }

  // The plugin's Panel: what FoamyPopup's owner and FoamySettingsState use.
  QtObject {
    id: panel
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
    panel: panel
    onHidden: if (shell.ownRefocus)
      Qt.callLater(function () {
        popup.bodyItem.list.forceActiveFocus()
      })
  }

  FoamyPopup {
    id: popup
    anchorItem: sim.anchor
    bar: bar
    owner: panel
    open: panel.opened
    body: Component {
      PanelKeyCatcher {
        id: view
        property alias list: list
        property alias page: page
        property alias pageField: pageField
        implicitHeight: 360
        blocked: settingsState.editing
        onCloseRequested: panel.close()
        // The panel's own list, which a plugin may focus itself.
        Item {
          id: list
          visible: !settingsState.editing
          width: parent.width
          height: 100
        }
        FoamySettingsPage {
          id: page
          visible: settingsState.editing
          width: parent.width
          height: parent.height
          onBack: settingsState.hide()
          SafeTextField {
            id: pageField
            width: 200
          }
        }
      }
    }
  }

  FoamyWait {
    id: wait
  }

  Component.onCompleted: closedOnSettings()

  // Opens Settings as a plugin does (show(), then the page takes the keys),
  // and runs `then` once the page has them.
  function openSettings(focus, label, then) {
    settingsState.show()
    wait.waitFor(function () {
      return popup.bodyItem !== null && popup.bodyItem.page.visible
    }, 5000, function (shown) {
      check(shown, label + ": Settings shows")
      focus()
      check(inside(focused(), popup.bodyItem.page), label + ": the settings page has the keys")
      then()
    })
  }
  // Opens the popup again and runs `then` once the host has given the body
  // the keys (KeyboardPanel focuses focusTarget after the open).
  function reopen(label, then) {
    panel.open()
    wait.waitFor(function () {
      return popup.open && focused() !== null && inside(focused(), popup.bodyItem)
    }, 5000, function (ok) {
      check(ok, label + ": the popup opens with the keys in its body")
      then()
    })
  }

  // 1. The popup closes on Settings and opens again: Esc closes it.
  function closedOnSettings() {
    openSettings(function () {
      popup.bodyItem.page.focusBack()
    }, "closed on Settings", function () {
      panel.close()
      check(!settingsState.editing, "closing the popup leaves Settings")
      reopen("closed on Settings", function () {
        check(!inside(focused(), popup.bodyItem.page), "the hidden settings page has no keys after the open: " + focused())
        esc()
        check(!panel.opened, "Esc closes the popup that was closed on Settings")
        backOnSettings()
      })
    })
  }

  // 2. Esc on Settings goes back; the next Esc closes the popup.
  function backOnSettings() {
    reopen("Back", function () {
      openSettings(function () {
        popup.bodyItem.page.focusBack()
      }, "Back", function () {
        esc()
        check(!settingsState.editing && panel.opened, "Esc on Settings goes back")
        wait.waitFor(function () {
          return focused() === popup.bodyItem
        }, 3000, function (home) {
          check(home, "the key catcher has the keys again: " + focused())
          esc()
          check(!panel.opened, "the next Esc closes the popup")
          fieldOnSettings()
        })
      })
    })
  }

  // 3. A focused field on the page hides with it when the popup closes: its
  // nearest key home, the page, hides too, so the keys go to the body.
  function fieldOnSettings() {
    reopen("field", function () {
      openSettings(function () {
        popup.bodyItem.pageField.focusInput()
      }, "field", function () {
        panel.close()
        reopen("field", function () {
          check(!popup.bodyItem.pageField.inputActiveFocus && !inside(focused(), popup.bodyItem.page), "the hidden page's field has no keys: " + focused())
          esc()
          check(!panel.opened, "Esc closes the popup that closed with a field focused on Settings")
          ownRefocusWins()
        })
      })
    })
  }

  // 4. A plugin that refocuses its own list when Settings hides keeps that.
  function ownRefocusWins() {
    shell.ownRefocus = true
    reopen("own refocus", function () {
      openSettings(function () {
        popup.bodyItem.page.focusBack()
      }, "own refocus", function () {
        esc()
        wait.waitFor(function () {
          return focused() === popup.bodyItem.list
        }, 3000, function (ok) {
          check(ok, "the plugin's own refocus wins: " + focused())
          console.log("FOAMY RESULT " + tag + " checks=" + checks + " failures=" + failures)
          console.log("FOAMY DONE")
          Qt.quit()
        })
      })
    })
  }
}
