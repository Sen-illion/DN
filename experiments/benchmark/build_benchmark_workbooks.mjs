import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const root = 'C:\\Users\\zhang\\Desktop\\DN\\experiments\\benchmark';
const postfixTables = 'C:\\Users\\zhang\\Desktop\\DN\\experiments\\efficiency_postfix\\tables';
const outputsDir = path.join(root, 'outputs');

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, 'utf8'));
}

async function readCsv(filePath) {
  const text = await fs.readFile(filePath, 'utf8');
  const lines = text.replace(/^\uFEFF/, '').trim().split(/\r?\n/);
  if (!lines.length) return [];
  const parseLine = (line) => {
    const out = [];
    let cur = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i += 1) {
      const ch = line[i];
      if (ch === '"') {
        if (inQuotes && line[i + 1] === '"') {
          cur += '"';
          i += 1;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (ch === ',' && !inQuotes) {
        out.push(cur);
        cur = '';
      } else {
        cur += ch;
      }
    }
    out.push(cur);
    return out;
  };
  const headers = parseLine(lines[0]);
  return lines.slice(1).map((line) => {
    const vals = parseLine(line);
    const row = {};
    headers.forEach((h, idx) => {
      row[h] = vals[idx] ?? '';
    });
    return row;
  });
}

function asTable(rows) {
  if (!rows.length) return [[]];
  const headers = Object.keys(rows[0]);
  return [headers, ...rows.map((row) => headers.map((key) => row[key] ?? null))];
}

function styleHeader(sheet, rangeAddress) {
  sheet.getRange(rangeAddress).format = {
    fill: { type: 'solid', color: '#DCE6F1' },
    font: { bold: true },
    borders: { preset: 'outside', style: 'thin', color: '#B8C2CC' },
    wrapText: true,
  };
}

function writeSheet(workbook, name, rows, headerRange) {
  const sheet = workbook.worksheets.add(name);
  sheet.getRange('A1').write(rows).format = { wrapText: true };
  sheet.getRange('A1:Z400').format.autofitColumns();
  sheet.getRange('A1:Z400').format.autofitRows();
  if (headerRange) styleHeader(sheet, headerRange);
  return sheet;
}

const benchmarkJson = await readJson(path.join(root, 'dn_quality_benchmark_v1.json'));
const benchmarkRows = await readCsv(path.join(root, 'dn_quality_benchmark_v1_flat.csv'));
const ratingRows = await readCsv(path.join(root, 'dn_human_rating_template_v1.csv'));
const proxySummaryRows = await readCsv(path.join(outputsDir, 'effectiveness_proxies_summary.csv'));
const proxyFullRows = await readCsv(path.join(outputsDir, 'effectiveness_proxies_fullchain_12.csv'));
const proxyWorldviewRows = await readCsv(path.join(outputsDir, 'effectiveness_proxies_worldview_16.csv'));
const extRefRows = await readCsv(path.join(postfixTables, 'external_reference_papers.csv'));

// Rating template workbook
const ratingWb = Workbook.create();
const rubric = ratingWb.worksheets.add('Rubric');
rubric.getRange('A1').write([
  ['DN Human Rating Template v1'],
  ['Use case', 'Rate a fixed DN benchmark sample after running one specific config.'],
  ['Scoring rule', 'Each 1-5 score uses: 5 excellent, 4 good, 3 usable, 2 weak, 1 unacceptable.'],
  ['Binary flags', 'playable / image_usable / major_error use 1=yes, 0=no.'],
  ['Recommended workflow', 'Two raters independently score the same benchmark rows, then average scores and review disagreements.'],
]);
rubric.getRange('A1:B5').format = { wrapText: true, borders: { preset: 'outside', style: 'thin', color: '#B8C2CC' } };
rubric.getRange('A1:A1').format.font = { bold: true, size: 16 };

rubric.getRange('A8').write([
  ['Field', 'Meaning'],
  ['theme_alignment_1to5', 'How well the output matches the benchmark theme and genre.'],
  ['narrative_coherence_1to5', 'Whether worldview + first scene are readable, consistent, and logically connected.'],
  ['option_actionability_1to5', 'Whether options are specific and can continue the game.'],
  ['visual_consistency_1to5', 'Whether image style and image content match the text.'],
  ['artifact_cleanliness_1to5', 'Whether there are no debug strings, URLs, garbling, or setting contamination.'],
  ['playable_0or1', 'Can a player continue playing from this state?'],
  ['image_usable_0or1', 'Is the returned image usable in a real session?'],
  ['major_error_0or1', 'Does the sample contain a severe quality/system error?'],
]);
styleHeader(rubric, 'A8:B8');
rubric.getRange('A1:B20').format.autofitColumns();
rubric.getRange('A1:B20').format.autofitRows();

writeSheet(ratingWb, 'Benchmark20', asTable(benchmarkRows), 'A1:I1');
writeSheet(ratingWb, 'RatingsBlank', asTable(ratingRows), 'A1:O1');
writeSheet(ratingWb, 'ReferencePapers', asTable(extRefRows), 'A1:H1');

// Unified efficiency + effectiveness workbook
const summaryWb = Workbook.create();
const overview = summaryWb.worksheets.add('Overview');
overview.getRange('A1').write([
  ['DN Efficiency + Effectiveness Summary'],
  ['Benchmark', benchmarkJson.benchmark_name],
  ['Benchmark size', benchmarkJson.sample_size],
  ['Scope', 'Post-fix results only; use this workbook as the standard reporting pack for DN v1 experiments.'],
]);
overview.getRange('A1:B4').format = { wrapText: true, borders: { preset: 'outside', style: 'thin', color: '#B8C2CC' } };
overview.getRange('A1:A1').format.font = { bold: true, size: 16 };

overview.getRange('A7').write([
  ['Category', 'Metric', 'Value', 'Reading'],
  ['Efficiency', 'Full-chain worldview median (s)', 11.6, 'Typical start-up worldview delay'],
  ['Efficiency', 'Full-chain worldview p95 (s)', 120.454, 'Long-tail worldview delay remains large'],
  ['Efficiency', 'Generate-option median (s)', 0.021, 'Cache / pregeneration hit path is very fast'],
  ['Efficiency', 'Main-character median completion (s)', 62.468, 'Main-character image remains a visible async bottleneck'],
  ['Effectiveness proxy', 'Playable / scene success rate', 1.0, 'All 12 post-fix full-chain runs were playable in the current sample'],
  ['Effectiveness proxy', 'Image return rate', 1.0, 'All 12 runs returned an image'],
  ['Effectiveness proxy', 'Fallback trigger rate', 0.0, 'No fallback text was triggered in the current sample'],
  ['A/B', 'Default worldview mean (s)', 22.642, 'Default is the stronger stable baseline in this sample'],
  ['A/B', 'No-council worldview mean (s)', 45.744, 'No-council shows worse long-tail behavior'],
  ['Concurrency', 'Best throughput (runs/min)', 2.782, 'Observed at concurrency 3'],
]);
styleHeader(overview, 'A7:D7');
overview.getRange('A7:D17').format.wrapText = true;
overview.getRange('A1:J30').format.autofitColumns();
overview.getRange('A1:J30').format.autofitRows();

overview.charts.add('bar', {
  title: 'Core Efficiency Metrics',
  categories: ['Worldview median', 'Worldview p95', 'Generate-option median', 'Main-character median'],
  series: [{ name: 'Seconds', values: [11.6, 120.454, 0.021, 62.468] }],
  hasLegend: false,
  barOptions: { direction: 'column', grouping: 'clustered', gapWidth: 70 },
  from: { row: 1, col: 5 },
  extent: { widthPx: 420, heightPx: 250 },
});

overview.charts.add('bar', {
  title: 'Effectiveness Proxy Rates',
  categories: ['Playable', 'Image return', 'Fallback inverse'],
  series: [{ name: 'Rate', values: [1.0, 1.0, 1.0] }],
  hasLegend: false,
  barOptions: { direction: 'column', grouping: 'clustered', gapWidth: 70 },
  from: { row: 14, col: 5 },
  extent: { widthPx: 420, heightPx: 230 },
});

writeSheet(summaryWb, 'Benchmark20', asTable(benchmarkRows), 'A1:I1');
writeSheet(summaryWb, 'ProxySummary', asTable(proxySummaryRows), 'A1:C1');
writeSheet(summaryWb, 'FullChainProxy12', asTable(proxyFullRows), 'A1:T1');
writeSheet(summaryWb, 'WorldviewProxy16', asTable(proxyWorldviewRows), 'A1:H1');
writeSheet(summaryWb, 'ReferencePapers', asTable(extRefRows), 'A1:H1');

const inspectOverview = await summaryWb.inspect({
  kind: 'table',
  range: 'Overview!A1:D17',
  include: 'values,formulas',
  tableMaxRows: 20,
  tableMaxCols: 6,
});
console.log(inspectOverview.ndjson);

await fs.mkdir(outputsDir, { recursive: true });
const ratingOutput = await SpreadsheetFile.exportXlsx(ratingWb);
const ratingPath = path.join(outputsDir, 'dn_human_rating_template_v1.xlsx');
await ratingOutput.save(ratingPath);

const summaryOutput = await SpreadsheetFile.exportXlsx(summaryWb);
const summaryPath = path.join(outputsDir, 'dn_efficiency_effectiveness_summary_v1.xlsx');
await summaryOutput.save(summaryPath);

console.log(ratingPath);
console.log(summaryPath);
