# Fase 20 — busca de dados realmente auditáveis

Data: 2026-09-06 · 6 arms · 6 passes céticos · **235 consultas registradas** ·
**47 candidatos** · Nada treinado

> **RESULTADO: B — existe rota plausível, e ela não é a que se procurava.**
>
> O canal DICOM do IDC **resolve identidade por completo** — máscara ligada à imagem por
> identificador em **908/908**. E **não resolve procedência de jeito nenhum**: a tag DICOM
> que responderia *"humano ou modelo?"* está **vazia nos 908**.
>
> Matriz: [`FASE20-CANDIDATOS-DADOS.md`](FASE20-CANDIDATOS-DADOS.md) ·
> Log: [`overnight/phase20/source_log.csv`](overnight/phase20/source_log.csv)

---

## 1. Candidatos

**47 candidatos**, de 235 consultas registradas em 15 fontes.

| Classe | N |
|---|---:|
| **A** — potencialmente elegível | **3** *(nenhum é dataset: 2 canais + 1 documento normativo)* |
| **B** — elegível com ressalvas | 2 |
| **C** — inadequado | 4 |
| **D** — inacessível | 14 |
| **E** — independência/definição indeterminada | 6 |
| **F** — reprovado | 18 |

**Zero datasets classe A.** É o mesmo resultado das Fases 11 e 15, por um motivo novo:
antes o bloqueio era independência; agora é **procedência da anotação**.

## 2. Fontes

TCIA · IDC · Zenodo · Figshare · Dryad · OSF · PhysioNet · MIDRC · Grand Challenge ·
Synapse · HuggingFace · Europe PMC · PubMed · arXiv/medRxiv · DataCite · Crossref ·
GitHub · Kaggle *(só descoberta)*.

Distribuição das 235 consultas: TCIA 41 · Zenodo 37 · IDC 26 · arXiv 12 · HuggingFace 10 ·
Europe PMC 10 · DataCite 10 · GitHub 8 · PubMed 7 · Figshare 4 · Grand Challenge 4 ·
Dryad 1 · OSF 1 · PhysioNet 1 · outras 63.

**Nenhuma conta criada, nenhum termo aceito, nenhum acesso solicitado.**

## 3. Licenças

**Medidas, não pesquisadas.** O `idc_index.parquet` traz `license_short_name` **por
série** — a licença do dado é legível por máquina, sem inferir de página web.

| Licença | Séries no IDC |
|---|---:|
| CC BY 4.0 | 865.935 |
| CC BY 3.0 | 132.303 |
| CC BY-NC 4.0 | 28.783 |
| CC BY-NC 3.0 | 5.851 |
| NLM Terms and Conditions | 39 |

**97 % é atribuição aberta.** Mas a licença **varia por série dentro da mesma coleção**, e
o caso concreto importa: **as RTSTRUCT de esôfago do NSCLC-Radiomics são CC BY-NC 3.0** —
mais restritivas que a manchete da coleção, que o VRmed já usou na Fase 10.

**Separação mantida em toda a fase:** licença do código ≠ do dataset ≠ das imagens ≠ das
máscaras. Foi essa confusão que produziu o falso "conflito de licença" do LyNoS na Fase 15.

## 4. Identidade

**A pergunta que a Fase 19 deixou aberta, respondida por medição.**

| Canal | das 4 chaves do esquema | Composição |
|---|---:|---|
| **DICOM (TCIA/IDC)** | **4** | 3 do arquivo (`PatientID`, `StudyInstanceUID`, `SeriesInstanceUID`) + `sha256` computado |
| **NIfTI** | **2** | `case_id` externo + `sha256` computado |

**Extra do DICOM:** `SOPInstanceUID` por instância, e
**`ReferencedSeriesInstanceUID` ligando máscara a imagem — 908/908.** É a prioridade 2 da
Fase 20.1 (*"DICOM completo + máscara vinculada por identificadores"*) satisfeita por
construção.

**E um limite que atinge o próprio DICOM:** `13.081 de 58.060` séries de versões
anteriores do IDC (**22,5 %**) têm UID **ausente** do índice corrente. O `series_id`
detecta vazamento **hoje**; entre *releases*, **só o `sha256` do conteúdo não deriva**.
Isso é um argumento **medido** a favor do desenho de quatro chaves, não uma justificativa
escrita depois.

## 5. Procedência — o gargalo, e ele é total

**FATO.** `ROIGenerationAlgorithm` (tag DICOM `3006,0036`, valores `MANUAL` /
`SEMIAUTOMATIC` / `AUTOMATIC`) está **VAZIA nas 908** RTSTRUCT com esôfago-órgão do canal
público inteiro.

A Fase 11 declarou que a tag vem preenchida em ~25 % das séries. **Para o esôfago são 0 %.**

**A consequência é a fase inteira.** Identidade e licença são verificáveis por máquina.
Procedência da anotação **não é** — e é a única das quatro exigências cujo modo de falha é
**silencioso e irreversível**: um GT de modelo ingerido como humano contamina o treino e
nenhuma sonda posterior o detecta. Foi exatamente a circularidade SegTHOR/BTCV que a
Fase 16 encontrou no TotalSegmentator.

### 5.1 O negativo perfeito

`totalsegmentator_ct_segmentations` no IDC:
**378.153 séries · 26.194 sujeitos · CC BY 4.0 · DICOM com identidade completa · inclui
esôfago.**

Passa em licença, em identidade, em formato, em n. **É saída de modelo.** Inelegível.

O canal de *analysis results* tem **471.946 séries derivadas** em 24 entradas. É um canal
inteiro que parece perfeito e falha no único eixo que não se verifica por máquina.

## 6. Overlap

Instrumentos aplicados, **cada um com sua sensibilidade declarada**:

| Instrumento | O que vê | O que **não** vê |
|---|---|---|
| `PatientID` / `StudyInstanceUID` / `SeriesInstanceUID` | duplicata entre partições **hoje** | renomeação; UID que mudou entre *releases* (22,5 %) |
| `sha256` do conteúdo | conteúdo idêntico sob nomes diferentes | mesmo exame reconvertido (bytes diferentes) |
| sonda geométrica calibrada (Fase 16/18) | coincidência de shape a 1,5 mm | inclusão de 1–3 casos em 15; recorte *in-plane*; canal documental |
| `ROIGenerationAlgorithm` | autoria **declarada** | autoria real; pré-anotação por modelo corrigida à mão |

**Nada nesta fase autoriza escrever "não houve overlap".** Onde não foi detectado, está
escrito **"não detectado pelo instrumento X"**.

## 7. Ranking — os três melhores

### 1º · Canal IDC/TCIA — **A como canal**
**Passou:** 4 identidades, licença por série legível por máquina, máscara↔imagem por UID.
**Bloqueia:** nada como canal. **Risco:** confundir identidade entregue com procedência
conhecida. **Próximo passo:** nenhum — já instrumentado.

### 2º · Atlas Kong et al. 2011 — **A, e não é dataset**
**Passou:** define operacionalmente os limites do esôfago em RT torácica (RTOG/EORTC/SWOG).
**Bloqueia:** não é dado. **Risco:** confundir "existe regra publicada" com "o projeto
consegue verificá-la" — a Fase 9 mediu que **não consegue**. **Próximo passo:** citar como
referência, **sem alterar a ontologia**.

### 3º · Pediatric-CT-SEG — **C, o melhor dataset e ainda assim reprovado**
**Passou:** 359 sujeitos, 1:1 série/sujeito, CC BY 4.0, identidade completa, GT manual
declarado por quatro analistas. **Bloqueia:** idade **mediana 6 anos, 100 % abaixo de 18** —
sob a `ESOPHAGUS_ONTOLOGY_V1`, calibrada na grade adulta, é **outro objeto**.
**Risco:** aceitar por qualidade de metadado o que a definição do alvo recusa.
**Próximo passo:** nenhum sob a V1 — reabrir exigiria uma V2 da ontologia, e essa decisão
não é desta fase.

**Nenhum promovido automaticamente.**

## 8. Bloqueios

| Bloqueio | Natureza |
|---|---|
| **procedência da anotação** | `UNKNOWN` em 908/908 no canal público |
| **ontologia** | o melhor dataset por metadado é pediátrico |
| **n por sujeito** | 4D-Lung: 6.690 séries de 20 sujeitos |
| **licença por série** | varia dentro da coleção; NC onde menos se espera |
| **acesso** | 14 candidatos classe D, nenhum aberto |
| **reuso proibido** | LCTSC e NSCLC-Radiomics já usados, split congelado |

## 9. O critério de sucesso da fase

> *"encontrar pelo menos uma rota plausível para dados cuja procedência, licença,
> identidade e uso possam ser auditados"*

**SIM — com uma condição nomeada.**

A rota é: **canal DICOM do IDC**, que entrega identidade completa, licença legível por
máquina e vínculo máscara↔imagem por identificador. **A condição** é que a procedência da
anotação **não vem do canal** — ela tem de ser estabelecida **por apuração documental,
coleção a coleção**, e registrada no manifesto.

Não é a rota que se procurava (um dataset pronto). É a rota que existe.

## 10. Os defeitos que os controles pegaram

| # | Defeito | Como apareceu |
|---|---|---|
| 1 | `series_revised_idc_version` lido como "foi revisada"; vem em **100 %** das séries | medição direta contradisse a leitura |
| 2 | flag `PEDIATRICA` marcou o 4D-Lung, cujas idades são `000Y` — artefato de anonimização | o próprio resultado ficou implausível |
| 3 | heredoc converteu `\b` em byte de *backspace* num regex de PRV | `cat -A` mostrou `^H` |
| 4 | um arm afirmou GT humano do STOPSTORM "verificado no arquivo" | a tag estava vazia; medi |

---

```
FASE 20 CONCLUIDA
RESULTADO: B — existe rota plausivel, e nao e a que se procurava
CANDIDATOS: 47 (A=3 · B=2 · C=4 · D=14 · E=6 · F=18) · 235 consultas registradas
MELHOR CANDIDATO: canal IDC/TCIA — 4 identidades, licenca por serie, mascara ligada a imagem em 908/908
LICENCA: legivel por maquina no indice; 97 % CC BY 3.0/4.0; VARIA POR SERIE (esofago do NSCLC e CC BY-NC 3.0)
PROVENIENCIA: BLOQUEIO TOTAL — ROIGenerationAlgorithm UNKNOWN em 908/908
IDENTIDADE: DICOM 4 de 4 chaves (3 do arquivo + sha256); NIfTI 2 de 4; UID cai 22,5 % entre releases
OVERLAP: nao detectado pelos instrumentos aplicados — cada um com sensibilidade declarada
TREINO: BLOQUEADO
```
