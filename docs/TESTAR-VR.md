# Como testar no Meta Quest

> Guia para quem vai testar o VRmed no headset. Leva ~5 minutos.

## O detalhe que trava todo mundo

**WebXR só funciona em contexto seguro: HTTPS ou `localhost`.**

Se você rodar `npm run dev` e abrir `http://192.168.0.10:3000` no navegador do Quest, o
`navigator.xr` **não existe** e o botão "Entrar em VR" fica desabilitado. Não é bug do app —
é regra do navegador. Escolha uma das opções abaixo.

---

## Opção A — HTTPS automático (recomendada, 1 comando)

O Next gera um certificado autoassinado sozinho.

```bash
npm install
npm run dev:vr
```

1. Anote o IP do computador na rede local:
   - Windows: `ipconfig` → "Endereço IPv4" (ex.: `192.168.0.10`)
   - macOS/Linux: `ifconfig | grep inet`
2. O computador e o Quest precisam estar **na mesma rede Wi-Fi**.
3. No navegador do Quest, abra: **`https://SEU_IP:3000/viewer`** (repare no **https**)
4. Vai aparecer um aviso de certificado → **Avançado → Prosseguir mesmo assim**.
5. Escolha um modelo (comece pela **Laringe**, a mais leve) e clique em **Entrar em VR**.

Se o Quest recusar o certificado e não deixar prosseguir, use a Opção B.

---

## Opção B — Cabo USB (mais chata, mas infalível)

Faz o `localhost` do computador virar `localhost` dentro do Quest — contexto seguro garantido.

**Pré-requisito:** modo desenvolvedor ativado no Quest (pelo app Meta Horizon no celular,
exige criar uma organização de desenvolvedor — é grátis).

1. Instale o **Android Platform Tools** (traz o `adb`).
2. Conecte o Quest no computador por USB e **aceite a permissão de depuração** dentro do headset.
3. Confirme que o aparelho aparece:
   ```bash
   adb devices
   ```
4. Redirecione a porta:
   ```bash
   adb reverse tcp:3000 tcp:3000
   ```
5. Rode o servidor normalmente:
   ```bash
   npm run dev
   ```
6. No navegador do Quest, abra: **`http://localhost:3000/viewer`**

---

## O que observar no teste (é isso que precisamos saber)

Ao entrar em VR, **olhe ao redor girando 360°** e responda:

| O que apareceu | O que significa |
|---|---|
| **Grade azul no chão + anel + o órgão** | ✅ Funcionando |
| **Grade e anel, mas sem o órgão** | Renderização OK; o problema é o carregamento do modelo |
| **Tudo preto, sem grade nenhuma** | Problema mais profundo na sessão XR |

O anel azul no chão marca onde o órgão está — se não estiver vendo nada, **gire o corpo**:
o modelo pode estar atrás de você, dependendo de para onde você estava virado ao iniciar.

### Ajuda extra
Se der erro, abra o console do navegador do Quest em `chrome://inspect` pelo computador
(com o cabo conectado) e copie as mensagens de erro.

---

## Tarja branca "rodando em segundo plano" ao sair

Faixa nativa do Quest Browser com **Retomar / Sair** (contexto em `docs/CONTEXTO.md`). Para
confirmar se a correção resolveu, ou para colher dados se a faixa voltar:

1. De preferência use o **deploy do Render** (HTTPS e build de produção, igual ao do evento).
   A Opção A (`npm run dev:vr`) também serve, mas roda o React em modo de desenvolvimento.
2. No Quest, abra **`https://…/viewer?debug=xrlog`**. Aparece uma barrinha verde no canto
   inferior esquerdo; a flag fica gravada.
3. Repita cada saída **5 vezes**, anotando se a faixa apareceu:

   | # | Entrar | Sair por |
   |---|---|---|
   | a | `/viewer` → Entrar em **VR** | botão 3D **Sair do VR** |
   | b | `/viewer` → Entrar em **AR** | botão 3D **Sair do AR** |
   | c | `/duelo` (escola e hospital) | botão 3D **Sair do VR** |
   | d | `/sala` → Entrar em VR | computador → um dos modos do hub |
   | e | qualquer cena | botão **Meta** → **Sair/Quit** do sistema |
   | f | qualquer cena | botão **Meta** → **Retomar** e depois o botão 3D |
   | g | qualquer cena | botão **Meta** → clicar na página 2D → **Entrar** de novo |

4. **Se a faixa aparecer**, toque em **"Marcar: tarja apareceu"** (antes de qualquer outra
   coisa) e depois em **Copiar**, ou em **Registro** para ler na tela. Com o cabo, também dá para
   ler em `chrome://inspect` no computador, filtrando `[xrlog]`.
5. O que olhar no registro, perto da marca:
   - `evento 'end' (SEM end da página…)` → quem encerrou foi o sistema;
   - `sessões=#N:visible-blurred` ou `quadros-parados` com a página 2D visível → sobrou sessão viva;
   - `offerSession(…)` → alguma oferta ainda está sendo feita (não deveria haver nenhuma);
   - `topo:` → se algum elemento **da página** cobre o topo (a faixa nativa não aparece ali).
6. Teste de controle: faça as mesmas saídas em
   `https://threejs.org/examples/webxr_vr_cubes.html`. Se a faixa aparecer lá também, é bug do
   Quest Browser.
7. Ao terminar: **Desligar** no painel, ou abrir `?debug=off`.

---

## Modelos e performance

Use **Laringe** (18k triângulos) ou **Coração** (11k) para testar.
**Não use Miologia** — tem 982k triângulos e não sustenta 72–90fps no Quest.
