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
