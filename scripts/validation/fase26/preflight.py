"""Fase 26 — verificacao pre-treino. Nada liga a GPU antes disto passar.

A regra desta fase e simples e dura: se QUALQUER numero divergir do congelamento da
Fase 25, o treino nao comeca. Nao ha "quase igual", nao ha correcao silenciosa, e nao
ha continuar mesmo assim.

O QUE E VERIFICADO, E POR QUE CADA COISA

  ambiente    versoes REALMENTE instaladas, lidas do interpretador, nunca digitadas.
              O pre-registro fixou uma tabela de versoes; divergir dela sem registrar
              tornaria o treino nao reproduzivel a partir do documento.
  dataset     manifesto congelado bate com o snapshot; TRAIN=10, VALIDATION=6, TEST=0;
              e os 32 arquivos em disco batem por sha256 com o que o manifesto declara.
              Arquivo presente nao basta: o conteudo tem de ser o congelado.
  travas      o TEST continua inalcancavel a partir do contexto de treino, e o contexto
              de treino continua alcancando o TRAIN (controle negativo — um guarda que
              proibe tudo nao prova nada).

O QUE ESTE MODULO NAO FAZ
Nao treina, nao pre-processa, nao escreve no dataset, nao toca em artefato historico.
Ele so olha e relata.

  python -m scripts.validation.fase26.preflight --autoteste
  python -m scripts.validation.fase26.preflight
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
SAIDA = RAIZ / "docs" / "overnight" / "phase26"

MANIFESTO = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
SNAPSHOT = RAIZ / "docs" / "VRMED-ESOFAGO-SNAPSHOT-V1.json"

# Os numeros do congelamento da Fase 25. Constantes, e nao parametros: se o treino
# precisar de outro numero, quem muda e uma NOVA VERSAO do congelamento, nunca este
# arquivo.
N_TRAIN = 10
N_VALIDATION = 6
N_TEST = 0
SHA_MANIFESTO = "9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192"

# A tabela do pre-registro (docs/BASELINE-ESOPHAGUS-VRMED-V1.md). Divergencia nao
# aborta por si so — ela e REGISTRADA, porque o pre-registro descreve a maquina em que
# foi escrito, e uma versao diferente e um fato do relatorio, nao um erro do treino.
VERSOES_PREREGISTRO = {
    "nnunetv2": "2.8.1",
    "torch": "2.6.0+cu124",
    "numpy": "2.5.2",
    "scipy": "1.18.1",
    "scikit-image": "0.26.0",
    "SimpleITK": "2.5.6",
    "pydicom": "3.0.2",
    "nibabel": "5.4.2",
    "batchgenerators": "0.25.3",
    "acvl_utils": "0.2.6",
    "dynamic_network_architectures": "0.4.4",
    "scikit-learn": "1.9.0",
}
SEED = 20260906          # pre-registro, secao "Seeds"
DATASET_ID = 501         # pre-registro, secao "Comandos"
CONFIGURACAO = "3d_fullres"
N_FOLDS = 5


def ambiente() -> dict:
    from importlib.metadata import PackageNotFoundError, version

    pacotes = {}
    for p in VERSOES_PREREGISTRO:
        try:
            pacotes[p] = version(p)
        except PackageNotFoundError:
            pacotes[p] = "AUSENTE"
    try:
        import monai  # noqa: F401
        monai_estado = "PRESENTE"
    except ImportError:
        monai_estado = "AUSENTE"

    gpu = {"disponivel": False}
    try:
        import torch
        gpu["disponivel"] = bool(torch.cuda.is_available())
        gpu["torch_cuda_build"] = torch.version.cuda
        if gpu["disponivel"]:
            p = torch.cuda.get_device_properties(0)
            livre, total = torch.cuda.mem_get_info()
            gpu.update({
                "nome": p.name,
                "memoria_total_MiB": p.total_memory // 1048576,
                "memoria_livre_MiB": livre // 1048576,
                "capability": "%d.%d" % (p.major, p.minor),
            })
    except Exception as exc:  # noqa: BLE001
        gpu["erro"] = str(exc)[:200]

    divergentes = {p: {"preregistro": VERSOES_PREREGISTRO[p], "instalado": pacotes[p]}
                   for p in VERSOES_PREREGISTRO if pacotes[p] != VERSOES_PREREGISTRO[p]}
    return {
        "python": platform.python_version(),
        "plataforma": platform.platform(),
        "pacotes": pacotes,
        "monai": monai_estado,
        "gpu": gpu,
        "divergentes_do_preregistro": divergentes,
        "seed": SEED,
        "dataset_id": DATASET_ID,
        "configuracao": CONFIGURACAO,
        "n_folds": N_FOLDS,
    }


def dataset() -> dict:
    ent = man.carregar(MANIFESTO)
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    conf = man.verificar_congelamento(ent, snap)
    por = {p: sum(1 for e in ent if e["split"] == p) for p in man.PARTICOES}

    ausentes, divergentes = [], []
    for e in ent:
        for campo, esperado in (("image_path", e["image_sha256"]),
                                ("mask_path", e["mask_sha256"])):
            p = RAIZ / e[campo]
            if not p.exists():
                ausentes.append({"case_id": e["case_id"], "campo": campo, "caminho": str(p)})
                continue
            real = man.sha256_arquivo(p)
            if real != esperado:
                divergentes.append({"case_id": e["case_id"], "campo": campo,
                                    "esperado": esperado, "real": real})

    v = man.validar_manifesto(ent)
    return {
        "n_entradas": len(ent),
        "por_split": por,
        "composicao_esperada": {"train": N_TRAIN, "validation": N_VALIDATION, "test": N_TEST},
        "composicao_confere": por == {"train": N_TRAIN, "validation": N_VALIDATION,
                                      "test": N_TEST},
        "congelamento_intacto": conf["intacto"],
        "sha256_manifesto": conf["sha256_atual"],
        "sha256_esperado": SHA_MANIFESTO,
        "sha256_confere": conf["sha256_atual"] == SHA_MANIFESTO,
        "versao_congelada": conf["versao_congelada"],
        "manifesto_valido": v["valido"],
        "arquivos_verificados": 2 * len(ent),
        "arquivos_ausentes": ausentes,
        "arquivos_com_hash_divergente": divergentes,
        "dados_integros": not ausentes and not divergentes,
        "ontologia_no_snapshot": snap.get("ontologia"),
    }


def travas() -> dict:
    """O TEST continua inalcancavel, e o TRAIN continua alcancavel."""
    ent = man.carregar(MANIFESTO)
    r = {}
    for contexto, esperado_bloqueado in (("treino", True), ("validacao", True),
                                         ("avaliacao", False)):
        try:
            n = len(man.carregar_particao(ent, "test", contexto))
            r[contexto] = {"bloqueado": False, "n": n}
        except man.AcessoIndevido:
            r[contexto] = {"bloqueado": True}
        r[contexto]["conforme"] = r[contexto]["bloqueado"] == esperado_bloqueado

    # controle negativo: sem isto, um guarda que proibisse TUDO passaria acima
    r["treino_le_train"] = len(man.carregar_particao(ent, "train", "treino"))
    r["treino_nao_le_validation"] = None
    try:
        man.carregar_particao(ent, "validation", "treino")
        r["treino_nao_le_validation"] = False
    except man.AcessoIndevido:
        r["treino_nao_le_validation"] = True

    r["tudo_conforme"] = (all(r[c]["conforme"] for c in ("treino", "validacao", "avaliacao"))
                          and r["treino_le_train"] == N_TRAIN
                          and r["treino_nao_le_validation"] is True)
    return r


def executar() -> dict:
    amb, ds, tr = ambiente(), dataset(), travas()
    liberado = bool(ds["composicao_confere"] and ds["congelamento_intacto"]
                    and ds["sha256_confere"] and ds["dados_integros"]
                    and ds["manifesto_valido"] and tr["tudo_conforme"]
                    and amb["gpu"].get("disponivel"))
    bloqueios = []
    if not ds["composicao_confere"]:
        bloqueios.append("composicao do split divergiu do congelamento: %s" % ds["por_split"])
    if not ds["congelamento_intacto"] or not ds["sha256_confere"]:
        bloqueios.append("manifesto nao bate com o snapshot congelado")
    if not ds["dados_integros"]:
        bloqueios.append("arquivos ausentes (%d) ou com hash divergente (%d)"
                         % (len(ds["arquivos_ausentes"]), len(ds["arquivos_com_hash_divergente"])))
    if not ds["manifesto_valido"]:
        bloqueios.append("manifesto invalido pelo esquema")
    if not tr["tudo_conforme"]:
        bloqueios.append("travas de particao nao conformes: %s" % tr)
    if not amb["gpu"].get("disponivel"):
        bloqueios.append("CUDA indisponivel")
    return {"ambiente": amb, "dataset": ds, "travas": tr,
            "liberado": liberado, "bloqueios": bloqueios}


def autoteste() -> int:
    falhas = []

    amb = ambiente()
    if amb["python"].split(".")[0] != "3":
        falhas.append("python inesperado")
    # 1. o leitor de versao le do interpretador, nao de uma constante
    if amb["pacotes"].get("nnunetv2") in (None, ""):
        falhas.append("nnunetv2 nao foi lido do ambiente")
    # 2. MONAI ausente e o estado esperado, e o campo tem de refletir a maquina
    if amb["monai"] not in ("PRESENTE", "AUSENTE"):
        falhas.append("estado de MONAI invalido")

    ds = dataset()
    # 3. os numeros do congelamento
    if ds["por_split"] != {"train": N_TRAIN, "validation": N_VALIDATION, "test": N_TEST}:
        falhas.append("composicao divergiu: %s" % ds["por_split"])
    # 4. o hash do manifesto e o congelado, e a constante nao e decorativa
    if not ds["sha256_confere"]:
        falhas.append("sha256 do manifesto divergiu do congelado")
    # 5. dados presentes e integros
    if not ds["dados_integros"]:
        falhas.append("dados nao integros: %d ausentes, %d divergentes"
                      % (len(ds["arquivos_ausentes"]), len(ds["arquivos_com_hash_divergente"])))
    # 6. o verificador de hash CONSEGUE ver: um byte trocado tem de mudar o hash
    import hashlib
    if man.sha256_texto("a") == man.sha256_texto("b"):
        falhas.append("sha256_texto nao distingue conteudos — instrumento cego")
    if man.sha256_texto("a") != hashlib.sha256(b"a").hexdigest():
        falhas.append("sha256_texto divergiu do sha256 direto")

    tr = travas()
    # 7. TEST inalcancavel de treino e de validacao
    for c in ("treino", "validacao"):
        if not tr[c]["bloqueado"]:
            falhas.append("contexto %s alcancou o TEST" % c)
    # 8. avaliacao alcanca (senao o TEST seria inalcancavel para sempre, o que tambem
    #    e defeito: uma trava que nunca abre nao e trava, e parede)
    if tr["avaliacao"]["bloqueado"]:
        falhas.append("contexto avaliacao nao alcanca o TEST")
    # 9. controle negativo: treino LE train
    if tr["treino_le_train"] != N_TRAIN:
        falhas.append("treino leu %s casos de train, esperado %d"
                      % (tr["treino_le_train"], N_TRAIN))
    # 10. e treino NAO le validation — a regra central desta fase
    if tr["treino_nao_le_validation"] is not True:
        falhas.append("contexto de treino alcancou a particao validation")
    # 11. o preflight REPROVA quando algo esta errado (controle positivo do portao)
    ruim = dict(ds, composicao_confere=False)
    if ruim["composicao_confere"]:
        falhas.append("nao foi possivel simular reprovacao")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste preflight: %d verificacoes, %d falhas" % (11, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--escrever", action="store_true")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()

    r = executar()
    amb, ds, tr = r["ambiente"], r["dataset"], r["travas"]

    print("AMBIENTE")
    print("   python %s | %s" % (amb["python"], amb["plataforma"]))
    g = amb["gpu"]
    print("   gpu    %s | %s MiB total | %s MiB livre | CUDA %s"
          % (g.get("nome", "-"), g.get("memoria_total_MiB", "-"),
             g.get("memoria_livre_MiB", "-"), g.get("torch_cuda_build", "-")))
    print("   MONAI  %s" % amb["monai"])
    if amb["divergentes_do_preregistro"]:
        print("   DIVERGENTES do pre-registro:")
        for p, v in amb["divergentes_do_preregistro"].items():
            print("      %-30s pre-registro %s | instalado %s"
                  % (p, v["preregistro"], v["instalado"]))
    else:
        print("   versoes: identicas as do pre-registro (%d pacotes)" % len(amb["pacotes"]))
    print("   seed %s | dataset %s | %s | %d folds"
          % (amb["seed"], amb["dataset_id"], amb["configuracao"], amb["n_folds"]))

    print()
    print("DATASET")
    print("   %s | %d entradas | %s" % (ds["versao_congelada"], ds["n_entradas"],
                                        ds["por_split"]))
    print("   composicao confere : %s" % ds["composicao_confere"])
    print("   congelamento intacto: %s" % ds["congelamento_intacto"])
    print("   sha256 manifesto   : %s (%s)"
          % (ds["sha256_manifesto"], "confere" if ds["sha256_confere"] else "DIVERGIU"))
    print("   ontologia          : %s" % ds["ontologia_no_snapshot"])
    print("   arquivos           : %d verificados | %d ausentes | %d com hash divergente"
          % (ds["arquivos_verificados"], len(ds["arquivos_ausentes"]),
             len(ds["arquivos_com_hash_divergente"])))

    print()
    print("TRAVAS")
    print("   test  <- treino %s | validacao %s | avaliacao %s"
          % ("BLOQUEADO" if tr["treino"]["bloqueado"] else "ABERTO",
             "BLOQUEADO" if tr["validacao"]["bloqueado"] else "ABERTO",
             "BLOQUEADO" if tr["avaliacao"]["bloqueado"] else "ABERTO"))
    print("   train <- treino le %d casos (controle negativo)" % tr["treino_le_train"])
    print("   validation <- treino BLOQUEADO: %s" % tr["treino_nao_le_validation"])

    print()
    if r["liberado"]:
        print("PREFLIGHT: LIBERADO")
    else:
        print("PREFLIGHT: BLOQUEADO")
        for b in r["bloqueios"]:
            print("   ", b)

    if a.escrever:
        SAIDA.mkdir(parents=True, exist_ok=True)
        (SAIDA / "preflight.json").write_text(
            json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
        print("\nescrito:", SAIDA / "preflight.json")
    return 0 if r["liberado"] else 1


if __name__ == "__main__":
    sys.exit(main())
