import { Workbook } from '@oai/artifact-tool';
const wb = Workbook.create();
console.log(wb.help('*', { search: 'font fill color number format column width wrap freeze panes', include: 'index,examples,notes', maxChars: 6000 }).ndjson);
