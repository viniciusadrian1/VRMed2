# Fases 24 e 25 — o universo de 16 fechado, auditado e congelado

**Data:** 2026-09-06
**Estado:** ambas concluídas · todos os portões passaram · **freeze executado**
**Resultado:** `VRMED-ESOPHAGUS-POOL16-V1` — **TRAIN 10 · VALIDATION 6 · TEST 0**

Relatórios completos: [Fase 24](RELATORIO-FASE24-POOL-16.md) ·
[Fase 25](RELATORIO-FASE25-CONGELAMENTO.md)

**Nenhuma das duas fases treinou, mediu Dice, rodou benchmark, tocou no TEST, alterou a
`ESOPHAGUS_ONTOLOGY_V1` ou recalculou métrica histórica.**

---

## O resumo em uma tela

| | Fase 24 | Fase 25 |
|---|---|---|
| objetivo | fechar e auditar o universo de 16 | congelar TRAIN/VALIDATION |
| entrada | 5 casos auditados (Fase 23) | 16 casos auditados |
| saída | `FASE24-POOL-16.json` | `VRMED-ESOFAGO-MANIFESTO-V1.jsonl` + snapshot |
| portões | 4/4 | 6/6 |
| achado com maior consequência | a regra de seleção de série **não era reproduzível** | a desidentificação **é declarada em fonte primária** — corrige a Fase 24 |

---

## Os três achados que mudaram alguma coisa

**1. A Fase 23 tinha uma regra de seleção não reproduzível, e a Fase 24 achou antes do freeze.**
O `<` estrito em `aquisicao.py` deixava a **ordem de iteração** decidir empates de tamanho — e há
empates reais (o sujeito 107 tem 10 candidatos com exatamente 43,158 MB). Corrigido com desempate
total por `(ct_mb, ct_uid)`. A regra nova **reproduz as 5 seleções da Fase 23 campo a campo**, então
a regra 14 está preservada — e isso foi **verificado, não assumido**, com autoteste que falha se
deixar de ser verdade.

**2. A Fase 25 corrigiu uma conclusão da Fase 24 sobre desidentificação.**
A Fase 24 concluiu *"método de desidentificação UNKNOWN"* porque só olhou as tags de PHI. As tags do
**grupo 0012** contam outra história: `PatientIdentityRemoved = YES`,
`DeidentificationMethod = Per DICOM PS 3.15 AnnexE` e um `CodeSequence` com sete opções nomeadas,
em 16/16. A correção está registrada como **adendo** ao relatório da Fase 24, com o texto original
preservado (regra 16).
**O que não mudou:** o projeto continua **não declarando o dataset anonimizado** — declaração do
produtor é evidência do que ele afirma ter feito, não verificação independente (regra 13).

**3. O hash de bytes do manifesto não serve como identidade do congelamento.**
O arquivo saiu com CRLF no Windows. O hash que vale é o do **conteúdo canônico**
(`9388c736…82632192`), que sobrevive a um checkout no Mac. Este projeto trabalha em duas máquinas;
citar o hash de bytes teria produzido uma divergência sem que nada tivesse mudado.

---

## O que ficou congelado

```
VRMED-ESOPHAGUS-POOL16-V1        carimbo 2026-09-06T00:00:00Z (parâmetro, não relógio)
esquema   VRMED-ESOPHAGUS-DATASET-V1   22 campos · 16/16 válidas · 0 erros
regra     VRMED-SPLIT-RULE-V1          sha256(case_id) mod 100 < 25 → validation
semente   não há — a regra não sorteia
banda     [2, 8] declarada ANTES → 6 → DENTRO

TRAIN 10   VALIDATION 6   TEST 0
sha256_manifesto  9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192
```

**VALIDATION saiu com 37,5 %, e o alvo era 25 %.** Está dentro da banda declarada e **não foi
ajustado**: mexer no limiar até sair um número bonito seria escolher o split depois de ver o split.

---

## TEST: vazio por decisão, e protegido por exceção

| Contexto | Lê `test`? |
|---|---|
| `treino` | **BLOQUEADO** (`AcessoIndevido`) |
| `validacao` | **BLOQUEADO** |
| `avaliacao` | aberto |
| controle negativo — `treino` lê `train` | **10 casos**, como deve |

Dois dos 13 mutantes atacam exatamente esta proteção (*"treino passa a poder ler test"*,
*"validação passa a poder ler test"*) e **ambos morreram**.

**Enquanto o TEST estiver vazio, não existe número de desempenho publicável.** Enchê-lo com casos
deste mesmo pool tornaria a avaliação dependente da mesma fonte, do mesmo TPS e do mesmo processo de
contorno; enchê-lo com LCTSC, LyNoS, NSCLC-Radiomics ou SegTHOR está proibido pela regra desta
execução.

---

## Instrumentação

| | |
|---|---|
| mutantes | **13/13 mortos**, com controle negativo antes e depois |
| arquivos de teste | **60/60** (`geometria` 10 · `controles_positivos` 8 · `ontologia_esofago` 13 · `baseline_v1` 18 · **`fase25_congelamento` 11**) |
| autotestes de módulo | **168/168**, 0 falhas, em 12 módulos |

O arquivo de teste novo não testa código: testa o **artefato congelado**. Ele cai se alguém trocar
um split, editar um caso, encostar no TEST ou alterar o manifesto sem subir a versão.

---

## O que continua UNKNOWN, e continua assim

| Campo | Por quê |
|---|---|
| `institution` | `InstitutionName` **removida na origem** |
| `annotation_protocol` | a fonte não declara protocolo de contorno |
| `annotation_date_known` = `False` | datas **existem mas foram deslocadas** (`Retain Longitudinal With Modified Dates`) |
| independência de **LyNoS** | **INCONCLUSIVA por construção** — NIfTI sem UIDs. *Nunca* "sem overlap" |
| conformidade da desidentificação | declarada pela fonte, **não verificada** por este projeto |

*"NÃO DETECTADO" é o resultado do instrumento, não uma afirmação de independência.*

---

## Limitações que acompanham este congelamento

1. **n = 16.** Pool pequeno; qualquer estimativa terá intervalo largo.
2. **Anotação `SEMIAUTOMATIC` em 16/16** — não é GT humano puro, e a regra 12 proíbe chamá-la assim.
3. **TEST = 0** — não há conjunto de avaliação independente.
4. **Extensão longitudinal herdada do GT**, não avaliável anatomicamente pela ontologia.
5. **Fase respiratória heterogênea** (`c00`×12, `c80`×2, `c10`×1, `c40`×1), consequência de escolher
   a menor série por sujeito. Registrada, não corrigida.

---

## Incidentes de processo, ambos registrados

| # | O que aconteceu | Correção |
|---|---|---|
| 1 | a Fase 24 sobrescreveu dois artefatos históricos da Fase 23 | conteúdo movido para `phase24/`, originais **restaurados** |
| 2 | a re-execução dos mutantes sobrescreveu `phase21/mutacao.json` | original **restaurado**; `mutacao.py` ganhou `--saida`, padrão inalterado |

A segunda ocorrência mostrou que o problema não era descuido pontual: fases novas reescrevendo
artefato de fase antiga é um padrão. Por isso a correção foi no **parâmetro**, não na cópia manual.

---

## Próximo passo, e o que ele NÃO é

O pool está congelado e auditado. O passo seguinte **não é treinar**: é decidir, com evidência, de
onde virá um **TEST independente** — e "independente" precisa ser demonstrado, não presumido.
Nenhum dos datasets já usados serve, e *"leakage não demonstrado"* nunca é *"independência
demonstrada"*.
