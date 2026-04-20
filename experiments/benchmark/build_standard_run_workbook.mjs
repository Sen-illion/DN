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

const summaryRows = await readCsv(path.join(outputsDir, 'benchmark_v1_summary_metrics.csv'));
const abRows = await readCsv(path.join(outputsDir, 'benchmark_v1_worldview_ab_20.csv'));
const fullRows = await readCsv(path.join(outputsDir, 'benchmark_v1_fullchain_20.csv'));
const refRows = await readCsv('C:\\Users\\zhang\\Desktop\\DN\\experiments\\efficiency_postfix\\tables\\external_reference_papers.csv');

const wb = Workbook.create();
const overview = wb.worksheets.add('Overview');
overview.getRange('A1').write([
  ['DN Benchmark-v1 Standard Run Summary'],
  ['Scope', 'Benchmark v1 fixed-task runs: worldview default 20, worldview no_council 20, full-chain default 20'],
  ['Interpretation note', 'These runs were executed in real time against live providers, so configuration effects may still mix with provider load variance.'],
]);
overview.getRange('A1:B3').format = { wrapText: true, borders: { preset: 'outside', style: 'thin', color: '#B8C2CC' } };
overview.getRange('A1:A1').format.font = { bold: true, size: 16 };

overview.getRange('A6').write([
  ['Block', 'Metric', 'Value', 'Comment'],
  ['Worldview default 20', 'Mean (s)', 33.657, 'Current default batch on benchmark v1'],
  ['Worldview default 20', 'Median (s)', 23.664, 'Typical single-run latency in this batch'],
  ['Worldview no_council 20', 'Mean (s)', 20.031, 'This batch was faster than default'],
  ['Worldview no_council 20', 'Median (s)', 14.938, 'Suggests no_council can be better under some windows'],
  ['Full-chain default 20', 'Worldview median (s)', 9.003, 'Typical full-chain worldview startup'],
  ['Full-chain default 20', 'Generate-option median (s)', 0.022, 'Pregeneration/cached path still strong'],
  ['Full-chain default 20', 'Main-character median (s)', 56.546, 'Main-character image remains a visible async segment'],
  ['Full-chain default 20', 'Full success rate', 1.0, 'All 20 runs completed end-to-end'],
]);
styleHeader(overview, 'A6:D6');
overview.getRange('A1:J25').format.autofitColumns();
overview.getRange('A1:J25').format.autofitRows();

overview.charts.add('bar', {
  title: 'Worldview Default vs No Council (Benchmark v1, n=20)',
  categories: ['Default mean', 'Default p95', 'No-council mean', 'No-council p95'],
  series: [{ name: 'Seconds', values: [33.657, 68.872, 20.031, 44.556] }],
  hasLegend: false,
  barOptions: { direction: 'column', grouping: 'clustered', gapWidth: 70 },
  from: { row: 1, col: 5 },
  extent: { widthPx: 420, heightPx: 250 },
});

overview.charts.add('bar', {
  title: 'Full-chain Core Metrics (Benchmark v1, n=20)',
  categories: ['Worldview median', 'Generate-option median', 'Main-character median'],
  series: [{ name: 'Seconds', values: [9.003, 0.022, 56.546] }],
  hasLegend: false,
  barOptions: { direction: 'column', grouping: 'clustered', gapWidth: 70 },
  from: { row: 14, col: 5 },
  extent: { widthPx: 420, heightPx: 230 },
});

writeSheet(wb, 'SummaryMetrics', asTable(summaryRows), 'A1:C1');
writeSheet(wb, 'WorldviewAB20', asTable(abRows), 'A1:I1');
writeSheet(wb, 'FullChain20', asTable(fullRows), 'A1:L1');
writeSheet(wb, 'ReferencePapers', asTable(refRows), 'A1:H1');

const inspect = await wb.inspect({
  kind: 'table',
  range: 'Overview!A1:D14',
  include: 'values,formulas',
  tableMaxRows: 20,
  tableMaxCols: 6,
});
console.log(inspect.ndjson);

await fs.mkdir(outputsDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(wb);
const outPath = path.join(outputsDir, 'benchmark_v1_standard_run_summary.xlsx');
await output.save(outPath);
console.log(outPath);
