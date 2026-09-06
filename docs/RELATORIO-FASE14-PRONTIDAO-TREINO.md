# Fase 14 — prontidão para treinamento

Data: 2026-09-06 · **Esta fase não treina** · Nenhum epoch, nenhum modelo, nenhuma otimização

> **RESULTADO: C — BLOQUEADO.**
> K4 resolvido na Fase 13. **K1, K2 e K3 permanecem bloqueados**, por razões independentes
> entre si. Um critério resolvido de quatro não desbloqueia nada.

---

## 1. Objetivo e método

Reavaliar K1–K4 **contra o estado real do repositório**, depois que a Fase 13 fechou K4.

**Método:** auditoria do que existe em disco + execução das guardas já construídas. Nada foi
inferido de memória; tudo abaixo tem comando reprodutível.

## 2. Guardas executadas

**FATO.** Todas passaram, e o teste por mutação confirma que não estão zeradas:

| Suíte / guarda | Resultado |
|---|---|
| `tests/test_geometria.py` | **10/10** |
| `tests/test_controles_positivos.py` | **8/8** |
| `tests/test_ontologia_esofago.py` | **12/12** (novo, Fase 13) |
| `protocolo_esofago --mutacao` (anti-leakage, Fase 9) | **10/10 guardas derrubam o autoteste** |
| `interobservador --autoteste` (censo, Fase 11) | 11 guardas com controle positivo e negativo |

**Total: 30 testes + 21 guardas com controle, todos ativos.**

### 2.1 Integridade do split congelado

**FATO.** `.clinica-dados/tier2/lctsc/fase5/split.json` — `sha256` começa em
`6e54c02b58bbb9b3a1667d4672eddef6`, 2.592 bytes, **mtime 2026-09-04T21:19:49**, anterior ao
início desta execução. Partições: `development` 30 · `validation` 15 · `test` 15.

**Nenhum `case_id` de `validation` ou `test` foi lido nesta fase** — só as contagens, que é o
que a guarda `g7` também faz.

## 3. K1 — desenho TRAIN / VALIDATION / TEST defensável

# **BLOQUEADO**

**FATO.** Não existe, no repositório nem em acesso obtido, um conjunto que possa servir de
TEST para o esôfago.

O que existe, e por que nenhum serve:

| Conjunto | N | Por que não pode ser TEST |
|---|---:|---|
| LCTSC `development` | 30 | **consumido** — foi a base das Fases 5, 7, 9, 10; qualquer avaliação nele é auto-referente |
| LCTSC `validation` | 15 | partição congelada; regra 5 do enunciado proíbe contar subset já usado |
| LCTSC `test` | 15 | **idem — e já foi consumido uma vez**, na Fase 7, para a hipótese cardíaca (`pericardium` × `heart`, 15/15 casos). A regra 5 é explícita: não contar o LCTSC TEST como novo TEST |
| NSCLC-Radiomics | 422 | já usado na Fase 10; compartilha instituição (MAASTRO) com o LCTSC-S1; GT de anotador único |
| iCurveE | 500 | **acesso não obtido** (Fase 12, classe C) |

**INFERÊNCIA.** A regra 3 do enunciado — *"não criar artificialmente TRAIN/VAL/TEST só para
liberar treinamento"* — fecha a única saída aritmética que restaria: reparticionar o LCTSC.
Reparticionar não cria independência; só redistribui um conjunto já visto.

## 4. K2 — baseline comparável sem leakage conhecido

# **BLOQUEADO**

**FATO.** O TotalSegmentator v2 declara **1.559 imagens de treino**, das quais **420 não são
publicamente atribuídas**. O repositório oficial diz, verbatim: *"we did not publish the
additional subjects we used for TotalSegmentator v2 training"* e *"more images from GE
scanners and other institutions"*.

**FATO.** Isso foi uma **correção contra afirmação anterior do próprio projeto**: o
`RELATORIO-TIER2-COORTE.md` dizia que o task `total` fora treinado *"exclusivamente em TCs do
University Hospital Basel (1082/57/65)"* — números que descrevem o dataset **público da v1**,
não o treino da v2. A correção está publicada na Fase 9.

**INFERÊNCIA, e ela é a regra 4 do enunciado.** 27 % do treino da v2 é não declarado.
Portanto:

- **não é possível afirmar** que o LCTSC está fora do treino do baseline;
- isso **não prova contaminação** — remove a **prova de independência**;
- *"leakage não demonstrado"* **não é** *"independência demonstrada"*.

**Consequência para K2:** a comparação baseline × qualquer conjunto público carrega
independência **não verificável**, não independência estabelecida. E, hoje, não há conjunto
novo contra o qual comparar — a comparação não é apenas arriscada: é **inexecutável**.

*(A Fase 16 desta mesma execução audita isso dataset a dataset.)*

## 5. K3 — avaliação futura com conjunto independente

# **BLOQUEADO**

**FATO.** Mesma raiz de K1, consequência diferente: K1 é sobre o desenho de hoje, K3 é sobre
a existência de um conjunto para a avaliação de amanhã.

O único candidato com o objeto e o desenho certos identificado em 11 fases — **iCurveE** —
está sob acesso restrito, e a Fase 12 registrou que mesmo se concedido: o padrão-ouro é o
contorno de **um** especialista escolhido órgão a órgão, e a fonte é **muda** sobre a retenção
das séries individuais de A e B.

**RECOMENDAÇÃO.** Um plano de avaliação que depende de um objeto não solicitado não é um
plano. O rascunho de pedido existe (`docs/ICURVEE-PEDIDO-ACESSO.md`) e **não foi enviado** —
enviá-lo é decisão do usuário.

## 6. K4 — definição do alvo congelada

# **RESOLVIDO** (Fase 13)

**FATO.** `ESOPHAGUS_ONTOLOGY_V1`, congelada em 2026-09-06, em duas formas que a suíte
obriga a concordar (`docs/ESOPHAGUS-ONTOLOGY-V1.md` e
`scripts/validation/tier2/ontologia_esofago.py`), com 12 testes de regressão.

Parede vs lúmen **não separados** · extensão longitudinal **herdada / não avaliável** ·
8 métricas congeladas · RTOG 1106 como protocolo de referência.

## 7. Matriz de cenários

| Cenário | Definição | Estado |
|---|---|---|
| **A** | TEST independente realmente defensável | **não** — nenhum conjunto satisfaz |
| **B** | TEST parcialmente defensável, com ressalvas | **não** — não há candidato sequer parcial em mãos; o único plausível (iCurveE) não foi obtido, e sua procedência por observador é indeterminada |
| **C** | **nenhum TEST defensável** | **SIM** |

**INFERÊNCIA sobre a fronteira B/C:** B exigiria um conjunto **em mãos** cujas ressalvas
fossem enumeráveis. Não há conjunto em mãos. Um candidato inacessível não é um TEST parcial —
é um TEST ausente com um caminho conhecido.

> ### Retorno da Fase 15 — K1 e K3 mudam de motivo, não de estado
>
> **FATO.** A Fase 15 (executada depois desta) encontrou o **LyNoS**: 15 TCs mediastinais com
> esôfago em máscara NIfTI binária, canal não-DICOM, fora do TCIA e de tudo que o VRmed já
> usou, com GT de 2019 — anterior ao TotalSegmentator. A compatibilidade com a
> `ESOPHAGUS_ONTOLOGY_V1` foi **medida** (fração de buracos 0,028 %: binária e preenchida),
> não inferida de documento.
>
> **O que muda:** a frase desta seção — *"não existe conjunto que possa servir de TEST"* —
> passa a ser **imprecisa**. Existe um, e ele é acessível. O cenário da Fase 15 é **B**, não C.
>
> **O que NÃO muda:** K1 e K3 continuam **BLOQUEADOS**. O LyNoS é classe **E**, independência
> indeterminada, pelo mesmo motivo que trava K2 — as 420 imagens não atribuídas do treino do
> TS v2. Somam-se três ressalvas medidas: n=15, TC **com contraste** e diagnóstica (não de
> planejamento), e conflito de licença entre três fontes oficiais do mesmo dataset.
>
> **INFERÊNCIA.** O bloqueio de K1/K3 deixou de ser *"não há candidato"* e passou a ser
> *"há um candidato cuja independência não é estabelecível pelo mesmo motivo que trava K2"*.
> É um bloqueio melhor caracterizado, não um bloqueio menor.

## 8. Candidatos — ficha por dataset

*(Os cinco que a Fase 11 identificou como tendo esôfago no canal DICOM público, mais o
iCurveE. A Fase 15 desta execução procura candidatos novos; o que ela encontrar entra no
relatório consolidado.)*

| DATASET | MODALIDADE | ESTRUTURA | LICENÇA | N | DEFINIÇÃO | PROVENIÊNCIA | OVERLAP | TRAIN? | VAL? | TEST? | INDEPENDÊNCIA | STATUS |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|
| **LCTSC** | CT + RTSTRUCT | Esophagus (OAR) | CC BY 3.0 | 60 | RTOG 1106, 1 contorno/caso | 3 instituições | **já usado pelo VRmed** | não | não | **não** (regra 5) | não verificável (420 do TS não declaradas) | **C** |
| **NSCLC-Radiomics** | CT + RTSTRUCT | Esophagus (OAR) | CC BY-NC 3.0 | 422 | não documentada (achado da Fase 10) | MAASTRO | **já usado; institui­ção compartilhada com LCTSC-S1** | possível, com ressalva | não | **não** | não verificável | **C** |
| **Pediatric-CT-SEG** | CT + RTSTRUCT | Esophagus (OAR) | CC BY 4.0 | 359 | `StructureSetName = 'AR AutoSegmentation'`, 42/42 AUTOMATIC | — | não medido | **não** (GT não humano) | não | não | não verificável | **C** |
| **4D-Lung** | CT + RTSTRUCT | Esophagus | CC BY 3.0 | 20 casos / 101 séries | sufixo é **fase respiratória**; SEMIAUTOMATIC 800/800 | — | não medido | não | não | não | não verificável | **C** |
| **EAY131** | CT + RTSTRUCT | "ESOPHAGUS" = **sítio de lesão** | CC BY 4.0 | 17 | catálogo de lesão, não OAR | — | não medido | não | não | não | — | **C** |
| **iCurveE** | CT + contornos | Esophagus (OAR), RTOG 1106 | dado **não** coberto pelo CC BY-NC-ND do artigo | 497 | RTOG 1106, borda inferior da cricoide, exclusão da ázigos | 5 centros | não medido | — | — | — | **indeterminada** | **D — inacessível** |

## 9. O que mudaria cada bloqueio

**RECOMENDAÇÃO**, em ordem de custo:

| Critério | O que o destravaria | Custo | Sob controle do projeto? |
|---|---|---|---|
| **K4** | — | — | ✅ **já feito** |
| **K2** | uma lista de treino auditável do TotalSegmentator, ou um baseline cuja procedência de treino seja verificável | alto — depende de terceiro | ❌ |
| **K1 / K3** | um conjunto com esôfago, definição compatível com a V1, e independência ao menos plausível | alto — depende de acesso ou de aquisição | ❌ |

**INFERÊNCIA.** K2 tem uma saída que K1/K3 não têm: trocar o baseline por um cujo treino
seja auditável tornaria a independência verificável **sem depender de dado novo**. Isso não
foi investigado nesta fase e é candidato a fase futura — **não é recomendação de trocar o
baseline**, que continua congelado.

## 10. O que esta fase NÃO fez

- **Não treinou.** Nenhum epoch.
- **Não otimizou** nada.
- **Não leu** `case_id` de `validation` nem de `test`.
- **Não declarou K1 resolvido** por existir "um dataset qualquer" — nenhum dos seis
  candidatos passa.
- **Não reparticionou** o LCTSC para fabricar um TEST.

---

```
FASE 14 CONCLUÍDA
RESULTADO: C — BLOQUEADO
K1: BLOQUEADO — nenhum conjunto pode ser TEST; LCTSC test já consumido (Fase 7) e vedado pela regra 5
K2: BLOQUEADO — 420 de 1.559 imagens do treino do TotalSegmentator v2 não são declaradas; independência não verificável
K3: BLOQUEADO — o único candidato com objeto e desenho certos (iCurveE) não foi obtido
K4: RESOLVIDO — ESOPHAGUS_ONTOLOGY_V1, 12 testes de regressão
CENÁRIO: C — nenhum TEST defensável
TREINO: BLOQUEADO
PRÓXIMO PASSO: a Fase 15 rodou e achou o LyNoS — K1/K3 seguem BLOQUEADOS, mas agora por independência não estabelecível (as 420 do TS v2), não por ausência de candidato. O bloqueio é estrutural, e se fecha do lado do MODELO, não do lado do dado
```
