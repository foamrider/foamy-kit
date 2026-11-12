import QtQuick
import "../kit"
import ".." as Demo

// Preview states for the foamy-kit preview harness (see foamy-kit README).
// The harness sets `bar` and `anchorItem`, then for each name in
// previewStates sets previewState, waits, and captures `popup`.
Item {
  id: preview
  required property QtObject bar
  required property Item anchorItem
  property var previewStates: ["devices", "empty", "artwork", "settings", "settings-error"]
  property string previewState: "devices"
  // `var`: qmllint types FoamyPopup as the host's PanelWindow, not an Item;
  // its id isn't `popup`, which would shadow this property.
  readonly property var popup: previewPopup

  readonly property var sample: [
    { name: "MX Master 3S", icon: "laptop", battery: 82 },
    { name: "MX Keys", icon: "monitor", battery: 14 },
    { name: "Headset", icon: "headphones", battery: 55 }
  ]

  FoamyPopup {
    id: previewPopup
    anchorItem: preview.anchorItem
    bar: preview.bar
    open: true
    body: Component {
      Demo.DemoView {
        devices: preview.previewState === "empty" ? [] : preview.sample
        settings: ({ showCount: true, refreshSeconds: 60 })
        editingSettings: preview.previewState.indexOf("settings") === 0
        settingsError: preview.previewState === "settings-error" ? "Couldn't save the setting." : ""
        canRetry: preview.previewState === "settings-error"
        artwork: preview.previewState === "artwork" ? Qt.resolvedUrl("artwork.png") : ""
      }
    }
  }
}
