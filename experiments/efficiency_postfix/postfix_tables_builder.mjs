import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const root = 'C:\\Users\\zhang\\Desktop\\DN\\experiments\\efficiency_postfix';
const tablesDir = path.join(root, 'tables');

function asTable(rows) {
  if (!rows.length) return [[]];
  const headers = Object.keys(rows[0]);
  return [headers, ...rows.map((row) => headers.map((key) => row[key] ?? null))];
}

function roundMaybe(value) {
  return typeof value === 'number' ? Math.round(value * 1000) / 1000 : value;
}

const suite = JSON.parse(await fs.readFile(path.join(root, 'postfix_suite_summary_v3.json'), 'utf8'));
const fullCombined = JSON.parse(await fs.readFile(path.join(root, 'fullchain_default_combined_12themes_summary.json'), 'utf8'));
const worldDefault = JSON.parse(await fs.readFile(path.join(root, 'worldview_default_v2_8themes.json'), 'utf8'));
const worldNo = JSON.parse(await fs.readFile(path.join(root, 'worldview_no_council_v2_8themes.json'), 'utf8'));
const concurrency = JSON.parse(await fs.readFile(path.join(root, 'concurrency_default_v1_6themes_1_3_5.json'), 'utf8'));

const externalRefs = [
  {
    reference_id: 'webarena_2023',
    title: 'WebArena: A Realistic Web Environment for Building Autonomous Agents',
    year: 2023,
    metric: 'GPT-4 success / human success / task count',
    value: '14.41% / 78.24% / 812',
    take_away: 'Great reference for benchmark scale and standardized long-horizon interactive evaluation.',
    url: 'https://arxiv.org/abs/2307.13854',
  },
  {
    reference_id: 'osworld_2024',
    title: 'OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments',
    year: 2024,
    metric: 'Best model success / human success / task count',
    value: '12.24% / 72.36% / 369',
    take_away: 'Shows how hard open-ended computer-use tasks are; useful quality-benchmark reference.',
    url: 'https://arxiv.org/abs/2404.07972',
  },
  {
    reference_id: 'agentbench_2023',
    title: 'AgentBench: Evaluating LLMs as Agents',
    year: 2023,
    metric: 'Benchmark coverage',
    value: '8 environments / 25 LLMs',
    take_away: 'Useful reference for broad multi-environment evaluation design.',
    url: 'https://arxiv.org/abs/2308.03688',
  },
  {
    reference_id: 'devils_advocate_2024',
    title: "Devil's Advocate: Iteration with Self-Feedback in RL for LLM Agents",
    year: 2024,
    metric: 'Efficiency-effectiveness tradeoff',
    value: '23.5% success with 45% fewer trials',
    take_away: 'Strong reference for why DN should report efficiency and effect together, not wall time alone.',
    url: 'https://arxiv.org/abs/2405.16334',
  },
  {
    reference_id: 'chatgpt_survey_2023',
    title: 'Harnessing the Power of LLMs in Practice: A Survey on ChatGPT and Beyond',
    year: 2023,
    metric: 'Single-query latency examples',
    value: '0.077s / 0.203s / 0.707s / 0.355s',
    take_away: 'Useful lower-level latency reference; DN is much slower because it is a multimodal multi-call pipeline.',
    url: 'https://arxiv.org/abs/2304.13712',
  },
];

const worldviewPaired = worldDefault.runs.map((b, idx) => {
  const n = worldNo.runs[idx];
  return {
    theme_id: b.theme_id,
    theme: b.theme,
    default_elapsed_s: roundMaybe(b.elapsed_s),
    no_council_elapsed_s: roundMaybe(n.elapsed_s),
    delta_no_minus_default_s: roundMaybe(n.elapsed_s - b.elapsed_s),
    default_queue_mean_ms: roundMaybe(b.provider_events.queue_wait_ms.mean),
    no_council_queue_mean_ms: roundMaybe(n.provider_events.queue_wait_ms.mean),
    default_status: b.status,
    no_council_status: n.status,
  };
});

const concurrencyRows = concurrency.levels.map((level) => ({
  concurrency: level.concurrency,
  sample_size: level.sample_size,
  wall_elapsed_s: roundMaybe(level.wall_elapsed_s),
  throughput_runs_per_min: roundMaybe(level.throughput_runs_per_min),
  elapsed_mean_s: roundMaybe(level.elapsed_s.mean),
  elapsed_p95_s: roundMaybe(level.elapsed_s.p95),
  queue_mean_ms: roundMaybe(level.provider_events.queue_wait_ms.mean),
  queue_p95_ms: roundMaybe(level.provider_events.queue_wait_ms.p95),
  latency_mean_ms: roundMaybe(level.provider_events.latency_ms.mean),
  latency_p95_ms: roundMaybe(level.provider_events.latency_ms.p95),
}));

const summaryMetrics = [
  {
    block: 'FullChain12',
    metric: 'worldview_mean_s',
    value: fullCombined.worldview_elapsed_s.mean,
  },
  {
    block: 'FullChain12',
    metric: 'worldview_median_s',
    value: fullCombined.worldview_elapsed_s.median,
  },
  {
    block: 'FullChain12',
    metric: 'worldview_p95_s',
    value: fullCombined.worldview_elapsed_s.p95,
  },
  {
    block: 'FullChain12',
    metric: 'generate_option_median_s',
    value: fullCombined.generate_option_elapsed_s.median,
  },
  {
    block: 'FullChain12',
    metric: 'main_character_median_s',
    value: fullCombined.main_character_completion_s.median,
  },
  {
    block: 'WorldviewDefault',
    metric: 'mean_s',
    value: worldDefault.summary.elapsed_s.mean,
  },
  {
    block: 'WorldviewDefault',
    metric: 'p95_s',
    value: worldDefault.summary.elapsed_s.p95,
  },
  {
    block: 'WorldviewNoCouncil',
    metric: 'mean_s',
    value: worldNo.summary.elapsed_s.mean,
  },
  {
    block: 'WorldviewNoCouncil',
    metric: 'p95_s',
    value: worldNo.summary.elapsed_s.p95,
  },
  {
    block: 'Concurrency',
    metric: 'best_throughput_runs_per_min',
    value: concurrencyRows.reduce((best, row) => (row.throughput_runs_per_min > best ? row.throughput_runs_per_min : best), 0),
  },
];

const workbook = Workbook.create();

function writeSheet(name, rows, opts = {}) {
  const sheet = workbook.worksheets.add(name);
  const range = sheet.getRange('A1').write(rows);
  range.format.wrapText = true;
  range.format.autofitColumns();
  range.format.autofitRows();
  if (opts.headerRange) {
    const header = sheet.getRange(opts.headerRange);
    header.format = {
      fill: { type: 'solid', color: '#DCE6F1' },
      font: { bold: true },
      borders: { preset: 'outside', style: 'thin', color: '#B8C2CC' },
    };
  }
  return sheet;
}

const overview = workbook.worksheets.add('Overview');
overview.getRange('A1').write([
  ['DN Post-Fix Efficiency Tables'],
  ['Generated at', new Date().toISOString()],
  ['Data scope', 'Only post-fix results; old phase1 data invalidated'],
]);
overview.getRange('A1:B3').format = {
  wrapText: true,
  borders: { preset: 'outside', style: 'thin', color: '#B8C2CC' },
};
overview.getRange('A1:A1').format.font = { bold: true, size: 16 };

overview.getRange('A5').write([
  ['Section', 'Metric', 'Value', 'Interpretation'],
  ['FullChain12', 'Worldview median', fullCombined.worldview_elapsed_s.median, 'Typical worldview delay under default config'],
  ['FullChain12', 'Worldview p95', fullCombined.worldview_elapsed_s.p95, 'Long-tail worldview delay'],
  ['FullChain12', 'Generate-option median', fullCombined.generate_option_elapsed_s.median, 'Cache/pregeneration hit path is usually fast'],
  ['FullChain12', 'Main-character median', fullCombined.main_character_completion_s.median, 'Async protagonist image completion remains a key slow segment'],
  ['Worldview A/B', 'Default mean', worldDefault.summary.elapsed_s.mean, 'Default average worldview latency over 8 themes'],
  ['Worldview A/B', 'No-council mean', worldNo.summary.elapsed_s.mean, 'No-council average worldview latency over same 8 themes'],
  ['Concurrency', 'Best throughput', concurrencyRows[1].throughput_runs_per_min, 'Observed at concurrency 3 in this run'],
  ['Concurrency', 'Queue mean at concurrency 5', concurrencyRows[2].queue_mean_ms, 'Queue amplification appears beyond concurrency 3'],
]);
overview.getRange('A5:D13').format.wrapText = true;
overview.getRange('A5:D13').format.autofitColumns();
overview.getRange('A5:D13').format.autofitRows();
overview.getRange('A5:D5').format = {
  fill: { type: 'solid', color: '#DCE6F1' },
  font: { bold: true },
};

overview.charts.add('bar', {
  title: 'Worldview Latency: Default vs No Council',
  categories: ['Default mean', 'Default p95', 'No-council mean', 'No-council p95'],
  series: [
    {
      name: 'Seconds',
      values: [
        worldDefault.summary.elapsed_s.mean,
        worldDefault.summary.elapsed_s.p95,
        worldNo.summary.elapsed_s.mean,
        worldNo.summary.elapsed_s.p95,
      ],
    },
  ],
  hasLegend: false,
  barOptions: { direction: 'column', grouping: 'clustered', gapWidth: 80 },
  from: { row: 1, col: 5 },
  extent: { widthPx: 420, heightPx: 260 },
});

overview.charts.add('bar', {
  title: 'Throughput by Concurrency',
  categories: concurrencyRows.map((row) => String(row.concurrency)),
  series: [{ name: 'Runs / min', values: concurrencyRows.map((row) => row.throughput_runs_per_min) }],
  hasLegend: false,
  barOptions: { direction: 'column', grouping: 'clustered', gapWidth: 80 },
  from: { row: 16, col: 0 },
  extent: { widthPx: 360, heightPx: 240 },
});

overview.charts.add('bar', {
  title: 'Queue Mean by Concurrency',
  categories: concurrencyRows.map((row) => String(row.concurrency)),
  series: [{ name: 'Queue mean ms', values: concurrencyRows.map((row) => row.queue_mean_ms) }],
  hasLegend: false,
  barOptions: { direction: 'column', grouping: 'clustered', gapWidth: 80 },
  from: { row: 16, col: 5 },
  extent: { widthPx: 360, heightPx: 240 },
});

overview.getRange('A1:J30').format.autofitColumns();
overview.getRange('A1:J30').format.autofitRows();

writeSheet('SummaryMetrics', asTable(summaryMetrics), { headerRange: 'A1:C1' });
writeSheet('FullChain12', asTable(fullCombined.runs), { headerRange: 'A1:I1' });
writeSheet('WorldviewAB', asTable(worldviewPaired), { headerRange: 'A1:I1' });
writeSheet('Concurrency', asTable(concurrencyRows), { headerRange: 'A1:J1' });
writeSheet('ExternalRefs', asTable(externalRefs), { headerRange: 'A1:F1' });

const inspect1 = await workbook.inspect({
  kind: 'table',
  range: 'Overview!A1:D13',
  include: 'values,formulas',
  tableMaxRows: 20,
  tableMaxCols: 6,
});
console.log(inspect1.ndjson);

const inspect2 = await workbook.inspect({
  kind: 'table',
  range: 'FullChain12!A1:I14',
  include: 'values,formulas',
  tableMaxRows: 14,
  tableMaxCols: 10,
});
console.log(inspect2.ndjson);

const render = await workbook.render({ sheetName: 'Overview', range: 'A1:J30', scale: 1.2 });
console.log(`Rendered Overview bytes=${render?.data?.length ?? 0}`);

await fs.mkdir(tablesDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
const outPath = path.join(tablesDir, 'postfix_experiment_tables.xlsx');
await output.save(outPath);
console.log(outPath);
