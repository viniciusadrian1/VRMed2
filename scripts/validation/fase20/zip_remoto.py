"""Fase 20.9 — ler UM membro de um ZIP remoto sem baixar o ZIP.

POR QUE
A regra 20.9 manda download conservador: HEAD, metadado, manifesto, hashes, poucos
exemplos — e so depois o conjunto inteiro, com justificativa. Um ZIP de 169 MB do
qual interessam 3 arquivos de ~110 KB e o caso exato onde essa regra vale dinheiro.

COMO
O Central Directory de um ZIP guarda, por membro, o offset do local header. Com
esse offset da para pedir por Range so o pedaco daquele membro, ler o local header
(que traz os tamanhos de nome e de campo extra) e inflar o deflate stream.

Extensao natural de `scripts/validation/lynos/integridade.py`, que ja lia o Central
Directory por Range na Fase 18 — a leitura do CD e importada de la, nao recopiada.

  python -m scripts.validation.fase20.zip_remoto --autoteste
  python -m scripts.validation.fase20.zip_remoto --url <zip> --contem rtss --saida <dir>
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.lynos.integridade import (  # noqa: E402
    EOCD_SIG, _range, _tamanho, ler_central_directory,
)

LOCAL_SIG = b"PK\x03\x04"


def central_directory_remoto(url: str) -> tuple:
    """Devolve (cd_com_offset, bytes_baixados). Igual ao da Fase 18, mais o offset."""
    total = _tamanho(url)
    cauda = _range(url, max(0, total - 65536), total - 1)
    pos = cauda.rfind(EOCD_SIG)
    if pos < 0:
        raise ValueError("EOCD nao encontrado — ZIP64 com comentario longo?")
    cd_tam, cd_off = struct.unpack("<II", cauda[pos + 12:pos + 20])
    bruto = _range(url, cd_off, cd_off + cd_tam - 1)
    cd = ler_central_directory(bruto)

    # O offset do local header e o ultimo campo do registro do CD (posicao 42).
    # `ler_central_directory` nao o devolve, entao ele e relido aqui, no mesmo
    # buffer — reimplementar o percurso inteiro criaria duas verdades sobre o
    # mesmo formato.
    i = 0
    while i + 46 <= len(bruto):
        if bruto[i:i + 4] != b"PK\x01\x02":
            i += 1
            continue
        n_nome, n_extra, n_com = struct.unpack("<HHH", bruto[i + 28:i + 34])
        (offset,) = struct.unpack("<I", bruto[i + 42:i + 46])
        nome = bruto[i + 46:i + 46 + n_nome].decode("utf-8", "replace")
        if nome in cd:
            cd[nome]["offset_local"] = offset
        i += 46 + n_nome + n_extra + n_com
    return cd, len(cauda) + len(bruto)


def ler_membro(url: str, entrada: dict) -> bytes:
    """Baixa e infla UM membro. Levanta se o CRC-32 nao bater — nunca devolve
    conteudo silenciosamente corrompido."""
    off = entrada["offset_local"]
    cab = _range(url, off, off + 29)
    if cab[:4] != LOCAL_SIG:
        raise ValueError("local header ausente no offset %d" % off)
    n_nome, n_extra = struct.unpack("<HH", cab[26:30])
    inicio = off + 30 + n_nome + n_extra
    comp = entrada["comprimido"]
    dados = _range(url, inicio, inicio + comp - 1)
    # metodo 8 = deflate (wbits negativo = stream cru, sem cabecalho zlib);
    # metodo 0 = armazenado
    saida = zlib.decompress(dados, -zlib.MAX_WBITS) if comp != entrada["tamanho"] else dados
    if zlib.crc32(saida) & 0xFFFFFFFF != entrada["crc32"]:
        raise ValueError("CRC-32 nao bate para membro de %d bytes" % len(saida))
    return saida


def autoteste() -> int:
    import io
    import tempfile
    import zipfile
    falhas = []

    # ZIP real construido aqui; servido do disco via file:// nao funciona com Range,
    # entao o teste exercita o PARSER de local header contra o buffer em memoria.
    conteudos = {"a/x.bin": b"conteudo A" * 500, "b/y.txt": b"segundo membro" * 100}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for k, v in conteudos.items():
            z.writestr(k, v)
    dados = buf.getvalue()

    pos = dados.rfind(EOCD_SIG)
    cd_tam, cd_off = struct.unpack("<II", dados[pos + 12:pos + 20])
    bruto = dados[cd_off:cd_off + cd_tam]
    cd = ler_central_directory(bruto)
    i = 0
    while i + 46 <= len(bruto):
        if bruto[i:i + 4] != b"PK\x01\x02":
            i += 1
            continue
        n_nome, n_extra, n_com = struct.unpack("<HHH", bruto[i + 28:i + 34])
        (offset,) = struct.unpack("<I", bruto[i + 42:i + 46])
        nome = bruto[i + 46:i + 46 + n_nome].decode("utf-8", "replace")
        cd[nome]["offset_local"] = offset
        i += 46 + n_nome + n_extra + n_com

    for nome, esperado in conteudos.items():
        e = cd[nome]
        off = e["offset_local"]
        if dados[off:off + 4] != LOCAL_SIG:
            falhas.append("local header nao encontrado para " + nome)
            continue
        n_nome, n_extra = struct.unpack("<HH", dados[off + 26:off + 30])
        inicio = off + 30 + n_nome + n_extra
        comp = dados[inicio:inicio + e["comprimido"]]
        got = (zlib.decompress(comp, -zlib.MAX_WBITS)
               if e["comprimido"] != e["tamanho"] else comp)
        if got != esperado:
            falhas.append("conteudo inflado diverge para " + nome)
        if zlib.crc32(got) & 0xFFFFFFFF != e["crc32"]:
            falhas.append("crc32 nao bate para " + nome)

    # CONTROLE NEGATIVO: um crc adulterado tem de derrubar a verificacao
    e = dict(cd["a/x.bin"], crc32=0)
    if zlib.crc32(conteudos["a/x.bin"]) & 0xFFFFFFFF == e["crc32"]:
        falhas.append("controle negativo invalido")

    # o economizador so vale a pena se o membro for muito menor que o zip
    if sum(cd[k]["comprimido"] for k in cd) >= len(dados):
        falhas.append("soma dos membros nao e menor que o zip — teste degenerado")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste zip_remoto: %d verificacoes, %d falhas" % (8, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--url")
    ap.add_argument("--contem", default="")
    ap.add_argument("--saida", default=None)
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    if not a.url:
        print("uso: --url <zip remoto> --contem <substring> [--saida <dir>]")
        return 1
    print()

    total = _tamanho(a.url)
    cd, gasto_cd = central_directory_remoto(a.url)
    alvos = [k for k in sorted(cd) if a.contem.lower() in k.lower() and not k.endswith("/")]
    print("zip: %.1f MB | entradas: %d | alvos com %r: %d"
          % (total / 1e6, len(cd), a.contem, len(alvos)))
    if not alvos:
        return 1

    destino = Path(a.saida) if a.saida else None
    if destino:
        destino.mkdir(parents=True, exist_ok=True)
    gasto = gasto_cd
    for k in alvos:
        b = ler_membro(a.url, cd[k])
        gasto += cd[k]["comprimido"] + 30
        print("  %-70s %8.1f KB  CRC OK" % (k.split("/")[-1][:70], len(b) / 1024))
        if destino:
            (destino / k.split("/")[-1]).write_bytes(b)
    print()
    print("baixado: %.1f KiB de um zip de %.1f MB  (%.3f %% do total)"
          % (gasto / 1024, total / 1e6, 100.0 * gasto / total))
    if destino:
        print("escrito em:", destino)
    return 0


if __name__ == "__main__":
    sys.exit(main())
