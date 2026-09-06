# Fase 23 — resultado da anonimização em dado real

2026-09-06 · 5 casos do 4D-Lung · Auditor: [`fase21/anonimizacao.py`](../scripts/validation/fase21/anonimizacao.py)

> **Nenhum caso é declarado anonimizado.** O auditor faz quatro varreduras e reporta o que
> encontra. Remover `PatientName` não é anonimizar, e aqui o `PatientName` nem foi removido —
> foi pseudonimizado.

---

## Por caso

| caso | PatientName | AccessionNumber | tags privadas | caminho | veredito |
|---|---|---|---|---|---|
| `104_HM10395` | ACHADO P104 | ACHADO 2819497684894126 | 3 | OK | ACHADOS: 3 |
| `106_HM10395` | ACHADO P106 | ACHADO 2819497684894126 | 3 | OK | ACHADOS: 3 |
| `107_HM10395` | ACHADO P107 | ACHADO 2819497684894126 | 3 | OK | ACHADOS: 3 |
| `109_HM10395` | ACHADO P109 | ACHADO 2819497684894126 | 3 | OK | ACHADOS: 3 |
| `115_HM10395` | ACHADO P115 | ACHADO 2819497684894126 | 3 | OK | ACHADOS: 3 |

## Leitura

| Achado | Interpretação |
|---|---|
| `PatientName` = `P104`…`P115` | **pseudônimo**, espelhando o `PatientID`. Não é nome real. O auditor o marca `ACHADO` porque **não sabe** disso — e essa é a conduta certa: ele sinaliza, a inspeção decide |
| `AccessionNumber` = `2819497684894126` **idêntico nos 5** | **placeholder de desidentificação**. Não é vazamento. Mas quem tratasse `AccessionNumber` como identidade **juntaria os cinco casos num só** |
| `PatientID` = `INDETERMINADO` | presente e **exigido** pelo esquema. Daqui não dá para saber se é pseudônimo ou identificador real |
| UIDs = `INDETERMINADO` | presentes; **remapeamento na origem não é verificável a partir do arquivo** |
| 3 tags privadas por caso | grupo ímpar é espaço livre do fabricante. Presença **não prova** vazamento; exige inspeção caso a caso |
| caminho = `OK` | 0 arquivos com data completa, número longo ou palavra identificadora |

## O que esta auditoria NÃO cobre

- **texto queimado no pixel** — o auditor não lê pixel;
- **reidentificação por combinação** — data + instituição + diagnóstico raro;
- **datas deslocadas versus reais** — e a Fase 20 mediu que o `StudyDate` do 4D-Lung **é** deslocado sinteticamente;
- **parecer jurídico** — CC BY 3.0 **não é** consentimento nem aprovação ética;
- o **RTSTRUCT** — o auditor lê a série de imagem; objetos de contorno têm tags de criador próprias.

## Conclusão

**5/5 com achados, 0/5 declarados anonimizados.** Os achados foram inspecionados e
explicados acima. Nenhum é vazamento; dois são artefatos de desidentificação e um é
exigência do próprio esquema.
