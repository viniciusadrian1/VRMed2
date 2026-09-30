import { AUDIO_MAX_BYTES, FORMATOS_GRAVACAO, GRAVACAO_MAX_SEGUNDOS, formatoAudio } from "./transcricao.ts";

export type FaseDitado = "pronto" | "permissao" | "gravando" | "transcrevendo" | "concluido" | "erro";
export interface EstadoDitado { fase: FaseDitado; segundos: number; mensagem: string }
interface Dependencias {
  obterMicrofone: () => Promise<MediaStream>;
  gravador: (stream: MediaStream) => MediaRecorder;
  enviar: (audio: Blob, signal: AbortSignal) => Promise<string>;
}
let donoMicrofone: object | null = null;
const pronto: EstadoDitado = { fase: "pronto", segundos: 0, mensagem: "" };

/** Controlador testável, independente de DOM/3D. Nunca envia a pergunta ao chat. */
export function criarDitadoTutor(aoTexto: (texto: string) => void, deps: Dependencias = {
  obterMicrofone: () => {
    if (!globalThis.isSecureContext || !navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      throw new Error("Use HTTPS e um navegador com gravação de áudio. A digitação continua disponível.");
    }
    return navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 }, video: false });
  },
  gravador: (stream) => {
    const mimeType = FORMATOS_GRAVACAO.find((tipo) => MediaRecorder.isTypeSupported(tipo));
    if (!mimeType) throw new Error("Este navegador não grava em um formato compatível. Use a digitação.");
    return new MediaRecorder(stream, { mimeType, audioBitsPerSecond: 64_000 });
  },
  enviar: async (audio, signal) => {
    const resposta = await fetch("/api/transcricao", { method: "POST", headers: { "Content-Type": audio.type }, body: audio, signal });
    const dados = await resposta.json().catch(() => null);
    if (!resposta.ok || typeof dados?.texto !== "string") throw new Error(dados?.error || "Não foi possível transcrever. Tente novamente.");
    return dados.texto;
  },
}) {
  const dono = {};
  const ouvintes = new Set<() => void>();
  let estado = pronto, geracao = 0;
  let stream: MediaStream | null = null, gravador: MediaRecorder | null = null;
  let timer: ReturnType<typeof setInterval> | undefined;
  let espera: ReturnType<typeof setTimeout> | undefined;
  let aborto: AbortController | null = null;
  const atualizar = (fase: FaseDitado, mensagem = "", segundos = estado.segundos) => {
    estado = { fase, mensagem, segundos }; ouvintes.forEach((fn) => fn());
  };
  const liberar = () => {
    clearInterval(timer); clearTimeout(espera);
    if (gravador) {
      gravador.ondataavailable = null; gravador.onstop = null; gravador.onerror = null;
      try { if (gravador.state !== "inactive") gravador.stop(); } catch { /* O microfone ainda precisa ser liberado. */ }
    }
    stream?.getTracks().forEach((track) => { track.onended = null; track.stop(); });
    stream = null; gravador = null;
    if (donoMicrofone === dono) donoMicrofone = null;
  };
  const cancelar = () => { geracao++; aborto?.abort(); aborto = null; liberar(); atualizar("pronto", "", 0); };
  const falhar = (mensagem: string) => { cancelar(); atualizar("erro", mensagem, 0); };
  const parar = () => {
    if (estado.fase !== "gravando" || !gravador) return;
    clearInterval(timer);
    atualizar("transcrevendo", "Transcrevendo…");
    try { gravador.stop(); } catch { falhar("Não foi possível finalizar a gravação. Tente novamente."); return; }
    // A captura termina imediatamente, antes da requisição à OpenAI.
    stream?.getTracks().forEach((track) => { track.onended = null; track.stop(); });
  };
  const iniciar = async () => {
    if (["permissao", "gravando", "transcrevendo"].includes(estado.fase)) return;
    if (donoMicrofone && donoMicrofone !== dono) { atualizar("erro", "Já há uma gravação em outro painel."); return; }
    donoMicrofone = dono;
    const id = ++geracao;
    atualizar("permissao", "Autorize o microfone no navegador. No Quest, pode ser necessário sair do VR e autorizar primeiro.", 0);
    try {
      espera = setTimeout(() => { if (id === geracao) falhar("A permissão demorou demais. Autorize o microfone e tente novamente."); }, 30_000);
      const obtido = await deps.obterMicrofone();
      if (id !== geracao) { obtido.getTracks().forEach((track) => track.stop()); return; }
      clearTimeout(espera); stream = obtido;
      gravador = deps.gravador(stream);
      const tipo = gravador.mimeType;
      if (!formatoAudio(tipo)) throw new Error("Formato de gravação incompatível neste navegador.");
      const partes: Blob[] = [];
      let bytes = 0;
      gravador.ondataavailable = (evento) => {
        if (id !== geracao || !evento.data.size) return;
        bytes += evento.data.size;
        if (bytes > AUDIO_MAX_BYTES) { falhar("Gravação muito grande. Tente uma pergunta mais curta."); return; }
        partes.push(evento.data);
      };
      gravador.onerror = () => falhar("A gravação foi interrompida. Verifique o microfone e tente novamente.");
      for (const track of stream.getTracks()) track.onended = () => falhar("O microfone foi desconectado. Grave novamente.");
      gravador.onstop = async () => {
        if (id !== geracao) return;
        const audio = new Blob(partes, { type: tipo });
        liberar();
        if (audio.size < 100) { falhar("Gravação curta demais. Fale a pergunta e tente novamente."); return; }
        atualizar("transcrevendo", "Transcrevendo…");
        const pedido = new AbortController(); aborto = pedido;
        espera = setTimeout(() => { if (id === geracao) falhar("A transcrição demorou demais. Tente novamente."); }, 50_000);
        try {
          const texto = (await deps.enviar(audio, pedido.signal)).trim();
          if (id !== geracao) return;
          if (!texto) throw new Error("Não foi possível identificar uma fala. Tente novamente.");
          aoTexto(texto);
          atualizar("concluido", "Transcrição pronta. Revise o texto antes de enviar.");
        } catch (erro) {
          if (id === geracao) falhar(erro instanceof Error ? erro.message : "Não foi possível transcrever. Tente novamente.");
        } finally { if (id === geracao) { clearTimeout(espera); aborto = null; } }
      };
      gravador.start(1000);
      atualizar("gravando", "Gravando…", 0);
      const inicio = performance.now();
      timer = setInterval(() => {
        if (id !== geracao) return;
        const segundos = Math.min(GRAVACAO_MAX_SEGUNDOS, Math.floor((performance.now() - inicio) / 1000));
        atualizar("gravando", "Gravando…", segundos);
        if (segundos >= GRAVACAO_MAX_SEGUNDOS) parar();
      }, 1000);
    } catch (erro) {
      if (id !== geracao) return;
      const nome = (erro as { name?: string })?.name;
      falhar(nome === "NotAllowedError" ? "Microfone não autorizado. Permita o acesso no navegador e tente novamente."
        : nome === "NotFoundError" ? "Nenhum microfone foi encontrado. Você pode digitar."
        : nome === "NotReadableError" ? "Microfone ocupado ou indisponível. Feche outros aplicativos de voz e tente novamente."
        : erro instanceof Error ? erro.message : "Não foi possível iniciar o microfone.");
    }
  };
  return { iniciar, parar, cancelar, atualizarRetorno: (retorno: (texto: string) => void) => { aoTexto = retorno; },
    getSnapshot: () => estado, subscribe: (fn: () => void) => { ouvintes.add(fn); return () => { ouvintes.delete(fn); }; } };
}
