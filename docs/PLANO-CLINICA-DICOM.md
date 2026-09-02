# Clínica — pipeline DICOM → órgão 3D fiel (plano reconciliado com o repo)

Estado em 2026-09-01. Origem: plano do grupo (`vr-med-pipeline-dicom-3d.md`, ideia surgida
da conversa com o professor sobre o trabalho em cardiologia no Dante Pazzanese) cruzado com o
código real do módulo Clínica. Regras de base continuam sendo as de `PROMPT-CLINICA.md`.

## 1. Reconciliação: o que o plano supunha × o que o código já fazia

O plano parte de "o pipeline antigo ia direto do exame para a malha, ligando voxels por
intensidade". **Isso não é verdade no repo**: desde o primeiro commit da Clínica o fluxo é
TC → TotalSegmentator (nnU-Net pré-treinado, inferência) → máscara por estrutura → marching
cubes **sobre a máscara suavizada** → Taubin → decimação → GLB nomeado
(`scripts/tc-para-vrmed.py`). Não existe limiar de HU gerando superfície em lugar nenhum.

Logo, o plano é uma **evolução** do pipeline, não uma substituição. Reescrever do zero
reintroduziria bugs já resolvidos (fissuras dos lobos, z-fighting entre máscaras vizinhas,
normais invertidas — commits 80f53d9, 6982492, 232072f).

### Causas reais dos artefatos ("linhas soltas, formas estranhas, preenchimento errado")

| # | Causa | Status |
|---|---|---|
| 1 | 5 lobos extraídos separados → fissuras interlobares lidas como "linhas" | corrigido (`--pulmoes-inteiros`) |
| 2 | Superfícies coplanares entre máscaras vizinhas → z-fighting (linhas finas claras) | corrigido (`level=0.56`) |
| 3 | Normais do marching cubes para dentro → iluminação invertida, HU amostrado na parede | corrigido no corpo principal (`fix_normals`) |
| 4 | **Sem filtro de maior componente / fill-holes**: ilhas de poucos voxels viram cascas soltas | **pendente — etapa 3a** (o QA de hoje já mostra ilhas de 2–11 mm³ nos lobos) |
| 5 | Fatias de 2,5 mm → degrau residual ("escadinha") no caso torax-completo | mitigado pela validação de espessura da ingestão; reamostrar isotrópico na 3a |
| 6 | Erosão de estruturas finas (esôfago, traqueia) pelo par gaussiana + level 0,56 | pendente — etapa 3a |
| 7 | Viewer descarta a escala real (`normalizeContent`) → impede medir e alinhar volume | pendente — etapa 4 |

## 2. Estrutura de módulos

```
scripts/
  preparar-caso.py        # NOVO — etapas 1+2 + métricas + QA (sem malha)
  tc-para-vrmed.py        # CLI da malha (etapa 3a); agora importa do pacote
  achados-pulmao.py       # inalterado
  pintar-pulmao.py        # inalterado (modo "Mapa de achados")
  clinica/                # pacote importado pelos CLIs e, na Fase 3, pelo worker
    ingestao.py           # etapa 1: DICOM|NRRD|NIfTI → .nii.gz em HU, spacing real, validação
    segmentacao.py        # etapa 2: presets, TotalSegmentator, licença, segmentacao.json
    metricas.py           # volume mL, bbox mm, componentes conexos por máscara
    qa.py                 # PNGs de máscara sobre a TC (3 planos × 3 cortes + mosaico)
    cores.py              # cores didáticas (GLB e QA)
    [malha.py]            # etapa 3a — mover de tc-para-vrmed.py quando for tocada
    [volume.py]           # etapa 3b — recorte HU + presets de função de transferência
.clinica-dados/<slug>/    # gitignored, só no PC: ct.nii.gz, masks/, qa/, relatorio.json
public/pacientes/         # publicado: <slug>.glb (Draco) + manifest.json
```

Por que assim: o hífen em `tc-para-vrmed.py` impede `import`, e a Fase 3 (worker Modal) precisa
importar o mesmo código que o CLI. Nada de FastAPI + Celery: as decisões de infraestrutura já
tomadas em `PROMPT-CLINICA.md` (rotas Next + Neon + R2 + Modal) não foram reabertas.

## 3. Etapas 1 e 2 — implementadas e testadas

```
.venv-pipeline\Scripts\python scripts\preparar-caso.py --input <dicom_dir | .nrrd | .nii.gz> ^
    --slug <caso> --preset cardiaco [--tarefas heartchambers_highres] [--reusar-mascaras]
```

- **Ingestão** (`clinica/ingestao.py`, SimpleITK): série DICOM ordenada por
  `ImagePositionPatient`, `RescaleSlope/Intercept` aplicados (HU), spacing real, NIfTI int16
  gzip. Valida: eixo mais grosso > 3 mm (aviso), passo irregular entre fatias (aviso),
  intensidades fora de HU (erro, `--forcar` rebaixa a aviso — critério: mínimo ≤ −900 **e** ≥ 1 %
  dos voxels perto de −1000 HU; a mediana não serve porque mede o enquadramento, não a escala),
  orientação oblíqua (aviso). Só metadados não identificáveis vão para o relatório (nem o UID da
  série); origem/direção gravadas em RAS, como o resto do pipeline. Regressão: o DICOM do LIDC
  reconvertido saiu idêntico ao NIfTI aceito em agosto (shape, zooms, affine, HU).
- **Segmentação** (`clinica/segmentacao.py`): tarefa `total` com `roi_subset` do preset
  (`torax`, `cardiaco` novo, `abdomen`, `completo`); tarefas extras em subpasta, com a checagem
  de licença da própria lib (`registry.requires_license` + `config.has_valid_license_offline`,
  cobre as 18 tarefas comerciais) virando aviso + "pulada" em vez do `sys.exit(1)` do
  TotalSegmentator; tarefa desconhecida ou `--fast` em tarefa extra também não derrubam o run;
  versão do TotalSegmentator sempre gravada (`masks/segmentacao.json`), inclusive quando reusada;
  `--reusar-mascaras` só reusa se todas as máscaras do preset existirem.
- **Métricas** (`clinica/metricas.py`): volume (mL), bbox (mm), número de componentes e tamanho
  das ilhas — medida automática, enquadramento educacional.
- **QA** (`clinica/qa.py`): 9 PNGs + mosaico, convenção radiológica, aspecto pelo spacing.

### Resultado no caso público CTA-cardio (3D Slicer Sample Data)

Angiotomografia cardíaca com contraste, 512×512×321, 0,93×0,93×1,25 mm, RTX 4060 Ti:
ingestão 4 s · TotalSegmentator 63 s · métricas + QA ~85 s · total 153 s.

| estrutura | volume (mL) | componentes | observação |
|---|---:|---:|---|
| heart | 496,5 | 1 | rótulo único da tarefa `total` (sem câmaras) |
| aorta | 133,7 | 1 | arco + descendente inteiros |
| superior / inferior vena cava | 16,6 / 24,3 | 1 / 2 | ilha de 297 mm³ na cava inferior |
| pulmonary_vein | 20,5 | 3 | várias veias = vários componentes, esperado |
| lobos pulmonares | 275–629 | 1–5 | ilhas de 1–11 mm³ → filtro de componente na 3a |
| trachea / esophagus | 47,0 / 25,5 | 1 / 1 | |

Fonte: `.clinica-dados/cta-cardio/relatorio.json`; imagens em `.clinica-dados/cta-cardio/qa/`.

**Câmaras (2026-09-02, `heartchambers_highres` com licença):** 82 s na RTX 4060 Ti, resolução
nativa (0,93×0,93×1,25 mm), sete máscaras, todas com um componente só; 95 % das câmaras +
miocárdio caem dentro do rótulo `heart` da tarefa `total`, que por sua vez é 89 % coberto por
elas (o resto é parede do VD/átrios e gordura). QA em `qa/heartchambers_highres/`.

| estrutura | volume (mL) | observação |
|---|---:|---|
| heart_ventricle_left / right | 94,7 / 123,9 | cavidades (sangue) |
| heart_atrium_left / right | 37,3 / 88,0 | AE sem a confluência das veias pulmonares |
| heart_myocardium | 123,7 | só o miocárdio do VE (limite da tarefa) |
| pulmonary_artery | 45,8 | tronco + ramos proximais, ausente na tarefa `total` |
| aorta | 99,0 | só o trecho dentro do recorte do coração; manter a aorta da `total` |

O código passou por revisão adversarial (3 revisores + 2 verificadores por achado; 14 defeitos
confirmados e corrigidos no mesmo dia — validação de HU sensível ao FOV, bbox por centro de
voxel, LPS misturado com RAS no relatório, licença hardcoded, UID da série no relatório, cores
das câmaras, tradução da aurícula, entre outros).
`fonteDados` ao publicar: "3D Slicer Sample Data (CTACardio) — uso irrestrito declarado pelos
mantenedores" (mesmo padrão do CTChest já publicado).

## 4. Câmaras cardíacas: licença do TotalSegmentator (ação do grupo)

`heartchambers_highres` (átrios, ventrículos, miocárdio, artéria pulmonar) e
`coronary_arteries` são tarefas marcadas como comerciais: exigem licença **acadêmica gratuita**.

1. Pedir em https://backend.totalsegmentator.com/license-academic/ (e-mail institucional).
2. No PC do pipeline: `.venv-pipeline\Scripts\totalseg_set_license -l aca_XXXX` (valida online).
3. Rodar de novo com `--tarefas heartchambers_highres --reusar-mascaras` — o primeiro uso baixa
   os pesos (Dataset301). Sem licença o script apenas avisa e pula, como hoje.

Registrar a licença em `docs/` (uso não comercial, compatível com a IC). Volume de câmara e
espessura de parede só aparecem como **"medida automática — visualização educacional, não
substitui laudo"**, com selo "experimental" enquanto não houver Dice/HD95 (§5 do PROMPT).

**Licença configurada em 2026-09-02** (licenciado: Vinícius, e-mail institucional), com as
quatro cláusulas aceitas: uso acadêmico não comercial; uso interno; sem aprovação regulatória
para diagnóstico; sem garantia. Regras derivadas:

- A chave (`aca_…`) fica só em `C:\Users\vinic\.totalsegmentator\config.json` deste PC. Nunca
  no git, no `.env`, em prints ou no chat.
- Os pesos das tarefas licenciadas (`heartchambers_highres`, `coronary_arteries`, Dataset301/509)
  não são copiados para o Mac nem para máquinas de outros membros; quem precisar rodar pede a
  própria licença (gratuita).
- Máscaras e GLBs gerados são resultado do projeto e podem ir para o site com a atribuição ao
  TotalSegmentator; o **software** não.
- Fase 3: antes de expor a tarefa licenciada num worker que processa exames enviados por
  terceiros, perguntar ao autor (contato no próprio pacote) — pode contar como "disponibilizar a
  terceiros". A tarefa `total` não tem essa restrição.

## 5. Próximas etapas

Antes de tocar na 3a, ler **`CLINICA-FIDELIDADE.md`**: lista priorizada (14 itens, com fontes)
do que separa o modelo cardíaco da realidade e o plano em três passos (malha + viewer sem
licença; câmaras com `heartchambers_highres`; camada de volume). Correção de fato: a tarefa
`heartchambers_highres` roda na resolução nativa do exame (sem `resample` na config), não a 1,5 mm.

- **3a — malha** (`clinica/malha.py`, a partir de `tc-para-vrmed.py`): maior componente conexo
  + `binary_fill_holes` ANTES do marching cubes; sigma mínimo de 1 voxel em z; `.stl` (1 linha);
  volume/bbox no relatório (já em `metricas.py`); orçamento continua ≤150k tris **por paciente**
  (o "~100k por estrutura" do plano estoura o Quest 2).
- **3b — volume** (`clinica/volume.py`): recorte HU pelo bbox das máscaras (+ margem), ≤384³,
  export para textura 3D; presets de função de transferência (cardíaco com contraste, tórax sem
  contraste, abdome). Decidir antes: retenção do volume HU derivado (LGPD — ok com dados
  públicos, precisa regra para a Fase 3).
- **4 — viewer**: escala real fixa na Clínica (pré-requisito para medir e alinhar), toggles por
  estrutura, plano de corte, janela HU; ray marching com `Data3DTexture` do próprio three.js
  (sem CDN, sem Niivue/vtk.js no produto). Desktop primeiro, Quest depois.
- **Validação §5**: `validar-segmentacao.py` (Dice/HD95) com o dataset do TotalSegmentator
  (Zenodo 10047292, CC-BY-4.0) — insumo certo, 3,2 GB no subset.

## 6. Fontes públicas de TC cardíaca avaliadas

| Fonte | Contraste | Acesso | Veredito |
|---|---|---|---|
| 3D Slicer CTACardio | sim, 1,25 mm | download direto (61 MB) | **usado hoje** |
| TotalSegmentator dataset v2 | misto, 1,5 mm | Zenodo, CC-BY-4.0 (3,2–23,6 GB) | validação Dice, não primeiro caso |
| TCIA | sem coleção de CTA cardíaca | NBIA Data Retriever | não |
| MM-WHS 2017 | sim, 1,6 mm | acordo por e-mail, sem redistribuição | só se o grupo assinar |
| ASOCA / ImageCHD / ImageCAS | sim | cadastro/ética ou login Kaggle | depois (coronárias / congênitas) |
