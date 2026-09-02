/**
 * Spotify no rádio da Sala de Estudos — modo "controle remoto" (Spotify Connect
 * pela Web API, login OAuth PKCE 100 % no navegador).
 *
 * Por que Connect e não o Web Playback SDK (regras verificadas em 2026-09-02,
 * detalhes em docs/SALA-SPOTIFY.md):
 * - O app fica em "development mode": no máximo 5 usuários cadastrados à mão
 *   no Dashboard e o dono precisa manter Premium. Serve ao grupo e à banca,
 *   não ao público de um evento — por isso o lo-fi local continua sendo o
 *   padrão e o Spotify é opcional.
 * - Connect é só fetch + UI 3D: nada de script externo, iframe ou DRM na
 *   página (o SDK exige Widevine e não tem confirmação de funcionar no
 *   navegador do Quest). O som sai do dispositivo que o usuário escolher —
 *   inclusive o app do Spotify do próprio Quest, que toca em segundo plano.
 * - Escopos mínimos: estado/controle de reprodução e playlists. Nada de
 *   e-mail ou perfil (LGPD). Tokens só neste navegador (localStorage);
 *   "Desconectar" apaga tudo. Nenhum dado passa pelo servidor do VRmed.
 * - Controlar a reprodução exige Premium do usuário (regra do Spotify);
 *   conta Free só consegue ver o que está tocando.
 */

const CLIENT_ID = process.env.NEXT_PUBLIC_SPOTIFY_CLIENT_ID ?? "";
const CHAVE = "vrmed.spotify";
const ESCOPOS = "user-read-playback-state user-modify-playback-state playlist-read-private";
const CONTAS = "https://accounts.spotify.com";
const API = "https://api.spotify.com/v1";
/** Evento DOM disparado ao conectar/desconectar — o rádio 3D escuta. */
export const EVENTO_SPOTIFY = "vrmed:spotify";

interface Tokens {
  access: string;
  refresh: string;
  /** epoch ms em que o access token expira (1 h após emitido). */
  expira: number;
}

export type CodigoErro =
  | "sem_login"
  | "nao_testador"
  | "sem_dispositivo"
  | "premium"
  | "limite"
  | "rede";

export class ErroSpotify extends Error {
  constructor(
    message: string,
    public readonly codigo: CodigoErro,
  ) {
    super(message);
  }
}

export interface Reproducao {
  tocando: boolean;
  faixa: string;
  artista: string;
  dispositivo: string;
  progressoMs: number;
  duracaoMs: number;
}

export function spotifyConfigurado(): boolean {
  return Boolean(CLIENT_ID);
}

function ler(): Tokens | null {
  try {
    const bruto = localStorage.getItem(CHAVE);
    return bruto ? (JSON.parse(bruto) as Tokens) : null;
  } catch {
    return null;
  }
}

function gravar(tokens: Tokens | null): void {
  try {
    if (tokens) localStorage.setItem(CHAVE, JSON.stringify(tokens));
    else localStorage.removeItem(CHAVE);
  } catch {
    /* navegador sem storage: a sessão dura até recarregar */
  }
  window.dispatchEvent(new Event(EVENTO_SPOTIFY));
}

export function conectado(): boolean {
  return ler() !== null;
}

export function desconectar(): void {
  gravar(null);
}

/** A mesma URL cadastrada no Dashboard do Spotify (loopback em dev: 127.0.0.1, não localhost). */
function redirectUri(): string {
  return `${window.location.origin}/sala`;
}

function base64url(bytes: Uint8Array): string {
  let s = "";
  bytes.forEach((b) => (s += String.fromCharCode(b)));
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** Redireciona para o login do Spotify (PKCE). Fazer ANTES de entrar em VR:
 *  a navegação encerra a sessão XR. */
export async function iniciarLogin(): Promise<void> {
  const verifier = base64url(crypto.getRandomValues(new Uint8Array(64)));
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  sessionStorage.setItem(`${CHAVE}.verifier`, verifier);
  const url = new URL(`${CONTAS}/authorize`);
  url.search = new URLSearchParams({
    client_id: CLIENT_ID,
    response_type: "code",
    redirect_uri: redirectUri(),
    scope: ESCOPOS,
    code_challenge_method: "S256",
    code_challenge: base64url(new Uint8Array(digest)),
  }).toString();
  window.location.assign(url.toString());
}

async function pedirTokens(corpo: Record<string, string>): Promise<Tokens | null> {
  const res = await fetch(`${CONTAS}/api/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ client_id: CLIENT_ID, ...corpo }),
  });
  if (!res.ok) return null;
  const j = (await res.json()) as { access_token: string; refresh_token?: string; expires_in: number };
  return {
    access: j.access_token,
    // No refresh o Spotify pode não devolver refresh_token novo: manter o antigo.
    refresh: j.refresh_token ?? corpo.refresh_token ?? "",
    expira: Date.now() + j.expires_in * 1000,
  };
}

/** Chamar ao montar /sala: se a URL voltou com ?code=…, troca por tokens e limpa a URL. */
export async function concluirLogin(): Promise<"ok" | "erro" | "nada"> {
  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");
  const erro = params.get("error");
  if (!code && !erro) return "nada";
  const verifier = sessionStorage.getItem(`${CHAVE}.verifier`);
  sessionStorage.removeItem(`${CHAVE}.verifier`);
  window.history.replaceState(null, "", window.location.pathname);
  if (!code || !verifier) return "erro";
  const tokens = await pedirTokens({
    grant_type: "authorization_code",
    code,
    redirect_uri: redirectUri(),
    code_verifier: verifier,
  });
  if (!tokens) return "erro";
  gravar(tokens);
  return "ok";
}

async function tokenValido(): Promise<string | null> {
  const atual = ler();
  if (!atual) return null;
  if (Date.now() < atual.expira - 60_000) return atual.access;
  const novo = await pedirTokens({ grant_type: "refresh_token", refresh_token: atual.refresh });
  if (!novo) {
    gravar(null); // refresh token expirado (6 meses) ou revogado: logar de novo
    return null;
  }
  gravar(novo);
  return novo.access;
}

async function chamar(metodo: "GET" | "PUT" | "POST", caminho: string, corpo?: unknown): Promise<Response> {
  const token = await tokenValido();
  if (!token) throw new ErroSpotify("Conecte o Spotify antes de entrar", "sem_login");
  let res: Response;
  try {
    res = await fetch(`${API}${caminho}`, {
      method: metodo,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(corpo !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: corpo !== undefined ? JSON.stringify(corpo) : undefined,
    });
  } catch {
    throw new ErroSpotify("Sem conexão com o Spotify", "rede");
  }
  if (res.ok) return res;

  let motivo = "";
  let mensagem = "";
  try {
    const j = (await res.json()) as { error?: { reason?: string; message?: string } };
    motivo = j.error?.reason ?? "";
    mensagem = j.error?.message ?? "";
  } catch {
    /* corpo vazio */
  }
  if (res.status === 401) {
    gravar(null);
    throw new ErroSpotify("Sessão do Spotify expirou — conecte de novo", "sem_login");
  }
  if (res.status === 403 && motivo === "PREMIUM_REQUIRED") {
    throw new ErroSpotify("Controlar a reprodução exige Spotify Premium", "premium");
  }
  if (res.status === 403 && /not registered/i.test(mensagem)) {
    throw new ErroSpotify("Seu e-mail não está na lista de testadores do app", "nao_testador");
  }
  if (res.status === 404 || motivo === "NO_ACTIVE_DEVICE") {
    throw new ErroSpotify("Abra o Spotify no celular ou no Quest e dê play", "sem_dispositivo");
  }
  if (res.status === 429) {
    throw new ErroSpotify("Spotify pediu uma pausa (limite de chamadas)", "limite");
  }
  throw new ErroSpotify(mensagem || `Spotify respondeu ${res.status}`, "rede");
}

/** O que está tocando agora (null = nada tocando ou anúncio/podcast). */
export async function estadoReproducao(): Promise<Reproducao | null> {
  const res = await chamar("GET", "/me/player");
  if (res.status === 204) return null;
  const j = (await res.json()) as {
    is_playing?: boolean;
    progress_ms?: number;
    device?: { name?: string };
    item?: { name?: string; duration_ms?: number; artists?: { name: string }[] } | null;
  };
  if (!j.item?.name) return null;
  return {
    tocando: Boolean(j.is_playing),
    faixa: j.item.name,
    artista: (j.item.artists ?? []).map((a) => a.name).join(", "),
    dispositivo: j.device?.name ?? "",
    progressoMs: j.progress_ms ?? 0,
    duracaoMs: j.item.duration_ms ?? 0,
  };
}

export async function alternar(tocandoAgora: boolean): Promise<void> {
  await chamar("PUT", tocandoAgora ? "/me/player/pause" : "/me/player/play");
}

export async function proximaFaixa(): Promise<void> {
  await chamar("POST", "/me/player/next");
}

export async function faixaAnterior(): Promise<void> {
  await chamar("POST", "/me/player/previous");
}

export interface Playlist {
  nome: string;
  uri: string;
}

/** Playlists do próprio usuário (as únicas que o modo dev ainda expõe). */
export async function playlists(): Promise<Playlist[]> {
  const res = await chamar("GET", "/me/playlists?limit=20");
  const j = (await res.json()) as { items?: ({ name: string; uri: string } | null)[] };
  return (j.items ?? []).flatMap((p) => (p ? [{ nome: p.name, uri: p.uri }] : []));
}

export async function tocarPlaylist(uri: string): Promise<void> {
  await chamar("PUT", "/me/player/play", { context_uri: uri });
}
