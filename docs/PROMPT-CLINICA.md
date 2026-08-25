# PROMPT MESTRE — VRmed Clínica (terceiro modo)

> **Como usar:** entregue este documento inteiro a quem for implementar (pessoa ou IA).
> Ele é autossuficiente: contexto, decisões já tomadas, fases com critérios de aceite,
> métricas de acurácia e o que NÃO fazer. Execute as fases EM ORDEM — cada uma é
> utilizável sozinha e é pré-requisito da seguinte.

---

## 1. Contexto do projeto (leia antes de codar)

O **VRmed** é uma plataforma de anatomia 3D/VR em pt-BR (Next.js 16 + React Three
Fiber + WebXR, Quest 2/3 via navegador), projeto de Iniciação Científica. Hoje tem
**dois modos**:

1. **Estudo** — visualizador (`/viewer`), comparar saudável×patológico, quiz, histórico.
2. **Arena** (`/arena`) — jogo de identificação anatômica em VR, rota **isolada**
   (não importa a store global; se quebrar, o resto fica de pé).

O objetivo deste prompt é o **terceiro modo: VRmed Clínica** (`/clinica`) — o médico
envia a tomografia do paciente e visualiza **o órgão daquele paciente** em 3D/VR.

**Leia também:** `docs/CONTEXTO.md` (estado do app e pegadinhas), `CLAUDE.md` (regras),
`docs/PLANO-FIAP-NEXT.md` (como a Arena foi estruturada — o modelo a seguir).

### Regras herdadas que valem aqui (aprendidas com dor)

- **Rota isolada** como a Arena: `/clinica` com seus componentes em
  `components/clinica/`. NÃO acoplar à store global (`lib/store.ts`) — o
  `setCurrentOrgan` dela reseta estado do visualizador e é persistido.
- **Malhas NOMEADAS são o contrato**: o visualizador identifica estruturas pelo nome
  do nó/malha (`lib/model-utils.ts: detectStructures/identifyStructure`) e traduz via
  `lib/anatomy-labels.ts`. Todo GLB gerado DEVE ter uma malha por estrutura, com nome.
- **Draco local** (`public/draco/`), **fonte local**, **perfis WebXR locais**
  (`public/webxr-profiles/`) — a aplicação funciona offline; não introduzir CDN.
- **NUNCA usar `--simplify` agressivo do gltf-transform** em anatomia (já destruiu o
  fígado uma vez). Decimação controlada no Python (ver §4), Draco só comprime.
- **Orçamento de VR**: alvo ≤ 150k triângulos por paciente carregado (ideal ≤ 80k).
  O Quest 2 renderiza estéreo a 72fps; `myology.glb` (982k) é o contraexemplo proibido.
- **WebXR exige HTTPS/localhost**; deploy atual no Render.
- Textos de UI em **pt-BR**. Enquadramento sempre: *"visualização e apoio ao estudo —
  não diagnóstico"* (nunca "assistência/diagnóstico": território ANVISA).

---

## 2. Arquitetura-alvo (decisões JÁ tomadas — não reabrir)

```
[Navegador /clinica]
   └─ upload assinado (ZIP DICOM, 100–500MB) ──► [Cloudflare R2: exames/]
   └─ cria job ─────────────────────────────────► [Postgres Neon: tabela jobs]
[Worker Python no Modal (GPU T4, serverless)]
   1. baixa exame do R2
   2. ANONIMIZA (pydicom: remove PatientName/ID/datas — antes de tudo)
   3. TotalSegmentator (CT) → máscaras NIfTI de 100+ estruturas nomeadas
   4. máscaras → malhas (marching cubes) → decimação → GLB nomeado → Draco
   5. sobe resultado para [R2: pacientes/], apaga exame original, job=pronto
[Navegador] ─ polling do status ─► caso aparece no catálogo da Clínica → abre no 3D/VR
```

**Stack fixa:** Python 3.11+, `pydicom`, `TotalSegmentator` (inferência apenas — **não
se treina nada**), `nibabel`, `scikit-image` (marching_cubes), `trimesh` +
`pyfqmr`/`fast-simplification` (decimação), `pygltflib` ou `trimesh` para GLB,
`gltf-transform` CLI para Draco. Infra: **Modal** (GPU), **Cloudflare R2** (storage),
**Neon Postgres** (jobs). Custos esperados: ~US$0,03–0,05/exame de GPU; faixas
gratuitas cobrem o MVP (ver `docs/` — apresentação da Fase 3).

**IA generativa/difusão: PROIBIDA no pipeline.** A malha deriva deterministicamente
da TC. (Difusão fica citada como trabalho futuro na IC, nada mais.)

---

## 3. FASE 1 — Pipeline offline + primeiro paciente (critério: demo em 2 semanas)

**Entregável:** script `scripts/tc-para-vrmed.py` (CLI) + 1 "paciente exemplo" no
catálogo estático da Clínica, visível em 3D e VR.

### Passos

1. **Dados de teste** (públicos, anonimizados — zero LGPD):
   - primeiro run: `CTChest` do 3D Slicer Sample Data (pequeno);
   - validação: subconjunto do **dataset do TotalSegmentator no Zenodo** (~1.200 TCs
     **com máscaras-gabarito** — essencial para a acurácia, ver §5);
   - variedade: TCIA / LIDC-IDRI.
2. **Script `tc-para-vrmed.py`** com argumentos:
   `--input <dicom_dir|nifti>` `--output <slug>.glb` `--structures <preset>`
   `--max-tris 120000` `--report <slug>.json`.
   - presets de estruturas: `torax` (pulmões por lobo, coração, aorta, traqueia,
     costelas opcionais), `abdomen` (fígado, rins, baço, pâncreas, aorta), `completo`;
   - uma malha **por estrutura**, `mesh.name` = nome TotalSegmentator
     (ex.: `lung_upper_lobe_left`);
   - suavização leve (taubin/laplaciano 1–2 iterações) + decimação até o orçamento;
   - GLB final passa por `npx gltf-transform draco` (SEM simplify);
   - `--report` grava JSON: nº estruturas, triângulos por malha, tempo por etapa,
     versão do TotalSegmentator.
3. **Tradução dos nomes**: adicionar ao `lib/anatomy-labels.ts` o mapeamento
   TotalSegmentator→pt-BR das estruturas dos presets
   (`lung_upper_lobe_left` → "Lobo superior esquerdo", etc.). SEM isso o
   clique-para-identificar mostra inglês técnico — inaceitável.
4. **Rota `/clinica` (versão estática)**:
   - página com identidade do app: lista de casos lida de
     `public/pacientes/manifest.json`
     (`[{ slug, titulo, descricao, glb, dataProcessamento, fonteDados }]`);
   - abrir caso → cena 3D isolada (padrão Arena: canvas próprio) com camadas,
     cortes, clique-para-identificar e botão Entrar em VR — **reusar** os
     componentes/utilitários existentes (`GLBModel`, `model-utils`, `XRManipulation`);
   - aviso fixo e visível: *"Visualização educacional a partir de exame real
     anonimizado. Não substitui laudo ou avaliação médica."*

### Critérios de aceite da Fase 1

- [ ] `tc-para-vrmed.py` roda de ponta a ponta numa TC pública sem intervenção manual
- [ ] GLB resultante ≤ 25 MB e ≤ 150k triângulos, todas as malhas nomeadas
- [ ] Caso abre em `/clinica`, clique identifica estruturas **em português**
- [ ] Funciona no Quest (72fps estáveis) — testar como a Arena foi testada
- [ ] `--report` gerado para cada caso processado

---

## 4. FASE 2 — Comparar + qualidade de malha (critério: demo forte)

1. **Comparar referência × paciente**: reusar o modo Comparar (câmeras sincronizadas)
   com o modelo de referência do catálogo de um lado e o paciente do outro.
2. **Qualidade**: relatório de malha por caso (buracos, componentes soltos,
   triângulos degenerados — `trimesh` dá isso de graça) anexado ao `--report`.
3. **3–5 pacientes exemplo** de fontes/patologias diferentes no manifest.

---

## 5. ACURÁCIA — como medir e reportar (obrigatório para a IC)

**O que se mede:** a segmentação (fonte de toda a geometria). Métrica padrão da área:
**Dice score** (0–1, sobreposição entre máscara prevista e gabarito), complementada
por **Hausdorff 95%** (erro de borda, em mm).

**Protocolo:**

1. Baixar N ≥ 20 casos do dataset Zenodo do TotalSegmentator (têm gabarito humano).
2. Script `scripts/validar-segmentacao.py`: roda o pipeline em cada caso, compara
   máscara prevista × gabarito por estrutura → CSV
   (`caso, estrutura, dice, hd95_mm, tempo_s`).
3. Script agrega e gera `docs/validacao/RELATORIO.md`: tabela por estrutura
   (média ± desvio), destacando as estruturas dos presets.
4. **Limiares de aceite** (baseados na literatura do próprio TotalSegmentator, que
   publica Dice ≈ 0,94 no conjunto de teste):
   - órgãos grandes (pulmões, fígado, coração): **Dice ≥ 0,90** — verde;
   - estruturas médias (rins, aorta, traqueia): Dice ≥ 0,85 — verde;
   - abaixo disso: estrutura entra como "experimental" na UI (badge âmbar) ou
     fica fora do preset.
5. Exibir na UI da Clínica, por caso: *"Segmentação validada em N casos públicos —
   Dice médio X,XX nas estruturas exibidas"* com link para o relatório.
   Transparência é argumento de defesa, não fraqueza.

**Importante:** nós NÃO treinamos o modelo; medimos a performance DELE no nosso
pipeline e nos nossos presets. É validação de uso, não de treinamento — deixar isso
explícito no texto da IC.

---

## 6. FASE 3 — Produto: upload → processa → aparece (critério: fluxo completo)

1. **Upload** em `/clinica/enviar`: aceita ZIP de DICOM; upload assinado direto ao R2
   (nunca pelo servidor Next); barra de progresso; limite 1 GB.
2. **API** (rotas Next): `POST /api/clinica/jobs` (cria job, devolve URL assinada),
   `GET /api/clinica/jobs/:id` (status: `enviado → processando → pronto | erro`,
   com etapa atual e % quando possível).
3. **Worker Modal**: função Python com imagem contendo o pipeline da Fase 1;
   timeout 30 min; retry 1×; **limite de gasto configurado no Modal desde o dia 1**;
   logs por etapa no job.
4. **Anonimização é a PRIMEIRA operação** sobre o arquivo, antes de persistir
   qualquer cópia processável. Exame original apagado do R2 após sucesso
   (retenção: só o GLB + report). Tabela de jobs sem nenhum dado de paciente.
5. **Catálogo por sessão do médico** (MVP: código de acesso simples por upload,
   sem contas; contas ficam para depois).
6. **Falhas legíveis**: cada erro do worker mapeado para mensagem em pt-BR na UI
   ("O arquivo não parece ser uma TC", "Exame sem tórax detectável", etc.).
   Aprendizado da Arena: falha silenciosa custa dias — TODO erro aparece na tela.

### Critérios de aceite da Fase 3

- [ ] Do ZIP à visualização em VR sem nenhum passo manual, em < 15 min
- [ ] Exame original comprovadamente apagado após processamento
- [ ] Custo por exame medido e registrado no report (bater com estimativa)
- [ ] 3 uploads simultâneos não quebram (fila serializa)
- [ ] TCLE/termos exibidos e aceitos antes do upload

---

## 7. O que NÃO fazer (tão importante quanto o resto)

- ❌ Treinar/fine-tunar qualquer modelo — só inferência com pesos publicados
- ❌ Difusão/IA generativa de imagem médica em qualquer ponto do fluxo
- ❌ Prometer "diagnóstico", "laudo", "assistência" — é visualização educacional
- ❌ Acoplar `/clinica` à store global ou modificar `/viewer`, `/arena`
- ❌ Processar dado de paciente real antes da Fase 3 completa (até lá, só datasets
  públicos anonimizados)
- ❌ Subir modelos > 150k triângulos para o catálogo VR
- ❌ Depender de CDN em runtime (regra do app inteiro)

---

## 8. Ordem de execução e verificação final

1. Fase 1 (pipeline + caso estático) → **já é demo e resultado de IC**
2. §5 Acurácia (pode rodar em paralelo com a Fase 2)
3. Fase 2 (comparar + qualidade)
4. Fase 3 (produto)

**Verificação de cada fase:** os critérios de aceite acima + teste no Quest real
(o navegador de desktop não substitui o headset — lição repetida deste projeto) +
`npm run build` limpo + commit com mensagem descritiva e push.
