"""Grava as fichas de fonte primaria da Fase 11-B em .clinica-dados/fase11/fichas/.

Uma ficha por candidato, com a estrutura da Parte D. Os NUMEROS vem dos
arquivos de medida (fichas/_medida/*.json) — nao sao digitados aqui; o que e
digitado sao os vereditos e as citacoes verbatim, cada uma com o arquivo local
onde o texto citado esta gravado (fichas/_bruto/*.txt).

`arquivos_lidos` sai da arvore em disco: SeriesInstanceUID = nome do diretorio,
conferido contra o _tcia_serie.json que a API devolveu.
"""
from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
FICHAS = RAIZ / ".clinica-dados/fase11/fichas"
MEDIDA = FICHAS / "_medida"
BRUTO = FICHAS / "_bruto"
VAR = RAIZ / ".clinica-dados/fase11/varredura"
HOJE = "2026-09-06"

ARVORES = {
    "Pediatric-CT-SEG": FICHAS / "_dl/Pediatric-CT-SEG",
    "Mediastinal-Lymph-Node-SEG": VAR / "dl/Mediastinal-Lymph-Node-SEG",
    "CT4Harmonization-Multicentric": VAR / "dl/CT4Harmonization-Multicentric",
    "NSCLC Radiogenomics": VAR / "dl/NSCLC_Radiogenomics",
    "Spine-Mets-CT-SEG": VAR / "Spine-Mets-CT-SEG",
    "QIBA CT-1C": VAR / "dl/QIBA_CT-1C",
}


def _medida(col: str, qual: str) -> dict:
    return json.loads((MEDIDA / f"{col.replace(' ', '_')}_{qual}.json").read_text("utf-8"))


def _lidos(col: str) -> list[dict]:
    """SeriesInstanceUID de cada serie de contorno ABERTA, com o registro da API."""
    saida = []
    for d in sorted(ARVORES[col].iterdir()):
        marcador = d / "_tcia_serie.json"
        if not marcador.is_dir() and marcador.exists():
            reg = json.loads(marcador.read_text("utf-8"))
            saida.append({
                "SeriesInstanceUID": reg["SeriesInstanceUID"],
                "StudyInstanceUID": reg["StudyInstanceUID"],
                "PatientID": reg["PatientID"],
                "Modality": reg["Modality"],
                "arquivos": sorted(p.name for p in d.glob("*.dcm")),
                "diretorio": str(d),
            })
    return saida


def _bloco(col: str) -> dict:
    c, i, r = _medida(col, "censo"), _medida(col, "idc"), _medida(col, "rotulos")
    lidos = _lidos(col)
    return {
        "medicao": {"censo_api": c, "cruzamento_idc": i, "rotulos_lidos_do_arquivo": r},
        "cobertura": {
            "series_de_contorno_na_colecao": c["contornos"],
            "cobertas_pelo_indice_idc": i["cobertos_pelo_idc"],
            "ausentes_do_indice_idc": i["ausentes_do_idc"],
            "arquivos_de_contorno_abertos": r["series_lidas"],
            "percentual_aberto": round(100 * r["series_lidas"] / max(c["contornos"], 1), 2),
        },
        "arquivos_lidos": lidos,
        "arquivos_de_medida": [
            str(MEDIDA / f"{col.replace(' ', '_')}_{q}.json") for q in ("censo", "idc", "rotulos")
        ],
    }


CMD = "cd C:/Users/vinic/Downloads/InnerVision/vrmed && ./.venv-pipeline/Scripts/python.exe -m "

FICHAS_TXT = {
    "Pediatric-CT-SEG": {
        "candidato": "Pediatric-CT-SEG (Pediatric Chest/Abdomen/Pelvic CT Exams with Expert Organ Contours)",
        "por_que_esta_ficha_existe": (
            "Unica colecao 'com esofago' da Fase 11 que nao tinha ficha de fonte primaria. "
            "A Fase 9 a excluiu por definicao nao documentavel e equivalencia anatomica, mas "
            "isso nao responde a pergunta da Fase 11: quantas anotacoes HUMANAS INDEPENDENTES "
            "de esofago existem sobre o MESMO exame?"
        ),
        "fonte": [
            {"tipo": "pagina da colecao (fonte primaria do provedor)",
             "url": "https://www.cancerimagingarchive.net/collection/pediatric-ct-seg/",
             "arquivo_local": str(BRUTO / "pediatric_ct_seg.txt")},
            {"tipo": "publicacao descritora do dataset (resumo integral)",
             "url": "https://pubmed.ncbi.nlm.nih.gov/35067940/",
             "citacao": "Jordan P, et al. Pediatric chest-abdomen-pelvis and abdomen-pelvis CT "
                        "images with expert organ contours. Med Phys. 2022 May;49(5):3523-3528.",
             "doi": "10.1002/mp.15485"},
            {"tipo": "API NBIA getSeries (colecao inteira)",
             "url": "https://services.cancerimagingarchive.net/nbia-api/services/v1/getSeries?Collection=Pediatric-CT-SEG",
             "arquivo_local": str(BRUTO / "Pediatric-CT-SEG_series.json")},
            {"tipo": "indice publico do IDC v24.2.2 (rtstruct_index)",
             "url": "https://github.com/ImagingDataCommons/idc-index"},
            {"tipo": "arquivos DICOM RTSTRUCT baixados do TCIA (20 series)",
             "url": "https://services.cancerimagingarchive.net/nbia-api/services/v1/getImage"},
        ],
        "doi": "10.7937/TCIA.X0H0-1706",
        "licenca": "Creative Commons Attribution 4.0 International (CC BY 4.0), lida do campo "
                   "LicenseName da API em 718/718 series; acesso publico, sem cadastro",
        "filtro_que_elimina": "F1",
        "filtros": {
            "F1": {"resultado": "FALHA — elimina",
                   "medido": "359 RTSTRUCT para 359 casos e 359 estudos; contornos por estudo = 1 "
                             "em 359/359; ImageCount = 1 em 359/359; o indice do IDC cobre 359/359 "
                             "series e o nome 'Esophagus' aparece exatamente UMA vez por serie "
                             "(esofagos_por_serie = {1: 359}). Um contorno de esofago por exame."},
            "F2": {"resultado": "NAO CONCLUSIVO, com contradicao medida",
                   "medido": "O artigo diz 'Expert contours were manually labeled'. No arquivo, "
                             "porem, 42/359 series declaram algum ROI com ROIGenerationAlgorithm "
                             "AUTOMATIC; das 10 dessas 42 que foram abertas, em 10/10 o ROI "
                             "'Esophagus' esta declarado AUTOMATIC. Nas 10 series sorteadas fora "
                             "desse grupo, 'Esophagus' e MANUAL em 10/10. Nao se conclui: mede-se "
                             "a divergencia entre a prosa da publicacao e o campo do arquivo."},
            "F3": {"resultado": "NAO VERIFICAVEL",
                   "medido": "Nem a pagina da colecao nem o resumo da publicacao declaram quantas "
                             "pessoas contornaram cada caso. Os agradecimentos nomeiam 7 pessoas "
                             "'for the bone contouring efforts', 2 dosimetristas 'for the initial "
                             "contour protocol evaluation' e 1 medico 'for contour review' — "
                             "nenhuma atribuicao por caso nem por estrutura. Nenhum campo DICOM "
                             "ajuda: ContentCreatorName, OperatorsName e InstitutionName estao "
                             "VAZIOS em 20/20 arquivos abertos. Lacuna declarada, nao negativo."},
            "F4": {"resultado": "OK", "medido": "CC BY 4.0 e download publico pela API do NBIA, "
                                                 "sem cadastro (as 20 series foram baixadas)."},
            "F5": {"resultado": "PARCIAL",
                   "medido": "O objeto certo existe: 'Esophagus' e uma das 29 estruturas, em TC de "
                             "torax-abdome-pelve. Mas a populacao e pediatrica ('Patient ages "
                             "range from 5 days to 16 years, with a mean age of 7'), o que nao e "
                             "o objeto do VRmed. Nao e o filtro que elimina — F1 elimina antes."},
            "F6": {"resultado": "NAO SE APLICA",
                   "medido": "Nao ha contornos multiplos a recuperar: um contorno de esofago por exame."},
            "F7": {"resultado": "NAO SE APLICA",
                   "medido": "Sem par, nao ha comparacao geometrica em mm a fazer."},
        },
        "evidencia_verbatim": [
            {"trecho": "The expert contours are stored in a single DICOM RTSTRUCT file for each subject.",
             "fonte": "Jordan P, et al., Med Phys 2022;49(5):3523-3528, resumo (secao 'Data format "
                      "and usage notes'), lido em https://pubmed.ncbi.nlm.nih.gov/35067940/ e "
                      "confirmado palavra por palavra no Europe PMC (EXT_ID:35067940)",
             "arquivo_local": str(BRUTO / "jordan2022_medphys_abstract.txt"),
             "por_que_importa": "E a declaracao da propria publicacao de que ha UM structure set "
                                "por caso — o que a medicao confirma (359/359)."},
            {"trecho": "Expert contours were manually labeled for up to 29 organ structures per subject.",
             "fonte": "idem, secao 'Acquisition and validation methods'",
             "arquivo_local": str(BRUTO / "jordan2022_medphys_abstract.txt"),
             "por_que_importa": "Diz 'manually' sem dizer por quantas pessoas (F3) e sem declarar "
                                "repeticao por observador (F1)."},
            {"trecho": "Each dataset contains expert contours of up to twenty-nine structures in DICOM RTSS format.",
             "fonte": "pagina da colecao no TCIA",
             "arquivo_local": str(BRUTO / "pediatric_ct_seg.txt")},
            {"trecho": "Note: Corrected RTSTRUCTs - 103 RTSTRUCT series incorrectly contained 2 files, "
                       "where one file had skin contours with errors and one file had corrected skin "
                       "contours. There is now only 1 file per each RTSTRUCT series containing the "
                       "corrected skin contours.",
             "fonte": "pagina da colecao no TCIA",
             "arquivo_local": str(BRUTO / "pediatric_ct_seg.txt"),
             "por_que_importa": "Este e o unico lugar da colecao onde ja existiram DOIS arquivos "
                                "por serie. NAO eram dois observadores: eram pele com erro e pele "
                                "corrigida, e a versao 2 deixou 1 arquivo por serie (ImageCount = "
                                "1 em 359/359 hoje). Armadilha da Parte C fechada com medida."},
            {"trecho": "The authors would like to thank Kate Bruckner, Jessica Contreras, Sean "
                       "Hergenrother, Maddie Johnson, Peter Lamberton, Liz McMahon and Jadie Rezach "
                       "of Marquette University for the bone contouring efforts. We would also like "
                       "to thank dosimetrists Alyssa Olson and Dana Cole for the initial contour "
                       "protocol evaluation and Dr. Gordan Wong for contour review.",
             "fonte": "pagina da colecao no TCIA (agradecimentos)",
             "arquivo_local": str(BRUTO / "pediatric_ct_seg.txt"),
             "por_que_importa": "E o mais perto que a fonte primaria chega de dizer quem contornou: "
                                "nomeia contornadores de OSSO, avaliacao de protocolo e UMA revisao. "
                                "Nada disso e 'dois observadores independentes do esofago'."},
        ],
        "parte_C_nao_confundir": (
            "Revisao nao e segundo observador: 'Dr. Gordan Wong for contour review' descreve "
            "revisao de um material unico, nao uma segunda delineacao independente arquivada. "
            "E os 103 casos que tinham 2 arquivos por serie eram versao com erro versus versao "
            "corrigida da PELE — intraobservador/correcao editorial, nunca interobservador."
        ),
        "lacunas_declaradas": [
            "Texto integral do artigo (Med Phys, pago) nao foi aberto: so o resumo integral, a "
            "pagina da colecao e os arquivos. Se o corpo do artigo declarar numero de anotadores, "
            "isso muda F3 — nao muda F1, que foi medido em 359/359.",
            "20 das 359 series de contorno foram abertas (5,57%). Os nomes de ROI, porem, saem do "
            "indice do IDC para 359/359 (100%): e sobre essa cobertura total que F1 esta decidido.",
            "A definicao anatomica do esofago (limite superior/inferior, atlas de referencia) nao "
            "foi encontrada em nenhuma das fontes abertas — permanece a lacuna que a Fase 9 apontou.",
        ],
        "veredito": (
            "Nao satisfaz F1: em 359/359 exames ha exatamente UM contorno de esofago, em um unico "
            "RTSTRUCT por caso, como a propria publicacao declara. A colecao tem o objeto certo "
            "(esofago, torax) e licenca limpa (CC BY 4.0), mas nao tem repeticao por observador. "
            "Nao foi identificado, nesta ficha, contorno de esofago duplicado em nenhum exame."
        ),
    },
    "Mediastinal-Lymph-Node-SEG": {
        "candidato": "Mediastinal-Lymph-Node-SEG (Mediastinal Lymph Node Quantification, LNQ2023)",
        "por_que_esta_ficha_existe": (
            "513 CT + 513 SEG de TORAX, vizinho anatomico direto do esofago, e zero arquivo aberto "
            "na 1a onda (a colecao caiu no bolo das 30 so-SEG marcadas INCONCLUSIVO)."
        ),
        "fonte": [
            {"tipo": "pagina da colecao (fonte primaria do provedor)",
             "url": "https://www.cancerimagingarchive.net/collection/mediastinal-lymph-node-seg/",
             "arquivo_local": str(BRUTO / "mediastinal_lymph_node_seg.txt")},
            {"tipo": "API NBIA getSeries (colecao inteira)",
             "arquivo_local": str(BRUTO / "Mediastinal-Lymph-Node-SEG_series.json")},
            {"tipo": "indice publico do IDC v24.2.2 (seg_index)"},
            {"tipo": "arquivos DICOM SEG baixados do TCIA (513 series, 100%)"},
        ],
        "doi": "10.7937/QVAZ-JA09",
        "licenca": "CC BY 4.0, lida do campo LicenseName da API em 1026/1026 series",
        "filtro_que_elimina": "F5 (e tambem F1)",
        "filtros": {
            "F1": {"resultado": "FALHA",
                   "medido": "513 SEG para 513 casos e 513 estudos; contornos por estudo = 1 em "
                             "513/513; um unico segmento por arquivo em 513/513 arquivos ABERTOS."},
            "F2": {"resultado": "OK para o que existe",
                   "medido": "SegmentAlgorithmType = MANUAL em 513/513 arquivos abertos; "
                             "anotadores humanos descritos na pagina."},
            "F3": {"resultado": "PARCIAL",
                   "medido": "A pagina descreve o perfil dos anotadores, mas nao ha atribuicao por "
                             "caso: ContentCreatorName/OperatorsName/InstitutionName vazios em 513/513."},
            "F4": {"resultado": "OK", "medido": "CC BY 4.0, download publico pela API."},
            "F5": {"resultado": "FALHA — elimina",
                   "medido": "Rotulo livre lido de 513/513 arquivos: 'Mediastinal lymph node', "
                             "unico valor; tipo codificado idem; indice do IDC confirma em 513/513. "
                             "Zero contorno de esofago na colecao. O objeto e linfonodo, nao o "
                             "orgao do VRmed."},
            "F6": {"resultado": "NAO SE APLICA", "medido": "Nao ha multiplos contornos a separar."},
            "F7": {"resultado": "NAO SE APLICA", "medido": "Sem par, sem comparacao em mm."},
        },
        "evidencia_verbatim": [
            {"trecho": "All annotators were trained radiologists or radiology domain experts with "
                       "over ten years of experience. The initial localization for the lymph nodes "
                       "in our partially annotated cases was performed as part of the clinical trial "
                       "reads by the staff at the Tumor Imaging Metrics Core (TIMC), and each case "
                       "was read by US-board certified radiologists in addition to TIMC Image "
                       "Analysts. Annotators on our project extended the initial localizations into "
                       "full segmentations in a subset of cases.",
             "fonte": "pagina da colecao no TCIA",
             "arquivo_local": str(BRUTO / "mediastinal_lymph_node_seg.txt"),
             "por_que_importa": "'each case was read by US-board certified radiologists in addition "
                                "to TIMC Image Analysts' e a frase que MAIS parece dois observadores "
                                "e NAO e: descreve a leitura clinica do ensaio (localizacao inicial) "
                                "e uma extensao posterior para segmentacao. O que ficou arquivado e "
                                "UMA segmentacao por caso — medido em 513/513."},
            {"trecho": "the Segment Editor module was used to perform manual delineation of the "
                       "lymph node boundary. The Draw tool within the Editor module was used to draw "
                       "free hand boundaries on axial cross-sections while viewing the sagittal and "
                       "coronal planes for reference. Excluded from the lesion boundary were large "
                       "vessels, artifacts, and non-nodal components.",
             "fonte": "pagina da colecao no TCIA",
             "arquivo_local": str(BRUTO / "mediastinal_lymph_node_seg.txt"),
             "por_que_importa": "Define o objeto: fronteira do LINFONODO, com vasos explicitamente "
                                "excluidos. Nao ha definicao de esofago porque nao ha esofago."},
        ],
        "parte_C_nao_confundir": (
            "Duas leituras clinicas do mesmo exame (radiologista + analista de imagem do core lab) "
            "nao sao dois contornos: a leitura produziu medida bidimensional/localizacao, e a "
            "segmentacao veio depois, uma por caso. Multi-institucional (MGH, Dana Farber, "
            "Brigham) tambem nao e multi-observador: e proveniencia dos exames."
        ),
        "lacunas_declaradas": [
            "O desafio LNQ2023 (MICCAI) distribuiu conjuntos proprios de validacao/teste; se algum "
            "deles contiver uma SEGUNDA anotacao dos MESMOS exames, isso esta fora do canal DICOM "
            "do TCIA e nao foi verificado nesta ficha. Nao se afirma ausencia — afirma-se que a "
            "colecao do TCIA, aberta em 513/513, tem uma anotacao por caso.",
        ],
        "veredito": (
            "Nao satisfaz F5 (objeto e linfonodo mediastinal; zero esofago em 513/513 arquivos "
            "abertos) nem F1 (uma segmentacao por exame). A lacuna que a 1a onda deixou — "
            "'INCONCLUSIVO, tem_esofago:false' sem ter aberto nada — esta fechada por leitura de "
            "100% dos arquivos de contorno."
        ),
    },
    "CT4Harmonization-Multicentric": {
        "candidato": "CT4Harmonization-Multicentric (A Multi-Centric Anthropomorphic 3D CT "
                     "Phantom-Based Benchmark Dataset for Harmonization)",
        "por_que_esta_ficha_existe": (
            "1.378 CT + 1.378 SEG e UM unico 'caso' — a forma exata que teria uma colecao onde "
            "varios observadores re-anotam o mesmo exame. Precisava ser aberta para saber se o "
            "'1 caso' e um paciente re-anotado ou outra coisa."
        ),
        "fonte": [
            {"tipo": "pagina da colecao (fonte primaria do provedor)",
             "url": "https://www.cancerimagingarchive.net/collection/ct4harmonization-multicentric/",
             "arquivo_local": str(BRUTO / "ct4harmonization.txt")},
            {"tipo": "artigo descritor (arXiv)", "url": "https://doi.org/10.48550/ARXIV.2507.01539"},
            {"tipo": "API NBIA getSeries (colecao inteira)",
             "arquivo_local": str(BRUTO / "CT4Harmonization-Multicentric_series.json")},
            {"tipo": "indice publico do IDC v24.2.2 (seg_index)"},
            {"tipo": "arquivos DICOM SEG baixados do TCIA (150 series)"},
        ],
        "doi": "10.7937/M0PB-BH69",
        "licenca": "CC BY 4.0, lida do campo LicenseName da API em 2756/2756 series",
        "filtro_que_elimina": "F5",
        "filtros": {
            "F1": {"resultado": "FALHA",
                   "medido": "1.378 SEG para 1.378 estudos; contornos por estudo = 1 em 1378/1378. "
                             "O '1 caso' e o PatientID unico do phantom, nao um paciente re-anotado."},
            "F2": {"resultado": "OK para o que existe",
                   "medido": "SegmentAlgorithmType = MANUAL em 900/900 segmentos lidos "
                             "(150 arquivos x 6 segmentos); descricao de serie 'Manually Segmented "
                             "Liver ROIs' em 1378/1378 pelo campo da API."},
            "F3": {"resultado": "NAO VERIFICAVEL",
                   "medido": "Nenhum campo de autoria util: ContentCreatorName = 'NIfTI to SEG' "
                             "(ferramenta de conversao) e InstitutionName = 'B' ou 'H' (codigo de "
                             "centro) nos 150 arquivos abertos. Numero de anotadores nao declarado."},
            "F4": {"resultado": "OK", "medido": "CC BY 4.0, download publico pela API."},
            "F5": {"resultado": "FALHA — elimina",
                   "medido": "Os 6 segmentos por arquivo sao normal1, normal2, cyst1, cyst2, "
                             "hemangioma, metastatsis (rotulo livre, 150/150 arquivos); tipos "
                             "codificados: Liver tissue, Cyst of liver, Hemangioma of liver, "
                             "Metastatic malignant neoplasm to liver — confirmados pelo indice do "
                             "IDC em 1378/1378. Zero esofago. Alem disso o objeto nem e humano: e "
                             "um figado 3D-impresso dentro de um phantom antropomorfico."},
            "F6": {"resultado": "NAO SE APLICA", "medido": "Nao ha multiplos contornos por exame."},
            "F7": {"resultado": "NAO SE APLICA", "medido": "Sem par, sem comparacao em mm."},
        },
        "evidencia_verbatim": [
            {"trecho": "The phantom mimics human anatomy, allowing repeated scans without radiation "
                       "delivery to real patients and isolating scanner effects by removing inter- "
                       "and intra-patient variations.",
             "fonte": "pagina da colecao no TCIA",
             "arquivo_local": str(BRUTO / "ct4harmonization.txt"),
             "por_que_importa": "O proposito declarado e isolar efeito de SCANNER removendo "
                                "variacao de paciente. Nada nesse desenho produz dois observadores."},
            {"trecho": "The 3D-printed liver includes three types of abnormal regions of interest, "
                       "including two cysts, a metastasis, and a hemangioma, with ground truth "
                       "segmentation masks that could be used for classification and segmentation.",
             "fonte": "pagina da colecao no TCIA",
             "arquivo_local": str(BRUTO / "ct4harmonization.txt"),
             "por_que_importa": "Define o objeto: figado impresso e suas lesoes. Nao ha esofago, e "
                                "nao ha anatomia humana real."},
            {"trecho": "Not available as this collection contains phantoms.",
             "fonte": "pagina da colecao no TCIA, campo de dados demograficos",
             "arquivo_local": str(BRUTO / "ct4harmonization.txt")},
            {"trecho": "For each CT scanner and each dose level, 10 repeated scans (identified in "
                       "the image series as #1 to #10) with identical settings were performed",
             "fonte": "pagina da colecao no TCIA",
             "arquivo_local": str(BRUTO / "ct4harmonization.txt"),
             "por_que_importa": "Explica os 1.378 estudos de um so 'caso': repeticao de AQUISICAO, "
                                "nao repeticao de ANOTACAO."},
        ],
        "parte_C_nao_confundir": (
            "Este e o caso-escola da Parte C. 1.378 aquisicoes do MESMO objeto, em 13 scanners de "
            "4 fabricantes e 8 instituicoes, com uma mascara por aquisicao: e variabilidade de "
            "scanner e de instituicao (inter-scanner / inter-institution), jamais interobservador. "
            "Um contorno por exame, muitos exames do mesmo objeto — o oposto do que a Fase 11 procura."
        ),
        "lacunas_declaradas": [
            "150 dos 1.378 SEG foram abertos (10,89%); os tipos codificados, porem, saem do indice "
            "do IDC para 1378/1378 (100%), e e sobre essa cobertura que F5 esta decidido. O rotulo "
            "LIVRE (onde moraria um 'Obs1') so foi lido nos 150 — nos 150, os seis rotulos sao "
            "anatomicos e identicos em todos.",
            "O artigo do arXiv nao foi aberto nesta ficha: a pagina da colecao ja declara phantom, "
            "que e o que elimina.",
        ],
        "veredito": (
            "Nao satisfaz F5: o objeto e um figado 3D-impresso em phantom, com quatro tipos de ROI "
            "hepaticos e zero esofago (cobertura 1378/1378 pelo indice; 150/150 arquivos abertos "
            "confirmam os rotulos livres). Tambem nao satisfaz F1 (um contorno por exame)."
        ),
    },
    "NSCLC Radiogenomics": {
        "candidato": "NSCLC Radiogenomics (Data for NSCLC Radiogenomics, Stanford)",
        "por_que_esta_ficha_existe": (
            "211 casos toracicos com SEG e nenhum arquivo aberto na 1a onda."
        ),
        "fonte": [
            {"tipo": "pagina da colecao (fonte primaria do provedor)",
             "url": "https://www.cancerimagingarchive.net/collection/nsclc-radiogenomics/",
             "arquivo_local": str(BRUTO / "nsclc_radiogenomics.txt")},
            {"tipo": "publicacao descritora, texto integral aberto",
             "url": "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6190740/fullTextXML",
             "citacao": "Bakr S, et al. A radiogenomic dataset of non-small cell lung cancer. "
                        "Sci Data. 2018;5:180202.",
             "doi": "10.1038/sdata.2018.202",
             "arquivo_local": str(BRUTO / "bakr2018_PMC6190740.txt")},
            {"tipo": "API NBIA getSeries (colecao inteira)",
             "arquivo_local": str(BRUTO / "NSCLC_Radiogenomics_series.json")},
            {"tipo": "indice publico do IDC v24.2.2 (seg_index)"},
            {"tipo": "arquivos DICOM SEG baixados do TCIA (144 series, 100%)"},
        ],
        "doi": "10.7937/K9/TCIA.2017.7hs46erv",
        "licenca": "CC BY 3.0, lida do campo LicenseName da API",
        "filtro_que_elimina": "F2 (e tambem F5, F6 e F1)",
        "filtros": {
            "F1": {"resultado": "FALHA",
                   "medido": "144 SEG para 211 casos; contornos por estudo = 1 em 144/144; um "
                             "unico segmento por arquivo em 144/144 arquivos abertos."},
            "F2": {"resultado": "FALHA — elimina",
                   "medido": "SegmentAlgorithmType = SEMIAUTOMATIC em 144/144 arquivos abertos, com "
                             "SegmentAlgorithmName ePAD2.0.1 (87), ePAD3.1 (43), ePAD3.3 (13) e "
                             "'Editor' (1). A publicacao declara o desenho: algoritmo automatico "
                             "nao publicado -> edicao por um radiologista -> revisao por um segundo "
                             "radiologista com discordancias DISCUTIDAS e aprovacao final por um "
                             "deles. Isto e model-in-the-loop seguido de CONSENSO, nao duas "
                             "delineacoes independentes."},
            "F3": {"resultado": "OK para o que existe",
                   "medido": "A publicacao nomeia dois radiologistas toracicos (M.K., >5 anos; "
                             "A.N.L., >20 anos), mas eles produziram um resultado UNICO."},
            "F4": {"resultado": "OK", "medido": "CC BY 3.0, download publico pela API."},
            "F5": {"resultado": "FALHA",
                   "medido": "Zero esofago em 144/144 (indice do IDC, cobertura 100%). Os rotulos "
                             "livres lidos dos arquivos sao 'Heart' (87), 'Tissue' (56) e "
                             "'Segmentation' (1), com tipos codificados Heart / Tissue / upper arm — "
                             "rotulagem que NAO corresponde ao objeto descrito pela publicacao "
                             "(segmentacao de TUMOR). Registra-se a divergencia como medida; em "
                             "nenhuma das duas leituras o objeto e o esofago."},
            "F6": {"resultado": "FALHA",
                   "medido": "So o resultado final esta arquivado (1 SEG por caso). Os contornos "
                             "individuais de M.K. e de A.N.L. nao existem no arquivo publico."},
            "F7": {"resultado": "NAO SE APLICA", "medido": "Sem par recuperavel, sem comparacao em mm."},
        },
        "evidencia_verbatim": [
            {"trecho": "Initial segmentations for 144 subjects were obtained from an axial CT image "
                       "series using an unpublished automatic segmentation algorithm. All of these "
                       "segmentations were viewed by a thoracic radiologist (M.K.) with more than 5 "
                       "years of experience and edited as necessary using ePAD. Final segmentations "
                       "were reviewed by an additional thoracic radiologist (A.N.L.); disagreements "
                       "in tumor boundaries were discussed and edited as appropriate, with final "
                       "approval by A.N.L. All segmentations are stored as DICOM Segmentation Objects.",
             "fonte": "Bakr S, et al., Sci Data 2018;5:180202, secao 'Segmentations'",
             "arquivo_local": str(BRUTO / "bakr2018_PMC6190740.txt"),
             "por_que_importa": "Fecha F2 e F6 de uma vez: origem automatica, edicao humana por "
                                "cima e resolucao de discordancia por DISCUSSAO — consenso. Dois "
                                "radiologistas envolvidos, um unico contorno arquivado."},
            {"trecho": "One radiologist (A.N.L.) with more than 20 years of experience ascribed the "
                       "semantic annotations for all subjects' CT scans using ePAD",
             "fonte": "idem, secao 'Semantic Annotations'",
             "arquivo_local": str(BRUTO / "bakr2018_PMC6190740.txt"),
             "por_que_importa": "As anotacoes semanticas (vocabulario controlado) tambem sao de UM "
                                "leitor — e nao sao contorno."},
        ],
        "parte_C_nao_confundir": (
            "Dois radiologistas tocando o mesmo contorno em sequencia (um edita, o outro revisa e "
            "aprova) e consenso, nao interobservador: a discordancia foi resolvida na hora e nao "
            "sobrou nenhum par para comparar. Alem disso, a semente foi um algoritmo automatico — "
            "cai tambem na clausula de model-in-the-loop do F2."
        ),
        "lacunas_declaradas": [
            "A pagina da colecao lista, fora do canal DICOM, 'Image segmentations produced by BAMF "
            "under the AIMI Annotations initiative' (comunidade IDC/Zenodo), que referenciam os "
            "MESMOS exames. Essas anotacoes nao foram abertas nesta ficha; nao se afirma nada sobre "
            "seu conteudo. Como sao produzidas por modelo, entrariam na discussao de F2 — mas isso "
            "e ficha de Analysis Result, nao desta colecao.",
        ],
        "veredito": (
            "Nao satisfaz F2: os contornos vem de algoritmo automatico editado por um radiologista "
            "e revisado por outro, com discordancias resolvidas por discussao — consenso "
            "model-in-the-loop, verbatim na publicacao. Tambem falha F6 (so o resultado final "
            "existe), F1 (um SEG por exame) e F5 (zero esofago em 144/144)."
        ),
    },
    "Spine-Mets-CT-SEG": {
        "candidato": "Spine-Mets-CT-SEG (Spine metastatic bone cancer: pre and post radiotherapy CT)",
        "por_que_esta_ficha_existe": "Colecao com contorno e zero arquivo aberto na 1a onda.",
        "fonte": [
            {"tipo": "pagina da colecao (fonte primaria do provedor)",
             "url": "https://www.cancerimagingarchive.net/collection/spine-mets-ct-seg/",
             "arquivo_local": str(BRUTO / "spine_mets_ct_seg.txt")},
            {"tipo": "API NBIA getSeries (colecao inteira)",
             "arquivo_local": str(BRUTO / "Spine-Mets-CT-SEG_series.json")},
            {"tipo": "indice publico do IDC v24.2.2 (seg_index)"},
            {"tipo": "arquivos DICOM SEG baixados do TCIA (55 series, 100%)"},
        ],
        "doi": "10.7937/kh36-ds04",
        "licenca": "CC BY 4.0, lida do campo LicenseName da API em 110/110 series",
        "filtro_que_elimina": "F5 (e tambem F1)",
        "filtros": {
            "F1": {"resultado": "FALHA",
                   "medido": "55 SEG para 55 casos e 55 estudos; contornos por estudo = 1 em 55/55; "
                             "cada arquivo referencia uma CT distinta (55 CT referenciadas distintas)."},
            "F2": {"resultado": "FALHA",
                   "medido": "SegmentAlgorithmType = SEMIAUTOMATIC em 782/782 segmentos lidos, "
                             "SegmentAlgorithmName = 'SlicerEditor'."},
            "F3": {"resultado": "OK para o que existe",
                   "medido": "A pagina nomeia UM anotador (iniciais RNA) para a segmentacao dos "
                             "niveis vertebrais, com verificacao pelo mesmo."},
            "F4": {"resultado": "OK", "medido": "CC BY 4.0, download publico pela API."},
            "F5": {"resultado": "FALHA — elimina",
                   "medido": "Os 17 rotulos livres lidos de 55/55 arquivos sao vertebras (T1..T12, "
                             "L1..L5); tipos codificados identicos; indice do IDC confirma em 55/55. "
                             "Zero esofago."},
            "F6": {"resultado": "NAO SE APLICA", "medido": "Nao ha multiplos contornos por exame."},
            "F7": {"resultado": "NAO SE APLICA", "medido": "Sem par, sem comparacao em mm."},
        },
        "evidencia_verbatim": [
            {"trecho": "Manual segmentation labels for the vertebral levels was performed and "
                       "verified by RNA in 3Dslicer",
             "fonte": "pagina da colecao no TCIA",
             "arquivo_local": str(BRUTO / "spine_mets_ct_seg.txt"),
             "por_que_importa": "Um anotador faz e o MESMO anotador verifica: nem dois observadores, "
                                "nem revisao independente."},
            {"trecho": "Vertebral metastatic bone lesion classifications performed by RNA (20 years "
                       "experience in biomechanics and image analysis of pathologic spines) and DBH "
                       "(49 years experience in evaluating clinical imaging of pathologic spines) "
                       "using standard radiological criteria as defined by the SINS protocol",
             "fonte": "pagina da colecao no TCIA",
             "arquivo_local": str(BRUTO / "spine_mets_ct_seg.txt"),
             "por_que_importa": "Duas pessoas aparecem aqui — mas para CLASSIFICAR lesao "
                                "(Normal/Osteolytic/Osteosclerotic/mixed), nao para contornar. "
                                "Dois classificadores nao sao dois contornos."},
        ],
        "parte_C_nao_confundir": (
            "Dois especialistas classificando lesao pelo escore SINS nao produzem dois contornos: a "
            "delineacao e de um so anotador (RNA). Concordancia de rotulo categorial nao substitui "
            "duas delineacoes geometricas — nao ha o que comparar em mm."
        ),
        "lacunas_declaradas": [
            "A colecao se chama 'pre and post radiotherapy CT', mas a API expoe 55 casos, 55 "
            "estudos e 55 CT — nao ha, no canal DICOM, o par pre/pos que o titulo sugere. Nao se "
            "afirma que ele nao existe: afirma-se que nao esta na colecao medida hoje.",
            "O modelo nnU-Net publicado pelos autores gera segmentacoes automaticas dos mesmos "
            "exames; saida de modelo nao e observador (F2) e nao foi baixada.",
        ],
        "veredito": (
            "Nao satisfaz F5 (objeto = corpos vertebrais T1-L5; zero esofago em 55/55) nem F1 (uma "
            "segmentacao por exame), e a delineacao e semiautomatica de um unico anotador (F2)."
        ),
    },
    "QIBA CT-1C": {
        "candidato": "QIBA CT-1C (RSNA QIBA Volumetric CT, Group 1C)",
        "por_que_esta_ficha_existe": (
            "O censo da API mostrou 462 series de contorno em apenas 6 estudos — 84 por estudo. "
            "E a assinatura numerica de 'varios observadores sobre o mesmo exame', e precisava ser "
            "aberta."
        ),
        "fonte": [
            {"tipo": "pagina da colecao (fonte primaria do provedor)",
             "url": "https://www.cancerimagingarchive.net/collection/qiba-ct-1c/",
             "arquivo_local": str(BRUTO / "qiba_ct_1c.txt")},
            {"tipo": "API NBIA getSeries (colecao inteira)",
             "arquivo_local": str(BRUTO / "QIBA_CT-1C_series.json")},
            {"tipo": "indice publico do IDC v24.2.2 (seg_index)"},
            {"tipo": "arquivos DICOM SEG baixados do TCIA (462 series, 100%)"},
        ],
        "doi": "10.7937/k9/tcia.2016.yxgr4blu",
        "licenca": "CC BY 3.0, lida do campo LicenseName da API em 1599/1599 series",
        "filtro_que_elimina": "F5",
        "filtros": {
            "F1": {"resultado": "SATISFEITO (para o objeto errado)",
                   "medido": "462 SEG em 6 estudos: 84 em cinco deles e 42 em um. Abrindo 462/462 "
                             "arquivos, o ContentCreatorName e 'QIBA CT 1C Reader 1' ... 'Reader 7' "
                             "— sete leitores, 66 SEG cada, e em CADA estudo os sete aparecem com o "
                             "mesmo numero de segmentacoes (12 por leitor em cinco estudos, 6 no "
                             "sexto). Varias anotacoes por exame, separadas por leitor."},
            "F2": {"resultado": "PARCIAL / DISCUTIVEL",
                   "medido": "SegmentAlgorithmType = SEMIAUTOMATED e SegmentAlgorithmName = "
                             "'Random Walker Algorithm' em 462/462. Sao leitores humanos operando "
                             "um algoritmo — nao e pseudo-label nem dois outputs do mesmo modelo "
                             "sem humano, mas tambem nao e delineacao manual."},
            "F3": {"resultado": "SATISFEITO",
                   "medido": "Sete leitores identificados NO PROPRIO ARQUIVO (ContentCreatorName), "
                             "com contagem verificavel: 66 series por leitor, 462 no total."},
            "F4": {"resultado": "SATISFEITO", "medido": "CC BY 3.0, download publico pela API, sem cadastro."},
            "F5": {"resultado": "FALHA — elimina",
                   "medido": "Species = Phantom, Subjects = 1, PatientID/PatientName = 'QIBA_CT_1C'. "
                             "Todos os 462 segmentos tem SegmentLabel 'Test Label', tipo codificado "
                             "'Neoplasm' e categoria 'Morphologically Altered Structure'. Zero "
                             "esofago; zero anatomia humana real."},
            "F6": {"resultado": "SATISFEITO",
                   "medido": "Cada leitor tem seus proprios arquivos: os contornos individuais sao "
                             "recuperaveis um a um, sem consenso pelo meio."},
            "F7": {"resultado": "PROBLEMATICO",
                   "medido": "Os SEG NAO tem ReferencedSeriesSequence nem SourceImageSequence "
                             "(verificado no arquivo); a unica ancora e o FrameOfReferenceUID. "
                             "Parear leitor-contra-leitor SOBRE A MESMA SERIE de CT exigiria "
                             "reconstruir a correspondencia por geometria, nao por referencia "
                             "declarada. Alem disso todos os ContentLabel sao '001'."},
        },
        "evidencia_verbatim": [
            {"trecho": "The QIBA CT-1C phantom collection was designed and shared to assist in "
                       "Characterizing Variability, sans Biology. This data set was contributed by "
                       "RSNA's Quantitative Imaging Biomarker Alliance activity, Volumetric CT Group "
                       "1C . Multiple image sets of the same phantoms were re-scanned across centers "
                       "to isolate contributors to variability.",
             "fonte": "pagina da colecao no TCIA",
             "arquivo_local": str(BRUTO / "qiba_ct_1c.txt"),
             "por_que_importa": "'sans Biology' e 'the same phantoms' fecham F5: nao ha paciente, "
                                "nao ha esofago."},
            {"trecho": "QIBA CT 1C Reader 1 / QIBA CT 1C Reader 2 / QIBA CT 1C Reader 3 / QIBA CT 1C "
                       "Reader 4 / QIBA CT 1C Reader 5 / QIBA CT 1C Reader 6 / QIBA CT 1C Reader 7",
             "fonte": "tag ContentCreatorName (0070,0084) lida dos 462 arquivos DICOM SEG",
             "por_que_importa": "E a evidencia mais forte desta onda de que o DESENHO procurado "
                                "existe em dado publico do TCIA: sete anotadores identificados, "
                                "sobre os mesmos exames, com arquivos separados por anotador."},
            {"trecho": "Phantom Physical Phantom 1 CT, PR, SEG, SR Phantom 36.51GB",
             "fonte": "pagina da colecao no TCIA, quadro 'Collection Snapshot' — sao os VALORES na "
                      "ordem dos rotulos Location / Species / Subjects / Data Types / Cancer Types "
                      "/ Size, como o texto da pagina os imprime",
             "arquivo_local": str(BRUTO / "qiba_ct_1c.txt"),
             "por_que_importa": "Species = Physical Phantom e Subjects = 1: nao ha exame humano."},
        ],
        "parte_C_nao_confundir": (
            "Aqui o risco e o inverso do usual: ha SETE observadores de verdade, e mesmo assim a "
            "colecao nao serve — porque o objeto e uma lesao sintetica em phantom, nao o esofago "
            "de um exame humano. Interobservador sobre o objeto errado nao vira evidencia para o "
            "objeto certo. E 'multiple image sets re-scanned across centers' continua sendo "
            "variabilidade de aquisicao, nao de observador."
        ),
        "lacunas_declaradas": [
            "Os 462 SR (structured reports) e 462 PR (presentation states) da colecao nao foram "
            "abertos; podem conter as medidas volumetricas por leitor. Nao muda F5.",
            "A pagina remete a 'QIBA CT-1C wiki page' (qibawiki.rsna.org) para detalhes do desenho "
            "de leitura; essa wiki nao foi aberta nesta ficha. A contagem de leitores nao depende "
            "dela: sai do proprio DICOM.",
        ],
        "veredito": (
            "Nao satisfaz F5: e um phantom fisico ('Characterizing Variability, sans Biology'), com "
            "lesao sintetica rotulada 'Test Label' / 'Neoplasm' e zero esofago em 462/462 arquivos. "
            "Registra-se, porem, o achado positivo: F1, F3, F4 e F6 SAO satisfeitos — sete leitores "
            "humanos identificados no arquivo, com contornos individuais recuperaveis sobre os "
            "mesmos exames. O padrao que a Fase 11 procura existe em dado publico e licenciado; "
            "o que nao existe, ate aqui, e esse padrao aplicado ao esofago."
        ),
    },
}


def main() -> int:
    FICHAS.mkdir(parents=True, exist_ok=True)
    for col, texto in FICHAS_TXT.items():
        ficha = {
            "fase": "11-B",
            "colecao_na_api_do_tcia": col,
            "data_de_acesso": HOJE,
            "pergunta_da_fase_11": (
                "Existe dataset publico, acessivel e legalmente utilizavel com >=2 anotacoes "
                "HUMANAS INDEPENDENTES do ESOFAGO sobre os MESMOS exames de TC toracica?"
            ),
            **texto,
            "comando_que_mediu": [
                f"{CMD}scripts.validation.tier2.fichas_fase11b censo \"{col}\"",
                f"{CMD}scripts.validation.tier2.fichas_fase11b_idc \"{col}\"",
                f"{CMD}scripts.validation.tier2.fichas_fase11b_rotulos \"{ARVORES[col]}\"",
                f"{CMD}scripts.validation.tier2.fichas_fase11b_medir  # grava as tres medidas",
            ],
            **_bloco(col),
        }
        destino = FICHAS / f"{col.replace(' ', '_')}.json"
        destino.write_text(json.dumps(ficha, ensure_ascii=False, indent=1), encoding="utf-8")
        print(destino.name, "->", ficha["filtro_que_elimina"],
              "| abertos", ficha["cobertura"]["arquivos_de_contorno_abertos"],
              "/", ficha["cobertura"]["series_de_contorno_na_colecao"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
