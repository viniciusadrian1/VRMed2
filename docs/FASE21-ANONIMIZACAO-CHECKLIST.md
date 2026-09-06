# Checklist de anonimização — VRmed

Fase 21.5 · 2026-09-06 · Auditor: [`scripts/validation/fase21/anonimizacao.py`](../scripts/validation/fase21/anonimizacao.py)

> **Este checklist não certifica anonimização.** Ele registra quatro varreduras e o que
> cada uma alcança. Um resultado "sem achado" significa *"as quatro varreduras não
> acharam"* — nunca *"o dado está anonimizado"*.
>
> A regra que motiva o documento: **remover `PatientName` não é anonimizar.** É o
> primeiro item de vinte e quatro no primeiro de quatro eixos.

---

## Eixo 1 — tags identificadoras (24 verificadas)

Subconjunto do **DICOM PS3.15, Anexo E** (*Basic Application Level Confidentiality
Profile*) aplicável a TC. A ação esperada não é a mesma para todas:

| Ação | Significado | Tags |
|---|---|---|
| **REMOVER** | não deve existir, ou deve estar vazia | `PatientBirthDate`, `PatientAddress`, `PatientTelephoneNumbers`, `OtherPatientIDs`, `OtherPatientNames`, `EthnicGroup`, `PatientComments`, `ReferringPhysicianName`, `PerformingPhysicianName`, `OperatorsName`, `PhysiciansOfRecord`, `InstitutionAddress`, `InstitutionalDepartmentName`, `DeviceSerialNumber`, `RequestingPhysician` |
| **REMOVER OU SUBSTITUIR** | pseudônimo aceitável | `PatientName`, `InstitutionName`, `StationName`, `AccessionNumber`, `StudyID`, `ContentCreatorName` |
| **SUBSTITUIR** | **deve** existir, com valor pseudonimizado | `PatientID` |
| **MANTER** | clinicamente necessária, não identificadora isolada | `PatientSex`, `PatientAge` |

**`PatientID` sai como `INDETERMINADO`, nunca `OK`.** Ele *precisa* existir — é uma das
quatro identidades que o esquema exige — e daqui não é possível saber se o valor é um
pseudônimo ou o identificador real. Marcar `OK` seria afirmar o que não se mediu.

Valores tratados como já anonimizados: vazio, `ANONYMOUS`, `ANONYMIZED`, `ANON`,
`NONE`, `UNKNOWN`, `REMOVED`, `NA`, `N/A`, `0`, `PATIENT`.

## Eixo 2 — UIDs

`StudyInstanceUID`, `SeriesInstanceUID`, `SOPInstanceUID`, `FrameOfReferenceUID`.

**UID não é identificador direto — é ligação.** Um UID original permite reencontrar o
exame no PACS de origem. O padrão manda remapear na desidentificação.

**Estado: `INDETERMINADO` por construção.** Os UIDs *devem* estar presentes (o esquema
os exige como identidade), e **não é possível, a partir do arquivo, saber se foram
remapeados**. Essa pergunta só se responde na documentação da fonte.

## Eixo 3 — tags privadas (grupo ímpar)

O grupo ímpar é espaço livre do fabricante. Já se encontrou nome de paciente e número de
prontuário ali. **É o buraco clássico** — um pipeline que limpa só as tags do Anexo E
deixa este eixo intacto.

Presença **não prova** vazamento, mas exige inspeção caso a caso.

## Eixo 4 — caminho e nome de arquivo

**Metadado também mora fora do arquivo.** O `.dcm` pode estar limpo e a pasta chamar-se
`1957-03-04_prontuario_123456789`.

Heurística: data completa, número de 9+ dígitos, e as palavras `nome`, `name`,
`paciente`, `patient`, `prontuario`, `mrn`, `cpf`, `rg`, `birth`, `nasc`, `dob`.
**Acusa demais de propósito** — um falso positivo custa uma conferência, um falso
negativo custa um vazamento.

> **Defeito real corrigido nesta fase.** A primeira versão usava `\b` nas partes
> numéricas. Como `_` **é** caractere de palavra em regex, `\b` não casa entre `04` e
> `_` — e a varredura ficava cega justamente em
> `1957-03-04_prontuario_123456789`, o padrão mais comum de nome de arquivo médico.
> O controle positivo pegou. Trocado por *lookaround* de dígito.

---

## O que este checklist NÃO cobre

| Não coberto | Por quê |
|---|---|
| **texto queimado no pixel** (*burned-in annotation*) | o auditor não lê pixel |
| **reidentificação por combinação** | data + instituição + diagnóstico raro pode identificar sem nenhuma tag identificadora |
| **datas deslocadas vs. reais** | o auditor vê a data, não sabe se foi deslocada consistentemente |
| **parecer jurídico** | licença aberta **não é** consentimento nem aprovação ética |
| **RTSTRUCT / SEG** | o auditor lê a série de imagem; objetos de contorno têm suas próprias tags de criador (`ContentCreatorName`, `ROIInterpreter`) |
| **base legal sob GDPR** | transferência e processamento fora do EEE é questão independente da licença |

## Procedimento antes de ingerir qualquer caso real

1. rodar o auditor sobre o diretório da série;
2. tratar **todo** `ACHADO` do eixo 1 como bloqueio até inspeção;
3. tratar **qualquer** tag privada como pendência de inspeção, não como falha automática;
4. registrar `ethics_approval` e `consent_basis` — **não** existem na V1; ver
   [proposta de V2](VRMED-ESOPHAGUS-DATASET-V2-PROPOSTA.md) §4;
5. anexar o JSON do auditor ao caso, com a data e a versão do auditor;
6. **escrever no relatório o que o auditor não cobre**, e não apenas o veredito.

## Estado atual

Rodado sobre a fixture sintética do funil (a única série DICOM que o projeto tem):
**sem achado nas quatro varreduras**, com `PatientID` e UIDs em `INDETERMINADO`.

**Nenhum dado clínico real foi auditado, porque nenhum foi ingerido.**
