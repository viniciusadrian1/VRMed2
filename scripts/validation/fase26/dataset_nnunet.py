"""Fase 26 — monta o dataset nnU-Net a partir do manifesto congelado, e so dele.

A UNICA PORTA DE ENTRADA

    man.carregar_particao(entradas, "train", "treino")

Nao ha lista de casos escrita a mao, nao ha glob de diretorio, nao ha filtro por nome.
Se alguem quiser colocar um caso de VALIDATION no treino, tera de mudar a tabela
`PERMISSOES` do manifesto congelado — e ha mutante plantado exatamente ai, alem do
autoteste 6 deste modulo.

POR QUE imagesTr TEM SO OS CASOS DE `train`, E NAO O POOL INTEIRO

O pre-registro (Fase 19) anotou que `plan_and_preprocess` "le train + validation". Aquele
desenho foi escrito quando se esperava um TEST externo: o pool seria a cross-validation e
o TEST seria o holdout. **Hoje TEST = 0.** Sob a leitura literal, os casos de VALIDATION
entrariam em imagesTr e seriam usados como TREINO em 4 dos 5 folds do nnU-Net — e nao
sobraria nenhum caso nunca visto.

A tabela de permissoes congelada na Fase 25 ja responde a pergunta, e ela e executavel:

    PERMISSOES = {"treino": ("train",), ...}

O contexto de treino pode ler `train`, e SO `train`. Colocar VALIDATION em imagesTr seria
exatamente o vazamento que essa tabela existe para impedir. Este modulo obedece a tabela.

**Isto e um desvio do texto do pre-registro e esta declarado como tal no relatorio.**

DOIS PERFIS, UM CODIGO (acrescentado na Fase 32)

O perfil `v1` e o dataset de 10 casos das Fases 26 e 26B. O perfil `v2` e o de 32 casos
do `VRMED-ESOPHAGUS-POOL46-V2`. **O default continua sendo `v1` e o resultado dele
continua identico byte a byte** — a Fase 32 prova isso rodando o perfil v1 contra o
`dataset.json` que ja esta em disco, em vez de afirmar.

Perfis diferentes escrevem em ARVORES diferentes e usam IDENTIFICADORES diferentes de
dataset. Reaproveitar `Dataset501` para 32 casos faria dois conteudos distintos
compartilharem um nome, e todo diretorio de resultado que carrega esse nome ficaria
ambiguo depois do fato.

O QUE E FEITO COM A MASCARA, E O QUE NAO E

O nnU-Net exige rotulos `0/1`. As mascaras congeladas estao em `uint8` com foreground
`255`. A conversao remapeia o VALOR do rotulo e nada mais:

    novo = (original > 0)  ->  uint8 {0, 1}

O CONJUNTO de voxels de foreground e identico, e isso e verificado voxel a voxel, nao
afirmado. Os arquivos originais nao sao tocados — a copia vai para o diretorio da fase, e
o `sha256` dos originais e reconferido no fim. Nenhuma operacao morfologica, nenhuma
reamostragem, nenhum recorte. As imagens sao copiadas byte a byte.

  python -m scripts.validation.fase26.dataset_nnunet --autoteste
  python -m scripts.validation.fase26.dataset_nnunet --escrever
  python -m scripts.validation.fase26.dataset_nnunet --perfil v2 --escrever
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.validation.baseline_v1 import manifesto as man  # noqa: E402
from scripts.validation.tier2 import ontologia_esofago as onto  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
MANIFESTO = RAIZ / "docs" / "VRMED-ESOFAGO-MANIFESTO-V1.jsonl"
SNAPSHOT = RAIZ / "docs" / "VRMED-ESOFAGO-SNAPSHOT-V1.json"
SAIDA = RAIZ / "docs" / "overnight" / "phase26"

# Tudo da Fase 26 vive aqui. Diretorio novo, nunca um caminho de fase anterior.
BASE = RAIZ / ".clinica-dados" / "fase26"
NNUNET_RAW = BASE / "nnUNet_raw"
NNUNET_PREPROCESSED = BASE / "nnUNet_preprocessed"
NNUNET_RESULTS = BASE / "nnUNet_results"
# Os casos de VALIDATION ficam FORA da arvore do nnU-Net, de proposito: o que nao esta
# em imagesTr nao pode ser sorteado para treino por engano.
HOLDOUT = BASE / "validation_holdout"

DATASET_ID = 501                       # pre-registro, secao "Comandos"
DATASET_NOME = "Dataset501_VRmedEsofago"
SEED = 20260906                        # pre-registro, secao "Seeds"

ROTULO_FUNDO = 0
ROTULO_ESOFAGO = 1

# Cada perfil e um dataset inteiro: manifesto, snapshot, arvore, identificador e o que
# vai carimbado no `dataset.json`. `n_train` e `n_holdout` NAO sao configuracao — sao a
# contagem esperada, conferida pelo autoteste contra o manifesto. Se o manifesto mudar,
# o autoteste cai; e para cair.
PERFIS = {
    "v1": {
        "manifesto": MANIFESTO,
        "snapshot": SNAPSHOT,
        "base": BASE,
        "saida": SAIDA,
        "dataset_id": DATASET_ID,
        "dataset_nome": DATASET_NOME,
        "n_train": 10,
        "n_holdout": 6,
        "versao_pool": "VRMED-ESOPHAGUS-POOL16-V1",
        "regra_split": "VRMED-SPLIT-RULE-V1",
        "source_dataset": "4D-Lung (TCIA)",
        "annotation_method": "SEMIAUTOMATIC",
    },
    "v2": {
        "manifesto": RAIZ / "docs" / "VRMED-ESOPHAGUS-MANIFESTO-V2.jsonl",
        "snapshot": RAIZ / "docs" / "VRMED-ESOPHAGUS-SNAPSHOT-V2.json",
        "base": RAIZ / ".clinica-dados" / "fase32",
        "saida": RAIZ / "docs" / "overnight" / "phase32",
        "dataset_id": 502,
        "dataset_nome": "Dataset502_VRmedEsofagoV2",
        "n_train": 32,
        "n_holdout": 14,
        "versao_pool": "VRMED-ESOPHAGUS-POOL46-V2",
        "regra_split": "VRMED-SPLIT-RULE-V2",
        "source_dataset": "4D-Lung (TCIA) + LCTSC (TCIA)",
        # nao ha um metodo so: o manifesto declara por caso. Escrever "MANUAL" aqui
        # apagaria a diferenca entre as duas fontes.
        "annotation_method": "declarado POR CASO no manifesto (MANUAL, SEMIAUTOMATIC, VAZIO)",
        # Apurado de primeira mao no nnUNetTrainer 2.8.1 instalado (Fase 32). Sem esta
        # nota, `vrmed_seed` seria lido como controle de treino, que ele nao e.
        "seed_nota": (
            "vrmed_seed e carimbo de pre-registro, NAO controle de treinamento. O "
            "nnUNetTrainer 2.8.1 nao semeia torch, numpy nem random, e roda com "
            "cudnn.deterministic=False e cudnn.benchmark=True. O unico passo semeado e a "
            "divisao em 5 folds (generate_crossval_split, seed=12345 fixo no framework), "
            "e ela fica congelada em splits_final.json."),
    },
}


def _perfil(p=None) -> dict:
    """Default `v1`, para quem ja chamava continuar recebendo o mesmo dataset."""
    if p is None:
        return PERFIS["v1"]
    return PERFIS[p] if isinstance(p, str) else p


def entradas(perfil=None):
    return man.carregar(_perfil(perfil)["manifesto"])


def casos_de_treino(ent):
    """A unica porta. `AcessoIndevido` se alguem pedir outra particao daqui."""
    return sorted(man.carregar_particao(ent, "train", "treino"),
                  key=lambda e: e["case_id"])


def casos_de_holdout(ent):
    """Os casos de VALIDATION. Contexto `validacao`, filtrados para a particao certa."""
    lidos = man.carregar_particao(ent, "validation", "validacao")
    return sorted([e for e in lidos if e["split"] == "validation"],
                  key=lambda e: e["case_id"])


def converter_mascara(origem: Path, destino: Path) -> dict:
    """255 -> 1. Remapeia o VALOR do rotulo; o conjunto de foreground nao muda.

    Devolve a prova: numero de voxels de foreground antes e depois, e se os dois
    conjuntos sao identicos voxel a voxel.
    """
    import numpy as np
    import nibabel as nib

    im = nib.load(str(origem))
    a = np.asanyarray(im.dataobj)
    fg = a > 0
    novo = fg.astype(np.uint8)

    img = nib.Nifti1Image(novo, im.affine, im.header)
    img.set_data_dtype(np.uint8)
    destino.parent.mkdir(parents=True, exist_ok=True)
    nib.save(img, str(destino))

    # Reler do DISCO. Verificar o array em memoria provaria menos: o que o nnU-Net vai
    # ler e o arquivo, com o dtype e o header que ele realmente ficou.
    lido = np.asanyarray(nib.load(str(destino)).dataobj)
    return {
        "voxels_fg_origem": int(fg.sum()),
        "voxels_fg_destino": int((lido == ROTULO_ESOFAGO).sum()),
        "conjuntos_identicos": bool(np.array_equal(fg, lido == ROTULO_ESOFAGO)),
        "valores_destino": sorted(int(v) for v in np.unique(lido)),
        "dtype_destino": str(lido.dtype),
        "shape_confere": bool(lido.shape == a.shape),
    }


def montar_dataset_json(n_treino: int, sha_manifesto: str, perfil=None) -> dict:
    """O `dataset.json`, carimbado com a procedencia — exigencia do pre-registro."""
    pf = _perfil(perfil)
    return {
        # ---- o que o nnU-Net le
        "channel_names": {"0": "CT"},
        "labels": {"background": ROTULO_FUNDO, "esophagus": ROTULO_ESOFAGO},
        "numTraining": n_treino,
        "file_ending": ".nii.gz",
        "overwrite_image_reader_writer": "SimpleITKIO",
        # ---- o que o VRmed carimba (o nnU-Net ignora, a auditoria nao)
        "vrmed_dataset_version": pf["versao_pool"],
        "vrmed_schema": man.VERSAO_ESQUEMA,
        "vrmed_ontology": onto.VERSAO,
        "vrmed_ontology_frozen_at": onto.CONGELADA_EM,
        "vrmed_split_rule": pf["regra_split"],
        "vrmed_sha256_manifesto": sha_manifesto,
        "vrmed_seed": SEED,
        "vrmed_source_dataset": pf["source_dataset"],
        "vrmed_annotation_method_declared": pf["annotation_method"],
        "vrmed_nota": (
            "imagesTr contem SOMENTE a particao train (%d casos). Os %d casos da particao "
            "validation sao holdout e ficam fora desta arvore. TEST = 0 e nao existe. "
            "O alvo e mascara binaria preenchida; parede e lumen sao um objeto so; a "
            "extensao longitudinal e herdada do GT e nao e avaliavel anatomicamente."
            % (n_treino, pf["n_holdout"])),
        **({"vrmed_seed_nota": pf["seed_nota"]} if pf.get("seed_nota") else {}),
    }


def montar(escrever: bool = False, perfil=None) -> dict:
    pf = _perfil(perfil)
    ent = entradas(pf)
    snap = json.loads(Path(pf["snapshot"]).read_text(encoding="utf-8"))
    conf = man.verificar_congelamento(ent, snap)
    if not conf["intacto"]:
        raise man.ManifestoInvalido("manifesto divergiu do snapshot; nao se monta dataset "
                                    "a partir de congelamento quebrado: %s" % conf["mudancas"])

    treino = casos_de_treino(ent)
    holdout = casos_de_holdout(ent)

    ids_treino = [e["case_id"] for e in treino]
    ids_holdout = [e["case_id"] for e in holdout]

    raiz_ds = pf["base"] / "nnUNet_raw" / pf["dataset_nome"]
    holdout_dir = pf["base"] / "validation_holdout"

    r = {
        "perfil": pf["versao_pool"],
        "dataset_id": pf["dataset_id"],
        "dataset_nome": pf["dataset_nome"],
        "base": str(pf["base"]),
        "sha256_manifesto": conf["sha256_atual"],
        "n_treino": len(treino),
        "n_holdout": len(holdout),
        "ids_treino": ids_treino,
        "ids_holdout": ids_holdout,
        "intersecao_treino_holdout": sorted(set(ids_treino) & set(ids_holdout)),
        "conversoes": [],
        "escrito": False,
    }
    if not escrever:
        return r

    (raiz_ds / "imagesTr").mkdir(parents=True, exist_ok=True)
    (raiz_ds / "labelsTr").mkdir(parents=True, exist_ok=True)
    (holdout_dir / "images").mkdir(parents=True, exist_ok=True)
    (holdout_dir / "labels").mkdir(parents=True, exist_ok=True)
    (pf["base"] / "nnUNet_preprocessed").mkdir(parents=True, exist_ok=True)
    (pf["base"] / "nnUNet_results").mkdir(parents=True, exist_ok=True)

    for e in treino:
        cid = e["case_id"]
        shutil.copyfile(RAIZ / e["image_path"], raiz_ds / "imagesTr" / ("%s_0000.nii.gz" % cid))
        prova = converter_mascara(RAIZ / e["mask_path"], raiz_ds / "labelsTr" / ("%s.nii.gz" % cid))
        r["conversoes"].append({"case_id": cid, "destino": "treino", **prova})

    for e in holdout:
        cid = e["case_id"]
        shutil.copyfile(RAIZ / e["image_path"], holdout_dir / "images" / ("%s_0000.nii.gz" % cid))
        prova = converter_mascara(RAIZ / e["mask_path"], holdout_dir / "labels" / ("%s.nii.gz" % cid))
        r["conversoes"].append({"case_id": cid, "destino": "holdout", **prova})

    dj = montar_dataset_json(len(treino), conf["sha256_atual"], pf)
    (raiz_ds / "dataset.json").write_text(json.dumps(dj, indent=1, ensure_ascii=False),
                                          encoding="utf-8")
    r["dataset_json"] = dj
    r["escrito"] = True

    # ---- o que foi realmente escrito, lido do disco (nao do que pretendiamos escrever)
    em_disco = sorted(p.name.replace("_0000.nii.gz", "")
                      for p in (raiz_ds / "imagesTr").glob("*_0000.nii.gz"))
    rotulos = sorted(p.name.replace(".nii.gz", "")
                     for p in (raiz_ds / "labelsTr").glob("*.nii.gz"))
    r["imagesTr_em_disco"] = em_disco
    r["labelsTr_em_disco"] = rotulos
    r["imagesTr_confere"] = em_disco == sorted(ids_treino)
    r["pareamento_imagem_rotulo"] = em_disco == rotulos
    r["holdout_fora_de_imagesTr"] = not (set(em_disco) & set(ids_holdout))
    r["conversoes_todas_identicas"] = all(c["conjuntos_identicos"] for c in r["conversoes"])

    # ---- os originais continuam intactos
    intactos = []
    for e in treino + holdout:
        for campo, esperado in (("image_path", e["image_sha256"]),
                                ("mask_path", e["mask_sha256"])):
            intactos.append(man.sha256_arquivo(RAIZ / e[campo]) == esperado)
    r["originais_intactos"] = all(intactos)
    r["n_originais_conferidos"] = len(intactos)
    return r


def autoteste(perfil=None) -> int:
    pf = _perfil(perfil)
    n_tr, n_ho = pf["n_train"], pf["n_holdout"]
    falhas = []
    ent = entradas(pf)

    # 1. a porta de entrada devolve exatamente a particao train
    tr = casos_de_treino(ent)
    if len(tr) != n_tr or any(e["split"] != "train" for e in tr):
        falhas.append("casos_de_treino nao devolveu %d casos de train: %d" % (n_tr, len(tr)))

    # 2. e o holdout e exatamente a particao validation
    ho = casos_de_holdout(ent)
    if len(ho) != n_ho or any(e["split"] != "validation" for e in ho):
        falhas.append("casos_de_holdout nao devolveu %d casos de validation: %d"
                      % (n_ho, len(ho)))

    # 3. os dois conjuntos sao disjuntos
    if set(e["case_id"] for e in tr) & set(e["case_id"] for e in ho):
        falhas.append("treino e holdout se sobrepoem")

    # 4. e cobrem o manifesto inteiro, sem sobra
    if len(tr) + len(ho) != len(ent):
        falhas.append("treino + holdout nao cobrem o manifesto")

    # 5. nenhum caso duplicado
    ids = [e["case_id"] for e in tr + ho]
    if len(ids) != len(set(ids)):
        falhas.append("case_id duplicado entre treino e holdout")

    # 6. CONTROLE NEGATIVO — a protecao que esta fase depende.
    #    Pedir a particao validation a partir do contexto de treino TEM de explodir.
    #    Se alguem afrouxar PERMISSOES, este teste cai, e e para cair.
    try:
        man.carregar_particao(ent, "validation", "treino")
        falhas.append("o contexto de treino conseguiu ler VALIDATION — a protecao caiu")
    except man.AcessoIndevido:
        pass

    # 7. e o TEST tambem continua inalcancavel do treino
    try:
        man.carregar_particao(ent, "test", "treino")
        falhas.append("o contexto de treino conseguiu ler TEST")
    except man.AcessoIndevido:
        pass

    # 8. controle NEGATIVO do controle negativo: treino ainda le train.
    #    Sem isto, uma tabela que proibisse tudo passaria em 6 e 7 sem provar nada.
    try:
        if len(man.carregar_particao(ent, "train", "treino")) != n_tr:
            falhas.append("treino nao leu os %d casos de train" % n_tr)
    except man.AcessoIndevido:
        falhas.append("treino nao consegue ler train — a tabela proibe demais")

    # 9. a conversao de mascara preserva o conjunto de foreground, e o verificador ve
    import tempfile
    import numpy as np
    import nibabel as nib
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        a = np.zeros((6, 6, 6), np.uint8)
        a[1:4, 1:4, 1:4] = 255
        nib.save(nib.Nifti1Image(a, np.eye(4)), str(d / "m.nii.gz"))
        p = converter_mascara(d / "m.nii.gz", d / "out.nii.gz")
        if not p["conjuntos_identicos"]:
            falhas.append("a conversao mudou o conjunto de foreground")
        if p["valores_destino"] != [0, 1]:
            falhas.append("a conversao nao produziu rotulos 0/1: %s" % p["valores_destino"])
        if p["voxels_fg_origem"] != 27 or p["voxels_fg_destino"] != 27:
            falhas.append("contagem de foreground errada: %s" % p)

        # 10. controle POSITIVO: se o conjunto MUDAR, o verificador tem de acusar.
        #     Um verificador que so diz "identicos" nao esta verificando nada.
        b = a.copy()
        b[1, 1, 1] = 0
        nib.save(nib.Nifti1Image(b, np.eye(4)), str(d / "m2.nii.gz"))
        p2 = converter_mascara(d / "m2.nii.gz", d / "out2.nii.gz")
        if p2["voxels_fg_destino"] != 26:
            falhas.append("o verificador nao percebeu a mudanca de foreground")

    # 11. o dataset.json carimba a ontologia congelada e o seed
    dj = montar_dataset_json(n_tr, "x" * 64, pf)
    if dj["vrmed_ontology"] != onto.VERSAO:
        falhas.append("dataset.json nao carimba a ontologia congelada")
    if dj["vrmed_seed"] != SEED:
        falhas.append("dataset.json nao carimba o seed do pre-registro")
    if dj["labels"] != {"background": 0, "esophagus": 1}:
        falhas.append("rotulos do dataset.json divergiram")
    if dj["numTraining"] != n_tr:
        falhas.append("numTraining divergiu de %d" % n_tr)

    # 12. montar() em modo seco nao escreve nada
    r = montar(escrever=False, perfil=pf)
    if r["escrito"] or r["intersecao_treino_holdout"]:
        falhas.append("montar(escrever=False) escreveu ou sobrepos particoes")

    # 13. NEUTRALIDADE DA PARAMETRIZACAO (Fase 32). O perfil v1 tem de reproduzir,
    #     campo a campo, o `dataset.json` que ja esta em disco desde a Fase 26.
    #     Sem esta checagem, "o default nao mudou" seria afirmacao, nao prova.
    ja_em_disco = (RAIZ / ".clinica-dados" / "fase26" / "nnUNet_raw"
                   / "Dataset501_VRmedEsofago" / "dataset.json")
    if ja_em_disco.exists():
        antigo = json.loads(ja_em_disco.read_text(encoding="utf-8"))
        novo = montar_dataset_json(10, antigo["vrmed_sha256_manifesto"], PERFIS["v1"])
        if novo != antigo:
            dif = sorted(k for k in set(novo) | set(antigo) if novo.get(k) != antigo.get(k))
            falhas.append("o perfil v1 deixou de reproduzir o dataset.json da Fase 26: %s" % dif)
    else:
        falhas.append("o dataset.json da Fase 26 sumiu; a checagem 13 nao prova nada")

    # 14. os dois perfis nao compartilham arvore nem identificador
    a_, b_ = PERFIS["v1"], PERFIS["v2"]
    if a_["base"] == b_["base"] or a_["dataset_nome"] == b_["dataset_nome"]:
        falhas.append("os perfis v1 e v2 colidem em arvore ou identificador")

    for f in falhas:
        print("FALHA:", f)
    print("autoteste dataset_nnunet [%s]: %d verificacoes, %d falhas"
          % (pf["versao_pool"], 14, len(falhas)))
    return 1 if falhas else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--escrever", action="store_true")
    ap.add_argument("--perfil", default="v1", choices=sorted(PERFIS))
    a = ap.parse_args(argv)
    pf = PERFIS[a.perfil]
    if a.autoteste:
        return autoteste(pf)
    if autoteste(pf) != 0:
        return 1
    print()

    r = montar(escrever=a.escrever, perfil=pf)
    print("DATASET %s (id %d)" % (r["dataset_nome"], r["dataset_id"]))
    print("   manifesto  : %s" % r["sha256_manifesto"])
    print("   arvore     : %s" % r["base"])
    print("   treino     : %d casos -> imagesTr" % r["n_treino"])
    for c in r["ids_treino"]:
        print("      %s" % c)
    print("   holdout    : %d casos -> FORA da arvore nnU-Net" % r["n_holdout"])
    for c in r["ids_holdout"]:
        print("      %s" % c)
    print("   intersecao : %s" % (r["intersecao_treino_holdout"] or "vazia"))

    if not r["escrito"]:
        print("\n(modo seco — nada foi escrito. Use --escrever.)")
        return 0

    print()
    print("ESCRITO EM %s" % (pf["base"] / "nnUNet_raw" / pf["dataset_nome"]))
    print("   imagesTr confere com a particao train : %s" % r["imagesTr_confere"])
    print("   imagem <-> rotulo pareados            : %s" % r["pareamento_imagem_rotulo"])
    print("   holdout fora de imagesTr              : %s" % r["holdout_fora_de_imagesTr"])
    print("   conversoes com foreground identico    : %s (%d mascaras)"
          % (r["conversoes_todas_identicas"], len(r["conversoes"])))
    print("   originais intactos por sha256         : %s (%d arquivos)"
          % (r["originais_intactos"], r["n_originais_conferidos"]))

    saida = Path(pf["saida"])
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "dataset_nnunet.json").write_text(
        json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\nescrito:", saida / "dataset_nnunet.json")

    ok = (r["imagesTr_confere"] and r["pareamento_imagem_rotulo"]
          and r["holdout_fora_de_imagesTr"] and r["conversoes_todas_identicas"]
          and r["originais_intactos"] and not r["intersecao_treino_holdout"])
    print("\nPORTAO DO DATASET: %s" % ("OK" if ok else "REPROVADO"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
