import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const root = 'C:\\Users\\zhang\\Desktop\\DN\\experiments\\benchmark';
const outputsDir = path.join(root, 'outputs');

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

const execRows = await readCsv(path.join(outputsDir, 'dn_current_best_executive_metrics_v1.csv'));
const stableRows = await readCsv(path.join(outputsDir, 'dn_current_best_stable_conclusions_v1.csv'));
const pendingRows = await readCsv(path.join(outputsDir, 'dn_current_best_pending_conclusions_v1.csv'));
const abSummary = JSON.parse(await fs.readFile(path.join(outputsDir, 'benchmark_v1_ab_repeat_validation_summary.json'), 'utf8'));
const refRows = await readCsv('C:\\Users\\zhang\\Desktop\\DN\\experiments\\efficiency_postfix\\tables\\external_reference_papers.csv');

const wb = Workbook.create();
const overview = wb.worksheets.add('Overview');
overview.getRange('A1').write([
  ['DN Current Best Conclusions v1'],
  ['Core claim', 'No-council shows a stable efficiency advantage for worldview generation on DN-quality-benchmark-v1 after two repeat runs.'],
  ['Boundary', 'This claim is stable for worldview only; full-chain no_council and quality-side tradeoffs remain unverified.'],
  ['Recommended next step', 'Run full-chain no_council 20 and compare against full-chain default 20 with the same benchmark and rating protocol.'],
]);
overview.getRange('A1:B4').format = { wrapText: true, borders: { preset: 'outside', style: 'thin', color: '#B8C2CC' } };
overview.getRange('A1:A1').format.font = { bold: true, size: 16 };

overview.getRange('A7').write([
  ['Config', 'Mean (s)', 'Median (s)', 'P95 (s)'],
  ['Default combined 40', 37.832, 30.002, 81.879],
  ['No-council combined 40', 20.244, 16.046, 40.133],
]);
styleHeader(overview, 'A7:D7');

overview.getRange('A12').write([
  ['Run', 'Default faster', 'No-council faster', 'Median delta no-default (s)'],
  ['Repeat 1', 3, 17, -7.127],
  ['Repeat 2', 4, 16, -18.117],
]);
styleHeader(overview, 'A12:D12');

overview.charts.add('bar', {
  title: 'Worldview Combined 40: Default vs No-council',
  categories: ['Mean', 'Median', 'P95'],
  series: [
    { name: 'Default', values: [37.832, 30.002, 81.879] },
    { name: 'No-council', values: [20.244, 16.046, 40.133] },
  ],
  hasLegend: true,
  legend: { position: 'top' },
  barOptions: { direction: 'column', grouping: 'clustered', gapWidth: 70 },
  from: { row: 1, col: 5 },
  extent: { widthPx: 460, heightPx: 260 },
});

overview.charts.add('bar', {
  title: 'Pairwise Wins Across Two Repeat Runs',
  categories: ['Repeat 1', 'Repeat 2'],
  series: [
    { name: 'Default faster', values: [3, 4] },
    { name: 'No-council faster', values: [17, 16] },
  ],
  hasLegend: true,
  legend: { position: 'top' },
  barOptions: { direction: 'column', grouping: 'clustered', gapWidth: 70 },
  from: { row: 14, col: 5 },
  extent: { widthPx: 460, heightPx: 240 },
});

overview.getRange('A1:J28').format.autofitColumns();
overview.getRange('A1:J28').format.autofitRows();

writeSheet(wb, 'ExecutiveMetrics', asTable(execRows), 'A1:C1', '#DCE6F1');
writeSheet(wb, 'StableConclusions', asTable(stableRows), 'A1:E1', '#E2F0D9');
writeSheet(wb, 'PendingConclusions', asTable(pendingRows), 'A1:D1', '#FCE4D6');
writeSheet(wb, 'ReferencePapers', asTable(refRows), 'A1:H1', '#DCE6F1');

const inspect = await wb.inspect({
  kind: 'table',
  range: 'Overview!A1:D15',
  include: 'values,formulas',
  tableMaxRows: 20,
  tableMaxCols: 6,
});
console.log(inspect.ndjson);

await fs.mkdir(outputsDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(wb);
const outPath = path.join(outputsDir, 'dn_current_best_conclusions_v1.xlsx');
await output.save(outPath);
console.log(outPath);
