// Inline settings schema for the demo widget (mirrors manifest defaults).
var fields = [
  { key: "showCount", type: "boolean", defaultValue: true },
  { key: "refreshSeconds", type: "integer", min: 30, max: 3600, step: 30, defaultValue: 60 },
  { key: "layout", type: "enum", options: ["list", "tiles"], defaultValue: "list" }
]
if (typeof module !== "undefined") module.exports = { fields: fields }
