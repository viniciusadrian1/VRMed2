import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Assets estáticos e bibliotecas de terceiros (decodificador Draco) — não
    // são código-fonte do projeto e não devem ser verificados pelo linter.
    "public/**",
    // Dataset local de pesquisa clínica; pode conter temporários criados por
    // ferramentas externas com permissões que o ESLint não consegue ler.
    ".clinica-dados/**",
  ]),
]);

export default eslintConfig;
