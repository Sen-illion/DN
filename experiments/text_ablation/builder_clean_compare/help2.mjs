import { Workbook } from '@oai/artifact-tool';
const wb = Workbook.create();
console.log(wb.help('worksheet.charts.add', { include: 'examples,notes,index', maxChars: 3000 }).ndjson);
console.log('---');
console.log(wb.help('range.values', { include: 'examples,notes,index', maxChars: 2000 }).ndjson);
console.log('---');
console.log(wb.help('range.format', { include: 'examples,notes,index', maxChars: 3000 }).ndjson);
