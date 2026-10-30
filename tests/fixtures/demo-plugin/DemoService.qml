pragma Singleton
import QtQuick

// Plugin-local state shared by every bar instance (one per monitor).
QtObject {
  property var devices: []
  property int refreshes: 0
  function refresh() { refreshes++ }
}
