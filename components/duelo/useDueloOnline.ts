"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  VERSAO_PROTOCOLO,
  type RodadaOnline,
  type VisaoSala,
} from "@/lib/duelo-salas";

export type ConexaoDuelo = "fora" | "conectando" | "conectado" | "reconectando" | "perdida";

type Ouvinte = (visao: VisaoSala, recebidoEm: number) => void;

export interface DueloOnline {
  /** Código da sala em que este óculos está (null = jogando contra bot). */
  sala: string | null;
  conexao: ConexaoDuelo;
  erro: string | null;
  /** Recebe cada atualização da sala; chama já com a última, se houver. */
  assinar: (ouvinte: Ouvinte) => () => void;
  criar: (rodadas: RodadaOnline[]) => void;
  entrar: (codigo: string) => void;
  responder: (
    indice: number,
    opcao: string,
    reacaoMs: number,
  ) => Promise<"certo" | "errado" | "tarde" | "falhou">;
  revanche: (rodadas: RodadaOnline[]) => void;
  sair: () => void;
  limparErro: () => void;
}

function novoId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `j-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

async function enviar(corpo: object): Promise<{ ok: boolean; dados: Record<string, unknown> }> {
  try {
    const resposta = await fetch("/api/duelo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ v: VERSAO_PROTOCOLO, ...corpo }),
    });
    const dados = (await resposta.json().catch(() => ({}))) as Record<string, unknown>;
    return { ok: resposta.ok, dados };
  } catch {
    return { ok: false, dados: { erro: "Sem conexão com o servidor. Confira o Wi-Fi." } };
  }
}

/**
 * Conexão do óculos com o duelo online.
 *
 * Mora no `DueloApp`, FORA do `<Canvas>`: a conexão pertence à página, não à
 * cena 3D, e nada que aconteça dentro do canvas pode derrubar a partida.
 *
 * Sair da página (inclusive pelo botão "Sair do VR", que troca de página) é
 * sair do duelo: o adversário é avisado na hora, sem esperar o limite de
 * abandono.
 */
export function useDueloOnline(): DueloOnline {
  const [sala, setSala] = useState<string | null>(null);
  const [conexao, setConexao] = useState<ConexaoDuelo>("fora");
  const [erro, setErro] = useState<string | null>(null);

  const jogador = useRef<string | null>(null);
  const meuId = () => (jogador.current ??= novoId());
  const ouvintes = useRef(new Set<Ouvinte>());
  const ultima = useRef<{ visao: VisaoSala; recebidoEm: number } | null>(null);
  /** Número do pedido de criar/entrar em voo; `sair` o invalida. */
  const pedido = useRef(0);
  /** Reabre a conexão quando o navegador desiste dela (ver `onerror`). */
  const [tentativa, setTentativa] = useState(0);
  const falhasSeguidas = useRef(0);
  const saidaPendente = useRef<{ sala: string; timer: ReturnType<typeof setTimeout> } | null>(
    null,
  );
  /** Sala da qual `sair()` já avisou o servidor: a desmontagem não repete. */
  const saidaAvisada = useRef<string | null>(null);

  useEffect(() => {
    if (!sala) return;
    const id = jogador.current;
    if (!id) return;
    // Remontagem com a mesma sala (StrictMode no dev, nova tentativa de
    // conexão) não é saída: cancela o aviso agendado pela desmontagem.
    if (saidaPendente.current?.sala === sala) {
      clearTimeout(saidaPendente.current.timer);
      saidaPendente.current = null;
    }

    const avisarSaida = () => {
      navigator.sendBeacon(
        "/api/duelo",
        new Blob(
          [JSON.stringify({ v: VERSAO_PROTOCOLO, acao: "sair", jogador: id, sala })],
          { type: "application/json" },
        ),
      );
    };

    const fonte = new EventSource(
      `/api/duelo?sala=${encodeURIComponent(sala)}&jogador=${encodeURIComponent(id)}`,
    );
    let reabrir: ReturnType<typeof setTimeout> | undefined;
    fonte.onmessage = (evento) => {
      const visao = JSON.parse(evento.data) as VisaoSala;
      const recebidoEm = performance.now();
      falhasSeguidas.current = 0;
      ultima.current = { visao, recebidoEm };
      setConexao("conectado");
      for (const ouvinte of ouvintes.current) ouvinte(visao, recebidoEm);
    };
    fonte.onerror = () => {
      if (fonte.readyState !== EventSource.CLOSED) {
        setConexao("reconectando");
        return;
      }
      // CLOSED: o navegador desiste com QUALQUER resposta que não seja 200 —
      // sala apagada, mas também um 502 passageiro do proxy. Tenta de novo
      // algumas vezes antes de dar a partida por perdida.
      falhasSeguidas.current += 1;
      if (falhasSeguidas.current > 4) {
        setConexao("perdida");
        return;
      }
      setConexao("reconectando");
      reabrir = setTimeout(() => setTentativa((t) => t + 1), 2000);
    };
    window.addEventListener("pagehide", avisarSaida);

    return () => {
      clearTimeout(reabrir);
      window.removeEventListener("pagehide", avisarSaida);
      fonte.close();
      // Sair pela navegação do próprio app (link "VRmed", voltar do
      // navegador) não dispara pagehide: o aviso sai daqui. Adiado um instante
      // para que uma remontagem imediata com a mesma sala o cancele.
      const timer = setTimeout(() => {
        saidaPendente.current = null;
        if (saidaAvisada.current !== sala) avisarSaida();
      }, 0);
      saidaPendente.current = { sala, timer };
    };
  }, [sala, tentativa]);

  const assinar = useCallback((ouvinte: Ouvinte) => {
    ouvintes.current.add(ouvinte);
    if (ultima.current) ouvinte(ultima.current.visao, ultima.current.recebidoEm);
    return () => {
      ouvintes.current.delete(ouvinte);
    };
  }, []);

  const entrarNaSala = (codigo: string) => {
    ultima.current = null;
    falhasSeguidas.current = 0;
    setErro(null);
    setSala(codigo);
  };

  /**
   * Criar e entrar: se a pessoa desistiu (Voltar/Cancelar) com o pedido ainda
   * em voo, a resposta que chega depois é ignorada — e, se o servidor chegou a
   * pô-la numa sala, ela sai dela na hora, sem prender o outro jogador.
   */
  const pedirSala = async (corpo: object, erroPadrao: string) => {
    const meu = ++pedido.current;
    setConexao("conectando");
    const { ok, dados } = await enviar(corpo);
    const codigo = ok && typeof dados.sala === "string" ? dados.sala : null;
    if (meu !== pedido.current) {
      if (codigo) void enviar({ acao: "sair", jogador: meuId(), sala: codigo });
      return;
    }
    if (codigo) return entrarNaSala(codigo);
    setConexao("fora");
    setErro(String(dados.erro ?? erroPadrao));
  };

  const criar = (rodadas: RodadaOnline[]) => {
    void pedirSala({ acao: "criar", jogador: meuId(), rodadas }, "Não foi possível criar a sala.");
  };

  const entrar = (codigo: string) => {
    void pedirSala(
      { acao: "entrar", jogador: meuId(), sala: codigo },
      "Não foi possível entrar na sala.",
    );
  };

  const responder = useCallback(
    async (indice: number, opcao: string, reacaoMs: number) => {
      if (!sala) return "falhou" as const;
      const { ok, dados } = await enviar({
        acao: "responder",
        jogador: meuId(),
        sala,
        indice,
        opcao,
        reacaoMs: Math.round(reacaoMs),
      });
      const r = dados.resultado;
      return ok && (r === "certo" || r === "errado" || r === "tarde") ? r : ("falhou" as const);
    },
    [sala],
  );

  const revanche = useCallback(
    (rodadas: RodadaOnline[]) => {
      if (sala) void enviar({ acao: "revanche", jogador: meuId(), sala, rodadas });
    },
    [sala],
  );

  const sair = useCallback(() => {
    pedido.current += 1;
    if (sala) {
      saidaAvisada.current = sala;
      void enviar({ acao: "sair", jogador: meuId(), sala });
    }
    ultima.current = null;
    setSala(null);
    setConexao("fora");
    setErro(null);
  }, [sala]);

  const limparErro = useCallback(() => setErro(null), []);

  return { sala, conexao, erro, assinar, criar, entrar, responder, revanche, sair, limparErro };
}
