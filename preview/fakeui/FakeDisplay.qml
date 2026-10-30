pragma Singleton
import QtQuick
// Offscreen stand-in for the compositor: layer surfaces are drawn into `overlay`.
QtObject { property Item overlay: null }
