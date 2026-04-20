import { Workbook } from '@oai/artifact-tool';
const wb = Workbook.create();
console.log(wb.help('chart', { include: 'examples,notes', maxChars: 4000 }).ndjson);
