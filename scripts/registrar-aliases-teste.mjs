// Resolve os aliases do projeto somente nos testes Node, sem mudar o runtime web.
import { registerHooks } from "node:module";

registerHooks({
  resolve(specifier, context, nextResolve) {
    if (!specifier.startsWith("@/")) return nextResolve(specifier, context);
    return nextResolve(new URL("../" + specifier.slice(2) + ".ts", import.meta.url).href, context);
  },
});
