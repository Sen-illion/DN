import { Workbook } from '@oai/artifact-tool';
const wb = Workbook.create();
console.log(wb.help('*', { search: 'autofit', include: 'index,examples,notes', maxChars: 4000 }).ndjson);
