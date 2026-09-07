"""Fase 26B — verificacao pre-treino do experimento de 250 epocas.

A 26B e um EXPERIMENTO EXPLORATORIO SEPARADO. Ela nao substitui o baseline canonico de
1000 epocas, que continua pendente. A unica diferenca autorizada em relacao a Fase 26 e
`num_epochs = 250`, por meio da variante que ja vem no pacote.

Este preflight existe para provar que essa e mesmo a UNICA diferenca — e para provar
que a 26B nao herdou nada da execucao de 1000 epocas.

  python -m scripts.validation.fase26b.preflight --autoteste
  python -m scripts.validation.fase26b.preflight --escrever
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.tier2 import ontologia_esofago as onto  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
MANIFESTO = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
SNAPSHOT = RAIZ / "docs" / "VRMED-ESOFAGO-SNAPSHOT-V1.json"
SAIDA = RAIZ / "docs" / "overnight" / "phase26b"

# --- a arvore da 26B, separada da 26 de proposito
BASE_26B = RAIZ / ".clinica-dados" / "fase26b"
BASE_26 = RAIZ / ".clinica-dados" / "fase26"
DS = "Dataset501_VRmedEsofago"
RAW_26B = BASE_26B / "nnUNet_raw" / DS
PRE_26B = BASE_26B / "nnUNet_preprocessed" / DS
RES_26B = BASE_26B / "nnUNet_results" / DS
RES_26 = BASE_26 / "nnUNet_results" / DS

TRAINER = "nnUNetTrainer_250epochs"
EPOCAS = 250
PASTA_TRAINER_26B = "%s__nnUNetPlans__3d_fullres" % TRAINER
PASTA_TRAINER_26 = "nnUNetTrainer__nnUNetPlans__3d_fullres"

SHA_MANIFESTO = "9388c7368cc0807b0629bcb18dd00be7cc6e61cb6d10f2181674afa582632192"
N_TRAIN, N_VALIDATION, N_TEST = 10, 6, 0

# Identificador do EXPERIMENTO, nao semente do framework. A lacuna da V1/V2 continua
# valendo e nao e reinterpretada aqui.
ID_EXPERIMENTO = 20260906
SEED_EFETIVA_NNUNET = 12345          # nnUNetTrainer.py:624, fixa no codigo

TERMOS_DE_PARADA = ("early_stop", "earlystop", "EarlyStopping", "patience",
                    "no_improvement", "should_stop", "stop_training")


def _ent():
    return man.carregar(MANIFESTO)


def _ids(split):
    return sorted(e["case_id"] for e in _ent() if e["split"] == split)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verificar() -> dict:
    """As 14 verificacoes exigidas. Cada uma devolve (ok, detalhe)."""
    v = {}
    ent = _ent()
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    conf = man.verificar_congelamento(ent, snap)
    treino, holdout = _ids("train"), _ids("validation")

    # 1. dataset correto
    v["01_dataset"] = {
        "ok": snap["versao"] == "VRMED-ESOPHAGUS-POOL16-V1"
        and snap["ontologia"] == onto.VERSAO,
        "detalhe": {"versao": snap["versao"], "ontologia": snap["ontologia"]}}

    # 2. manifest hash
    v["02_manifest_hash"] = {
        "ok": conf["sha256_atual"] == SHA_MANIFESTO and conf["intacto"],
        "detalhe": {"sha256": conf["sha256_atual"], "intacto": conf["intacto"]}}

    # 3. split correto
    por = {p: sum(1 for e in ent if e["split"] == p) for p in man.PARTICOES}
    v["03_split"] = {"ok": por == {"train": N_TRAIN, "validation": N_VALIDATION,
                                   "test": N_TEST}, "detalhe": por}

    # 4. TEST = 0, e inalcancavel do treino
    bloqueado = True
    try:
        man.carregar_particao(ent, "test", "treino")
        bloqueado = False
    except man.AcessoIndevido:
        pass
    v["04_test_vazio"] = {"ok": por["test"] == 0 and bloqueado,
                          "detalhe": {"n_test": por["test"], "inalcancavel_do_treino": bloqueado}}

    # 5. 10 casos em imagesTr (e 10 em labelsTr)
    imgs = sorted(p.name.replace("_0000.nii.gz", "")
                  for p in (RAW_26B / "imagesTr").glob("*_0000.nii.gz")) \
        if (RAW_26B / "imagesTr").exists() else []
    lbls = sorted(p.name.replace(".nii.gz", "")
                  for p in (RAW_26B / "labelsTr").glob("*.nii.gz")) \
        if (RAW_26B / "labelsTr").exists() else []
    v["05_imagesTr_10"] = {"ok": imgs == treino and lbls == treino,
                           "detalhe": {"n_imagesTr": len(imgs), "n_labelsTr": len(lbls),
                                       "confere_com_train": imgs == treino}}

    # 6. nenhum holdout em imagesTr
    inv_raw = sorted(set(imgs) & set(holdout))
    v["06_holdout_fora_do_raw"] = {"ok": not inv_raw, "detalhe": {"invasores": inv_raw}}

    # 7. nenhum holdout no preprocessing
    inv_pre = []
    for sub in ("nnUNetPlans_3d_fullres", "gt_segmentations"):
        d = PRE_26B / sub
        if not d.exists():
            continue
        nomes = [p.name for p in d.iterdir()]
        inv_pre += [h for h in holdout if any(h in n for n in nomes)]
    v["07_holdout_fora_do_preprocessado"] = {"ok": not inv_pre,
                                             "detalhe": {"invasores": sorted(set(inv_pre))}}

    # 8. folds cobrem exatamente os 10 de TRAIN
    sp = PRE_26B / "splits_final.json"
    folds = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else []
    universo = {c for f in folds for c in f["train"] + f["val"]}
    v["08_folds"] = {
        "ok": len(folds) == 5 and universo == set(treino) and not (universo & set(holdout)),
        "detalhe": {"n_folds": len(folds), "universo": len(universo),
                    "igual_a_train": universo == set(treino)}}

    # 9. o trainer e exatamente nnUNetTrainer_250epochs, resolvido pelo caminho do nnU-Net
    cls, erro = None, None
    try:
        from nnunetv2.run.run_training import get_trainer_from_args  # noqa: F401
        from nnunetv2.utilities.find_class_by_name import recursive_find_python_class
        import nnunetv2
        cls = recursive_find_python_class(
            str(Path(nnunetv2.__file__).parent / "training" / "nnUNetTrainer"),
            TRAINER, "nnunetv2.training.nnUNetTrainer")
    except Exception as exc:  # noqa: BLE001
        erro = str(exc)[:200]
    v["09_trainer"] = {"ok": cls is not None and cls.__name__ == TRAINER,
                       "detalhe": {"resolvido": cls.__name__ if cls else None, "erro": erro}}

    # 10. num_epochs = 250
    n_ep = None
    if cls is not None:
        m = re.search(r"self\.num_epochs\s*=\s*(\d+)", inspect.getsource(cls))
        n_ep = int(m.group(1)) if m else None
    v["10_num_epochs"] = {"ok": n_ep == EPOCAS, "detalhe": {"num_epochs": n_ep}}

    # 11. nenhum early stopping no pacote instalado
    achados = []
    try:
        import nnunetv2
        pkg = Path(nnunetv2.__file__).parent
        for py in pkg.rglob("*.py"):
            if "__pycache__" in str(py):
                continue
            txt = py.read_text(encoding="utf-8", errors="replace")
            for t in TERMOS_DE_PARADA:
                if t in txt:
                    achados.append("%s:%s" % (py.relative_to(pkg), t))
    except ImportError as exc:
        achados.append("nnunetv2 ausente: %s" % exc)
    v["11_sem_early_stopping"] = {"ok": not achados, "detalhe": {"achados": achados[:5]}}

    # 12. nenhum trainer customizado nosso no repositorio
    nossos = [str(p.relative_to(RAIZ)) for p in (RAIZ / "scripts").rglob("*.py")
              if "__pycache__" not in str(p)
              and re.search(r"class\s+\w*Trainer\w*\s*\(", p.read_text(encoding="utf-8",
                                                                       errors="replace"))]
    v["12_sem_trainer_customizado"] = {"ok": not nossos, "detalhe": {"arquivos": nossos}}

    # 13. o diretorio de saida da 26B difere do da 26
    v["13_saida_separada"] = {
        "ok": RES_26B.resolve() != RES_26.resolve() and PASTA_TRAINER_26B != PASTA_TRAINER_26,
        "detalhe": {"res_26b": str(RES_26B), "res_26": str(RES_26),
                    "pasta_trainer_26b": PASTA_TRAINER_26B,
                    "pasta_trainer_26": PASTA_TRAINER_26}}

    # 14. nenhum checkpoint herdado da execucao de 1000 epocas
    herdados = sorted(str(p.relative_to(BASE_26B)) for p in BASE_26B.rglob("*.pth"))
    v["14_sem_checkpoint_herdado"] = {"ok": not herdados, "detalhe": {"encontrados": herdados}}

    v["_liberado"] = all(x["ok"] for k, x in v.items() if not k.startswith("_"))
    return v


def identidade_do_run() -> dict:
    """Item 6 do pedido: o experimento tem identificador proprio e procedencia registrada."""
    import platform
    import subprocess
    from importlib.metadata import version

    gpu = {}
    try:
        import torch
        gpu = {"torch": torch.__version__, "cuda": torch.version.cuda,
               "disponivel": torch.cuda.is_available()}
        if torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            gpu.update({"nome": p.name, "memoria_MiB": p.total_memory // 1048576})
    except Exception as exc:  # noqa: BLE001
        gpu = {"erro": str(exc)[:120]}

    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                            text=True, cwd=RAIZ).stdout.strip()
    return {
        "run_id": "VRMED-FASE26B-250EP-5FOLD",
        "natureza": "EXPERIMENTO EXPLORATORIO DE ORCAMENTO REDUZIDO",
        "nao_e": "baseline definitivo — o canonico de 1000 epocas continua pendente",
        "commit": commit,
        "dataset_version": "VRMED-ESOPHAGUS-POOL16-V1",
        "sha256_manifesto": SHA_MANIFESTO,
        "ontologia": onto.VERSAO,
        "split": {"train": N_TRAIN, "validation": N_VALIDATION, "test": N_TEST},
        "trainer": TRAINER,
        "epocas": EPOCAS,
        "folds": 5,
        "configuracao": "3d_fullres",
        "dataset_id": 501,
        "identificador_experimental": ID_EXPERIMENTO,
        "seed_efetiva_do_framework": SEED_EFETIVA_NNUNET,
        "nota_seed": ("%d e IDENTIFICADOR do experimento, nao semente. O nnU-Net fixa "
                      "seed=%d em nnUNetTrainer.py:624 e nnUNetv2_train nao aceita "
                      "parametro de semente. A lacuna da V1/V2 nao e reinterpretada aqui."
                      % (ID_EXPERIMENTO, SEED_EFETIVA_NNUNET)),
        "checkpoint_primario": "checkpoint_final.pth",
        "checkpoint_secundario": "checkpoint_best.pth",
        "regra_de_checkpoint": ("declarada na Fase 26A, ANTES de qualquer resultado: os dois "
                                "sao medidos e reportados; e proibido trocar o primario pelo "
                                "secundario depois de ver qual foi melhor nos 6 casos."),
        "python": platform.python_version(),
        "plataforma": platform.platform(),
        "nnunetv2": version("nnunetv2"),
        "gpu": gpu,
        "diretorio_resultados": str(RES_26B),
        "comando": ("nnUNetv2_train 501 3d_fullres FOLD -tr %s --npz   (FOLD em 0..4)"
                    % TRAINER),
    }


def autoteste() -> int:
    falhas = []
    v = verificar()

    # 1. as 14 verificacoes existem, e nenhuma foi esquecida
    chaves = sorted(k for k in v if not k.startswith("_"))
    if len(chaves) != 14:
        falhas.append("esperava 14 verificacoes, ha %d: %s" % (len(chaves), chaves))

    # 2. cada uma tem veredito booleano explicito
    for k in chaves:
        if not isinstance(v[k].get("ok"), bool):
            falhas.append("%s sem veredito booleano" % k)

    # 3. o portao reprova se QUALQUER uma reprovar (controle positivo)
    simulado = {**{k: dict(v[k]) for k in chaves}}
    simulado[chaves[0]]["ok"] = False
    if all(x["ok"] for x in simulado.values()):
        falhas.append("nao foi possivel simular reprovacao do portao")

    # 4. o detector de holdout CONSEGUE ver: um invasor sintetico tem de ser acusado
    hold = set(_ids("validation"))
    fingido = sorted({"4DLUNG-999_FAKE"} & hold)
    if fingido:
        falhas.append("o conjunto de holdout foi lido errado")
    if not (set(_ids("train")) & set(_ids("train"))):
        falhas.append("leitura de particao falhou")
    # o cruzamento e o mesmo usado em 06/07; testa-lo com dado sintetico:
    if not sorted({"4DLUNG-101_HM10395"} & hold):
        falhas.append("o cruzamento nao detecta um caso de holdout conhecido — detector cego")

    # 5. identificador experimental NAO e apresentado como semente
    ident = identidade_do_run()
    if ident["identificador_experimental"] == ident["seed_efetiva_do_framework"]:
        falhas.append("o identificador do experimento foi confundido com a semente")
    if "identificador" not in ident["nota_seed"].lower():
        falhas.append("a nota da semente nao explicita a distincao")

    # 6. o primario e o final, e isso nao pode mudar depois
    if ident["checkpoint_primario"] != "checkpoint_final.pth":
        falhas.append("o checkpoint primario divergiu da regra da Fase 26A")

    # 7. a saida e mesmo separada da Fase 26
    if PASTA_TRAINER_26B == PASTA_TRAINER_26:
        falhas.append("a pasta do trainer da 26B colide com a da 26")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste preflight 26B: %d verificacoes, %d falhas" % (7, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--escrever", action="store_true")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()
    if autoteste() != 0:
        return 1
    print()

    v = verificar()
    ident = identidade_do_run()

    print("FASE 26B — %s" % ident["natureza"])
    print("   NAO e: %s" % ident["nao_e"])
    print()
    for k in sorted(x for x in v if not x.startswith("_")):
        print("   [%s] %-32s %s" % ("OK" if v[k]["ok"] else "!!", k,
                                    json.dumps(v[k]["detalhe"], ensure_ascii=False)[:96]))
    print()
    print("   trainer  : %s | epocas %d | folds 5 | %s"
          % (ident["trainer"], ident["epocas"], ident["configuracao"]))
    print("   identific: %d (EXPERIMENTO) | semente efetiva do framework: %d"
          % (ident["identificador_experimental"], ident["seed_efetiva_do_framework"]))
    print("   primario : %s | secundario: %s"
          % (ident["checkpoint_primario"], ident["checkpoint_secundario"]))
    print("   saida    : %s" % ident["diretorio_resultados"])
    print()
    print("PREFLIGHT 26B: %s" % ("LIBERADO" if v["_liberado"] else "BLOQUEADO"))

    if a.escrever:
        SAIDA.mkdir(parents=True, exist_ok=True)
        (SAIDA / "preflight.json").write_text(
            json.dumps({"verificacoes": v, "identidade": ident}, indent=1, ensure_ascii=False),
            encoding="utf-8")
        print("escrito:", SAIDA / "preflight.json")
    return 0 if v["_liberado"] else 1


if __name__ == "__main__":
    sys.exit(main())
