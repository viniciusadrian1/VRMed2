@AGENTS.md

# VRmed — leia antes de mexer

Plataforma de estudo de anatomia 3D/VR em **pt-BR** (projeto de Iniciação Científica).
Responda e escreva comentários/UI em português.

**Contexto completo:** [`docs/CONTEXTO.md`](docs/CONTEXTO.md) — estado atual, o que já foi
corrigido, backlog adiado e pegadinhas.
**Próximo objetivo:** [`docs/PLANO-FIAP-NEXT.md`](docs/PLANO-FIAP-NEXT.md) — experiência VR para
a competição FIAP Next.

## Regras que já custaram tempo

- **Números do catálogo:** 18 modelos = 6 sistemas + 6 regiões + 6 órgãos; 3 com par patológico
  (coração, pulmão, fígado). É projeto de pesquisa — **nunca inventar estatística**. A fonte da
  verdade é `lib/organs.ts`.
- **VR:** `myology.glb` tem **982k triângulos — proibido em VR**. Usar `larynx.glb` (18k, 20
  estruturas nomeadas) e `coracao.glb` (11k).
- **WebXR exige HTTPS ou localhost.** Em `http://192.168.x.x:3000` o `navigator.xr` não existe e
  o botão de VR não funciona. Usar HTTPS ou cabo USB com `adb reverse`.
- **Otimizar GLB:** só compressão Draco. **Nunca `--simplify-ratio`** em modelo anatômico — dizima
  a malha e destrói o detalhe (já aconteceu com o fígado).
- **Turbopack:** ao editar variáveis CSS em `app/globals.css`, cache antigo de `next build` pode
  servir valores velhos. `rm -rf .next` + reiniciar.
- **`.env` nunca vai para o Git** (contém `OPENAI_API_KEY`). O modelo é `.env.example`.
- Só **regiões** e **órgãos** têm malhas nomeadas; **sistemas** agrupam por material (tecido),
  então `detectStructures()` retorna vazio para eles — é esperado, não é bug.

## Rodar

```
npm install
npm run dev
```
