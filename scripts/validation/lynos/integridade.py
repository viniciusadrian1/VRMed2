"""Fase 18 — as mascaras que medimos sao as mascaras que a licenca cobre?

A PERGUNTA, E POR QUE ELA NAO E RETORICA
A Fase 18 mediu a ontologia em 15 arquivos baixados do HUGGINGFACE. A licenca que a
mesma fase resolveu (CC BY 4.0) e a do ZENODO. Sao dois hosts diferentes, e o
raciocinio "o loader do HF baixa do Zenodo, logo e o mesmo dado" e INFERENCIA sobre
um script — nao verificacao dos bytes.

Se os dois hosts divergirem em qualquer arquivo, entao ou a medicao de ontologia nao
vale para o dado licenciado, ou a licenca apurada nao vale para o dado medido. As duas
metades da Fase 18 ficariam desconectadas.

COMO VERIFICAR SEM BAIXAR 2,9 GB
Um arquivo ZIP termina com o End Of Central Directory, e o Central Directory lista
cada membro com nome, tamanho comprimido, tamanho original e **CRC-32 do conteudo
descomprimido**. Dois Range HTTP bastam: um para achar o EOCD no fim, outro para ler
o Central Directory. O CRC-32 local sai do arquivo em disco.

CRC-32 nao e criptografico e nao serve contra adversario. Nao e disso que se trata
aqui: a pergunta e se dois espelhos do mesmo deposito carregam o mesmo conteudo, e
para colisao acidental em 15 arquivos ele e suficiente — e e o unico digest que o
formato ZIP oferece de graca.

  python -m scripts.validation.lynos.integridade --autoteste
  python -m scripts.validation.lynos.integridade
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

RAIZ = Path(__file__).resolve().parents[3]
LOCAL = RAIZ / ".clinica-dados" / "fase18" / "lynos"
ZIP_URL = "https://zenodo.org/records/10102261/files/LyNoS.zip"

EOCD_SIG = b"PK\x05\x06"
CD_SIG = b"PK\x01\x02"


def _range(url: str, inicio: int, fim: int) -> bytes:
    req = urllib.request.Request(url, headers={"Range": "bytes=%d-%d" % (inicio, fim)})
    with urllib.request.urlopen(req, timeout=180) as r:  # noqa: S310 (host fixo, https)
        return r.read()


def _tamanho(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310
        n = r.headers.get("Content-Length")
        if n is None:
            raise RuntimeError("servidor nao informou Content-Length")
        return int(n)


def ler_central_directory(bruto: bytes) -> dict:
    """Percorre o Central Directory e devolve {nome: {crc32, tamanho, comprimido}}.

    Le a estrutura de verdade, campo a campo, em vez de procurar padroes: um parser
    por regex sobre binario acha assinatura dentro de dado comprimido e mente.
    """
    saida = {}
    i = 0
    while i + 46 <= len(bruto):
        if bruto[i:i + 4] != CD_SIG:
            i += 1
            continue
        crc, comp, orig, n_nome, n_extra, n_com = struct.unpack("<IIIHHH", bruto[i + 16:i + 34])
        nome = bruto[i + 46:i + 46 + n_nome].decode("utf-8", "replace")
        saida[nome] = {"crc32": crc, "tamanho": orig, "comprimido": comp}
        i += 46 + n_nome + n_extra + n_com
    return saida


def crc32_arquivo(caminho: Path, bloco: int = 1 << 20) -> int:
    c = 0
    with Path(caminho).open("rb") as fh:
        for pedaco in iter(lambda: fh.read(bloco), b""):
            c = zlib.crc32(pedaco, c)
    return c & 0xFFFFFFFF


def autoteste() -> int:
    import io
    import tempfile
    import zipfile
    falhas = []

    # ZIP real, construido aqui, com conteudo conhecido: o parser tem de reproduzir
    # exatamente o CRC-32 que o modulo zipfile gravou.
    buf = io.BytesIO()
    conteudos = {"a/x.bin": b"conteudo A" * 100, "b/y.bin": b"outro conteudo" * 50}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for k, v in conteudos.items():
            z.writestr(k, v)
    dados = buf.getvalue()

    pos = dados.rfind(EOCD_SIG)
    if pos < 0:
        falhas.append("EOCD nao encontrado no zip de teste")
    else:
        cd_tam, cd_off = struct.unpack("<II", dados[pos + 12:pos + 20])
        cd = ler_central_directory(dados[cd_off:cd_off + cd_tam])
        if set(cd) != set(conteudos):
            falhas.append("nomes lidos do CD divergem: " + str(sorted(cd)))
        for k, v in conteudos.items():
            if k in cd:
                if cd[k]["crc32"] != zlib.crc32(v) & 0xFFFFFFFF:
                    falhas.append("crc32 lido errado para " + k)
                if cd[k]["tamanho"] != len(v):
                    falhas.append("tamanho lido errado para " + k)

    # crc32_arquivo tem de bater com o calculo em memoria
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.bin"
        p.write_bytes(conteudos["a/x.bin"])
        if crc32_arquivo(p) != zlib.crc32(conteudos["a/x.bin"]) & 0xFFFFFFFF:
            falhas.append("crc32_arquivo divergiu do calculo direto")
        # controle NEGATIVO: um byte trocado tem de mudar o crc
        p.write_bytes(conteudos["a/x.bin"][:-1] + b"Z")
        if crc32_arquivo(p) == zlib.crc32(conteudos["a/x.bin"]) & 0xFFFFFFFF:
            falhas.append("crc32 nao mudou apos alterar um byte — instrumento cego")

    # controle NEGATIVO: lixo nao pode virar entrada de CD
    if ler_central_directory(b"\x00" * 500):
        falhas.append("parser inventou entradas a partir de lixo")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste integridade: %d verificacoes, %d falhas" % (7, len(falhas)))
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

    total = _tamanho(ZIP_URL)
    print("LyNoS.zip no Zenodo: %d bytes (%.2f GB)" % (total, total / 2 ** 30))

    # O EOCD fica no fim. 64 KiB cobrem o caso sem comentario de arquivo.
    cauda = _range(ZIP_URL, max(0, total - 65536), total - 1)
    pos = cauda.rfind(EOCD_SIG)
    if pos < 0:
        print("EOCD nao encontrado — o zip pode ser ZIP64 com comentario longo")
        return 1
    cd_tam, cd_off = struct.unpack("<II", cauda[pos + 12:pos + 20])
    print("Central Directory: offset %d, %d bytes" % (cd_off, cd_tam))

    cd_bruto = _range(ZIP_URL, cd_off, cd_off + cd_tam - 1)
    cd = ler_central_directory(cd_bruto)
    baixado = len(cauda) + len(cd_bruto)
    print("entradas no zip: %d  |  trafego: %.1f KiB" % (len(cd), baixado / 1024))
    print()

    linhas = []
    for i in range(1, 16):
        nome_local = "pat%d_labels_Esophagus.nii.gz" % i
        alvo = "Benchmark/Pat%d/%s" % (i, nome_local)
        p = LOCAL / nome_local
        entrada = cd.get(alvo)
        if entrada is None:
            # o prefixo pode variar; procura pelo sufixo
            cand = [k for k in cd if k.endswith("/" + nome_local)]
            entrada = cd[cand[0]] if cand else None
            alvo = cand[0] if cand else alvo
        if entrada is None or not p.exists():
            linhas.append({"caso": "pat%d" % i, "erro": "ausente",
                           "no_zip": entrada is not None, "local": p.exists()})
            print("pat%-3d AUSENTE (zip=%s local=%s)" % (i, entrada is not None, p.exists()))
            continue
        crc_local = crc32_arquivo(p)
        igual = (crc_local == entrada["crc32"]) and (p.stat().st_size == entrada["tamanho"])
        linhas.append({
            "caso": "pat%d" % i, "caminho_no_zip": alvo,
            "crc32_zenodo": "%08x" % entrada["crc32"],
            "crc32_local_hf": "%08x" % crc_local,
            "tamanho_zenodo": entrada["tamanho"],
            "tamanho_local_hf": p.stat().st_size,
            "identico": igual,
        })
        print("pat%-3d zenodo crc %08x %9d  |  huggingface crc %08x %9d  |  %s"
              % (i, entrada["crc32"], entrada["tamanho"], crc_local, p.stat().st_size,
                 "IDENTICO" if igual else "DIVERGE"))

    ok = sum(1 for r in linhas if r.get("identico"))
    print()
    print("IDENTICOS: %d/%d" % (ok, len(linhas)))
    veredito = ("MESMO DADO — a medicao de ontologia vale para o dado licenciado"
                if ok == len(linhas) else "DIVERGENCIA ENTRE ESPELHOS")
    print("VEREDITO:", veredito)

    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "lynos_integridade.json").write_text(json.dumps({
        "fase": 18,
        "pergunta": ("as mascaras medidas (HuggingFace) sao byte-identicas as do "
                     "deposito que carrega a licenca CC BY 4.0 (Zenodo)?"),
        "metodo": ("Central Directory do LyNoS.zip lido por Range HTTP; CRC-32 por "
                   "membro comparado ao CRC-32 do arquivo local"),
        "ressalva": ("CRC-32 nao e criptografico. Serve para divergencia acidental "
                     "entre espelhos, que e a pergunta; nao serve contra adversario."),
        "zip_bytes": total,
        "bytes_baixados": baixado,
        "entradas_no_zip": len(cd),
        "identicos": ok,
        "total": len(linhas),
        "veredito": veredito,
        "casos": linhas,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print("escrito:", SAIDA / "lynos_integridade.json")
    return 0 if ok == len(linhas) else 1


if __name__ == "__main__":
    sys.exit(main())
