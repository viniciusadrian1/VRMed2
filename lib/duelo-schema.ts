import { z } from "zod";
import { TOTAL_RODADAS } from "./duelo-salas.ts";
import { conhecimentoValido, MODELOS_DUELO } from "./duelo-perguntas.ts";

const texto = z.string().min(1).max(80);
export const rodadasSchema = z.array(z.object({
  tipo: z.enum(["orgao", "estrutura", "conhecimento"]),
  pontos: z.union([z.literal(100), z.literal(200)]),
  alvo: texto, opcoes: z.array(texto).length(4),
  modelo: z.string().max(120).optional(),
  marcador: z.tuple([z.number().finite(), z.number().finite(), z.number().finite()]).optional(),
  perguntaId: texto.optional(), pergunta: texto.optional(), explicacao: z.string().max(160).optional(),
})).length(TOTAL_RODADAS).refine((lista) => lista.every((r, i) =>
  r.pontos === (i % 2 ? 200 : 100) && r.opcoes.includes(r.alvo) && new Set(r.opcoes).size === 4 &&
  (r.tipo === "conhecimento" ? conhecimentoValido(r) :
    r.tipo === "estrutura" ? r.pontos === 200 && Boolean(r.marcador) :
      r.pontos === 100 && MODELOS_DUELO.some((m) => m.caminho === r.modelo))), "Rodadas inválidas.");
