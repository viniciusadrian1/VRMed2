# RUN-LOG — execução autônoma Fases 13–17

Registro cronológico de comandos, durações, falhas e decisões.
Fatos medidos são marcados **FATO**; deduções, **INFERÊNCIA**; sugestões, **RECOMENDAÇÃO**.

## Setup

- **FATO** commit inicial `a590aa3`, branch `master`, árvore de trabalho limpa.
- **FATO** GPU RTX 4060 Ti 16.380 MiB disponível; `torch.cuda.is_available() = True`.
- **FATO** 170,4 GiB livres em disco; 15,3 GiB de RAM disponíveis; 12 CPUs.
- **FATO** `du -sh .clinica-dados` excedeu 120 s e foi mandado para segundo plano em vez de
  bloquear o pipeline (política de timeout do enunciado).
- **DECISÃO** experimentos novos em `.clinica-dados/overnight/`; nada sobrescreve resultado
  congelado.

## Fase 13 — ESOPHAGUS_ONTOLOGY_V1

- **FATO** ontologia já estava 90% correta: a Fase 9 removera cricoide/JGE por medição.
  O que faltava era documento normativo versionado e mecanismo antirregressão.
- **FATO** 3 linhas qualificadas em `VRMED-ANATOMICAL-ONTOLOGY.md`; zero linhas apagadas.
- **FATO** varredura lexical: 30 documentos, 0 violações.
- **FATO** primeira versão do varredor tinha 2 falsos positivos (linhas que *proibiam* a
  frase) e 1 falso negativo (conjugação "separamos" escapava). Ambos corrigidos.
- **FATO** `digital twin`: banimento total era errado — 3 documentos de análise usam o termo
  corretamente, para contrastar. Regra virou de COMPANHIA (exige `patient-specific` no mesmo
  documento). Termo canônico registrado: `patient-specific 3D model`.
- **FATO** `tests/test_ontologia_esofago.py` — 12/12.
- **DECISÃO** K4 = RESOLVIDO. Não desbloqueia treino sozinho.

## Fase 14 — prontidão para treinamento

- **FATO** 30 testes (10+8+12) e 21 guardas com controle positivo, todos ativos.
  `protocolo_esofago --mutacao`: 10/10 guardas derrubam o autoteste quando desligadas.
- **FATO** split congelado íntegro: sha256 6e54c02b…, mtime 2026-09-04T21:19:49 (anterior a
  esta execução), 30/15/15. Nenhum case_id de validation/test lido.
- **FATO** K4 = RESOLVIDO (Fase 13). K1, K2, K3 = BLOQUEADOS, por razões independentes.
- **FATO** LCTSC test já foi consumido uma vez, na Fase 7, para a hipótese cardíaca — e a
  regra 5 do enunciado o veda como novo TEST de qualquer jeito.
- **INFERÊNCIA** cenário C: nenhum TEST defensável. B exigiria conjunto EM MÃOS com ressalvas
  enumeráveis; candidato inacessível não é TEST parcial.
- **DECISÃO** TREINO permanece BLOQUEADO. Fase 15 em curso pode mexer em K1/K3.

## Fase 17 — benchmark de reconstrução

- **FATO** 182 medições (14 variantes × 13 fantomas) em 24,6 s. Fantomas REUSADOS de
  `phantom.py`, não reconstruídos.
- **FATO** erro vs fórmula fechada (mediana |%|): taubin20 1,31 · MASTER 1,58 · sdf 2,88 ·
  sigma1 6,14 · surface_nets 15,86.
- **FATO** a troca escondida pela mediana: mais Taubin melhora estrutura grande e piora
  estrutura fina, monotonicamente. Ganho 0,27 pp na esfera, perda 2,11 pp no tubo de 3 mm.
- **FATO** sigma=1 funde `dois_cilindros_contato` (2→1) E rompe `ponte_fina_gap4` (1→2).
- **FATO** LOD: 50 % custa ASSD máx 0,0047 mm; 10 % rompe a ponte e derruba Dice mín a 0,6391.
- **FATO** Draco 7,74×–13,20× com erro de vértice máx 0,00099–0,00328 mm.
- **DECISÃO** MASTER MANTIDO. Candidatas registradas, nenhuma promovida.
- **4 achados de instrumento**, todos erro meu, todos corrigidos e documentados.

## Interrupção e retomada — ~07:30

- **FATO** a sessão caiu e derrubou 3 processos de fundo.
- **FATO** Fase 15: 13 resultados recuperados do journal (7 arms + 6 fichas). Relatório escrito
  a partir deles, com a lacuna (sem passe cético) declarada.
- **FATO** Fase 16: journal vazio, relançada do zero (`wqo33i814`).
- **FATO** anatomia real: retomada de 8/48 por script que pula o já gravado.
- **DECISÃO** o relatório consolidado foi publicado com a Fase 16 em aberto, para não deixar
  relatório incompleto se a sessão cair de novo.

## Fase 15 — busca de teste independente (parcial)

- **FATO** 79 candidatos, 230 consultas com fonte/string/data. A=0 B=1 C=57 D=14 E=7.
- **FATO** LyNoS: máscara de esôfago binária {0,1}, buracos 0,028 % e 0,001 % — compatível com
  a ONTOLOGY_V1 por MEDIÇÃO. 1,80 MiB baixados, tamanho conferido por HEAD antes.
- **FATO** classe E, não A: anterioridade da ANOTAÇÃO (2019) não é anterioridade da IMAGEM.
- **DECISÃO** cenário B. K1/K3 seguem bloqueados, com motivo melhor caracterizado.

## Fase 17 — braço de anatomia real

- **FATO** surface_nets é a única variante que quebra watertight em anatomia real, nas 3
  estruturas prontas (8/8/4 arestas não-manifold), com −2,8 % a −7,0 % de volume.
- **FATO** a ordenação de erro de volume é idêntica à dos fantomas nas 3 estruturas.
- **FATO** sdf é 8× mais lento que o MASTER pelo mesmo resultado geométrico.

## Fase 16 — independência do baseline

- **FATO** SegTHOR (Task 55, inclui esôfago) e BTCV (Task 17) semearam a primeira segmentação
  do treino do TotalSegmentator (suplemento S2). É circularidade de ANOTAÇÃO, invisível a
  qualquer sonda de imagem. Remove os dois da lista de candidatos a teste.
- **FATO** Dataset343 × task total: 1.524 formas em comum, 85,3 % do 343 vem do pool do total.
  `pericardium` não é segunda opinião independente.
- **FATO** LUNG1-059 e LUNG1-042 (coorte da Fase 10) estão no SAROS, em folds de TREINO.
- **FATO** não há model card, splits_final.json nem identificador de caso em disco — verificado
  nos opcodes dos .pth sem executar pickle. `fold=0` agrava: nem as 1.139 públicas são
  atribuíveis ao treino efetivo.
- **FATO** `dataset_fingerprint.json` vaza as formas das 1.559 imagens, inclusive as 420 não
  publicadas. LCTSC 3/60 (nulo 2,40, p=0,502); NSCLC 1/25 (nulo 1,00). Sem excesso; teto ≲4.
- **FATO** hipótese SAROS-em-343 derrubada: teto ≈30 casos, sem enriquecimento.
- **FATO** defeito ATIVO corrigido: a correção da Fase 9 era só documental; manifest.json e o
  GERADOR coorte.py ainda emitiam a afirmação falsa. Corrigidos os dois juntos.
- **DECISÃO** K2 BLOQUEADO; K3 BLOQUEADO e registrado como ESTRUTURAL.

## 2026-09-06 — Fase 18 (auditoria do LyNoS)

| hora (UTC) | comando | resultado |
|---|---|---|
| 15:47 | `git rev-parse HEAD` | `c1f4441`, working tree limpo |
| 15:50 | HEAD nas 15 mascaras do LyNoS (HuggingFace) | 15/15, 10,2 MiB no total |
| 15:54 | download das 15 mascaras | `.clinica-dados/fase18/lynos/`, 11 MiB |
| 16:02 | `lynos.auditoria --autoteste` | 10 verificacoes, 0 falhas |
| 16:03 | `lynos.auditoria` | 15/15 ONTOLOGY_COMPATIBLE=SIM; sonda 2/15 exato, 7/15 tol |
| 16:10 | **defeito de instrumento encontrado** | o nulo de `auditoria.py` embaralhava y e x separadamente contra um pool 75 % quadrado; nulo deflacionado (0,041) inflava o sinal |
| 16:18 | `lynos.calibracao` (permutacao por bloco) | nulo correto 0,931; **p = 0,229** — sem excesso sobre o acaso |
| 16:24 | `lynos.grade_ct` | premissa mascara=grade da TC **VERIFICADA** 15/15 com 240 KiB |
| 16:31 | `lynos.adequacao` | IC95 de n=15 tem largura 0,077 de Dice; poder 0,485 para delta=0,05 |
| 16:50 | workflow fase18 (15 agentes) | 7 arms + 7 ceticos + 1 critico · 0 erros · 493 chamadas de ferramenta |
| 17:05 | correcao: DOI fabricado na ficha | `10.5281/zenodo.10102261` NAO EXISTE; o registro usa o DOI do artigo |
| 17:12 | `lynos.integridade` | HuggingFace x Zenodo: **15/15 CRC-32 identicos**, 76,2 KiB de trafego |
| 17:20 | varredura de docs | 40 documentos, 0 violacoes |
| 17:40 | relatorios das fases 18, 19 e consolidado | escritos; varredura: 42 documentos, 0 violacoes |
| 17:45 | auditoria final | PASS=157 FAIL=0 SKIP=0 · split INTOCADO |

## 2026-09-06 — Fases 20-21

| hora (UTC) | comando | resultado |
|---|---|---|
| 17:30 | `git rev-parse HEAD` | `98e806c`, working tree limpo |
| 17:32 | `idc_esofago` (reexecucao do censo) | 908 em 5 colecoes — bate com a Fase 11 |
| 17:40 | `fase20.censo_identidade` | **4D-Lung: 6.690 series de 20 SUJEITOS** (334,5 s/suj); NSCLC com DUAS licencas |
| 17:52 | `fase20.proveniencia_roi` | **ROIGenerationAlgorithm UNKNOWN em 908/908**; CT ligada por UID em **908/908**; 807 sujeitos |
| 17:55 | defeito de instrumento | heredoc converteu `\b` em byte de backspace no regex de PRV; corrigido, 0 PRV entre os 908 |
| 18:20 | `fase21.funil` | 14/14 casos controlados; DICOM 4 identidades, NIfTI 2 |
| 18:35 | `fase21.mutacao` | 12/13 na 1a rodada — **L4 sobreviveu** (contexto desconhecido nao testado); corrigido, 13/13 |
| 18:50 | `fase21.anonimizacao` | 4 eixos; regex de caminho estava cego a `_`; corrigido |
| 19:05 | verificacao de afirmacao de arm | `nsclc_radiomics_interobserver1`: 5 observadores, **0 esofago** (so GTV) |
| 19:10 | `estabilidade_de_uid` | **13.081 de 58.060 UIDs (22,5 %) de versoes anteriores sumiram do indice** |
| 19:40 | `censo_identidade` + demografia | `pediatric_ct_seg` mediana **6 anos, 100 % < 18** — reprovacao por definicao, medida |
| 19:45 | falso positivo proprio | `000Y` do 4D-Lung marcava a colecao como PEDIATRICA; e artefato de anonimizacao, nao lactente |
| 20:05 | `zip_remoto` no STOPSTORM | 3 RTSTRUCT em **344,9 KiB de um zip de 169,5 MB (0,21 %)**, CRC conferido |
| 20:10 | `fase20.stopstorm` | **arm REFUTADO**: `ROIGenerationAlgorithm` VAZIO em 93/93 ROIs; label `AutoSS`, fabricante `Plastimatch`; `case_id`='NOID' nos tres |
| 20:25 | PDF do benchmark STOPSTORM (0,96 MB) | *"delete our temporary contours from the templates"* |
| 20:30 | fatias por ROI | **1 fatia em 31/31 ROIs, 3/3 casos** — sao templates, nao segmentacoes. STOPSTORM cai para **F** |
| 20:50 | ontologia no GT do split congelado | **60/60 LCTSC preenchidas, buracos 0,0000 %** — lacuna que o critico nomeou, fechada |
| 20:55 | bug proprio | `binaria` exigia {0,1} e reprovava as 60 do LCTSC, que usam {0,255} — a convencao do PROPRIO projeto |

## 2026-09-06 — Fases 22-23

| hora (UTC) | comando | resultado |
|---|---|---|
| 19:05 | `git rev-parse HEAD` | `b0dcb2e`, working tree limpo |
| 19:20 | `fase22.rtstruct_lctsc` | **60 RTSTRUCT abertos pela primeira vez** — `ROIGenerationAlgorithm` = **MANUAL em 59/60** |
| 19:30 | comparacao indice x arquivo | a coluna do indice e **DEDUPLICADA** (0, 1 ou 2 valores, nunca por ROI) |
| 19:35 | **correcao da Fase 20** | `proveniencia_roi` alinhava por indice; TUDO caia em UNKNOWN. Era artefato do leitor |
| 19:40 | remedicao dos 908 | **MANUAL 731 · SEMIAUTOMATIC 101 · INDETERMINADO 42 · UNKNOWN 34** |
