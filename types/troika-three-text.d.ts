/**
 * O pacote `troika-three-text` (dependência do <Text> do drei) não publica
 * tipos. Declaramos apenas o que usamos: a pré-carga do atlas de glifos.
 */
declare module "troika-three-text" {
  export function preloadFont(
    options: { font?: string; characters?: string | string[]; sdfGlyphSize?: number },
    callback: () => void,
  ): void;
}
