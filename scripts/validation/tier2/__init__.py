"""Tier2 — acuracia da SEGMENTACAO contra ground truth INDEPENDENTE.

Definicao de tier usada em todo o repositorio:
    Tier1 = fidelidade da RECONSTRUCAO a mascara (malha x mascara de entrada).
    Tier2 = acuracia da SEGMENTACAO contra ground truth INDEPENDENTE.  <-- aqui
    Tier3 = fantoma analitico.

Nenhum numero produzido por este pacote diz nada sobre reconstrucao. Na
decomposicao de erro (A = segmentacao, B = reconstrucao, C = simplificacao,
D = compressao) isto quantifica APENAS o bloco A. Os blocos NUNCA sao somados.

Ground truth: LCTSC (Lung CT Segmentation Challenge 2017, TCIA),
DOI 10.7937/K9/TCIA.2017.3r3fvz08, licenca CC BY 3.0 Unported — o nome e a URI
da licenca sao lidos da propria API do TCIA por serie e gravados no manifesto,
nunca digitados a mao.

Independencia do GT: o TotalSegmentator v2 (tarefa `total`) foi treinado em TCs
clinicas do University Hospital Basel; a LCTSC nao entra no treino.

Uso educacional/experimental. Nao e avaliacao clinica: "caso" e "estrutura",
nunca "paciente" ou "diagnostico".
"""
