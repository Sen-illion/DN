const mod = await import("@oai/artifact-tool");
for (const k of ["buildPresentationLayoutExport","createPresentationLayoutExportBlob","paintRenderedDocumentPage"]) {
  console.log("---"+k+"---");
  console.log(String(mod[k]).slice(0,1200));
}
