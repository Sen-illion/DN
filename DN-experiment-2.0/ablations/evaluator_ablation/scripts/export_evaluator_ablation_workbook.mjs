import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const part = argv[index];
    if (!part.startsWith("--")) {
      continue;
    }
    args[part.slice(2)] = argv[index + 1];
    index += 1;
  }
  return args;
}

function normalizeValue(value) {
  if (value === undefined || value === null) {
    return null;
  }
  if (Array.isArray(value) || typeof value === "object") {
    return JSON.stringify(value);
  }
  return value;
}

function estimateColumnWidthPx(values) {
  let maxLength = 8;
  for (const value of values) {
    const length = String(value ?? "").length;
    if (length > maxLength) {
      maxLength = length;
    }
  }
  return Math.max(100, Math.min(320, maxLength * 7 + 24));
}

function metadataMap(runMetadata) {
  return Object.fromEntries((runMetadata || []).map((row) => [row.key, row.value]));
}

function diagnosticsMap(rows) {
  const out = {};
  for (const row of rows || []) {
    out[row.metric] = row.value;
  }
  return out;
}

function setColumnWidths(sheet, startCol, matrix) {
  const colCount = Math.max(...matrix.map((row) => row.length), 1);
  for (let col = 0; col < colCount; col += 1) {
    const values = matrix.map((row) => row[col]);
    sheet.getRangeByIndexes(0, startCol + col, 1, 1).format.columnWidthPx = estimateColumnWidthPx(values);
  }
}

function writeMatrix(sheet, startRow, startCol, matrix, options = {}) {
  const { header = false, compact = false } = options;
  const rowCount = Math.max(matrix.length, 1);
  const colCount = Math.max(...matrix.map((row) => row.length), 1);
  const padded = matrix.map((row) => {
    const next = row.slice();
    while (next.length < colCount) {
      next.push(null);
    }
    return next.map((value) => normalizeValue(value));
  });

  sheet.getRangeByIndexes(startRow, startCol, rowCount, colCount).values = padded;
  const bodyRange = sheet.getRangeByIndexes(startRow, startCol, rowCount, colCount);
  bodyRange.format.wrapText = true;
  bodyRange.format.verticalAlignment = "top";
  if (header) {
    sheet.getRangeByIndexes(startRow, startCol, 1, colCount).format = {
      fill: "#1F2937",
      font: { color: "#FFFFFF", bold: true, size: 10 },
      horizontalAlignment: "center",
      verticalAlignment: "center",
    };
  }
  if (rowCount > 1) {
    sheet.getRangeByIndexes(startRow + 1, startCol, rowCount - 1, colCount).format = {
      verticalAlignment: "top",
      wrapText: true,
      fill: compact ? "#FFFFFF" : "#FBFCFE",
    };
    sheet.getRangeByIndexes(startRow + 1, startCol, rowCount - 1, colCount).format.rowHeightPx = compact ? 24 : 28;
  }
  for (let col = 0; col < colCount; col += 1) {
    const values = padded.map((row) => row[col]);
    sheet.getRangeByIndexes(startRow, startCol + col, 1, 1).format.columnWidthPx = estimateColumnWidthPx(values);
  }
  return startRow + rowCount;
}

function addPageTitle(sheet, title, subtitle, width = 10) {
  const titleRange = sheet.getRangeByIndexes(0, 0, 1, width);
  titleRange.merge();
  titleRange.values = [[title]];
  titleRange.format = {
    fill: "#FFFFFF",
    font: { bold: true, color: "#111827", size: 18 },
    verticalAlignment: "center",
  };

  const subtitleRange = sheet.getRangeByIndexes(1, 0, 1, width);
  subtitleRange.merge();
  subtitleRange.values = [[subtitle]];
  subtitleRange.format = {
    fill: "#FFFFFF",
    font: { color: "#4B5563", size: 10 },
    verticalAlignment: "center",
    wrapText: true,
  };
}

function addCaption(sheet, row, caption, width = 10) {
  const range = sheet.getRangeByIndexes(row, 0, 1, width);
  range.merge();
  range.values = [[caption]];
  range.format = {
    fill: "#E5E7EB",
    font: { bold: true, color: "#111827", size: 10 },
    verticalAlignment: "center",
  };
}

function addNoteBox(sheet, startRow, width, lines) {
  const heading = sheet.getRangeByIndexes(startRow, 0, 1, width);
  heading.merge();
  heading.values = [["Notes"]];
  heading.format = {
    fill: "#E5E7EB",
    font: { bold: true, color: "#111827", size: 10 },
  };
  const content = sheet.getRangeByIndexes(startRow + 1, 0, 1, width);
  content.merge();
  content.values = [[lines.join("  ")]];
  content.format = {
    fill: "#F9FAFB",
    font: { color: "#374151", size: 10 },
    wrapText: true,
    verticalAlignment: "top",
  };
}

function addDatasetOverviewSheet(workbook, payload) {
  const sheet = workbook.worksheets.add("overview");
  sheet.showGridLines = true;
  addPageTitle(
    sheet,
    "Evaluator Ablation Dataset",
    "Dataset inventory for the evaluator-ablation study. This page summarizes how many themes and reusable image samples actually exist in the repository, and which samples were selected for the current run.",
    8,
  );

  const meta = metadataMap(payload.run_metadata || []);
  const diag = diagnosticsMap(payload.diagnostics || []);
  const selectedRows = (payload.dataset_manifest || []).filter((row) => row.selected);
  const previewHeaders = ["theme_id", "theme", "game_id", "segment_index", "sample_id"];
  const previewRows = selectedRows.slice(0, 12).map((row) => previewHeaders.map((header) => row[header]));

  let row = 3;
  addCaption(sheet, row, "Table A1. Dataset availability summary", 8);
  row += 1;
  row = writeMatrix(sheet, row, 0, [
    ["metric", "value"],
    ["preset_size", meta.size || ""],
    ["seed", meta.seed || ""],
    ["available_themes", meta.available_themes || ""],
    ["available_games", meta.available_games || ""],
    ["available_samples", meta.available_samples || ""],
    ["selected_themes", meta.selected_themes || ""],
    ["selected_games", meta.selected_games || ""],
    ["selected_samples", meta.selected_samples || ""],
    ["themes_with_manifest", diag.themes_with_manifest || ""],
    ["themes_without_manifest", diag.themes_without_manifest || ""],
    ["themes_with_available_samples", diag.themes_with_available_samples || ""],
  ], { header: true, compact: true });

  row += 1;
  addCaption(sheet, row, "Table A2. Selected sample snapshot", 8);
  row += 1;
  row = writeMatrix(sheet, row, 0, [previewHeaders, ...previewRows], { header: true });

  row += 1;
  addNoteBox(sheet, row, 8, [
    "Use `dataset_manifest` for the full manifest including filtered-out and unavailable rows.",
    "Use `theme_summary` to see which themes are missing reusable images.",
    "This workbook is for dataset transparency; evaluation results are in `latest_evaluator_ablation.xlsx`.",
  ]);

  sheet.freezePanes.freezeRows(4);
}

function addAnalysisOverviewSheet(workbook, payload) {
  const sheet = workbook.worksheets.add("overview");
  sheet.showGridLines = true;
  addPageTitle(
    sheet,
    "Evaluator Ablation Results",
    "Group-level comparison on the same selected image-consistency samples. Higher `overall_score_mean` means the evaluator group is more favorable on average; higher `judge_disagreement_mean` means the judges inside that group disagree more strongly.",
    11,
  );

  const meta = metadataMap(payload.run_metadata || []);
  const groupRows = (payload.per_group_summary || []).slice();
  const comparisonRows = (payload.group_comparison || [])
    .slice()
    .sort((left, right) => Math.abs(right.delta_overall_score_mean || 0) - Math.abs(left.delta_overall_score_mean || 0));
  const disagreementRows = (payload.disagreement_analysis || []).slice(0, 8);
  const highestGroup = groupRows.slice().sort((left, right) => (right.overall_score_mean || 0) - (left.overall_score_mean || 0))[0];
  const lowestGroup = groupRows.slice().sort((left, right) => (left.overall_score_mean || 0) - (right.overall_score_mean || 0))[0];
  const highestDisagreement = groupRows.slice().sort((left, right) => (right.judge_disagreement_mean || 0) - (left.judge_disagreement_mean || 0))[0];

  let row = 3;
  addCaption(sheet, row, "Study setup", 11);
  row += 1;
  row = writeMatrix(sheet, row, 0, [
    ["metric", "value"],
    ["selected_sample_count", meta.selected_sample_count || ""],
    ["selected_theme_count", meta.selected_theme_count || ""],
    ["judge_groups", meta.judge_groups || ""],
    ["highest_overall_group", highestGroup ? `${highestGroup.group_label} (${highestGroup.overall_score_mean})` : ""],
    ["lowest_overall_group", lowestGroup ? `${lowestGroup.group_label} (${lowestGroup.overall_score_mean})` : ""],
    ["highest_disagreement_group", highestDisagreement ? `${highestDisagreement.group_label} (${highestDisagreement.judge_disagreement_mean})` : ""],
  ], { header: true, compact: true });

  row += 1;
  addCaption(sheet, row, "Table 1. Group-level evaluator comparison", 11);
  row += 1;
  const groupHeaders = [
    "group_label",
    "judge_models",
    "overall_score_mean",
    "judge_disagreement_mean",
    "coverage",
    "valid_sample_count",
    "semantic_consistency_mean",
    "subject_attribute_consistency_mean",
    "spatial_consistency_mean",
    "style_lighting_consistency_mean",
    "detail_integrity_mean",
  ];
  row = writeMatrix(sheet, row, 0, [groupHeaders, ...groupRows.map((item) => groupHeaders.map((header) => item[header]))], { header: true });

  row += 1;
  addCaption(sheet, row, "Table 2. Largest pairwise deltas between evaluator groups", 11);
  row += 1;
  const comparisonHeaders = [
    "left_group_label",
    "right_group_label",
    "delta_overall_score_mean",
    "pairwise_mean_abs_diff",
    "delta_judge_disagreement_mean",
    "common_sample_count",
  ];
  row = writeMatrix(sheet, row, 0, [comparisonHeaders, ...comparisonRows.slice(0, 8).map((item) => comparisonHeaders.map((header) => item[header]))], { header: true });

  row += 1;
  addCaption(sheet, row, "Table 3. Most disputed samples", 11);
  row += 1;
  const disagreementHeaders = [
    "group_label",
    "theme",
    "sample_id",
    "overall_score_mean",
    "judge_disagreement",
    "top_disagreement_dimension",
    "judge_score_map_json",
  ];
  row = writeMatrix(sheet, row, 0, [disagreementHeaders, ...disagreementRows.map((item) => disagreementHeaders.map((header) => item[header]))], { header: true });

  row += 1;
  addNoteBox(sheet, row, 11, [
    "Read `per_group_summary` for the same information in raw detail.",
    "Read `group_comparison` for all pairwise deltas, not just the largest ones shown here.",
    "Read `disagreement_analysis` for the judge-level score maps and rationale text behind high-disagreement samples.",
  ]);

  sheet.freezePanes.freezeRows(4);
}

function genericSheetSpecs(mode, payload) {
  if (mode === "dataset") {
    return [
      {
        name: "dataset_manifest",
        headers: [
          "theme_id",
          "theme",
          "style_label_zh",
          "game_id",
          "segment_index",
          "sample_id",
          "image_path",
          "is_available",
          "selected",
          "selection_reason",
          "availability_reason",
          "source_manifest_path",
        ],
        rows: payload.dataset_manifest || [],
      },
      {
        name: "theme_summary",
        headers: [
          "theme_id",
          "theme",
          "style_label_zh",
          "game_count",
          "candidate_samples",
          "available_samples",
          "status",
          "notes",
        ],
        rows: payload.theme_summary || [],
      },
      {
        name: "diagnostics",
        headers: ["section", "metric", "value", "notes"],
        rows: payload.diagnostics || [],
      },
      {
        name: "run_metadata",
        headers: ["key", "value"],
        rows: payload.run_metadata || [],
      },
    ];
  }

  return [
    {
      name: "per_group_summary",
      headers: [
        "group_id",
        "group_label",
        "judge_models",
        "judge_count",
        "selected_sample_count",
        "valid_sample_count",
        "full_coverage_sample_count",
        "coverage",
        "partial_coverage_mean",
        "overall_score_mean",
        "semantic_consistency_mean",
        "subject_attribute_consistency_mean",
        "spatial_consistency_mean",
        "style_lighting_consistency_mean",
        "detail_integrity_mean",
        "judge_disagreement_mean",
        "runtime_seconds_total",
      ],
      rows: payload.per_group_summary || [],
    },
    {
      name: "group_comparison",
      headers: [
        "left_group_id",
        "left_group_label",
        "right_group_id",
        "right_group_label",
        "common_sample_count",
        "left_overall_score_mean",
        "right_overall_score_mean",
        "delta_overall_score_mean",
        "left_semantic_consistency_mean",
        "right_semantic_consistency_mean",
        "delta_semantic_consistency_mean",
        "left_subject_attribute_consistency_mean",
        "right_subject_attribute_consistency_mean",
        "delta_subject_attribute_consistency_mean",
        "left_spatial_consistency_mean",
        "right_spatial_consistency_mean",
        "delta_spatial_consistency_mean",
        "left_style_lighting_consistency_mean",
        "right_style_lighting_consistency_mean",
        "delta_style_lighting_consistency_mean",
        "left_detail_integrity_mean",
        "right_detail_integrity_mean",
        "delta_detail_integrity_mean",
        "pairwise_mean_abs_diff",
        "delta_judge_disagreement_mean",
      ],
      rows: payload.group_comparison || [],
    },
    {
      name: "disagreement_analysis",
      headers: [
        "group_id",
        "group_label",
        "theme_id",
        "theme",
        "game_id",
        "segment_index",
        "sample_id",
        "overall_score_mean",
        "judge_disagreement",
        "top_disagreement_dimension",
        "top_dimension_spread",
        "judge_models",
        "judge_score_map_json",
        "judge_reason_map_json",
      ],
      rows: payload.disagreement_analysis || [],
    },
    {
      name: "per_sample_results",
      headers: [
        "group_id",
        "group_label",
        "judge_models",
        "required_judge_count",
        "valid_judge_count",
        "judge_coverage",
        "theme_id",
        "theme",
        "game_id",
        "segment_index",
        "sample_id",
        "image_path",
        "overall_score_mean",
        "semantic_consistency_mean",
        "subject_attribute_consistency_mean",
        "spatial_consistency_mean",
        "style_lighting_consistency_mean",
        "detail_integrity_mean",
        "judge_disagreement",
        "missing_judges",
        "judge_score_map_json",
        "judge_confidence_map_json",
        "judge_reason_map_json",
        "runtime_seconds",
      ],
      rows: payload.per_sample_results || [],
    },
    {
      name: "dataset_manifest",
      headers: [
        "theme_id",
        "theme",
        "style_label_zh",
        "game_id",
        "segment_index",
        "sample_id",
        "image_path",
        "is_available",
        "selected",
        "selection_reason",
        "availability_reason",
        "source_manifest_path",
      ],
      rows: payload.dataset_manifest || [],
    },
    {
      name: "run_metadata",
      headers: ["key", "value"],
      rows: payload.run_metadata || [],
    },
  ];
}

function addGenericTableSheet(workbook, spec) {
  const sheet = workbook.worksheets.add(spec.name);
  const rows = spec.rows || [];
  const headers = spec.headers;
  const matrix = [headers, ...rows.map((row) => headers.map((header) => row[header]))];
  writeMatrix(sheet, 0, 0, matrix, { header: true });
  sheet.freezePanes.freezeRows(1);
}

async function buildWorkbook(mode, payload) {
  const workbook = Workbook.create();
  if (mode === "dataset") {
    addDatasetOverviewSheet(workbook, payload);
  } else {
    addAnalysisOverviewSheet(workbook, payload);
  }

  const specs = genericSheetSpecs(mode, payload);
  for (const spec of specs) {
    addGenericTableSheet(workbook, spec);
  }

  await workbook.inspect({
    kind: "sheet",
    include: "id,name",
    maxChars: 2000,
  });
  await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 50 },
    summary: "formula error scan",
  });

  const sheetNames = ["overview", ...specs.map((spec) => spec.name)];
  for (const sheetName of sheetNames) {
    await workbook.render({
      sheetName,
      autoCrop: "all",
      scale: 1,
      format: "png",
    });
  }

  return workbook;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const mode = args.mode || "analysis";
  if (!args.input || !args.output) {
    throw new Error("Usage: export_evaluator_ablation_workbook.mjs --mode <dataset|analysis> --input <json> --output <xlsx>");
  }

  const inputPath = path.resolve(args.input);
  const outputPath = path.resolve(args.output);
  const payload = JSON.parse(await fs.readFile(inputPath, "utf8"));
  const workbook = await buildWorkbook(mode, payload);

  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const artifact = await SpreadsheetFile.exportXlsx(workbook);
  await artifact.save(outputPath);
  console.log(JSON.stringify({ output: outputPath, mode }));
}

await main();
