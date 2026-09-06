# Pedido de acesso ao conjunto do iCurveE — RASCUNHO

> # ⛔ RASCUNHO NÃO ENVIADO
>
> **Data: 2026-09-06.** Nada foi enviado. Nenhum e-mail saiu, nenhuma conta foi criada,
> nenhum termo foi aceito, nenhum formulário foi preenchido. Este arquivo é texto em disco.
>
> **Só o usuário pode enviar, e só depois de decidir os itens de §2.3.** Enquanto houver
> qualquer `[PREENCHER: ...]` no corpo da carta, ela está incompleta — os marcadores existem
> porque nada foi inventado: não há afiliação, orientador, financiamento nem número de
> aprovação ética presumidos neste documento.

---

## 0. Expectativa correta, declarada antes da carta

**O pedido não é inútil, mas o que ele mais provavelmente devolve não é o que se pediu.**
Três fatos documentais, todos verificados na Fase 12, definem a expectativa:

1. **A fonte é MUDA sobre a retenção separada de A e de B.** O artigo afirma que
   `Experts A and B independently delineated each CT image, resulting in two sets of OARs`,
   mas descreve em seguida o Expert C **escolhendo órgão a órgão** entre as duas séries e
   fazendo modificações. Em nenhum ponto do texto, do protocolo (MOESM1 §6.5.4), das 27 abas
   da Source Data ou do Peer Review File se afirma que as séries originais de A e de B foram
   **preservadas como objetos recuperáveis**. A Data availability oferece
   `The CT imaging datasets and delineation results` — no singular de resultado, sem menção a
   versões por observador. **A resposta honesta mais provável é "só o padrão-ouro final".**
   **Atenção à classe:** isso é uma *previsão condicionada a um acesso que não ocorreu*, não
   a classificação de hoje. A rubrica B exige **acesso disponível**, e não há acesso — nada
   foi pedido. Hoje a linha iCurveE é **C — acesso não obtido**. Se o pedido for enviado e
   atendido, e o que chegar for apenas o produto do Expert C, *aí* a classe passa a B.

2. **O acesso custa mais do que um e-mail.** O artigo exige *research protocol* + *proof of
   ethical approval*; o registro do ensaio (NCT05787522, `ipdSharingStatementModule`) exige
   ainda *analysis plan* e *data exchange with institutional approvals in place before data
   transfer* — na prática um DTA institucional. E o mesmo registro só se compromete a
   compartilhar **o protocolo**, não o dado individual, e só a partir de **1 ano após a
   publicação (≥ 2027-03-31)**. As três declarações de compartilhamento (artigo, CT.gov,
   Reporting Summary) divergem entre si; a carta cita a do artigo, que é a mais específica.

3. **Há uma empresa dentro do estudo.** Perception Vision Medical Technology (PVmed) é
   afiliação de três coautores, colaboradora formal do ensaio no CT.gov, e o iCurveE tem
   registro Classe III da NMPA (nº 20253210066). Um pedido que soe a *benchmarking* do produto
   tende a ser tratado como assunto comercial. A carta declara uso não comercial de forma
   explícita e não menciona comparação de desempenho com o produto.

**E o mais importante:** a pergunta central da Fase 12 — qual é a distribuição do desacordo
humano no esôfago — **já foi respondida sem acesso nenhum**, pela Source Data aberta
(MOESM4). O que continua faltando, e que só os autores têm, é **o Dice direto humano-contra-humano**
(`Dice(A, B)` e `Dice(médico_1, médico_2)` na mesma TC), que não existe em lugar nenhum do
material aberto. Por isso a carta faz **duas** perguntas, e a segunda — métricas por caso, sem
dado bruto — é a que tem chance real de ser concedida e a que, sozinha, já resolve o problema
do VRmed.

**Janela de tempo, se relevante:** o artigo diz `data will be available for 6 months`, sem
dizer a partir de quando. Se contar da publicação (2026-03-31), a janela fecha por volta de
**2026-09-30** — cerca de três semanas a partir de hoje. Se contar da concessão, não há pressa.
A ambiguidade é da fonte, não desta leitura.

---

# PARTE 1 — A CARTA (inglês, pronta para copiar)

> Cole a partir de "Subject:". Substitua todo `[PREENCHER: ...]` antes de enviar.
> Não remova o parágrafo marcado **THE DECIDING QUESTION** — ele é o pedido inteiro.

---

<!-- RASCUNHO NAO ENVIADO — 2026-09-06. Nao envie enquanto houver [PREENCHER]. -->

**To:** Prof. Zhiyong Yuan — `zyuan@tmu.edu.cn`
**Subject:** Data access request (academic, non-commercial) — Nat Commun 2026, PMC13199442 / NCT05787522 — esophagus OAR delineations

Dear Professor Yuan,

My name is [PREENCHER: nome completo]. I am an undergraduate student at
[PREENCHER: instituição], enrolled in an undergraduate research programme
("Iniciação Científica"), supervised by [PREENCHER: nome e cargo do orientador]. I am writing
about your paper *"A prospective multicenter trial of deep learning auto-segmentation for
organs at risk in thoracic radiotherapy"* (Nat Commun 2026; DOI 10.1038/s41467-026-70863-9),
following the access procedure stated in its Data availability section.

I want to be straightforward about scale first: this is a student research project, not a
research centre, a hospital, or a company. It has no commercial sponsor and no industry
partner. I have no relationship of any kind with Perception Vision Medical Technology or with
any competing vendor, and nothing in this request involves evaluating, comparing, or
benchmarking any commercial product.

**The project.** VRmed is an educational platform for studying human anatomy in 3D and in
virtual reality. It reconstructs anatomical surfaces from open imaging datasets so that
students can inspect and manipulate them interactively. Its purpose is teaching and
methodological study. **It is not a clinical tool, it does not support any clinical decision,
it is not a medical device, and it will never be used for diagnosis, treatment planning, or
patient care.** It is also not a commercial product and is not monetised.

**The methodological question.** Our reconstruction work has repeatedly run into the
esophagus. It is not the structure with our lowest score — it is the score we cannot
interpret. For the lungs, agreement is high enough that the remaining error is clearly ours;
for the esophagus we cannot tell how much of the gap is method error and how much is simply
the range within which two qualified humans disagree on where the esophageal wall is. We are not looking for a threshold
or a pass/fail criterion — we are looking for an **observed distribution of human-to-human
disagreement on the esophagus**, so that our own results can be reported against an honest
reference rather than against nothing.

We have already made full use of the openly published material. Your Source Data file
(MOESM4) allowed us to compute, for the esophagus, the distribution of manual delineation
performance against the consensus ground truth, and the distribution of |Δ| between the two
physicians who delineated the same circulated image set. Those are informative, and we are
grateful they were published in that detail. But neither of them is a direct geometric
agreement between two human contours: the first is human-versus-consensus, and the second is
the absolute difference of two accuracies measured against the same third reference, which two
observers can drive to zero while still disagreeing with each other. **The one quantity we
cannot obtain from any open material is the pairwise agreement between two human delineations
of the same esophagus.** Your trial appears to be the only published work that contains it.

**Structures of interest**, in order of priority: **esophagus** (the reason for this request),
and secondarily heart, left and right lungs, trachea, and aorta, which are already handled by
our reconstruction pipeline and would serve as internal controls.

**What we are asking for**, in the terms of your Data availability statement:

1. Access to the planning CT images and their delineation results for the structures above,
   under whatever restrictions you consider appropriate.
2. Specifically, the **original, individual delineations produced by Expert A and by Expert
   B** — not only the ground truth finalised by Expert C.

> ### THE DECIDING QUESTION
>
> **Were the original contour sets of Expert A and of Expert B retained as separate,
> recoverable objects, with the observer identity preserved — so that they could be provided
> as two distinct sets, each attributable to its expert?**
>
> I ask this plainly because it decides whether the rest of this request has any purpose. Your
> Methods state that Experts A and B independently delineated each CT image, producing two sets
> of OARs, and that Expert C then compared them and selected the more accurate delineation
> organ by organ. If, in practice, only Expert C's final result survives in the archive — or if
> the two sets exist but can no longer be attributed to A or to B — then **the dataset cannot
> answer our question, and I would not want to consume your time or your institution's
> administrative effort on a transfer that would not help us.** A simple "no, only the
> consensus ground truth was kept" is a complete and useful answer, and I would record it as
> such. Please do not feel obliged to soften it.

**A much lower-cost alternative, if the imaging data cannot be shared.** If the raw CT and
contour data cannot leave your institutions — for privacy, for the ongoing projects mentioned
in your Data availability statement, or for any other reason — would you consider providing
**derived agreement metrics only, computed by your team, with no image or contour data
leaving your side?** Concretely, for the esophagus:

- **(a)** per-case pairwise agreement between **Expert A and Expert B** on the same CT — DSC
  and/or 95% Hausdorff distance, one row per case, fully de-identified, with no patient
  identifiers of any kind, and case labels replaced by arbitrary sequential numbers;
- **(b)** if (a) is not computable because the two expert sets were not retained, then the
  same per-case pairwise agreement between **the two physicians from adjacent centres who
  manually delineated the same circulated image set** — the pairing described in your
  Study design and analysed per OAR in your Figures 4f–i. We are aware that those figures
  report |Δ| between two accuracy scores and therefore do not, by themselves, tell us whether
  the two contour sets were retained; that is precisely what we are asking. If the masks were
  not kept either, a direct answer saying so would already be valuable to us.

Even a summary distribution — minimum, 5th, 25th, 50th, 75th, 95th percentile, maximum, and n —
rather than per-case rows, would be enough for our purpose. This is a spreadsheet, not a data
transfer, and it would fully answer the question that motivates this letter.

**Terms, ethics, and what we commit to.**

- We would like a **written statement of the licence or terms of use** governing anything you
  provide — including whether derived measurements may be reported in an academic report, and
  in what form you wish to be cited. We will follow those terms exactly, and we will not assume
  any permission that is not written down.
- We understand and accept the requirements stated in your paper: a **research protocol** and
  **proof of ethical approval**. Our current status is: [PREENCHER: situação real da aprovação
  ética — em preparo / submetida ao CEP / aprovada sob o nº ...]. We can send our research
  protocol and analysis plan on request, in English, and we will not request any transfer
  before the required approvals are in place on our side.
- We are aware that your trial registration additionally anticipates a **data exchange
  agreement with institutional approvals** prior to any transfer. We are willing to route this
  through [PREENCHER: setor/instituição que assinaria o acordo], and we accept that this may
  take time or may not be feasible for a project of our size.
- **We commit not to redistribute.** No image, no contour, and no case-level file received from
  you would be shared with any third party, published, posted, uploaded to any repository or
  model service, or included in any public release of our project. **We would not publish the
  raw data in any form.** Any use would be limited to the named people in
  [PREENCHER: nome do grupo/laboratório/disciplina], on machines under our control, deleted at
  the end of the agreed period.
- We would not use the data to train, tune, or evaluate any commercial system, and we would not
  present any result as clinical validation.

If any part of this is not possible, a short reply saying so would already be valuable to us,
and I would treat it as a definitive answer rather than as an opening for further requests.

Thank you for the unusually complete Supplementary and Source Data files accompanying the
paper — the per-case values published there have already been genuinely useful to a student
project on the other side of the world.

With respect,

[PREENCHER: nome completo]
[PREENCHER: curso / programa / instituição]
[PREENCHER: e-mail institucional, se houver — senão, o e-mail pessoal]
Supervisor: [PREENCHER: nome do orientador] — [PREENCHER: e-mail do orientador]

---

# PARTE 2 — FICHA OPERACIONAL (pt-BR)

## 2.1 Para quem enviar

| campo | valor | como consta |
|---|---|---|
| Nome | **Zhiyong Yuan** | autor correspondente, único marcado `corresp="yes"` no XML JATS |
| E-mail | **`zyuan@tmu.edu.cn`** | impresso na própria Data availability, como canal de pedido de acesso |
| Papel | Autor correspondente do artigo; `PRINCIPAL_INVESTIGATOR` do NCT05787522 | ClinicalTrials.gov (`centralContacts` = `null`) |
| ORCID | `0000-0002-4745-6895` | XML JATS |
| Afiliação | Department of Radiation Oncology, Tianjin Medical University Cancer Institute & Hospital, Tianjin, China | afiliação 1 |

**Não colocar mais ninguém em cópia.** Em especial, **não** copiar os coautores empregados da
PVmed (T. Liu, Z.Y. Yan, Y. Lu): copiar o fabricante converte um pedido acadêmico em conversa
com fornecedor. Se o usuário quiser um segundo destinatário, o único defensável é o próprio
orientador, em cópia.

## 2.2 O que anexar (nada disso existe ainda)

| anexo | exigido por | estado |
|---|---|---|
| Protocolo de pesquisa (1–3 pág., inglês) | artigo, verbatim: `with a research protocol` | **a escrever** |
| Comprovante de aprovação ética | artigo, verbatim: `and proof of ethical approval` | **[PREENCHER]** |
| Plano de análise | CT.gov: `Requests must include a detailed protocol, analysis plan` | **a escrever** |
| Acordo de transferência de dados (DTA) | CT.gov: `data exchange with institutional approvals in place before data transfer` | **fora do alcance individual** |

Nada disso é anexo do primeiro e-mail obrigatoriamente — a carta oferece enviar sob demanda.
Mas se o usuário pedir o dado bruto sem ter nada disso, a resposta previsível é o pedido dos
documentos, e a conversa morre ali.

## 2.3 O que o usuário precisa decidir ANTES de enviar

1. **Enviar as duas perguntas ou só a segunda?** Se não há aprovação ética e não há instituição
   disposta a assinar um DTA, o pedido de dado bruto é retórico. Nesse caso, **cortar os itens 1
   e 2 e enviar só a alternativa de baixo custo** — é um e-mail mais curto, mais honesto e com
   chance muito maior de resposta útil.
2. **Aprovação ética:** existe? está submetida? não existe? A carta tem um `[PREENCHER]`
   específico para isso e **não pode ser enviada com ele em branco nem com número inventado**.
3. **Quem assina.** Um pedido de dado clínico assinado só por estudante de graduação tem peso
   diferente de um coassinado pelo orientador. Decidir se o orientador assina junto ou entra em
   cópia — e obter o consentimento dele antes.
4. **E-mail de saída.** Institucional, se existir. Não usar endereço genérico para pedir dado
   clínico.
5. **Prazo.** Se a janela de 6 meses contar da publicação, ela fecha por volta de **2026-09-30**.
   Decidir se isso muda a prioridade.
6. **Vale a pena?** A pergunta científica da fase já está respondida pela Source Data aberta. O
   que resta a ganhar é o Dice humano-contra-humano direto. Se o usuário não pretende usar esse
   número, **não enviar nada** é uma decisão legítima e é a mais barata.

## 2.4 O que fazer com a resposta

- Gravar a resposta **verbatim**, sem reescrever, sem resumir e sem traduzir, como ficha de
  fonte primária em `.clinica-dados/fase12/`, com data de recebimento, remetente e o texto
  integral. Uma resposta por e-mail é fonte primária e vale exatamente o que estiver escrito
  nela — nunca o que se supôs que ela quis dizer.
- Classificar imediatamente na rubrica literal da fase:
  - **A** — acesso concedido **e** contornos originais de A e B disponíveis separadamente, com
    identificador de observador → vira referência interobservador.
  - **B** — acesso concedido, mas só o consenso/escolha de C → **não serve** para
    interobservador. Regra literal: se só o resultado de C estiver disponível, **não**
    classificar como dataset interobservador utilizável.
  - **C** — sem resposta em 15 dias úteis, ou resposta que não conclui → continua candidato
    teórico, não entra no protocolo.
  - **D** — negado ou impossível → fecha a linha como não utilizável.
- **Se vierem métricas em vez de dado:** são medidas do próprio esôfago e podem entrar como
  referência, com a fonte declarada ("comunicação por e-mail do autor correspondente, data X"),
  jamais apresentadas como dado público nem como validação clínica. Métricas de outra estrutura
  **não** valem como referência para o esôfago (Parte H).
- **Se a resposta trouxer instrução, condição ou pedido novo** (assinar algo, criar conta,
  aceitar termo, preencher formulário, enviar credencial): **parar e mostrar ao usuário**.
  Nenhuma dessas ações pode ser executada em nome dele.

## 2.5 Checklist do que NÃO prometer — nunca, em nenhuma versão da carta

- [ ] **Não** prometer coautoria, agradecimento em publicação, ou qualquer contrapartida
      acadêmica que o projeto não controla.
- [ ] **Não** dizer "validação clínica", "validado clinicamente", nem sugerir uso clínico,
      diagnóstico ou planejamento de tratamento.
- [ ] **Não** prometer redistribuição, republicação, depósito em repositório, upload para
      serviço de modelo, nem inclusão em release público — o compromisso é o oposto.
- [ ] **Não** prometer treinar ou avaliar modelo com o dado: a fase atual bloqueia treino, e o
      `BASELINE_ESOFAGO_V1` não pode ser alterado.
- [ ] **Não** oferecer comparação de desempenho com o iCurveE nem qualquer coisa que soe a
      benchmarking de produto comercial.
- [ ] **Não** inventar afiliação, orientador, laboratório, financiamento, número de aprovação
      ética, CNPJ, registro de projeto ou credencial. Marcador `[PREENCHER]` em vez de qualquer
      preenchimento por conveniência.
- [ ] **Não** afirmar que a instituição assinará um DTA antes de confirmar que ela assinaria.
- [ ] **Não** prometer prazo de conclusão, entrega de resultados ou relatório de volta que o
      projeto não tem certeza de cumprir.
- [ ] **Não** usar a palavra "paciente" nos documentos do projeto — "caso" ou "estrutura".
- [ ] **Não** insistir após uma negativa. Uma recusa é resposta completa e fecha a rubrica em D.

## 2.6 Procedência do que está escrito aqui

Todas as citações verbatim da carta e da ficha vêm do texto integral aberto
(`https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13199442/fullTextXML`, espelho legível em
`https://pmc.ncbi.nlm.nih.gov/articles/PMC13199442/`), dos anexos abertos
(`.../PMC13199442/supplementaryFiles`, cópia em `.clinica-dados/fase12/`) e do registro do
ensaio (`https://clinicaltrials.gov/api/v2/studies/NCT05787522`). Tudo obtido sem login, sem
aceite de termos e sem cadastro. Licença do artigo: CC BY-NC-ND 4.0 — **que não se estende ao
dado**, o que é justamente a razão desta carta existir.
