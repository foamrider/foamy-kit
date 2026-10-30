import QtQuick
import qs.Ui

// A row or tile in the panel's single keyboard cursor model: the stock
// CursorSurface (one highlight for keyboard and pointer, theme state fills)
// with the foamy radius. Paint from `hasCursor`/`current`, never from
// containsMouse; route hover back to the panel cursor with `hovered`.
//
//   FoamyCursorSurface {
//     hasCursor: cursor.at(index)
//     onHovered: cursor.hover(index)
//     onClicked: root.activate(index)
//   }
CursorSurface {
  id: root

  signal hovered()
  signal clicked()

  radius: FoamyStyle.radius

  HoverHandler {
    onHoveredChanged: if (hovered) root.hovered()
  }
  TapHandler {
    onTapped: root.clicked()
  }
}
