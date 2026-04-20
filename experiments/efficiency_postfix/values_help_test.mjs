import { Workbook } from '@oai/artifact-tool';
const wb = Workbook.create();
console.log(wb.help('range.values', { include: 'examples,notes', maxChars: 4000 }).ndjson);
