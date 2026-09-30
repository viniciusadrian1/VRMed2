/** Limites compartilhados; a chave e o cliente OpenAI nunca entram neste módulo. */
export const AUDIO_MAX_BYTES = 2 * 1024 * 1024;
export const GRAVACAO_MAX_SEGUNDOS = 60;
export const TRANSCRICAO_MAX_CARACTERES = 2000;
export const CANCELAR_DITADO = "vrmed:cancelar-ditado";
export const FORMATOS_GRAVACAO = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
const EXTENSOES: Record<string, string> = {
  "audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a",
  "audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3",
};
export function formatoAudio(tipo: string) {
  const mime = tipo.split(";")[0].trim().toLowerCase();
  return EXTENSOES[mime] ? { mime, extensao: EXTENSOES[mime] } : null;
}
export function anexarDitado(atual: string, texto: string) {
  return [atual.trim(), texto.trim()].filter(Boolean).join(" ").slice(0, 8000);
}

/** Linhas limitadas: a revisão no livro VR não corta palavras nem esconde o final. */
export function paginasDitado(texto: string, colunas = 42, linhas = 7) {
  const todas: string[] = [];
  let linha = "";
  for (const palavra of texto.trim().split(/\s+/).filter(Boolean)) {
    if (linha && linha.length + palavra.length + 1 > colunas) { todas.push(linha); linha = ""; }
    let resto = palavra;
    while (resto.length > colunas) { todas.push(resto.slice(0, colunas)); resto = resto.slice(colunas); }
    linha = linha ? `${linha} ${resto}` : resto;
  }
  if (linha) todas.push(linha);
  const paginas: string[] = [];
  for (let i = 0; i < todas.length; i += linhas) paginas.push(todas.slice(i, i + linhas).join("\n"));
  return paginas.length ? paginas : [""];
}
