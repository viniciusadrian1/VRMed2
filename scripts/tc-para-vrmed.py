#!/usr/bin/env python
"""
tc-para-vrmed — máscaras do TotalSegmentator → GLB de malhas NOMEADAS para o
VRmed Clínica (etapa 3a). Ingestão, segmentação e QA: scripts/preparar-caso.py.

Uso:
  python scripts/tc-para-vrmed.py --input .clinica-dados/<slug>/ct.nii.gz \
      --masks-dir .clinica-dados/<slug>/masks --structures cardiaco \
      [--camaras .clinica-dados/<slug>/masks/heartchambers_highres] [--sem-pulmoes] \
      [--pulmoes-inteiros] [--max-tris 150000] --output <slug>-sem-draco.glb --report malha.json

Depois: npx gltf-transform draco entrada.glb saida.glb   (APENAS Draco; --simplify destrói anatomia.)

O GLB sai em metros, eixo Y para cima, sem espelhamento (esquerda/direita do
paciente preservadas). Com --camaras, o rótulo `heart` vira envelope translúcido
no viewer e as câmaras/artéria pulmonar entram como malhas próprias.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import nibabel as nib
import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clinica import malha as M  # noqa: E402
from clinica.segmentacao import PRESETS, info_segmentacao, rodar_segmentacao  # noqa: E402

PISO_TRIS = 3_000


def log(msg: str) -> None:
    print(f"[tc-para-vrmed] {msg}", flush=True)


def orcamentos(brutos: dict[str, int], total: int, piso: int) -> dict[str, int]:
    """Pisos garantidos para as pequenas; o que sobra é dividido proporcionalmente
    entre as grandes — sem isso 20 pisos de 3k somados às grandes estouravam o teto."""
    orc = {nome: piso for nome in brutos}
    livres = set(brutos)
    for _ in range(len(brutos)):
        restante = max(0, total - piso * (len(brutos) - len(livres)))
        soma = sum(brutos[n] for n in livres) or 1
        rebaixados = [n for n in livres if round(restante * brutos[n] / soma) < piso]
        for n in livres:
            orc[n] = max(piso, round(restante * brutos[n] / soma))
        if not rebaixados:
            break
        livres.difference_update(rebaixados)
    return orc


def carregar(caminho: Path) -> tuple[np.ndarray, np.ndarray]:
    img = nib.load(str(caminho))
    return np.asarray(img.dataobj) > 0.5, img.affine


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="CT em .nii/.nii.gz (ou pasta DICOM: roda a segmentação)")
    parser.add_argument("--output", required=True, help="GLB de saída")
    parser.add_argument("--structures", default="torax", choices=list(PRESETS))
    parser.add_argument("--max-tris", type=int, default=150_000, help="orçamento total (Quest 2: ≤150k)")
    parser.add_argument("--report", default=None, help="JSON de relatório")
    parser.add_argument("--fast", action="store_true", help="modo rápido (3 mm) se for segmentar aqui")
    parser.add_argument("--masks-dir", default=None, help="máscaras já segmentadas (preparar-caso.py)")
    parser.add_argument("--camaras", default=None, help="pasta das máscaras de heartchambers_highres")
    parser.add_argument("--pulmoes-inteiros", action="store_true", help="une os lobos em pulmão esq/dir")
    parser.add_argument("--sem-pulmoes", action="store_true", help="não exporta os pulmões (caso cardíaco)")
    parser.add_argument("--cores-tc", default=None, help="CT para pintar pelo HU (padrão: --input se for NIfTI)")
    args = parser.parse_args()

    entrada = Path(args.input)
    saida = Path(args.output)
    if not entrada.exists():
        log(f"ERRO: entrada não existe: {entrada}")
        return 1
    estruturas = PRESETS[args.structures]
    relatorio: dict = {"entrada": str(entrada), "preset": args.structures, "etapas_s": {}, "estruturas": {}}

    # ----- 1. Máscaras (reuso ou segmentação) -----
    if args.masks_dir:
        masks_dir = Path(args.masks_dir)
        log(f"reusando máscaras de {masks_dir}")
        seg = info_segmentacao(masks_dir)
        if seg:
            relatorio["totalsegmentator_versao"] = seg.get("totalsegmentator_versao")
    else:
        masks_dir = Path(".clinica-dados") / (saida.stem + "_masks")
        seg = rodar_segmentacao(entrada, masks_dir, estruturas, args.fast, log=log)
        relatorio["etapas_s"]["segmentacao"] = seg["tempo_s"]
        relatorio["totalsegmentator_versao"] = seg["totalsegmentator_versao"]

    inicio = time.time()
    arquivos = sorted(masks_dir.glob("*.nii.gz"))
    if estruturas is not None:
        arquivos = [m for m in arquivos if m.name.removesuffix(".nii.gz") in estruturas]
    if args.sem_pulmoes:
        arquivos = [m for m in arquivos if not m.name.startswith("lung")]
    if not arquivos:
        log(f"ERRO: nenhuma máscara encontrada em {masks_dir}")
        return 1

    mascaras: dict[str, np.ndarray] = {}
    affine = None
    for caminho in arquivos:
        nome = caminho.name.removesuffix(".nii.gz")
        mascaras[nome], affine = carregar(caminho)

    # Pulmões inteiros: une os lobos ANTES do marching cubes (as fissuras
    # entre lobos liam-se como "linhas soltas").
    if args.pulmoes_inteiros:
        for lado in ("left", "right"):
            lobos = [n for n in mascaras if n.startswith("lung_") and n.endswith(f"_{lado}")]
            if lobos:
                mascaras[f"lung_{lado}"] = np.logical_or.reduce([mascaras[n] for n in lobos])
                for n in lobos:
                    del mascaras[n]

    com_camaras = False
    if args.camaras:
        pasta = Path(args.camaras)
        for nome in M.CAMARAS:
            caminho = pasta / f"{nome}.nii.gz"
            if caminho.exists():
                mascaras[nome], _ = carregar(caminho)
                com_camaras = True
        log(f"câmaras: {sum(n in mascaras for n in M.CAMARAS)} de {len(M.CAMARAS)} máscaras")
        if not com_camaras:
            log(f"ERRO: nenhuma máscara de câmaras em {pasta} (tarefa heartchambers_highres não rodou?)")
            return 1

    assert affine is not None
    zooms = M.zooms_de(affine)
    log(f"{len(mascaras)} máscaras para converter (voxel {zooms.round(3).tolist()} mm)")

    # ----- 2. Limpeza na máscara (ilhas, buracos, contato com o coração) -----
    for nome in list(mascaras):
        mascaras[nome] = M.limpar(mascaras[nome], zooms, manter_todos=nome in M.CLASSES_MULTIPLAS)
    if "heart" in mascaras:
        for nome in M.ENCOSTAM_NO_CORACAO:
            if nome in mascaras:
                mascaras[nome] = M.encostar(mascaras[nome], mascaras["heart"])

    # ----- 3. CT para pintar + campos de ocupação -----
    caminho_ct = Path(args.cores_tc) if args.cores_tc else (entrada if entrada.is_file() else None)
    ct = None
    if caminho_ct is not None:
        internos = [n for n in mascaras if n.startswith("heart_")]
        externos = [n for n in mascaras if n not in internos]
        uniao = lambda nomes: np.logical_or.reduce([mascaras[n] for n in nomes]) if nomes else None  # noqa: E731
        ct = M.preparar_ct(caminho_ct, uniao(externos), uniao(internos), affine_mascaras=affine)
        log(f"pintando pelo HU de {caminho_ct.name}")

    # ----- 4. Malhas brutas (para conhecer os tamanhos) -----
    brutas: list[tuple[str, trimesh.Trimesh, int, float, list[str]]] = []
    for nome, mask in mascaras.items():
        resultado = M.malha_de_volume(mask, affine, afastamento_mm=M.afastamento_de(nome))
        if resultado is None:
            log(f"  - {nome}: vazia no exame, pulando")
            relatorio["estruturas"][nome] = {"presente": False}
            continue
        vol_mascara = float(mask.sum()) * float(np.prod(zooms)) / 1000.0
        brutas.append((nome, *resultado, vol_mascara, M.toca_borda(mask, affine)))

    # ----- 5. Orçamento proporcional + decimação + pintura -----
    orcamento_por = orcamentos({n: t for n, _, t, _, _ in brutas}, args.max_tris, PISO_TRIS)
    cena = trimesh.Scene()
    total_tris = 0
    for nome, bruta, tris_brutos, vol_mascara, bordas in brutas:
        orcamento = orcamento_por[nome]
        malha = M.decimar(bruta, orcamento)
        papel = M.papel_de(nome, com_camaras)
        M.pintar(malha, nome, papel, ct)
        cena.add_geometry(malha, node_name=nome, geom_name=nome)
        vol_malha = M.volume_ml(malha)
        perda = 1.0 - vol_malha / vol_mascara if vol_mascara else 0.0
        info = {
            "presente": True,
            "papel": papel,
            "triangulos_brutos": int(tris_brutos),
            "triangulos_finais": int(len(malha.faces)),
            "volume_mascara_ml": round(vol_mascara, 1),
            "volume_malha_ml": round(vol_malha, 1),
            "perda_volume_pct": round(100 * perda, 1),
            "toca_borda": bordas,
            "watertight": bool(malha.is_watertight),
        }
        relatorio["estruturas"][nome] = info
        total_tris += info["triangulos_finais"]
        # Em estrutura minúscula (< 10 mL) a própria malha decimada já
        # distorce o volume; o aviso vale para as grandes.
        aviso = "  AVISO: perda de volume > 5%" if perda > 0.05 and vol_mascara >= 10 else ""
        log(f"  + {nome} [{papel}]: {info['triangulos_finais']} tris (bruto {tris_brutos}), "
            f"{vol_malha:.0f}/{vol_mascara:.0f} mL{aviso}")

    relatorio["etapas_s"]["malhas"] = round(time.time() - inicio, 1)
    relatorio["triangulos_total"] = total_tris
    relatorio["com_camaras"] = com_camaras
    if total_tris == 0:
        log("ERRO: nenhuma estrutura gerou malha — o exame cobre a região do preset?")
        return 1
    if total_tris > 150_000:
        log(f"AVISO: {total_tris} tris > orçamento VR (150k). Reduza --max-tris.")

    # ----- 6. Exporta -----
    saida.parent.mkdir(parents=True, exist_ok=True)
    cena.export(str(saida))
    tamanho_mb = saida.stat().st_size / 1_048_576
    relatorio["glb"] = {"arquivo": str(saida), "mb": round(tamanho_mb, 2)}
    log(f"GLB: {saida} ({tamanho_mb:.1f} MB, {total_tris} tris)")
    log(f"Agora comprima: npx gltf-transform draco {saida} {saida.with_suffix('')}.min.glb  (SEM --simplify!)")
    if args.report:
        Path(args.report).write_text(json.dumps(relatorio, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"relatório: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
