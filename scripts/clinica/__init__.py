"""
Pacote do pipeline clínico do VRmed:

  TC (DICOM | NRRD | NIfTI) → ingestao (NIfTI em HU, espaçamento validado)
     → segmentacao (TotalSegmentator, inferência) → máscaras por estrutura
     → metricas (volume, bbox, componentes) + qa (máscaras sobre a TC)
     → [malha: ainda em scripts/tc-para-vrmed.py]

Os CLIs em scripts/ inserem scripts/ no sys.path antes de importar; na Fase 3
o worker (Modal) importa este mesmo pacote. Nada aqui treina modelo nem usa
IA generativa — regra do PROMPT-CLINICA.
"""
