import QtQuick

// A bar that also reports per-screen thickness, like the 4.5 Bar itself
// (and PluginBarStateApi): barSizeFor(screen) may exceed barSize, e.g. a
// notch floor on a top bar.
MockBar {
  property var barSizes: ({})
  function barSizeFor(screenName) {
    var size = barSizes && barSizes[screenName] ? Number(barSizes[screenName]) : 0
    return size > 0 ? size : barSize
  }
}
