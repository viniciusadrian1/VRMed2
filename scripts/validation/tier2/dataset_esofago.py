"""Partes 10, 15 e 16 — ingestao de dataset externo de esofago, teste de tamanho
e plano de controle de superajuste.

NAO TREINA, NAO BAIXA, NAO MEDE CASO NOVO. Este arquivo e infraestrutura e
aritmetica. Roda seco: o autoteste usa dado sintetico.

------------------------------------------------------------------------------
PARTE A — o pipeline de ingestao

Aceita um par (CT, mascara de esofago) de fonte independente e o normaliza para
o MESMO layout do LCTSC ja em uso:

    <destino>/<case_id>/gt/image.nii.gz
    <destino>/<case_id>/gt/mask_<Estrutura>.nii.gz   (foreground 255)
    <destino>/<case_id>/procedencia.json

Duas fontes, um caminho: NIfTI direto, ou DICOM+RTSTRUCT via tier2/rtstruct.py.
As duas desembocam em `_normalizar`, que e onde vivem as TRES recusas. Colocar
a recusa em um lugar so e o que impede uma fonte nova de entrar por uma porta
sem tranca.

RECUSA 1 — procedencia. `Procedencia` exige `gt_humano: bool` sem valor padrao
e levanta `ProcedenciaInvalida` se vier False. Isto e a Parte 14 do pedido
virando codigo: mascara que e saida de modelo nao entra como ground truth, e a
recusa nao depende de ninguem lembrar da regra. Ja custou caro nesta base — o
Zenodo 10.5281/zenodo.7975081 anota esofago sob CC BY 4.0 e o "ground truth"
dele e saida de nnU-Net (docs/VRMED-DATASET-MATRIX.md secao 0).

RECUSA 2 — grade. `geometria.verificar_alinhamento` compara shape, zooms,
affine e orientacao e levanta `DesalinhamentoGeometrico`. NAO ha reamostragem
em lugar nenhum deste arquivo, nem silenciosa nem declarada: reamostrar a
mascara para caber na imagem inventa fronteira que o anotador nao desenhou.
Fonte desalinhada e problema da FONTE.

RECUSA 3 — mascara vazia. Zero voxel acima do limiar e `MascaraVazia`. Um caso
vazio nao e um caso facil, e um caso quebrado: passa por todo o resto do
pipeline sem erro e envenena qualquer media.

Convencao de leitura herdada do Tier2: foreground 255, limiar > 0.5.

------------------------------------------------------------------------------
PARTE B — teste de tamanho (Parte 15)

Aritmetica sobre numeros JA MEDIDOS na fase 6 (lidos do disco, nao redigitados).
Responde "quantos casos para a razao voxel/parametro chegar a 1? e a 0,1?" e
depois DISCUTE se essa razao e criterio. Spoiler declarado antes da conta: nao
e — a conta esta aqui porque foi pedida e porque o numero grande e informativo,
nao porque ele decide.

------------------------------------------------------------------------------
PARTE C — plano de controle de superajuste (Parte 16)

Constante `PLANO_SUPERAJUSTE`, escrita antes de existir treino. Protocolo que
so vale escrito antes.
------------------------------------------------------------------------------

Uso educacional/experimental. "caso" e "estrutura", nunca "paciente".

    python -m scripts.validation.tier2.dataset_esofago --autoteste
    python -m scripts.validation.tier2.dataset_esofago
"""

from __future__ import annotations

import csv
import json
import statistics as st
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.tier2 import geometria, rtstruct as rtst  # noqa: E402

RAIZ_PADRAO = Path(".clinica-dados/tier2/lctsc")
SAIDA_PADRAO = RAIZ_PADRAO / "fase7" / "esofago" / "dataset"
FASE6 = RAIZ_PADRAO / "fase6" / "suficiencia"

NM = "nao medido"
NA = "nao aplicavel"

ESTRUTURA = "Esophagus"
FOREGROUND = 255          # convencao do dcmrtstruct2nii, herdada pelo Tier2
LIMIAR_LEITURA = 0.5

# Medido na fase 6 (docs/RELATORIO-FASE6-ONTOLOGIA-MODELO.md secao 8), confirmado
# por dois caminhos independentes. Premissa desta fase, nao remedida aqui.
PARAMETROS_REDE = 31_214_109

# Lidos de docs/VRMED-DATASET-MATRIX.md — REUSO, nao pesquisa nova. Os N vem de
# paginas e artigos; NENHUM dataset foi baixado ou inspecionado.
N_DATASETS_PUBLICOS = {
    "LCTSC": {"n": 60, "gt_humano": True, "uso": "validacao (ja em uso)"},
    "NSCLC-Radiomics": {"n": 422, "gt_humano": True, "uso": "treino, compartilha MAASTRO com o LCTSC"},
    "TotalSegmentator (Zenodo 6802613)": {
        "n": 1228, "gt_humano": False,
        "uso": "model-in-the-loop — RECUSADO por este pipeline como GT",
    },
    "AMOS22": {"n": 500, "gt_humano": False, "uso": "model-in-the-loop — RECUSADO"},
    "SegTHOR": {"n": 60, "gt_humano": True, "uso": "bloqueado por DUA"},
    "RAOS": {"n": NM, "gt_humano": True, "uso": "anotador unico, licenca nao verificada"},
}


# ============================================================ PARTE A — pipeline


class ProcedenciaInvalida(ValueError):
    """A procedencia declarada desqualifica a mascara como ground truth."""


class MascaraVazia(ValueError):
    """Zero voxel acima do limiar — caso quebrado, nao caso facil."""


@dataclass(frozen=True)
class Procedencia:
    """Procedencia de UM caso. `gt_humano` nao tem padrao: quem ingere declara.

    Um campo sem valor padrao forca a decisao a aparecer na chamada. Um padrao
    True deixaria a omissao virar aprovacao silenciosa, que e exatamente o
    modo de falha que a Parte 14 pede para fechar.
    """

    case_id: str
    dataset: str
    licenca: str
    gt_humano: bool
    instituicao: str = NM
    anotador: str = NM
    fonte_da_mascara: str = NM   # "contorno manual", "RTSTRUCT clinico", "saida de nnU-Net"...
    doi: str = NM

    def __post_init__(self) -> None:
        if not isinstance(self.gt_humano, bool):
            raise ProcedenciaInvalida(
                f"{self.case_id}: gt_humano tem que ser bool, veio {type(self.gt_humano).__name__}"
                " — um valor ambiguo nao pode virar aprovacao por acidente"
            )
        if not self.gt_humano:
            raise ProcedenciaInvalida(
                f"{self.case_id} ({self.dataset}): gt_humano=False. Mascara declarada como saida "
                f"de modelo (fonte: {self.fonte_da_mascara}) NAO entra como ground truth. "
                "Treinar contra pseudo-rotulo ensina o modelo antigo, nao a anatomia."
            )


def _ler_mascara(caminho: Path) -> np.ndarray:
    """Booleano com limiar > 0.5 — mesma regra de rtstruct.carregar_mascara."""
    return rtst.carregar_mascara(caminho)


def _normalizar(
    imagem: Path,
    mascara: Path,
    proc: Procedencia,
    destino: Path,
    estrutura: str = ESTRUTURA,
    log=print,
) -> dict:
    """Verifica e grava UM caso no layout do LCTSC. Unico ponto com as 3 recusas.

    A ordem importa: procedencia (ja imposta pelo dataclass), depois grade,
    depois conteudo. Nada e escrito antes das tres passarem.
    """
    imagem, mascara, destino = Path(imagem), Path(mascara), Path(destino)

    # RECUSA 2 — grade. Levanta DesalinhamentoGeometrico. Nunca reamostra.
    alinhamento = geometria.verificar_alinhamento(
        mascara, imagem, rotulos=("mascara", "imagem")
    )

    # RECUSA 3 — conteudo.
    m = _ler_mascara(mascara)
    n_voxels = int(m.sum())
    if n_voxels == 0:
        raise MascaraVazia(
            f"{proc.case_id}: mascara {mascara.name} nao tem voxel acima de "
            f"{LIMIAR_LEITURA} — caso nao ingerido"
        )

    desc = alinhamento["imagem"]
    spacing = desc["zooms_mm"]
    voxel_mm3 = float(np.prod(np.asarray(spacing, dtype=float)))

    dir_caso = destino / proc.case_id
    dir_gt = dir_caso / "gt"
    dir_gt.mkdir(parents=True, exist_ok=True)

    nib.save(nib.load(str(imagem)), str(dir_gt / rtst.NOME_IMAGEM))
    img_m = nib.load(str(mascara))
    nib.save(
        nib.Nifti1Image(np.where(m, FOREGROUND, 0).astype(np.uint8), img_m.affine),
        str(dir_gt / f"{rtst.PREFIXO_MASCARA}{estrutura}.nii.gz"),
    )

    registro = {
        "case_id": proc.case_id,
        "estrutura": estrutura,
        "procedencia": asdict(proc),
        "spacing_mm": list(spacing),
        "shape": list(desc["shape"]),
        "orientacao": desc["orientacao"],
        "voxel_mm3": voxel_mm3,
        "n_voxels_gt": n_voxels,
        "volume_gt_mL": n_voxels * voxel_mm3 / 1000.0,
        "foreground_gravado": FOREGROUND,
        "limiar_leitura": f"> {LIMIAR_LEITURA}",
        "reamostragem": "NENHUMA — a mascara ja estava na grade da imagem",
        "alinhamento": alinhamento,
        "origem": {"imagem": str(imagem), "mascara": str(mascara)},
    }
    (dir_caso / "procedencia.json").write_text(
        json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log(f"  {proc.case_id}: {n_voxels} voxels, spacing {spacing}, {alinhamento['veredito']}")
    return registro


def ingerir_nifti(
    imagem: Path, mascara: Path, proc: Procedencia, destino: Path, **kw
) -> dict:
    """Fonte ja em NIfTI. A validacao inteira e a de `_normalizar`."""
    return _normalizar(imagem, mascara, proc, destino, **kw)


def ingerir_dicom_rtstruct(
    dicom_dir: Path,
    arquivo_rtstruct: Path,
    roi: str,
    proc: Procedencia,
    destino: Path,
    tmp: Path | None = None,
    **kw,
) -> dict:
    """Fonte DICOM+RTSTRUCT. Converte com tier2/rtstruct.py e cai no mesmo funil.

    O `roi` tem que ser um nome REAL do arquivo — use `rtstruct.listar_rois`
    antes. Nome da literatura nao vale: e assim que se ingere a estrutura
    errada com o rotulo certo.
    """
    tmp = Path(tmp or (Path(destino) / "_conversao" / proc.case_id))
    convertido = rtst.converter(Path(arquivo_rtstruct), Path(dicom_dir), tmp, estruturas=[roi])
    caminho = convertido["mascaras"].get(roi)
    if caminho is None:
        raise FileNotFoundError(
            f"{proc.case_id}: RTSTRUCT nao produziu mascara para a ROI {roi!r}; "
            f"ROIs convertidas: {sorted(convertido['mascaras'])}"
        )
    return _normalizar(convertido["imagem"], caminho, proc, destino, **kw)


# ====================================================== PARTE B — teste de tamanho


def _medidas_fase6(fase6: Path = FASE6) -> dict:
    """Le os numeros da fase 6 do DISCO. Redigitar numero e como inventar numero."""
    j = json.loads((fase6 / "suficiencia_esofago.json").read_text(encoding="utf-8"))
    with open(fase6 / "por_caso.csv", encoding="utf-8") as fh:
        linhas = list(csv.DictReader(fh))
    inv = j["inventario"]
    voxels = [int(r["n_voxels"]) for r in linhas]
    return {
        "fonte": str(fase6),
        "split_usado": j["split_usado"],
        "n_casos": inv["n_casos"],
        "voxels_positivos": inv["n_voxels_positivos_total"],
        "volume_mediano_mL": inv["volume_mL"]["mediana"],
        "voxel_mm3_mediano": st.median(float(r["voxel_mm3"]) for r in linhas),
        "voxels_por_caso_media": sum(voxels) / len(voxels),
        "voxels_por_caso_mediana": st.median(voxels),
    }


def teste_de_tamanho(
    voxels_positivos: int,
    n_casos: int,
    voxels_por_caso: dict[str, float],
    parametros: int = PARAMETROS_REDE,
    razoes: tuple[float, ...] = (1.0, 0.1),
) -> dict:
    """Quantos casos para a razao voxel/parametro atingir cada alvo. Funcao pura.

    Tres estimadores de voxels/caso de proposito: se o veredito mudasse conforme
    o estimador, o veredito seria do estimador e nao do dado.
    """
    if parametros <= 0 or n_casos <= 0:
        raise ValueError("parametros e n_casos tem que ser positivos")
    atual = voxels_positivos / parametros
    alvos = {}
    for r in razoes:
        por_est = {
            nome: {
                "voxels_por_caso": v,
                "voxels_necessarios": r * parametros,
                "n_casos_implicado": int(-(-r * parametros // v)),  # teto
                "fator_sobre_o_que_temos": (r * parametros / v) / n_casos,
            }
            for nome, v in voxels_por_caso.items()
        }
        implicados = [d["n_casos_implicado"] for d in por_est.values()]
        alvos[f"razao_{r:g}"] = {
            "por_estimador": por_est,
            "n_casos_min": min(implicados),
            "n_casos_max": max(implicados),
            "amplitude_entre_estimadores_pct": 100 * (max(implicados) - min(implicados)) / min(implicados),
        }
    return {
        "parametros": parametros,
        "origem_dos_parametros": (
            "medido na fase 6 (rede do task total que produz o esofago), nao remedido aqui"
        ),
        "voxels_positivos": voxels_positivos,
        "n_casos": n_casos,
        "razao_voxel_por_parametro_atual": atual,
        "alvos": alvos,
        "leitura": (
            f"a razao hoje e {atual:.4f}. Chegar a 1 pede ~{alvos['razao_1']['n_casos_min']}-"
            f"{alvos['razao_1']['n_casos_max']} casos de esofago contornado por humano; chegar a "
            f"0,1 pede ~{alvos['razao_0.1']['n_casos_min']}-{alvos['razao_0.1']['n_casos_max']}. "
            "O numero de 1 e maior que a soma de TODOS os datasets publicos de esofago com GT "
            "humano listados na matriz."
        ),
    }


def confronto_com_datasets(alvo: dict, datasets: dict = N_DATASETS_PUBLICOS) -> dict:
    """O n implicado contra o n que existe. Sem baixar nada."""
    humanos = {k: v for k, v in datasets.items() if v["gt_humano"] is True and isinstance(v["n"], int)}
    soma = sum(v["n"] for v in humanos.values())
    disponivel = {k: v for k, v in humanos.items() if "bloqueado" not in v["uso"]}
    soma_disp = sum(v["n"] for v in disponivel.values())
    # O que sobra para TREINAR: acessivel menos a coorte de validacao. Somar o
    # LCTSC ao treino gastaria a unica validacao independente que existe.
    treinavel = {k: v for k, v in disponivel.items() if "validacao" not in v["uso"]}
    soma_treino = sum(v["n"] for v in treinavel.values())
    n1 = alvo["alvos"]["razao_1"]["n_casos_max"]
    n01 = alvo["alvos"]["razao_0.1"]["n_casos_max"]
    return {
        "fonte": "docs/VRMED-DATASET-MATRIX.md — reuso, nenhum dataset baixado ou inspecionado",
        "datasets_com_gt_humano": humanos,
        "soma_n_gt_humano": soma,
        "soma_n_gt_humano_acessivel": soma_disp,
        "soma_n_treinavel": soma_treino,
        "datasets_treinaveis": sorted(treinavel),
        "nota_acessivel": "SegTHOR sai da soma acessivel: DUA exige termo assinado e aprovacao humana",
        "nota_treinavel": (
            "o LCTSC sai da soma treinavel: e a coorte de validacao. Sobra o "
            "NSCLC-Radiomics, que compartilha o MAASTRO com ela — logo nem esse resto e "
            "independente da validacao."
        ),
        "n_implicado_razao_1": n1,
        "n_implicado_razao_0.1": n01,
        "razao_1_alcancavel": soma_treino >= n1,
        "razao_0.1_alcancavel": soma_treino >= n01,
        "criterio_de_alcancavel": "soma TREINAVEL (com GT humano, acessivel, fora da validacao)",
        "ressalva_soma": (
            "somar N de datasets diferentes e otimista ate para contagem: LCTSC e "
            "NSCLC-Radiomics compartilham o MAASTRO, entao os casos nao sao todos "
            "independentes; e o LCTSC e a coorte de VALIDACAO, logo nao pode entrar no treino."
        ),
    }


def _n(x: float, casas: int = 0) -> str:
    """Numero em pt-BR: ponto de milhar, virgula decimal."""
    return f"{x:,.{casas}f}".translate(str.maketrans({",": ".", ".": ","}))


# A discussao que a Parte 15 pede EXPLICITAMENTE: nao usar o numero grande como
# argumento de autoridade. Escrita como constante para ir inteira para o disco.
DISCUSSAO_CRITERIO = {
    "a_favor_da_razao": (
        "voxel/parametro e uma cota de capacidade: com 0,0157 voxel por parametro a rede tem "
        "folga de sobra para decorar cada voxel do conjunto. E a formulacao mais crua do risco "
        "e nao depende de treinar nada para ser calculada."
    ),
    "contra_a_razao": [
        "voxel nao e amostra independente: os ~16 mil voxels de um caso vem do mesmo corpo, "
        "do mesmo aparelho e do mesmo contorno. O numerador e inflado por construcao.",
        "parametro tambem nao e grau de liberdade efetivo: convolucao compartilha peso, "
        "augmentation multiplica exemplo, weight decay e early stopping cortam capacidade "
        "util. A razao trata 31 milhoes de pesos como 31 milhoes de escolhas livres, e nao sao.",
        "o criterio contradiz a pratica que funciona: a literatura de nnU-Net treina orgao com "
        "dezenas de casos e generaliza. Se a razao fosse criterio, esses trabalhos nao "
        "existiriam — e existem, entao a razao esta medindo outra coisa.",
        "a razao nao ve o que a fase 6 mediu como o problema real: ICC1 0,5098 e 0,4719 "
        "(p 0,0005) de estilo por instituicao contra 3 instituicoes so. Mais voxels da mesma "
        "convencao nao compram generalizacao entre convencoes.",
    ],
    "criterio_defensavel": {
        "1_curva_de_aprendizado": (
            "treinar com n crescente (por exemplo 8, 12, 16, 20, 24 casos) com a MESMA "
            "validacao fixa e olhar onde o Dice de validacao para de subir. Se ainda sobe no "
            "maior n, faltam casos e o numero de casos que falta e mensuravel; se ja achatou, "
            "mais casos da mesma fonte nao e o gargalo. Isto MEDE o que a razao so estima."
        ),
        "2_diferenca_treino_menos_validacao": (
            "a distancia entre Dice de treino e Dice de validacao e a medida direta de "
            "memorizacao. Capacidade sobrando so importa se ela estiver sendo usada para "
            "decorar, e essa diferenca mostra se esta."
        ),
        "3_generalizacao_entre_instituicoes": (
            "treinar deixando uma instituicao inteira de fora e avaliar nela. Como instituicao "
            "e spacing estao confundidos (S1 dz 3,0 em 10/10, S2 dz 2,5 em 10/10), esse teste "
            "mede a fragilidade que importa. Um modelo que decora estilo passa no split "
            "aleatorio e reprova aqui."
        ),
        "4_a_barra_que_ja_existe": (
            "o criterio final nao e uma razao: e superar o A_BASELINE_V1 (dice 0,8003 no "
            "esofago, n=60) por mais que LIMIAR_MELHORIA_DICE=0,01 em dado que nunca escolheu "
            "intervencao. Um modelo com razao pessima que bate o baseline no holdout e util; "
            "um modelo com razao boa que nao bate, nao e."
        ),
    },
    "veredito_honesto": (
        "a razao voxel/parametro NAO decide esta questao e nao deve ser citada como se "
        "decidisse. Ela responde 'ha capacidade para memorizar?' — sim, muita — e nao "
        "'o modelo vai memorizar?', que so a curva de aprendizado e o holdout por instituicao "
        "respondem. O numero grande fica no relatorio como contexto, nao como argumento."
    ),
}


# ========================================== PARTE C — controle de superajuste


PLANO_SUPERAJUSTE: dict[str, Any] = {
    "escrito_antes_de_qualquer_treino": True,
    "divisao": {
        "unidade": "CASO. Nunca fatia.",
        "porque": (
            "fatias vizinhas do mesmo caso sao quase a mesma imagem: mesmo corpo, mesma "
            "aquisicao, mesmo contorno, ~2,5 a 3,0 mm de distancia. Dividir por fatia poe "
            "vizinhas imediatas de cada lado da parede e a validacao passa a medir "
            "interpolacao dentro de um caso ja visto. Com esofago o vazamento e pior que o "
            "usual: sao 86,5 fatias por caso na mediana, entao cada caso vazado carrega "
            "dezenas de exemplos quase identicos."
        ),
        "implementacao": "split por case_id, como fase5.construir_split ja faz; nenhum case_id em dois conjuntos",
        "verificacao": "assert de intersecao vazia entre os conjuntos de case_id antes de comecar",
    },
    "separacao_por_instituicao": {
        "regra": (
            "quando houver mais de uma instituicao, rodar DOIS protocolos: (a) split "
            "estratificado por instituicao, que mede generalizacao entre casos; (b) "
            "leave-one-institution-out, que mede generalizacao entre convencoes de contorno."
        ),
        "porque": (
            "a fase 6 mediu ICC1 0,5098 e 0,4719 (p 0,0005) nos descritores de ESTILO e "
            "0,0788 / 0,0275 / -0,0762 (p 0,16-0,74) nos de ANATOMIA. Instituicao explica "
            "estilo de contorno e nao explica anatomia — logo o risco nao e decorar corpo, "
            "e decorar convencao."
        ),
        "confusao_declarada": (
            "instituicao e spacing estao confundidos: S1 dz 3,0 em 10/10, S2 dz 2,5 em 10/10, "
            "so S3 varia. Um leave-one-institution-out que caia mede instituicao OU spacing e "
            "nao consegue separar os dois com esta coorte. Declarar isso e parte do resultado."
        ),
        "limite": "com 3 instituicoes, sao 3 dobras — n pequeno demais para intervalo estreito. Reportar as 3, nao a media",
    },
    "augmentation": {
        "estrutura": "tubo fino, longo e de baixo contraste — 40,64 mL de mediana em 229 mm de comprimento",
        "usar": [
            "rotacao pequena (±10 graus) e escala (0,9-1,1): o esofago desvia lateralmente entre casos",
            "deformacao elastica suave: acompanha a variacao real de trajeto",
            "ruido gaussiano e simulacao de baixa resolucao: o contraste com o mediastino e o problema, treinar com ele degradado ajuda",
            "variacao de brilho/contraste e gamma: cobre diferenca de protocolo entre servicos",
            "reamostragem de spacing em Z dentro da faixa observada (2,5-3,0 mm): o spacing esta confundido com instituicao, augmentar nele ataca justamente o confundimento",
        ],
        "nao_usar": [
            "espelhamento esquerda-direita: o esofago tem lateralidade e o mediastino nao e simetrico — espelhar ensina uma anatomia que nao existe",
            "recorte agressivo que possa remover a extremidade cranial ou distal: a fase 5 mediu que o erro de extensao e DISTAL e que no lado cranial a predicao ja para 3,0 mm ANTES do GT; cortar a ponta treina o modelo a errar exatamente onde ele ja erra",
            "deformacao elastica forte: um tubo de ~168 mm2 de area mediana por fatia rompe ou funde antes de o resto da imagem se deformar de forma plausivel",
        ],
        "amostragem_de_patch": (
            "forcar fracao de patches centrados em voxel positivo. O esofago ocupa fracao "
            "minuscula do volume; amostragem uniforme entrega quase so fundo e o modelo "
            "aprende a prever vazio."
        ),
    },
    "monitorar": {
        "validation_loss": "por epoca. Subida sustentada com treino ainda caindo = memorizacao comecando",
        "dice_de_validacao": "metrica primaria de parada, agregada por CASO e nao por fatia",
        "hd95_de_validacao": (
            "obrigatorio junto com o Dice. A fase 5 mediu que o erro do esofago e de EXTENSAO "
            "e de fronteira; Dice de um tubo fino se move pouco com erro que HD95 enxerga. "
            "Duas metricas porque uma delas e cega para o modo de erro conhecido."
        ),
        "diferenca_treino_menos_validacao": "registrar sempre; e a leitura direta de memorizacao",
        "por_instituicao": "quebrar as tres metricas por instituicao a cada avaliacao — a media esconde a dobra que caiu",
        "dice_de_treino": {
            "papel": "diagnostico apenas. NAO decide nada.",
            "porque": (
                "o modelo ajusta os pesos contra exatamente esses voxels; o Dice de treino "
                "mede o que ele ja viu e sobe monotonicamente com capacidade. Com 0,0157 voxel "
                "por parametro ha folga para leva-lo perto de 1,0 sem aprender nada "
                "generalizavel. Ele so serve para uma coisa: comparado com o de validacao, "
                "dizer QUANTO da capacidade virou memorizacao. Sozinho, e ruido caro."
            ),
        },
    },
    "early_stopping": {
        "metrica": "Dice de validacao agregado por caso",
        "criterio": "parar apos 50 epocas sem melhora maior que 0,005 sobre o melhor valor ja visto",
        "0.005_de_onde_vem": (
            "metade do LIMIAR_MELHORIA_DICE=0,01 da fase 5, que por sua vez veio da meia-largura "
            "medida dos IC 95 % da coorte (0,005 a 0,031). Melhora abaixo disso nao e "
            "distinguivel de ruido nesta ordem de n; esperar por ela e esperar por ruido."
        ),
        "teto": "limite duro de epocas declarado antes do treino, para o custo ser previsivel",
        "checkpoint": "guardar o do melhor Dice de validacao, nunca o da ultima epoca",
        "nao_negociavel": (
            "o criterio e declarado ANTES e nao se mexe depois de ver a curva. Afrouxar a "
            "paciencia porque 'ia melhorar' e escolher o resultado."
        ),
        "conjunto_de_teste": (
            "o `test` nao entra em early stopping, nem em selecao de checkpoint, nem em "
            "ajuste de augmentation. Uma leitura para escolher qualquer coisa e o gasta."
        ),
    },
}


# ================================================================== orquestracao


def rodar(raiz: Path = RAIZ_PADRAO, fase6: Path | None = None) -> dict:
    med = _medidas_fase6(Path(fase6) if fase6 else Path(raiz) / "fase6" / "suficiencia")
    tamanho = teste_de_tamanho(
        med["voxels_positivos"],
        med["n_casos"],
        {
            "media_medida": med["voxels_por_caso_media"],
            "mediana_medida": med["voxels_por_caso_mediana"],
            "volume_mediano_sobre_voxel_mediano": (
                med["volume_mediano_mL"] * 1000.0 / med["voxel_mm3_mediano"]
            ),
        },
    )
    return {
        "estrutura": ESTRUTURA,
        "escopo": "Partes 10, 15 e 16 — pipeline, teste de tamanho e plano de superajuste",
        "nao_executado": [
            "nenhum dataset foi baixado", "nenhum modelo foi treinado",
            "nenhum caso externo foi ingerido — o pipeline rodou seco no autoteste",
        ],
        "split_usado": med["split_usado"],
        "medidas_fase6": med,
        "parte_a_pipeline": {
            "layout_de_saida": "<destino>/<case_id>/gt/{image.nii.gz,mask_<Estrutura>.nii.gz} + procedencia.json",
            "fontes_aceitas": ["NIfTI (imagem + mascara)", "DICOM + RTSTRUCT (via tier2/rtstruct.py)"],
            "campos_de_procedencia": [f.name for f in Procedencia.__dataclass_fields__.values()],
            "recusas": {
                "procedencia": "ProcedenciaInvalida se gt_humano nao for exatamente True",
                "grade": "DesalinhamentoGeometrico se shape/zooms/affine/orientacao divergirem",
                "conteudo": "MascaraVazia se nao houver voxel acima de 0,5",
            },
            "reamostragem": "NENHUMA em nenhum caminho — mascara fora da grade e recusada, nao corrigida",
            "foreground_gravado": FOREGROUND,
        },
        "parte_b_teste_de_tamanho": tamanho,
        "parte_b_confronto": confronto_com_datasets(tamanho),
        "parte_b_discussao": DISCUSSAO_CRITERIO,
        "parte_c_plano": PLANO_SUPERAJUSTE,
    }


def _summary_md(r: dict) -> str:
    t = r["parte_b_teste_de_tamanho"]
    c = r["parte_b_confronto"]
    m = r["medidas_fase6"]
    linhas = [
        f"# Fase 7 — dataset de {r['estrutura']}: pipeline, tamanho e superajuste",
        "",
        f"Split: **{r['split_usado']}**. " + " · ".join(r["nao_executado"]) + ".",
        "",
        "## Parte A — pipeline (roda seco)",
        "",
        "| Recusa | Excecao | Gatilho |",
        "|---|---|---|",
        "| procedencia | `ProcedenciaInvalida` | `gt_humano` diferente de `True` |",
        "| grade | `DesalinhamentoGeometrico` | shape/zooms/affine/orientacao divergem |",
        "| conteudo | `MascaraVazia` | nenhum voxel acima de 0,5 |",
        "",
        "Nenhuma reamostragem em nenhum caminho. Mascara fora da grade e recusada, nao corrigida.",
        "",
        "## Parte B — teste de tamanho",
        "",
        f"Medido na fase 6: **{_n(t['voxels_positivos'])} voxels** positivos em "
        f"**{t['n_casos']} casos**, contra **{_n(t['parametros'])} parametros**. "
        f"Razao atual **{_n(t['razao_voxel_por_parametro_atual'], 4)}**.",
        "",
        "| Alvo | n casos (min-max entre estimadores) | fator sobre os 30 que temos |",
        "|---|---|---|",
    ]
    for nome, a in t["alvos"].items():
        fator = a["n_casos_max"] / t["n_casos"]
        alvo = nome.replace("razao_", "").replace(".", ",")
        linhas.append(f"| voxel/parametro = {alvo} | "
                      f"{_n(a['n_casos_min'])} - {_n(a['n_casos_max'])} | {_n(fator, 1)}x |")
    linhas += [
        "",
        f"Estimadores de voxels/caso: media {_n(m['voxels_por_caso_media'], 1)}, mediana "
        f"{_n(m['voxels_por_caso_mediana'], 1)}, volume mediano "
        f"{_n(m['volume_mediano_mL'], 2)} mL / voxel mediano "
        f"{_n(m['voxel_mm3_mediano'], 4)} mm3 = "
        f"{_n(m['volume_mediano_mL'] * 1000 / m['voxel_mm3_mediano'], 1)}. "
        f"Amplitude entre estimadores: "
        f"{_n(t['alvos']['razao_1']['amplitude_entre_estimadores_pct'], 1)} %.",
        "",
        f"Soma de N com GT humano na matriz: **{c['soma_n_gt_humano']}**, dos quais "
        f"**{c['soma_n_gt_humano_acessivel']}** acessiveis e **{c['soma_n_treinavel']}** "
        f"treinaveis ({', '.join(c['datasets_treinaveis'])}). "
        f"Razao 1 alcancavel: **{'sim' if c['razao_1_alcancavel'] else 'nao'}**. "
        f"Razao 0,1 alcancavel: **{'sim' if c['razao_0.1_alcancavel'] else 'nao'}**.",
        "",
        f"> {c['nota_treinavel']}",
        "",
        f"> {c['ressalva_soma']}",
        "",
        "### O criterio nao e esse",
        "",
        r["parte_b_discussao"]["veredito_honesto"],
        "",
        "Criterio defensavel, em ordem:",
        "",
    ]
    for k, v in r["parte_b_discussao"]["criterio_defensavel"].items():
        linhas.append(f"{k[0]}. **{k[2:].replace('_', ' ')}** — {v}")
    linhas += [
        "",
        "## Parte C — controle de superajuste",
        "",
        f"- **Divisao por caso, nunca por fatia.** {r['parte_c_plano']['divisao']['porque']}",
        f"- **Instituicao.** {r['parte_c_plano']['separacao_por_instituicao']['regra']}",
        f"- **Augmentation.** Sem espelhamento esquerda-direita e sem recorte das pontas; "
        f"amostragem de patch forcada em voxel positivo.",
        f"- **Monitorar.** Dice de validacao (primaria) + HD95 de validacao + validation loss, "
        f"tudo por caso e quebrado por instituicao.",
        f"- **Early stopping.** {r['parte_c_plano']['early_stopping']['criterio']}.",
        f"- **Dice de treino nao decide nada.** "
        f"{r['parte_c_plano']['monitorar']['dice_de_treino']['porque']}",
        "",
    ]
    return "\n".join(linhas)


def gravar(r: dict, saida: Path = SAIDA_PADRAO, log=print) -> dict:
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    p_json = saida / "dataset_esofago.json"
    p_md = saida / "summary.md"
    p_json.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    p_md.write_text(_summary_md(r), encoding="utf-8")
    for p in (p_json, p_md):
        log(f"gravado: {p}")
    return {"json": str(p_json), "md": str(p_md)}


# ==================================================================== autoteste


def _tubo(shape=(24, 24, 30), z=(6, 22), raio=3) -> np.ndarray:
    m = np.zeros(shape, dtype=bool)
    yy, xx = np.ogrid[: shape[0], : shape[1]]
    disco = (xx - shape[1] // 2) ** 2 + (yy - shape[0] // 2) ** 2 <= raio**2
    m[:, :, z[0] : z[1]] = disco[:, :, None]
    return m


def _autoteste() -> None:
    import tempfile

    aff = np.diag([1.0, 1.0, 3.0, 1.0])
    tubo = _tubo()

    # ---------- Procedencia: gt_humano e gate, nao rotulo
    ok = Procedencia(case_id="c1", dataset="sintetico", licenca="NA", gt_humano=True)
    assert ok.gt_humano is True and ok.instituicao == NM

    # CONTROLE POSITIVO (b): gt_humano=False TEM que derrubar
    try:
        Procedencia(case_id="c2", dataset="pseudo", licenca="CC BY 4.0", gt_humano=False,
                    fonte_da_mascara="saida de nnU-Net")
    except ProcedenciaInvalida as e:
        assert "gt_humano=False" in str(e), e
    else:
        raise AssertionError("mascara declarada como saida de modelo passou pelo gate")

    # e um valor ambiguo tambem: "true", 1, None nao viram aprovacao
    for ruim in ("true", 1, None):
        try:
            Procedencia(case_id="c3", dataset="x", licenca="y", gt_humano=ruim)  # type: ignore[arg-type]
        except ProcedenciaInvalida:
            pass
        else:
            raise AssertionError(f"gt_humano={ruim!r} passou pelo gate")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        img = td / "image.nii.gz"
        msk = td / "mask.nii.gz"
        nib.save(nib.Nifti1Image(np.zeros(tubo.shape, np.int16), aff), str(img))
        nib.save(nib.Nifti1Image(tubo.astype(np.uint8), aff), str(msk))
        destino = td / "out"

        # ---------- caminho feliz
        reg = ingerir_nifti(img, msk, ok, destino, log=lambda *_: None)
        assert reg["n_voxels_gt"] == int(tubo.sum()), reg["n_voxels_gt"]
        assert reg["voxel_mm3"] == 3.0 and reg["spacing_mm"] == [1.0, 1.0, 3.0]
        assert abs(reg["volume_gt_mL"] - int(tubo.sum()) * 3.0 / 1000) < 1e-12
        gravada = destino / "c1" / "gt" / f"mask_{ESTRUTURA}.nii.gz"
        assert gravada.exists() and (destino / "c1" / "gt" / "image.nii.gz").exists()
        assert (destino / "c1" / "procedencia.json").exists()
        # foreground 255 e leitura pelo limiar > 0,5 devolvem a MESMA mascara
        bruto = np.asarray(nib.load(str(gravada)).dataobj)
        assert set(np.unique(bruto)) == {0, FOREGROUND}, np.unique(bruto)
        assert np.array_equal(_ler_mascara(gravada), tubo), "round-trip mudou a mascara"

        # CONTROLE POSITIVO (a): mascara fora da grade TEM que derrubar.
        # Tres desalinhamentos diferentes, porque um so testaria uma comparacao so.
        deslocada = aff.copy()
        deslocada[2, 3] += 1.5
        for nome, aff_ruim, shape_ruim in (
            ("origem", deslocada, tubo.shape),
            ("spacing", np.diag([1.0, 1.0, 2.5, 1.0]), tubo.shape),
            ("shape", aff, (24, 24, 29)),
        ):
            dados = tubo if shape_ruim == tubo.shape else _tubo(shape=shape_ruim)
            ruim = td / f"ruim_{nome}.nii.gz"
            nib.save(nib.Nifti1Image(dados.astype(np.uint8), aff_ruim), str(ruim))
            p = Procedencia(case_id=f"fora_{nome}", dataset="s", licenca="NA", gt_humano=True)
            try:
                ingerir_nifti(img, ruim, p, destino, log=lambda *_: None)
            except geometria.DesalinhamentoGeometrico as e:
                assert nome in str(e) or "affine" in str(e), (nome, str(e))
            else:
                raise AssertionError(f"mascara com {nome} divergente entrou no dataset")
            assert not (destino / p.case_id).exists(), "recusa gravou caso mesmo assim"

        # CONTROLE POSITIVO (c): mascara vazia TEM que derrubar
        vazia = td / "vazia.nii.gz"
        nib.save(nib.Nifti1Image(np.zeros(tubo.shape, np.uint8), aff), str(vazia))
        p_vazia = Procedencia(case_id="vazio", dataset="s", licenca="NA", gt_humano=True)
        try:
            ingerir_nifti(img, vazia, p_vazia, destino, log=lambda *_: None)
        except MascaraVazia as e:
            assert "vazia.nii.gz" in str(e), e
        else:
            raise AssertionError("mascara vazia entrou no dataset")
        assert not (destino / "vazio").exists()

        # so um caso foi realmente ingerido
        assert sorted(p.name for p in destino.iterdir()) == ["c1"], list(destino.iterdir())

        # uma mascara so com valor 1 (foreground 1, nao 255) tem que passar igual:
        # o limiar e > 0,5, nao == 255
        assert _ler_mascara(msk).sum() == tubo.sum()

    # ---------- Parte B: aritmetica confere a mao
    t = teste_de_tamanho(488_710, 30, {"a": 16_290.333333333334}, parametros=31_214_109)
    assert abs(t["razao_voxel_por_parametro_atual"] - 488_710 / 31_214_109) < 1e-15
    assert t["alvos"]["razao_1"]["n_casos_min"] == 1917, t["alvos"]["razao_1"]
    assert t["alvos"]["razao_0.1"]["n_casos_min"] == 192, t["alvos"]["razao_0.1"]
    # CONTROLE POSITIVO: alvo 10x menor tem que pedir 10x menos casos
    assert (t["alvos"]["razao_1"]["n_casos_min"]
            > 9 * t["alvos"]["razao_0.1"]["n_casos_min"]), "os alvos nao escalam"
    # dobrar voxels/caso tem que METADE o n implicado
    t2 = teste_de_tamanho(488_710, 30, {"a": 2 * 16_290.333333333334}, parametros=31_214_109)
    assert t2["alvos"]["razao_1"]["n_casos_min"] == 959, t2["alvos"]["razao_1"]["n_casos_min"]
    for ruim in ((0, 30), (31_214_109, 0)):
        try:
            teste_de_tamanho(488_710, ruim[1], {"a": 1.0}, parametros=ruim[0] or 31_214_109)
            if ruim[1] == 0:
                raise AssertionError("n_casos=0 passou")
        except ValueError:
            pass

    conf = confronto_com_datasets(t)
    assert conf["razao_1_alcancavel"] is False, conf["soma_n_treinavel"]
    assert "TotalSegmentator (Zenodo 6802613)" not in conf["datasets_com_gt_humano"], (
        "dataset model-in-the-loop entrou na soma de GT humano"
    )
    # as tres somas tem que ser estritamente decrescentes: total > acessivel > treinavel.
    # Se alguma empatar, um filtro deixou de filtrar.
    assert (conf["soma_n_gt_humano"] > conf["soma_n_gt_humano_acessivel"]
            > conf["soma_n_treinavel"]), conf
    assert "LCTSC" not in conf["datasets_treinaveis"], "a coorte de validacao entrou no treino"
    assert "SegTHOR" not in conf["datasets_treinaveis"], "dataset bloqueado por DUA entrou"

    assert _n(31_214_109) == "31.214.109", _n(31_214_109)
    assert _n(0.015657, 4) == "0,0157", _n(0.015657, 4)

    # ---------- Parte C: o plano nao pode ficar vago em silencio
    assert PLANO_SUPERAJUSTE["divisao"]["unidade"].startswith("CASO")
    assert "espelhamento" in " ".join(PLANO_SUPERAJUSTE["augmentation"]["nao_usar"])
    assert PLANO_SUPERAJUSTE["monitorar"]["dice_de_treino"]["papel"].endswith("decide nada.")
    assert "0,005" in PLANO_SUPERAJUSTE["early_stopping"]["criterio"].replace("0.005", "0,005")

    print("dataset_esofago.py: autoteste OK")


def _main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--autoteste" in argv:
        _autoteste()
        return 0
    raiz = Path(argv[argv.index("--raiz") + 1]) if "--raiz" in argv else RAIZ_PADRAO
    r = rodar(raiz)
    gravar(r, raiz / "fase7" / "esofago" / "dataset")
    print("\n" + _summary_md(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
