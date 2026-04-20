import { Workbook } from '@oai/artifact-tool';
const wb = Workbook.create();
console.log(wb.help('worksheet.getRange', { include: 'examples,notes', maxChars: 3000 }).ndjson);
