# Fase 21 — o funil de ingestão, provado em arquivos reais

Data: 2026-09-06 · Nada treinado · Nada avaliado · Split congelado intocado

> **RESULTADO: A — o funil aceita o válido, recusa o inválido, e as guardas provaram
> que enxergam.**
>
> 14/14 casos controlados · 13/13 mutantes mortos · determinismo e reexecução OK ·
> e **três defeitos meus**, todos achados por controle, nenhum por revisão.

---

## 1. Por que a Fase 19 não bastava

A Fase 19 provou o esquema com **dicionários**: 24 autotestes e 17 testes de suíte,
todos sobre `dict`. Isso prova a **lógica** e não prova o **funil** — nenhum arquivo foi
lido, nenhuma grade comparada, nenhum UID extraído de cabeçalho, nenhum hash calculado
de bytes reais.

Aqui as fixtures são **arquivos**: uma série CT DICOM escrita com `pydicom` e pares
imagem+máscara em NIfTI escritos com `nibabel`.

## 2. O mapa do funil (21.1)

| Etapa | Entrada | Validação | Falha possível | Arquivo responsável |
|---|---|---|---|---|
| **ENTRADA** | caminhos | existência | `FileNotFoundError` | `fase21/funil.py` |
| **IDENTIDADE** | cabeçalho | 4 chaves DICOM / 2 NIfTI | `UNKNOWN` declarado | `fase21/funil.py` |
| **PROVENIÊNCIA** | declaração | `gt_humano` sem padrão | `ProcedenciaInvalida` | `tier2/dataset_esofago.py` |
| **LICENÇA** | `license_class` | 4 classes bloqueiam | erro de validação | `baseline_v1/manifesto.py` |
| **IMAGEM** | NIfTI | legível | erro de leitura | `tier2/geometria.py` |
| **MÁSCARA** | NIfTI | não vazia | `MascaraVazia` | `tier2/dataset_esofago.py` |
| **ONTOLOGIA** | máscara | `ESOPHAGUS_ONTOLOGY_V1` | `validar_alvo` reprova | `baseline_v1/plano.py` |
| **GRADE** | par | shape/zoom/affine | `DesalinhamentoGeometrico` | `tier2/geometria.py` |
| **HASH** | bytes | `sha256` obrigatório | campo `UNKNOWN` recusado | `baseline_v1/manifesto.py` |
| **MANIFEST** | entradas | JSONL canônico | `validar_manifesto` | `baseline_v1/manifesto.py` |
| **SPLIT** | manifesto | 4 identidades | `validar_vazamento` | `baseline_v1/manifesto.py` |
| **SNAPSHOT** | manifesto | `sha256` | `congelar` recusa inválido | `baseline_v1/manifesto.py` |
| **CONGELAMENTO** | snapshot | comparação | `VERSION INCREMENT` | `baseline_v1/manifesto.py` |

**Nada foi reimplementado.** O módulo da Fase 21 é o **arame** que liga peças existentes,
mais as fixtures. Uma segunda cópia da verificação de grade ou da ontologia divergiria —
e a divergência apareceria como diferença de desempenho.

## 3. Identidade por canal — medida, não suposta

| | DICOM | NIfTI |
|---|---|---|
| `case_id` | **SIM** (`PatientID`) | externo ao arquivo |
| `study_id` | **SIM** (`StudyInstanceUID`) | **UNKNOWN** |
| `series_id` | **SIM** (`SeriesInstanceUID`) | **UNKNOWN** |
| `SOPInstanceUID` | **SIM**, 8/8 únicos na fixture | não existe |
| `sha256` do conteúdo | computável | computável |
| **identidades entregues** | **4** | **2** |

**O motivo do `UNKNOWN` não é limitação nossa:** o cabeçalho NIfTI-1 **não tem campo**
para `StudyInstanceUID` nem `SeriesInstanceUID`. Falsificá-los seria inventar procedência.

**Consequência (21.4):** para um caso NIfTI, **duas das quatro regras anti-vazamento
ficam impossíveis de verificar** — mesmo estudo em duas partições, e mesma série em duas
partições. Restam `case_id` e o hash do conteúdo.

**E há um limite que atinge o próprio DICOM (medido na Fase 20):** `13.081 de 58.060`
séries de versões anteriores do IDC (**22,5 %**) têm UID **ausente** do índice corrente.
O `series_id` é identidade útil para detectar vazamento **hoje** e **não é âncora durável
entre releases**. O `sha256` do conteúdo é a única das quatro chaves que não deriva.

## 4. Os 14 casos controlados (21.2) — **14/14**

| # | Caso | Esperado | Guarda que disparou |
|---|---|---|---|
| 01 | caso válido | **ACEITA** | — (controle negativo da lista) |
| 02 | máscara vazia | RECUSA | `validar_alvo` → `mascara_vazia` |
| 03 | spacing incompatível | RECUSA | `DesalinhamentoGeometrico` |
| 04 | orientação incompatível | RECUSA | `DesalinhamentoGeometrico` |
| 05 | shapes diferentes | RECUSA | `DesalinhamentoGeometrico` |
| 06 | hash alterado após congelar | RECUSA | `verificar_congelamento` |
| 07 | licença `UNKNOWN` | RECUSA | `validar_licenca` |
| 08 | licença `CONFLITO` | RECUSA | `validar_licenca` |
| 09 | mesmo `case_id` em dois splits | RECUSA | `validar_vazamento` |
| 10 | mesmo `study_id`, `case_id` diferente | RECUSA | `validar_vazamento` |
| 11 | mesma `series_id`, `case_id` diferente | RECUSA | `validar_vazamento` |
| 12 | mesmo **conteúdo**, ids diferentes | RECUSA | `validar_vazamento` (sha256) |
| 13 | ontologia errada (anel oco) | RECUSA | `validar_alvo` |
| 14 | TEST lido em contexto de treino | RECUSA | `AcessoIndevido` |

**O caso 01 é o controle negativo da lista inteira.** Sem ele, um funil que recusasse
tudo passaria nos treze defeitos e pareceria excelente.

## 5. Determinismo e reexecução (21.11, 21.12)

- **Determinismo:** duas passadas independentes produzem os **mesmos `sha256` de
  conteúdo** para as mesmas fixtures.
- **Reexecução:** rodar duas vezes no mesmo diretório produz o **mesmo `sha256` de
  manifesto e o mesmo snapshot**.
- **E um teste de sinal contrário:** dois diretórios diferentes produzem hashes de
  manifesto **diferentes** — porque o caminho entra no manifesto. Se dessem igual, o
  manifesto não estaria registrando onde o dado mora.

## 6. Mutação (21.14) — **13/13 mortos**, e um sobrevivente que virou teste

Treze mutantes plantados numa **cópia** da árvore, com controle negativo antes e depois.
O repositório real nunca é tocado — nem "com restauração depois": um mutante que escreve
no repo fica lá se a execução morrer no meio.

| Grupo | Mutantes | Mortos |
|---|---:|---:|
| `validators` | 5 | **5** |
| `loader` | 5 | **5** |
| `hashing/snapshot` | 3 | **3** |

**A primeira rodada deu 12/13.** O sobrevivente foi **L4**: *"contexto desconhecido deixa
de ser recusado"*. Nada no projeto testava que `carregar_particao` recusa um **contexto**
inexistente — a guarda existia e ninguém a exercitava. Um contexto digitado errado
(`"eval"`, `"treinamento"`) devolveria **lista vazia em silêncio**, e o laço de treino
falharia longe dali, com outra mensagem.

**Um mutante que sobrevive não é bug do mutante: é buraco na suíte.** Teste acrescentado,
agora 13/13.

## 7. Anonimização (21.5)

Quatro eixos, detalhados em
[`FASE21-ANONIMIZACAO-CHECKLIST.md`](FASE21-ANONIMIZACAO-CHECKLIST.md):
24 tags do PS3.15 Anexo E · UIDs · tags privadas (grupo ímpar) · caminho e nome.

O veredito é **"SEM ACHADO NAS QUATRO VARREDURAS"**, e o auditor imprime, junto, o que
isso **não** significa: pixel não foi lido (texto queimado é invisível), reidentificação
por combinação não é avaliada, e licença aberta **não é** consentimento.

`PatientID` e os UIDs saem como **`INDETERMINADO`**, nunca `OK`: eles *devem* existir — o
esquema os exige — e daqui não é possível saber se foram remapeados na origem.

## 8. Revisão do esquema (21.13)

Quatro lacunas medidas → [proposta de V2](VRMED-ESOPHAGUS-DATASET-V2-PROPOSTA.md),
**não promovida**. A recomendação da própria proposta é **não promover nada agora**: das
quatro, só a de dado derivado tem modo de falha silencioso, e alterar a V1 com base em
fixtures repetiria o erro que a criou — ela nunca viu um caso real.

`test_17` falha se a V1 sair de 22 campos, se um campo proposto invadi-la, ou se o
documento da V2 deixar de se declarar proposta.

## 9. Os três defeitos que os controles pegaram — todos meus

1. **O harness contava `AssertionError` como recusa.** Os casos 6 e 9–14 sinalizam *"a
   guarda não acusou"* levantando exceção; então uma guarda **quebrada** aparecia como
   OK. **Os 14 casos passaram na primeira execução sem provar nada.**
2. **A correção óbvia quebrou os casos 3–5.** Tratar `AssertionError` como falha
   colidiu com `DesalinhamentoGeometrico`, que **já é** subclasse de `AssertionError` no
   Tier2 — uma recusa legítima do projeto virava "guarda cega". Agora o sinal é uma
   exceção própria, `GuardaCega`. **A hierarquia existente manda.**
3. **O regex de caminho da anonimização estava cego.** Usava `\b` nas partes numéricas, e
   `_` **é** caractere de palavra: `1957-03-04_prontuario_123456789` não casava — o
   separador mais comum em nome de arquivo médico. Trocado por *lookaround* de dígito.

## 10. Auditoria (21.15) — **PASS = 258 · FAIL = 0 · SKIP = 0**

| Categoria | N |
|---|---:|
| testes de suíte (`test_geometria` 10, `controles_positivos` 8, `ontologia_esofago` 13, `baseline_v1` 18) | **49** |
| verificações de autoteste de módulo (13 módulos) | **168** |
| guardas derrubadas por mutação (fase21 13, interobservador 21, estilo_esofago 7) | **41** |
| **total** | **258** |

Casos controlados do 21.2: **14/14** (contados dentro do autoteste do funil).
Varredura de docs: **44 documentos, 0 violações**.
Split congelado: `sha256` `6e54c02b58bbb9b3a1667d4672eddef6…` — **INTOCADO**.

**Nenhum SKIP silencioso.** O único `SKIP` possível é o de `candidatos.py` quando o JSON
de medição da Fase 18 não existe, e ele **imprime** a razão.

## 11. Critério de sucesso da fase

| Exigência | Estado |
|---|---|
| aceitar fixture válida | **SIM** — caso 01 |
| rejeitar fixture inválida | **SIM** — 13/13 |
| detectar alteração | **SIM** — caso 06, mutante H1 |
| impedir leakage | **SIM** — casos 09–12, mutante V1 |
| gerar manifest determinístico | **SIM** — 21.11 e 21.12 |
| preservar hashes | **SIM** |
| impedir TEST fora de avaliação | **SIM** — caso 14, mutantes L1–L3 |
| deixar explícitas as limitações do NIfTI | **SIM** — 2 de 4 identidades, com motivo |

---

```
FASE 21 CONCLUIDA
RESULTADO: A — o funil aceita o valido, recusa o invalido, e as guardas provam que veem
FIXTURE_VALID: PASS
HASH: PASS
MANIFEST: PASS (JSONL canonico, hash independente de ordem de insercao)
SPLIT: PASS (4 identidades; casos 9-12)
TEST_ISOLATION: PASS (excecao real, nao convencao de nome)
NIFTI_LIMITATIONS: 2 de 4 identidades — study_id e series_id nao existem no formato;
  duas regras anti-vazamento ficam inverificaveis por caso NIfTI
MUTATION: PASS=13 FAIL=0 (12/13 na primeira rodada; L4 virou teste)
TESTES: PASS=258 FAIL=0 SKIP=0
TREINAMENTO: BLOQUEADO
```
