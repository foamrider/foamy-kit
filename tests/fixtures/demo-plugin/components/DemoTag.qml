import QtQuick

// Uses DemoBadge from its own directory without a qmldir, as plugins do.
DemoBadge {
  property int battery: 0
  text: battery < 20 ? "low" : "ok"
}
