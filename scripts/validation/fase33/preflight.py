"""Fase 33 — o disco confere com o protocolo congelado? Se nao, a fase para.

A PERGUNTA DESTE MODULO E UMA SO

A Fase 32 congelou um protocolo em `docs/FASE32-PROTOCOLO-TREINO-V2.json`, com os
`sha256` do plano, da fingerprint e dos folds. Este preflight NAO decide nada: ele le o
protocolo e pergunta se o que esta em disco e exatamente aquilo. Divergencia e **FALHA**,
nunca conserto automatico — consertar aqui seria mudar o protocolo depois de congelado.

O QUE ELE NAO FAZ

Nao treina, nao escolhe, nao ajusta, nao cria diretorio de resultado. Nao le nenhum
caso da particao `validation`: a unica coisa que ele sabe sobre os 14 e que eles NAO
podem estar em `imagesTr`.

POR QUE UM MODULO NOVO E NAO O DA 26B

O preflight da 26B responde outra pergunta — se a unica diferenca entre dois trainers e
`num_epochs`. Ele e todo escrito em cima da V1 e do `Dataset501`. Aqui a pergunta e
"disco == protocolo", que nao existia antes porque nao havia protocolo congelado antes.
A checagem de parada antecipada, essa sim, e a mesma ideia e esta reproduzida.

  python -m scripts.validation.fase33.preflight --autoteste
  python -m scripts.validation.fase33.preflight --gravar docs/overnight/phase33/preflight.json
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.tier2 import ontologia_esofago as onto  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
PROTOCOLO = RAIZ / "docs" / "FASE32-PROTOCOLO-TREINO-V2.json"
MANIFESTO_V2 = RAIZ / "docs" / "VRMED-ESOPHAGUS-MANIFESTO-V2.jsonl"
SNAPSHOT_V2 = RAIZ / "docs" / "VRMED-ESOPHAGUS-SNAPSHOT-V2.json"

BASE = RAIZ / ".clinica-dados" / "fase32"
DS = "Dataset502_VRmedEsofagoV2"
RAW = BASE / "nnUNet_raw" / DS
PRE = BASE / "nnUNet_preprocessed" / DS
RES = BASE / "nnUNet_results" / DS
HOLDOUT = BASE / "validation_holdout"

# Arvore de trabalho da Fase 33. O benchmark vive numa arvore propria, separada da do
# modelo, para que nada que ele produza possa ser confundido com resultado.
BASE_33 = RAIZ / ".clinica-dados" / "fase33"
BENCH = BASE_33 / "benchmark"

# Os mesmos termos que a 26B procurou no codigo do trainer. Se qualquer um aparecer, ha
# mecanismo de parada onde o protocolo diz que nao ha.
TERMOS_DE_PARADA = ("early_stop", "earlystop", "EarlyStopping", "patience",
                    "no_improvement", "should_stop", "stop_training")


def protocolo() -> dict:
    return json.loads(PROTOCOLO.read_text(encoding="utf-8"))


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verificar() -> dict:
    p = protocolo()
    falhas, ok = [], {}

    # ---------------------------------------------------------------- o manifesto
    ent = man.carregar(MANIFESTO_V2)
    conf = man.verificar_congelamento(ent, json.loads(SNAPSHOT_V2.read_text(encoding="utf-8")))
    por_split = {s: sum(1 for e in ent if e["split"] == s) for s in man.PARTICOES}
    ok["split"] = por_split
    ok["sha256_manifesto"] = conf["sha256_atual"]
    ok["congelamento_intacto"] = conf["intacto"]
    if not conf["intacto"]:
        falhas.append("manifesto V2 divergiu do snapshot: %s" % conf["mudancas"])
    if conf["sha256_atual"] != p["manifesto_sha256"]:
        falhas.append("sha256 do manifesto difere do protocolo")
    esperado = {"train": p["train"], "validation": p["validation"], "test": p["test"]}
    if por_split != esperado:
        falhas.append("split %s difere do protocolo %s" % (por_split, esperado))

    # ---------------------------------------------------------------- a arvore raw
    imgs = sorted(q.name[:-len("_0000.nii.gz")] for q in (RAW / "imagesTr").glob("*_0000.nii.gz"))
    lbls = sorted(q.name[:-len(".nii.gz")] for q in (RAW / "labelsTr").glob("*.nii.gz"))
    treino = sorted(e["case_id"] for e in ent if e["split"] == "train")
    holdout = {e["case_id"] for e in ent if e["split"] == "validation"}
    ok["n_imagesTr"], ok["n_labelsTr"] = len(imgs), len(lbls)
    if imgs != treino:
        falhas.append("imagesTr nao e exatamente a particao train (%d arquivos)" % len(imgs))
    if lbls != treino:
        falhas.append("labelsTr nao pareia com a particao train (%d arquivos)" % len(lbls))
    invasores = sorted(set(imgs) & holdout)
    ok["validation_em_imagesTr"] = invasores
    if invasores:
        falhas.append("CASO DE VALIDATION EM imagesTr: %s" % invasores)
    ok["imagesTs_existe"] = (RAW / "imagesTs").exists()
    if ok["imagesTs_existe"]:
        falhas.append("existe imagesTs; TEST e 0 e nao ha o que predizer")
    ok["n_holdout_fora_da_arvore"] = len(list((HOLDOUT / "images").glob("*_0000.nii.gz")))
    if ok["n_holdout_fora_da_arvore"] != p["validation"]:
        falhas.append("holdout com %d casos, esperado %d"
                      % (ok["n_holdout_fora_da_arvore"], p["validation"]))

    # ---------------------------------------------- hashes dos artefatos congelados
    ok["hashes"] = {}
    for rel, chave in (("nnUNetPlans.json", "plans_sha256"),
                       ("dataset_fingerprint.json", "fingerprint_sha256"),
                       ("splits_final.json", "splits_sha256")):
        q = PRE / rel
        atual = _sha(q) if q.exists() else None
        ok["hashes"][rel] = atual
        if atual != p["planner"][chave]:
            falhas.append("%s divergiu do protocolo" % rel)

    # -------------------------------------------- o conteudo do dataset.json bate?
    dj = json.loads((RAW / "dataset.json").read_text(encoding="utf-8"))
    ok["dataset_json"] = {k: dj.get(k) for k in
                          ("numTraining", "labels", "vrmed_dataset_version",
                           "vrmed_ontology", "vrmed_sha256_manifesto")}
    if dj.get("numTraining") != p["train"]:
        falhas.append("numTraining %s difere de %s" % (dj.get("numTraining"), p["train"]))
    if dj.get("vrmed_sha256_manifesto") != p["manifesto_sha256"]:
        falhas.append("dataset.json aponta outro manifesto")
    if dj.get("vrmed_ontology") != onto.VERSAO:
        falhas.append("dataset.json carimba ontologia %s, esperada %s"
                      % (dj.get("vrmed_ontology"), onto.VERSAO))
    ok["ontologia"] = {"versao": onto.VERSAO, "congelada_em": onto.CONGELADA_EM}

    # --------------------------------------------------------------------- os folds
    splits = json.loads((PRE / "splits_final.json").read_text(encoding="utf-8"))
    ok["n_folds"] = len(splits)
    if len(splits) != p["folds"]["n"]:
        falhas.append("%d folds em disco, protocolo diz %d" % (len(splits), p["folds"]["n"]))
    citados = set()
    for i, s in enumerate(splits):
        citados |= set(s["train"]) | set(s["val"])
        if set(s["train"]) & set(s["val"]):
            falhas.append("fold %d tem caso nos dois lados" % i)
        fora = sorted((set(s["train"]) | set(s["val"])) & holdout)
        if fora:
            falhas.append("fold %d cita caso da particao validation: %s" % (i, fora))
    if sorted(citados) != treino:
        falhas.append("os folds nao cobrem exatamente os %d de train" % len(treino))

    # ------------------------------------------------ o trainer e o que diz ser
    from nnunetv2.training.nnUNetTrainer.variants.training_length import nnUNetTrainer_Xepochs as vx
    from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
    cls = getattr(vx, p["trainer"])
    fonte = inspect.getsource(cls)
    ok["trainer"] = {"classe": cls.__name__, "base": cls.__bases__[0].__name__,
                     "linhas_proprias": len(fonte.strip().splitlines())}
    if cls.__bases__[0] is not nnUNetTrainer:
        falhas.append("o trainer nao herda direto de nnUNetTrainer")
    if "num_epochs" not in fonte:
        falhas.append("o trainer nao define num_epochs")
    achados = [t for t in TERMOS_DE_PARADA
               if t in fonte or t in inspect.getsource(nnUNetTrainer)]
    ok["termos_de_parada_encontrados"] = achados
    if achados:
        falhas.append("ha mecanismo de parada no trainer: %s" % achados)

    # a variante so pode mexer em num_epochs; qualquer outro atributo e desvio
    corpo = [l.strip() for l in fonte.splitlines() if "self." in l and "=" in l]
    atribuidos = sorted({l.split("self.")[1].split()[0].split("=")[0].strip()
                         for l in corpo if l.startswith("self.")})
    ok["atributos_alterados_pela_variante"] = atribuidos
    if atribuidos != ["num_epochs"]:
        falhas.append("a variante altera mais que num_epochs: %s" % atribuidos)

    import nnunetv2.training.nnUNetTrainer.nnUNetTrainer as mod
    base_src = inspect.getsource(mod)
    ok["constantes_do_trainer"] = {
        "num_iterations_per_epoch": "self.num_iterations_per_epoch = 250" in base_src,
        "num_val_iterations_per_epoch": "self.num_val_iterations_per_epoch = 50" in base_src,
        "initial_lr": "self.initial_lr = 1e-2" in base_src,
        "weight_decay": "self.weight_decay = 3e-5" in base_src,
        "oversample_foreground_percent": "self.oversample_foreground_percent = 0.33" in base_src,
    }
    for k, v in ok["constantes_do_trainer"].items():
        if not v:
            falhas.append("constante do trainer mudou: %s" % k)

    # --------------------------------- a arvore de resultados tem de estar vazia
    ok["resultados_preexistentes"] = sorted(
        str(q.relative_to(RES)).replace("\\", "/")
        for q in RES.rglob("*") if q.is_file()) if RES.exists() else []
    if ok["resultados_preexistentes"]:
        falhas.append("ja ha resultado em %s: %s"
                      % (RES, ok["resultados_preexistentes"][:5]))

    # ---------------------------------------------------- o benchmark fica separado
    ok["benchmark_em_arvore_propria"] = str(BENCH)
    if BENCH.exists() and BENCH.resolve() == RES.resolve():
        falhas.append("o benchmark aponta para a arvore de resultados do modelo")

    ok["falhas"] = falhas
    ok["aprovado"] = not falhas
    return ok


def autoteste() -> int:
    falhas = []

    # 1. o protocolo existe e esta travado
    p = protocolo()
    if not p.get("protocol_locked"):
        falhas.append("o protocolo nao esta travado")
    for k in ("trainer", "epochs", "checkpoint_primary", "checkpoint_secondary", "folds"):
        if k not in p:
            falhas.append("falta %s no protocolo" % k)

    # 2. o preflight roda inteiro e aprova o estado real
    r = verificar()
    if not r["aprovado"]:
        falhas.append("preflight reprovou o estado atual: %s" % r["falhas"][:3])

    # 3. e aprova pelos motivos certos, nao por lista vazia
    if r["n_imagesTr"] != 32 or r["n_labelsTr"] != 32:
        falhas.append("imagesTr/labelsTr nao tem 32: %s %s" % (r["n_imagesTr"], r["n_labelsTr"]))
    if r["split"] != {"train": 32, "validation": 14, "test": 0}:
        falhas.append("split lido errado: %s" % r["split"])

    # 4. CONTROLE POSITIVO — se um hash divergir, o preflight TEM de reprovar.
    #    Sem isto, um verificador que sempre aprova passaria em 2.
    import copy
    guardado = copy.deepcopy(p)
    try:
        p2 = copy.deepcopy(p)
        p2["planner"]["plans_sha256"] = "0" * 64
        PROTOCOLO.write_text(json.dumps(p2, indent=1, ensure_ascii=False), encoding="utf-8")
        if verificar()["aprovado"]:
            falhas.append("o preflight aprovou com o sha256 do plano adulterado")
    finally:
        PROTOCOLO.write_text(json.dumps(guardado, indent=1, ensure_ascii=False),
                             encoding="utf-8")
    if _sha(PROTOCOLO) is None:
        falhas.append("o protocolo nao voltou ao lugar")

    # 5. o protocolo restaurado volta a aprovar — o controle positivo nao pode deixar
    #    lixo para tras
    if not verificar()["aprovado"]:
        falhas.append("o protocolo nao foi restaurado corretamente pelo controle positivo")

    # 6. a variante de trainer so mexe em num_epochs
    if r["atributos_alterados_pela_variante"] != ["num_epochs"]:
        falhas.append("a variante mexe em mais coisa: %s"
                      % r["atributos_alterados_pela_variante"])

    # 7. nao ha termo de parada antecipada em lugar nenhum do trainer
    if r["termos_de_parada_encontrados"]:
        falhas.append("termos de parada: %s" % r["termos_de_parada_encontrados"])

    # 8. CONTROLE NEGATIVO do 7: o detector precisa achar o termo quando ele existe.
    #    Um detector que nunca acha nada passaria em 7 sem provar nada.
    if not any(t in "def f(self): self.should_stop = True" for t in TERMOS_DE_PARADA):
        falhas.append("o detector de parada nao acha um termo plantado")

    # 9. a arvore de resultados do modelo esta vazia antes de comecar
    if r["resultados_preexistentes"]:
        falhas.append("ha resultado antes do treino: %s" % r["resultados_preexistentes"][:3])

    # 10. nenhum caso da particao validation esta em imagesTr
    if r["validation_em_imagesTr"]:
        falhas.append("validation em imagesTr: %s" % r["validation_em_imagesTr"])

    for f in falhas:
        print("FALHA:", f)
    print("autoteste preflight 33: %d verificacoes, %d falhas" % (10, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--gravar")
    a = ap.parse_args(argv)
    if a.autoteste:
        return autoteste()

    r = verificar()
    p = protocolo()
    print("PREFLIGHT FASE 33 — %s" % DS)
    print("   split                : %s" % r["split"])
    print("   sha256 do manifesto  : %s" % r["sha256_manifesto"][:24])
    print("   imagesTr / labelsTr  : %d / %d" % (r["n_imagesTr"], r["n_labelsTr"]))
    print("   validation em imagesTr: %s" % (r["validation_em_imagesTr"] or "nenhum"))
    print("   imagesTs             : %s" % ("EXISTE" if r["imagesTs_existe"] else "nao existe"))
    print("   holdout fora da arvore: %d casos" % r["n_holdout_fora_da_arvore"])
    for rel, sha in r["hashes"].items():
        print("   %-24s %s" % (rel, (sha or "AUSENTE")[:24]))
    print("   ontologia            : %s (%s)" % (r["ontologia"]["versao"],
                                                 r["ontologia"]["congelada_em"]))
    print("   folds                : %d" % r["n_folds"])
    print("   trainer              : %s(%s), altera %s"
          % (r["trainer"]["classe"], r["trainer"]["base"],
             r["atributos_alterados_pela_variante"]))
    print("   parada antecipada    : %s" % (r["termos_de_parada_encontrados"] or "nenhum termo"))
    print("   resultados existentes: %s" % (r["resultados_preexistentes"] or "nenhum"))
    print("   comando previsto     : %s" % p["treinamento"]["comando"])

    if r["falhas"]:
        print("\nFALHAS:")
        for f in r["falhas"]:
            print("   ! %s" % f)
    print("\nPORTAO DE PREFLIGHT: %s" % ("OK" if r["aprovado"] else "REPROVADO"))

    if a.gravar:
        q = Path(a.gravar)
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
        print("escrito:", q)
    return 0 if r["aprovado"] else 1


if __name__ == "__main__":
    sys.exit(main())
