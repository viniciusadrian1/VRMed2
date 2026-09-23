// Carregamento de TSX exclusivamente nos testes Node; não modifica o runtime web.
import { registerHooks } from "node:module";
import { existsSync, readFileSync, statSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";

registerHooks({
  resolve(specifier, context, nextResolve) {
    const interno = specifier.startsWith("@/") ? new URL("../" + specifier.slice(2), import.meta.url) :
      specifier.startsWith(".") && context.parentURL?.startsWith("file:") ? new URL(specifier, context.parentURL) : null;
    if (interno && !interno.pathname.includes("/node_modules/")) {
      const caminho = fileURLToPath(interno);
      for (const sufixo of ["", ".ts", ".tsx", ".mjs"]) {
        if (existsSync(caminho + sufixo) && statSync(caminho + sufixo).isFile()) return nextResolve(pathToFileURL(caminho + sufixo).href, context);
      }
    }
    return nextResolve(specifier, context);
  },
  load(url, context, nextLoad) {
    if (url.endsWith(".tsx") && !url.includes("/node_modules/")) {
      return { format: "module", shortCircuit: true, source: ts.transpileModule(readFileSync(fileURLToPath(url), "utf8"), {
        compilerOptions: { jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext, esModuleInterop: true },
      }).outputText };
    }
    return nextLoad(url, context);
  },
});
