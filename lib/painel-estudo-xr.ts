/** Medidas em metros. A faixa central fica livre para a anatomia. */
export const PAINEIS_XR = {
  largura: 1.04, altura: 1.12, lateral: 0.95, distancia: 1.12, abaixoDosOlhos: 0.12,
  inclinacao: 0.55, alturaBotao: 0.065, camadasPorPagina: 3,
} as const;

export const TECLAS_XR = ["qwertyuiop", "asdfghjklç", "zxcvbnm,.?", "áéíóúãõâêô", "1234567890"];
export const CORES_XR = [
  { nome: "Original", cor: null }, { nome: "Azul", cor: "#5896c8" },
  { nome: "Âmbar", cor: "#ffc166" }, { nome: "Verde", cor: "#71e0b2" },
  { nome: "Coral", cor: "#ed8a7b" },
];

export function limitar(valor: number, min: number, max: number) {
  return Math.min(max, Math.max(min, Math.round(valor * 100) / 100));
}

/** Paginação por linhas, não por pixels ou rolagem: preserva todo o texto. */
export function paginasXR(texto: string, colunas = 30, linhas = 6): string[] {
  const palavras = texto.replace(/\s+/g, " ").trim().split(" ").filter(Boolean);
  const resultado: string[] = [];
  let linha = "", pagina: string[] = [];
  const guardar = () => {
    pagina.push(linha); linha = "";
    if (pagina.length === linhas) { resultado.push(pagina.join("\n")); pagina = []; }
  };
  for (const palavra of palavras) {
    // Palavras excepcionalmente longas também cabem sem sair do painel.
    for (let inicio = 0; inicio < palavra.length; inicio += colunas) {
      const parte = palavra.slice(inicio, inicio + colunas);
      if (linha && linha.length + parte.length + 1 > colunas) guardar();
      linha += (linha ? " " : "") + parte;
    }
  }
  if (linha) guardar();
  if (pagina.length) resultado.push(pagina.join("\n"));
  return resultado.length ? resultado : [""];
}

export function editarTextoXR(texto: string, tecla: string, limite = 500) {
  if (tecla === "Apagar") return [...texto].slice(0, -1).join("");
  if (tecla === "Espaço") return (texto + " ").slice(0, limite);
  if (tecla === "Limpar") return "";
  return (texto + tecla).slice(0, limite);
}
