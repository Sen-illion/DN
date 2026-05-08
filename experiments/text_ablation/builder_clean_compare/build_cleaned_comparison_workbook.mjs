import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "C:/Users/User/Desktop/DN-main/experiments/text_ablation";
const resultsDir = path.join(root, "results");
const inputPath = path.join(resultsDir, "cleaned_comparison_data.json");
const outputPath = path.join(resultsDir, "coherence_comparison_cleaned.xlsx");

const labelMap = {
  wv_off_text_off: "WV off / Text off",
  wv_off_text_on: "WV off / Text on",
  wv_on_text_off: "WV on / Text off",
  wv_on_text_on: "WV on / Text on",
};

const colorMap = {
  "WV off / Text off": "#9CA3AF",
  "WV off / Text on": "#2563EB",
  "WV on / Text off": "#F59E0B",
  "WV on / Text on": "#059669",
};

function fmt(value, digits = 4) {
  return typeof value === "number" ? Number(value.toFixed(digits)) : null;
}

function setHeader(range) {
  range.format = {
    fill: {
      type: "solid",
      color: "#0F172A",
    },
    font: { name: "Calibri", size: 11, color: "#FFFFFF", bold: true },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
}

function setTableBorders(range) {
  range.format.borders = {
    preset: "inside+outside",
    style: "thin",
    color: "#CBD5E1",
  };
}

const raw = JSON.parse(await fs.readFile(inputPath, "utf8"));
const workbook = Workbook.create();

// Summary sheet
const summary = workbook.worksheets.add("Summary");
summary.getRange("A1").values = [["Cleaned Text Coherence Comparison"]];
summary.getRange("A1:F1").merge();
summary.getRange("A1:F1").format = {
  font: { name: "Calibri", size: 18, bold: true, color: "#0F172A" },
  horizontalAlignment: "left",
  verticalAlignment: "center",
};

summary.getRange("A3").values = [[
  "This workbook keeps only theme_item_id 1-6 for fair four-way comparison. theme_item_id 12/18/54/73 are excluded because they collapse into fallback-like 323-char stories.",
]];
summary.getRange("A3:F4").merge();
summary.getRange("A3:F4").format = {
  fill: "#F8FAFC",
  font: { name: "Calibri", size: 10, color: "#334155" },
  wrapText: true,
  verticalAlignment: "top",
};

const summaryHeader = [
  "Rank",
  "Config",
  "Samples",
  "Avg consistency",
  "Avg story chars",
  "Best theme",
  "Worst theme",
];
summary.getRange("A6:G6").values = [summaryHeader];
setHeader(summary.getRange("A6:G6"));

const summaryRows = raw.summary.map((item, idx) => [
  idx + 1,
  labelMap[item.config] || item.config,
  item.sample_count,
  fmt(item.avg_consistency),
  fmt(item.avg_story_chars, 1),
  item.best_theme,
  item.worst_theme,
]);
summary.getRange(`A7:G${6 + summaryRows.length}`).values = summaryRows;
summary.getRange(`A7:G${6 + summaryRows.length}`).format = {
  font: { name: "Calibri", size: 11, color: "#0F172A" },
  verticalAlignment: "center",
};
summary.getRange(`D7:D${6 + summaryRows.length}`).format.numberFormat = "0.0000";
summary.getRange(`E7:E${6 + summaryRows.length}`).format.numberFormat = "0.0";
setTableBorders(summary.getRange(`A6:G${6 + summaryRows.length}`));

summary.getRange("I2").values = [["Avg consistency by config"]];
summary.getRange("I2:M2").merge();
summary.getRange("I2:M2").format = {
  font: { name: "Calibri", size: 13, bold: true, color: "#0F172A" },
};

summary.charts.add("bar", {
  title: "Avg consistency (clean first 6 themes)",
  categories: summaryRows.map((row) => row[1]),
  series: [
    {
      name: "Avg consistency",
      values: summaryRows.map((row) => row[3]),
    },
  ],
  hasLegend: false,
  barOptions: { direction: "column", grouping: "clustered", gapWidth: 55 },
  dataLabels: { showValue: true },
  from: { row: 2, col: 8 },
  extent: { widthPx: 560, heightPx: 300 },
});

summary.freezePanes.freezeRows(6);
summary.getRange("A1:M20").format.autofitColumns();

// Fair comparison sheet
const compare = workbook.worksheets.add("FairCompare");
compare.getRange("A1").values = [["Fair comparison across the shared 6 themes"]];
compare.getRange("A1:G1").merge();
compare.getRange("A1:G1").format = {
  font: { name: "Calibri", size: 16, bold: true, color: "#0F172A" },
};

const compareHeader = [
  "Theme ID",
  "Theme",
  "WV off / Text off",
  "WV off / Text on",
  "WV on / Text off",
  "WV on / Text on",
  "Spread",
];
compare.getRange("A3:G3").values = [compareHeader];
setHeader(compare.getRange("A3:G3"));

const compareRows = raw.per_theme.map((item) => [
  item.theme_item_id,
  item.theme,
  fmt(item.wv_off_text_off),
  fmt(item.wv_off_text_on),
  fmt(item.wv_on_text_off),
  fmt(item.wv_on_text_on),
  fmt(item.spread),
]);
compare.getRange(`A4:G${3 + compareRows.length}`).values = compareRows;
compare.getRange(`A4:G${3 + compareRows.length}`).format = {
  font: { name: "Calibri", size: 11, color: "#0F172A" },
};
compare.getRange(`C4:G${3 + compareRows.length}`).format.numberFormat = "0.0000";
setTableBorders(compare.getRange(`A3:G${3 + compareRows.length}`));

compare.charts.add("bar", {
  title: "Per-theme comparison",
  categories: raw.per_theme.map((item) => `${item.theme_item_id} ${item.theme}`),
  series: [
    {
      name: "WV off / Text off",
      values: raw.per_theme.map((item) => item.wv_off_text_off),
      color: colorMap["WV off / Text off"],
    },
    {
      name: "WV off / Text on",
      values: raw.per_theme.map((item) => item.wv_off_text_on),
      color: colorMap["WV off / Text on"],
    },
    {
      name: "WV on / Text off",
      values: raw.per_theme.map((item) => item.wv_on_text_off),
      color: colorMap["WV on / Text off"],
    },
    {
      name: "WV on / Text on",
      values: raw.per_theme.map((item) => item.wv_on_text_on),
      color: colorMap["WV on / Text on"],
    },
  ],
  hasLegend: true,
  legend: { position: "top" },
  barOptions: { direction: "column", grouping: "clustered", gapWidth: 60 },
  dataLabels: { showValue: false },
  from: { row: 9, col: 0 },
  extent: { widthPx: 860, heightPx: 320 },
});

compare.freezePanes.freezeRows(3);
compare.getRange("A1:H28").format.autofitColumns();

// Excluded samples sheet
const excluded = workbook.worksheets.add("ExcludedSamples");
excluded.getRange("A1").values = [["Excluded garbage / fallback samples"]];
excluded.getRange("A1:G1").merge();
excluded.getRange("A1:G1").format = {
  font: { name: "Calibri", size: 16, bold: true, color: "#0F172A" },
};

excluded.getRange("A3").values = [[
  "These rows stay out of the fair comparison because the generated story collapses into a fallback-like 323-char output.",
]];
excluded.getRange("A3:G4").merge();
excluded.getRange("A3:G4").format = {
  fill: "#FEF3C7",
  font: { name: "Calibri", size: 10, color: "#7C2D12" },
  wrapText: true,
};

const excludedHeader = [
  "Config",
  "Theme ID",
  "Theme",
  "Story chars",
  "Consensus",
  "Reason",
  "Source file note",
];
excluded.getRange("A6:G6").values = [excludedHeader];
setHeader(excluded.getRange("A6:G6"));

const excludedRows = raw.excluded.map((item) => [
  labelMap[item.config] || item.config,
  item.theme_item_id,
  item.theme,
  item.story_chars,
  fmt(item.consensus),
  item.exclude_reason,
  item.config === "wv_on_text_off" ? "Already rerun as clean 6-sample file" : "Present in original 10-sample file",
]);
if (excludedRows.length) {
  excluded.getRange(`A7:G${6 + excludedRows.length}`).values = excludedRows;
  excluded.getRange(`A7:G${6 + excludedRows.length}`).format = {
    font: { name: "Calibri", size: 11, color: "#0F172A" },
    verticalAlignment: "center",
  };
  excluded.getRange(`E7:E${6 + excludedRows.length}`).format.numberFormat = "0.0000";
  setTableBorders(excluded.getRange(`A6:G${6 + excludedRows.length}`));
}
excluded.freezePanes.freezeRows(6);
excluded.getRange("A1:H24").format.autofitColumns();

// Method sheet
const method = workbook.worksheets.add("Method");
method.getRange("A1").values = [["How to read this workbook"]];
method.getRange("A1:F1").merge();
method.getRange("A1:F1").format = {
  font: { name: "Calibri", size: 16, bold: true, color: "#0F172A" },
};

const noteRows = raw.notes.map((text, idx) => [idx + 1, text]);
method.getRange("A3:B3").values = [["#", "Note"]];
setHeader(method.getRange("A3:B3"));
method.getRange(`A4:B${3 + noteRows.length}`).values = noteRows;
method.getRange(`A4:B${3 + noteRows.length}`).format = {
  font: { name: "Calibri", size: 11, color: "#0F172A" },
  wrapText: true,
};
setTableBorders(method.getRange(`A3:B${3 + noteRows.length}`));
method.getRange("A8").values = [[
  "Practical takeaway: WV on + Text on is the strongest setting on the fair 6-theme comparison. WV on + Text off stays competitive, but it also shortens stories much more, so its higher coherence is likely helped by being more conservative.",
]];
method.getRange("A8:F11").merge();
method.getRange("A8:F11").format = {
  fill: "#EFF6FF",
  font: { name: "Calibri", size: 11, color: "#1E3A8A" },
  wrapText: true,
  verticalAlignment: "top",
};
method.getRange("A1:F15").format.autofitColumns();

const inspectSummary = await workbook.inspect({
  kind: "table",
  range: "Summary!A6:G10",
  include: "values",
  tableMaxRows: 10,
  tableMaxCols: 10,
});
console.log(inspectSummary.ndjson);

const inspectCompare = await workbook.inspect({
  kind: "table",
  range: "FairCompare!A3:G9",
  include: "values",
  tableMaxRows: 10,
  tableMaxCols: 10,
});
console.log(inspectCompare.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  summary: "formula error scan",
});
console.log(errors.ndjson);

await fs.mkdir(resultsDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`SAVED ${outputPath}`);
