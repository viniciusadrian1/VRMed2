# VRmed

**Plataforma de estudo de anatomia humana em 3D, realidade virtual e IA tutor.**

VRmed é uma aplicação web desenvolvida como projeto de **Iniciação Científica
(IC)**. O público são estudantes de medicina e das áreas da saúde que desejam
estudar anatomia de forma imersiva. Além de ferramenta de estudo, a aplicação é
instrumentada para gerar dados quantitativos e qualitativos para a pesquisa.

A aplicação tem três pilares:

1. **Visualizador 3D/VR** — modelos `.glb` que podem ser girados, ampliados,
   fatiados com cortes anatômicos, inspecionados em camadas e explorados em VR.
2. **Chat com IA tutor** — assistente que responde dúvidas de anatomia e
   fisiologia citando apenas fontes médicas reconhecidas.
3. **Camada pedagógica e de pesquisa** — modo quiz, comparação saudável vs.
   patológica, histórico exportável em PDF e telemetria anônima.

---

## Sumário

- [Como rodar](#como-rodar)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Como adicionar modelos `.glb`](#como-adicionar-modelos-glb)
- [Como adicionar descrições JSON](#como-adicionar-descrições-json)
- [Como interpretar os dados coletados](#como-interpretar-os-dados-coletados)
- [Como o system prompt foi construído](#como-o-system-prompt-foi-construído)
- [Páginas administrativas](#páginas-administrativas)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Stack técnica](#stack-técnica)
- [Decisões de projeto](#decisões-de-projeto)

---

## Como rodar

### Pré-requisitos

- **Node.js 20.9+** (exigência do Next.js 16).
- npm (incluso no Node).

### Instalação

```bash
npm install
```

### Configuração

Copie o arquivo de exemplo de variáveis de ambiente e preencha os valores:

```bash
cp .env.example .env.local
```

O `.env.local` **não** é versionado. Veja a seção
[Variáveis de ambiente](#variáveis-de-ambiente).

### Desenvolvimento

```bash
npm run dev
```

A aplicação fica disponível em `http://localhost:3000`.

### Build de produção

```bash
npm run build
npm run start
```

### Outros comandos

```bash
npm run typecheck   # verificação de tipos (tsc --noEmit)
npm run lint        # ESLint
```

---

## Variáveis de ambiente

| Variável                    | Obrigatória | Descrição                                                       |
| --------------------------- | ----------- | --------------------------------------------------------------- |
| `OPENAI_API_KEY`            | Para o chat | Chave da API da OpenAI. Usada apenas no servidor.               |
| `ADMIN_PASSWORD`            | Para /admin | Senha de acesso às páginas administrativas (HTTP Basic Auth).   |
| `NEXT_PUBLIC_ANALYTICS_URL` | Opcional    | URL da instância de analytics (Umami self-hosted recomendado).  |
| `NEXT_PUBLIC_ANALYTICS_ID`  | Opcional    | ID do site/projeto no analytics.                                |

Sem `OPENAI_API_KEY`, todo o restante da aplicação funciona — apenas o chat
tutor fica indisponível. Sem as variáveis de analytics, nenhuma telemetria é
carregada e o banner de consentimento não aparece.

---

## Como adicionar modelos `.glb`

A aplicação já é totalmente funcional **sem** modelos reais: quando um arquivo
`.glb` não existe, o visualizador exibe um **modelo de demonstração procedural**
com camadas nomeadas, permitindo testar cortes, raio-X, anotações e quiz.

Para adicionar um modelo real:

1. **Coloque o arquivo** em `public/models/healthy/<id>.glb`.
   O `<id>` deve corresponder ao identificador do órgão no catálogo.
2. **(Opcional) Versão patológica:** coloque em
   `public/models/pathological/<id>.glb`, com o **mesmo nome** do saudável.
3. **Cadastre o órgão** em `lib/organs.ts`, no array `ORGANS`:

   ```ts
   {
     id: "novo-orgao",
     name: "Novo Órgão",
     category: "digestorio",
     modelPath: "/models/healthy/novo-orgao.glb",
     pathologicalPath: "/models/pathological/novo-orgao.glb", // opcional
     pathologyName: "Nome da condição",                       // opcional
     blurb: "Descrição curta para o seletor.",
   }
   ```

4. **Nomeie os meshes** do modelo de forma descritiva (`skin`, `muscle`,
   `vessel`, `bone`, `nerve`...). A aplicação faz `traverse` na cena, lista cada
   mesh como uma camada e traduz nomes em inglês via `lib/anatomy-labels.ts`. A
   profundidade anatômica (externa / intermediária / interna) é estimada pelo
   nome — base do preset do **modo raio-X**.

O modelo é normalizado automaticamente (centralizado e escalado), portanto não
precisa ter um tamanho ou origem específicos.

---

## Como adicionar descrições JSON

Cada órgão tem uma descrição textual usada no painel de áudio/narração. Crie o
arquivo `public/descriptions/<id>.json` no formato:

```json
{
  "name": "Coração",
  "shortDescription": "Resumo de uma linha exibido como destaque.",
  "fullDescription": "Texto completo, narrado pela síntese de voz e exibido como transcrição acessível.",
  "sources": ["Gray's Anatomy, 42ª ed.", "Mayo Clinic"]
}
```

- `fullDescription` é o texto narrado pela **Web Speech API** (voz `pt-BR`) e
  também exibido visualmente (transcrição acessível para leitores de tela).
- Para um fallback de áudio pré-gravado, coloque um `.mp3` em
  `public/audio/<id>.mp3` — usado apenas quando o navegador não tem voz pt-BR.

---

## Como interpretar os dados coletados

A camada de pesquisa gera **dois conjuntos de dados**, ambos anônimos.

### 1. Telemetria de uso (analytics)

Eventos anônimos enviados ao Umami/PostHog **somente após consentimento**
explícito do usuário (banner LGPD). O wrapper `lib/analytics.ts` verifica o
consentimento antes de qualquer envio. Eventos registrados:

| Evento                            | O que indica                                          |
| --------------------------------- | ----------------------------------------------------- |
| `organ_viewed`                    | Órgão visualizado + tempo de permanência (`dwellMs`). |
| `clipping_plane_used`             | Uso de corte anatômico (qual eixo).                   |
| `xray_mode_toggled`               | Ativação/desativação do modo raio-X.                  |
| `layer_visibility_changed`        | Alteração de visibilidade de uma camada.              |
| `annotation_created`              | Criação de anotação.                                  |
| `annotation_clicked`              | Clique em um hotspot.                                 |
| `audio_narration_played`          | Narração reproduzida + tempo ouvido.                  |
| `quiz_started` / `quiz_completed` | Início/fim de quiz, com pontuação.                    |
| `chat_message_sent`               | Pergunta enviada — **hash** + categoria, nunca o texto. |
| `chat_response_rated`             | Avaliação 👍/👎 de uma resposta.                       |
| `compare_mode_used`               | Uso do modo de comparação (qual par).                 |
| `vr_entered` / `vr_exited`        | Entrada/saída de VR, com duração.                     |
| `pdf_exported`                    | Exportação de sessão em PDF.                          |

Esses dados são consultados no **painel do Umami** configurado em
`NEXT_PUBLIC_ANALYTICS_URL`: órgãos mais estudados, ferramentas mais usadas,
clusters de perguntas, etc. Importante: o texto das perguntas **nunca** é
enviado — apenas um hash FNV-1a irreversível e uma categoria temática.

### 2. Avaliações do tutor (feedback)

Quando um estudante avalia uma resposta da IA, o registro é gravado no servidor
em `feedback.jsonl` (um JSON por linha) com: pergunta, resposta, nota (up/down),
tags de problema, comentário, órgão em foco e timestamp.

- Visualize e exporte em **`/admin/feedback`** (CSV pronto para planilha).
- Veja agregados (aprovação por órgão, problemas mais apontados) em
  **`/admin/insights`**.
- A interface de armazenamento (`lib/feedback-store.ts`) foi mantida simples
  para permitir migração futura a Supabase/Postgres — basta substituir as
  funções `appendFeedback` e `readAllFeedback`.

---

## Como o system prompt foi construído

O system prompt do tutor está em `lib/medical-system-prompt.ts` e foi
estruturado em torno de seis diretrizes, derivadas dos requisitos da IC:

1. **Papel** — tutor de anatomia/fisiologia para estudantes de medicina, com
   profundidade calibrada para a graduação e incentivo ao estudo ativo.
2. **Fontes** — ensina apenas o que está consolidado nos tratados da graduação
   (Moore, Gray's Anatomy, Netter, Sobotta, Guyton & Hall, Robbins); veta sites,
   blogs e artigos não verificáveis; indica onde estudar uma única vez, no fim,
   em frase natural, e só com certeza; nunca inventa referência.
3. **Escopo** — recusa cordial a perguntas fora do âmbito educacional médico.
4. **Limites clínicos** — proibição explícita de diagnóstico ou conduta para
   casos reais; orientação a procurar um profissional.
5. **Formato** — português do Brasil, texto puro sem Markdown (a gaveta da Sala
   e o painel VR não renderizam Markdown), 2 a 5 frases.
6. **Contexto dinâmico** — o órgão/sistema atualmente visualizado é acrescentado
   ao final do prompt.

O chat usa o **ChatGPT da OpenAI** (`gpt-4o` por padrão), via Route Handler do
Next.js com resposta em streaming. O bloco estável de diretrizes é mantido no
início do system prompt, favorecendo o cache automático de prompt da OpenAI; o
contexto do modelo em foco é anexado ao final. O chip de citação em
`components/chat/SourceCitation.tsx` é legado do prompt antigo (`[Fonte: X]`) e
não é mais acionado.

---

## Páginas administrativas

`/admin/feedback` e `/admin/insights` são protegidas por **HTTP Basic Auth**
(arquivo `proxy.ts`). Ao acessar, o navegador pede usuário e senha — informe
qualquer usuário e a senha definida em `ADMIN_PASSWORD`. Sem essa variável, o
acesso é totalmente bloqueado.

---

## Estrutura do projeto

```
app/                      Rotas (App Router)
  page.tsx                Landing page
  viewer/                 Visualizador 3D principal
  compare/                Comparação saudável vs. patológica
  quiz/                   Modo quiz
  history/                Histórico de sessões
  privacidade/            Política de privacidade (LGPD)
  admin/                  Painel do pesquisador (protegido)
  api/chat/               Endpoint do chat (streaming)
  api/feedback/           Endpoint de feedback
components/
  viewer/  chat/  compare/  quiz/  history/  layout/  ui/  analytics/
lib/                      Estado (Zustand), OpenAI, 3D, analytics, TTS, PDF
public/
  models/systems/         Modelos .glb de sistemas (corpo inteiro)
  models/healthy/         Modelos .glb de órgãos saudáveis
  models/pathological/    Modelos .glb de órgãos patológicos
  descriptions/           JSON descritivo de cada modelo
  audio/                  Áudios pré-gravados (fallback do TTS)
types/                    Tipos TypeScript centrais
proxy.ts                  Proteção das rotas /admin
```

---

## Stack técnica

- **Next.js 16** (App Router) + **TypeScript** estrito + **Turbopack**
- **React Three Fiber + drei + three.js** — motor 3D
- **@react-three/xr** — WebXR (VR no navegador)
- **Tailwind CSS v4** + componentes shadcn/ui + **Framer Motion** + lucide-react
- **Zustand** (com `persist`) — estado global e persistência em localStorage
- **OpenAI SDK** (`openai`) — chat tutor (ChatGPT), via Route Handler
- **react-markdown + remark-gfm** — renderização das respostas
- **Zod** — validação dos payloads de API
- **jsPDF** — exportação de sessões em PDF
- **Web Speech API** — narração (com fallback para `.mp3`)

---

## Decisões de projeto

Pontos em que a implementação ajustou ou interpretou a especificação:

- **Next.js 16:** `create-next-app` instalou a versão 16 (a especificação pedia
  "14+"). O código segue as convenções do Next 16 (APIs de request assíncronas,
  Turbopack, `proxy.ts` no lugar de `middleware.ts`).
- **Modelo do chat:** o tutor usa o ChatGPT da OpenAI (`gpt-4o`), definido na
  constante `CHAT_MODEL` em `lib/openai.ts` — basta alterá-la para usar outro
  modelo da OpenAI.
- **Exportação em PDF:** construída diretamente com **jsPDF** (texto
  selecionável). Optou-se por não capturar o DOM com `html2canvas` porque a
  biblioteca não interpreta as cores `oklch`; por isso a paleta da aplicação usa
  hexadecimais.
- **Superfície de corte:** os cortes anatômicos usam renderização em dupla face
  (`DoubleSide`), que revela o interior do modelo. Um _capping_ por stencil é
  uma evolução planejada.
- **Distratores do quiz:** gerados a partir das demais anotações do órgão e de
  uma lista de termos anatômicos genéricos (`lib/quiz.ts`) — a opção
  "pré-cadastrados" prevista na especificação, robusta e sem depender de rede.
- **Modelos de demonstração:** enquanto não há arquivos `.glb`, todo o
  visualizador funciona com modelos procedurais — assim a IC pode validar a
  experiência antes de produzir os modelos definitivos.
- **Sistemas e órgãos:** o catálogo aceita dois tipos de modelo. _Sistemas_
  (corpo inteiro, em `models/systems/`) têm as camadas agrupadas por **tecido**,
  via material — útil para modelos cujas malhas não têm nomes anatômicos.
  _Órgãos_ (em `models/healthy/`) agrupam camadas por **malha**. O tipo é
  definido por `kind`/`layerBy` em `lib/organs.ts`.
- **Identificar estruturas:** clicar numa estrutura no visualizador exibe o que
  ela é. Modelos com malhas nomeadas mostram o nome da estrutura; modelos sem
  nomes (como exports do Sketchfab) mostram o tecido. Anotações numeradas do
  Sketchfab não fazem parte do `.glb` e não são importadas.

---

Projeto de Iniciação Científica · VRmed.
