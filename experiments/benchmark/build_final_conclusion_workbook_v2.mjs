import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const outputsDir = 'C:\\Users\\zhang\\Desktop\\DN\\experiments\\benchmark\\outputs';

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
        out.push(cur); cur = '';
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
    headers.forEach((h, idx) => { row[h] = vals[idx] ?? ''; });
    return row;
  });
}

function asTable(rows) {
  if (!rows.length) return [[]];
  const headers = Object.keys(rows[0]);
  return [headers, ...rows.map((row) => headers.map((key) => row[key] ?? null))];
}

function styleHeader(sheet, rangeAddress, color = '#DCE6F1') {
  sheet.getRange(rangeAddress).format = {
    fill: { type: 'solid', color },
    font: { bold: true },
    borders: { preset: 'outside', style: 'thin', color: '#B8C2CC' },
    wrapText: true,
  };
}

function writeSheet(workbook, name, rows, headerRange, color) {
  const sheet = workbook.worksheets.add(name);
  sheet.getRange('A1').write(rows).format = { wrapText: true };
  sheet.getRange('A1:Z400').format.autofitColumns();
  sheet.getRange('A1:Z400').format.autofitRows();
  if (headerRange) styleHeader(sheet, headerRange, color);
  return sheet;
}

const execRows = await readCsv(path.join(outputsDir, 'dn_current_best_executive_metrics_v2.csv'));
const stableRows = await readCsv(path.join(outputsDir, 'dn_current_best_stable_conclusions_v2.csv'));
const pendingRows = await readCsv(path.join(outputsDir, 'dn_current_best_pending_conclusions_v2.csv'));
const fullABRows = await readCsv(path.join(outputsDir, 'benchmark_v1_fullchain_ab_20.csv'));

const wb = Workbook.create();
const overview = wb.worksheets.add('Overview');
overview.getRange('A1').write([
  ['DN Current Best Conclusions v2'],
  ['Worldview conclusion', 'No-council remains a stable speedup for worldview generation after repeat validation.'],
  ['Full-chain conclusion', 'That single-stage speedup does not carry over to better full-chain performance; default remains the safer end-to-end baseline.'],
  ['Key engineering takeaway', 'Do not replace the full-chain default config with no_council yet; treat it as a local worldview optimization candidate.'],
]);
overview.getRange('A1:B4').format = { wrapText: true, borders: { preset: 'outside', style: 'thin', color: '#B8C2CC' } };
overview.getRange('A1:A1').format.font = { bold: true, size: 16 };

overview.getRange('A7').write([
  ['Metric', 'Default', 'No-council'],
  ['Worldview combined mean (40 runs)', 37.832, 20.244],
  ['Worldview combined median (40 runs)', 30.002, 16.046],
  ['Worldview combined p95 (40 runs)', 81.879, 40.133],
  ['Full-chain worldview median (20 runs)', 9.003, 13.799],
  ['Full-chain success rate', 1.0, 0.95],
]);
styleHeader(overview, 'A7:C7');

overview.charts.add('bar', {
  title: 'Worldview Repeat-Validated Comparison',
  categories: ['Mean', 'Median', 'P95'],
  series: [
    { name: 'Default', values: [37.832, 30.002, 81.879] },
    { name: 'No-council', values: [20.244, 16.046, 40.133] },
  ],
  hasLegend: true,
  legend: { position: 'top' },
  barOptions: { direction: 'column', grouping: 'clustered', gapWidth: 70 },
  from: { row: 1, col: 5 },
  extent: { widthPx: 460, heightPx: 240 },
});

overview.charts.add('bar', {
  title: 'Full-chain End-to-End Comparison',
  categories: ['Worldview median', 'Generate-option median', 'Main-character median', 'Success rate'],
  series: [
    { name: 'Default', values: [9.003, 0.022, 56.546, 1.0] },
    { name: 'No-council', values: [13.799, 0.026, 48.452, 0.95] },
  ],
  hasLegend: true,
  legend: { position: 'top' },
  barOptions: { direction: 'column', grouping: 'clustered', gapWidth: 70 },
  from: { row: 14, col: 5 },
  extent: { widthPx: 460, heightPx: 260 },
});

overview.getRange('A1:J28').format.autofitColumns();
overview.getRange('A1:J28').format.autofitRows();

writeSheet(wb, 'ExecutiveMetrics', asTable(execRows), 'A1:C1', '#DCE6F1');
writeSheet(wb, 'StableConclusions', asTable(stableRows), 'A1:E1', '#E2F0D9');
writeSheet(wb, 'PendingConclusions', asTable(pendingRows), 'A1:D1', '#FCE4D6');
writeSheet(wb, 'FullChainAB20', asTable(fullABRows), 'A1:L1', '#DCE6F1');

const inspect = await wb.inspect({
  kind: 'table',
  range: 'Overview!A1:C12',
  include: 'values,formulas',
  tableMaxRows: 15,
  tableMaxCols: 5,
});
console.log(inspect.ndjson);

const output = await SpreadsheetFile.exportXlsx(wb);
const outPath = path.join(outputsDir, 'dn_current_best_conclusions_v2.xlsx');
await output.save(outPath);
console.log(outPath);
