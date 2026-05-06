import { Workbook } from '@oai/artifact-tool';
const wb = Workbook.create();
console.log(wb.help('worksheet.getRange', { include: 'examples,notes,index', maxChars: 3000 }).ndjson);
console.log('---');
console.log(wb.help('chart', { include: 'examples,notes,index', maxChars: 3000 }).ndjson);
console.log('---');
console.log(wb.help('worksheet.freezePanes', { include: 'examples,notes,index', maxChars: 3000 }).ndjson);
