const { PresentationFile } = await import("@oai/artifact-tool");
console.log(Object.getOwnPropertyNames(PresentationFile).sort().join("\n"));
