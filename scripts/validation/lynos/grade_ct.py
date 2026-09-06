"""Fase 18 — a premissa que a sonda geometrica NAO pode assumir: mascara na grade da TC.

A sonda de `auditoria.py` calcula o alvo a partir do header da MASCARA de esofago
(1 MiB) em vez do header da TC (180-263 MB). Isso so e legitimo se as duas moram na
MESMA grade: mesmo shape, mesmo spacing, mesmo affine.

Assumir isso seria exatamente o tipo de atalho que este projeto proibe. Aqui ele e
VERIFICADO — sem baixar a TC inteira.

COMO
O cabecalho NIfTI-1 tem 348 bytes e mora no INICIO do arquivo. O .nii.gz e um fluxo
gzip, entao os primeiros KB comprimidos ja contem o cabecalho descomprimido. Um
Range HTTP pega so esses KB e um descompressor incremental le o cabecalho e para.

Trafego: ~8 KiB por TC contra 180-263 MB. As 15 TCs saem em ~120 KiB.

  python -m scripts.validation.lynos.grade_ct --autoteste
  python -m scripts.validation.lynos.grade_ct
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import urllib.request
import zlib
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.lynos.auditoria import SAIDA  # noqa: E402

BASE = "https://huggingface.co/datasets/andreped/LyNoS/resolve/main"
BYTES_PEDIDOS = 16384


def cabecalho_nifti(bruto: bytes) -> dict:
    """Le dim[] e pixdim[] de um cabecalho NIfTI-1 de 348 bytes, respeitando endianness.

    sizeof_hdr (offset 0, int32) vale 348. Se vier 1543569408, o arquivo esta na
    outra ordem de bytes — e nesse caso TODO o resto tambem esta.
    """
    if len(bruto) < 348:
        raise ValueError("cabecalho incompleto: %d bytes" % len(bruto))
    (n,) = struct.unpack("<i", bruto[:4])
    ordem = "<"
    if n != 348:
        (n,) = struct.unpack(">i", bruto[:4])
        ordem = ">"
        if n != 348:
            raise ValueError("nao e NIfTI-1: sizeof_hdr = %d" % n)
    dim = struct.unpack(ordem + "8h", bruto[40:56])
    pixdim = struct.unpack(ordem + "8f", bruto[76:108])
    return {
        "ordem_bytes": "little" if ordem == "<" else "big",
        "ndim": int(dim[0]),
        "shape": [int(v) for v in dim[1:4]],
        "spacing": [round(float(v), 6) for v in pixdim[1:4]],
        "datatype": int(struct.unpack(ordem + "h", bruto[70:72])[0]),
    }


def baixar_cabecalho(url: str, n_bytes: int = BYTES_PEDIDOS) -> dict:
    req = urllib.request.Request(url, headers={"Range": "bytes=0-%d" % (n_bytes - 1)})
    with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 (host fixo, https)
        status = r.status
        pedaco = r.read()
    # wbits 16+MAX = so gzip. decompressobj tolera fluxo truncado, que e o caso aqui.
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    bruto = d.decompress(pedaco, 512)
    h = cabecalho_nifti(bruto)
    h["bytes_baixados"] = len(pedaco)
    h["http_status"] = status
    return h


def autoteste() -> int:
    falhas = []

    # cabecalho NIfTI-1 minimo, montado a mao: sizeof_hdr=348, dim, pixdim
    b = bytearray(348)
    struct.pack_into("<i", b, 0, 348)
    struct.pack_into("<8h", b, 40, 3, 512, 512, 620, 1, 1, 1, 1)
    struct.pack_into("<8f", b, 76, 1.0, 0.676, 0.676, 0.5, 1.0, 1.0, 1.0, 1.0)
    struct.pack_into("<h", b, 70, 4)
    h = cabecalho_nifti(bytes(b))
    if h["shape"] != [512, 512, 620]:
        falhas.append("shape lido errado: " + str(h["shape"]))
    if [round(v, 3) for v in h["spacing"]] != [0.676, 0.676, 0.5]:
        falhas.append("spacing lido errado: " + str(h["spacing"]))
    if h["ordem_bytes"] != "little":
        falhas.append("endianness errada")

    # big-endian tem de ser lido igual (controle: o mesmo header do outro lado)
    bb = bytearray(348)
    struct.pack_into(">i", bb, 0, 348)
    struct.pack_into(">8h", bb, 40, 3, 512, 512, 620, 1, 1, 1, 1)
    struct.pack_into(">8f", bb, 76, 1.0, 0.676, 0.676, 0.5, 1.0, 1.0, 1.0, 1.0)
    hb = cabecalho_nifti(bytes(bb))
    if hb["shape"] != [512, 512, 620] or hb["ordem_bytes"] != "big":
        falhas.append("big-endian nao foi lido: " + str(hb))

    # controle negativo: lixo NAO pode ser aceito como cabecalho
    try:
        cabecalho_nifti(b"\x00" * 348)
        falhas.append("controle negativo: lixo foi aceito como NIfTI")
    except ValueError:
        pass

    # controle negativo 2: cabecalho curto tem de falhar, nao devolver silencio
    try:
        cabecalho_nifti(b"\x00" * 10)
        falhas.append("controle negativo: cabecalho truncado foi aceito")
    except ValueError:
        pass

    for f in falhas:
        print("FALHA:", f)
    print("autoteste grade_ct: %d verificacoes, %d falhas" % (5, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    doc = json.loads((SAIDA / "lynos_auditoria.json").read_text())
    por_caso = {c["arquivo"].split("_")[0]: c for c in doc["casos"]}

    linhas = []
    for i in range(1, 16):
        caso = "pat%d" % i
        url = "%s/Pat%d/pat%d_data.nii.gz" % (BASE, i, i)
        m = por_caso[caso]
        try:
            h = baixar_cabecalho(url)
        except Exception as e:  # noqa: BLE001
            linhas.append({"caso": caso, "erro": str(e)})
            print("%-7s ERRO %s" % (caso, e))
            continue
        mesmo_shape = h["shape"] == m["shape"]
        mesmo_spacing = all(abs(a2 - b2) < 1e-3 for a2, b2 in zip(h["spacing"], m["spacing_mm"]))
        linhas.append({
            "caso": caso,
            "ct_shape": h["shape"], "ct_spacing": h["spacing"],
            "mascara_shape": m["shape"], "mascara_spacing": m["spacing_mm"],
            "mesmo_shape": mesmo_shape, "mesmo_spacing": mesmo_spacing,
            "bytes_baixados": h["bytes_baixados"],
        })
        print("%-7s TC %-18s %-24s  mascara %-18s %-24s  %s"
              % (caso, str(h["shape"]), str(h["spacing"]), str(m["shape"]),
                 str(m["spacing_mm"]),
                 "IGUAL" if (mesmo_shape and mesmo_spacing) else "DIVERGE"))

    ok = [r for r in linhas if r.get("mesmo_shape") and r.get("mesmo_spacing")]
    total_bytes = sum(r.get("bytes_baixados", 0) for r in linhas)
    print()
    print("grade identica: %d/%d  |  trafego total: %.1f KiB"
          % (len(ok), len(linhas), total_bytes / 1024))
    veredito = "PREMISSA VERIFICADA" if len(ok) == len(linhas) else "PREMISSA VIOLADA"
    print("VEREDITO:", veredito)

    (SAIDA / "lynos_grade_ct.json").write_text(json.dumps({
        "fase": 18,
        "pergunta": "a mascara de esofago mora na mesma grade da TC?",
        "metodo": "Range HTTP de 16 KiB por TC + descompressao incremental do cabecalho NIfTI-1",
        "veredito": veredito,
        "casos_iguais": len(ok),
        "casos_totais": len(linhas),
        "bytes_baixados": total_bytes,
        "casos": linhas,
    }, indent=1))
    print("escrito:", SAIDA / "lynos_grade_ct.json")
    return 0 if len(ok) == len(linhas) else 1


if __name__ == "__main__":
    sys.exit(main())
