const mod = await import("@oai/artifact-tool");
console.log(JSON.stringify(Object.keys(mod).filter(k => /Presentation|render|export|png|pdf|Pptx|File/i.test(k)).sort(), null, 2));
