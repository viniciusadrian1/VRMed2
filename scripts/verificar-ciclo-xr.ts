/**
 * Checagem do ciclo de vida WebXR sem headset (ver lib/xr-sessao.ts).
 *
 *  1. Toda store XR do app desliga a oferta automática e a entrada em sessão
 *     concedida — as chamadas de WebXR que o app fazia sem clique.
 *  2. Nenhuma cena navega direto com a sessão viva (só via sairENavegar).
 *  3. sairENavegar: encerra antes de navegar, uma vez só, e navega mesmo se o
 *     end() rejeitar.
 *  4. entrarNoXR: não sobrepõe pedidos e encerra a sessão viva antes.
 *  5. Registro de diagnóstico: distingue end pedido pela página do fim vindo
 *     do sistema.
 *
 * Rodar: npm run verify:xr (Node 22+)
 */
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { entrarNoXR, sairENavegar } from "../lib/xr-sessao.ts";

const falhas: string[] = [];
const conferir = (ok: boolean, msg: string) => {
  if (!ok) falhas.push(msg);
  console.log(ok ? "  ok:" : "  FALHA:", msg);
};

function arquivos(dir: string): string[] {
  return readdirSync(dir).flatMap((nome) => {
    const caminho = join(dir, nome);
    if (statSync(caminho).isDirectory()) return arquivos(caminho);
    return /\.(ts|tsx)$/.test(nome) ? [caminho] : [];
  });
}
const fontes = ["app", "components", "lib", "hooks"].flatMap(arquivos);

// ---------------------------------------------------------------- 1. stores
for (const arquivo of fontes) {
  const texto = readFileSync(arquivo, "utf8");
  let inicio = texto.indexOf("createXRStore(");
  while (inicio >= 0) {
    // Recorta os argumentos da chamada contando parênteses.
    let profundidade = 0;
    let fim = inicio + "createXRStore".length;
    for (; fim < texto.length; fim += 1) {
      if (texto[fim] === "(") profundidade += 1;
      if (texto[fim] === ")" && --profundidade === 0) break;
    }
    // Sem comentários: `// offerSession: false` não conta.
    const chamada = texto.slice(inicio, fim).replace(/\/\/.*$/gm, "");
    // Ignora o `import { createXRStore }` e menções em comentário.
    if (!/import|^\s*\/\//.test(texto.slice(texto.lastIndexOf("\n", inicio), inicio))) {
      conferir(
        /offerSession:\s*false/.test(chamada) && /enterGrantedSession:\s*false/.test(chamada),
        `${arquivo}: createXRStore com offerSession:false e enterGrantedSession:false`,
      );
    }
    inicio = texto.indexOf("createXRStore(", fim);
  }
}

// ------------------------------------------------ 2. navegação com sessão viva
for (const arquivo of fontes) {
  const texto = readFileSync(arquivo, "utf8");
  if (!texto.includes("@react-three/xr")) continue;
  conferir(
    !/\blocation\.(assign|replace)\(|\blocation\.href\s*=|router\.(push|replace)\(/.test(texto),
    `${arquivo}: cena XR não navega direto (usa sairENavegar)`,
  );
}

// ------------------------------------- 2b. entrada e desmontagem pelos helpers
for (const arquivo of fontes) {
  const texto = readFileSync(arquivo, "utf8");
  // Só a store direto; o XRButton chama o viewerBridge, que já passa por aqui.
  if (!/[sS]tore\.enter(VR|AR)\(\)/.test(texto)) continue;
  conferir(texto.includes("entrarNoXR("), `${arquivo}: enterVR/enterAR passam por entrarNoXR`);
}
{
  const sair = readFileSync(join("components", "xr", "SairDoVR.tsx"), "utf8");
  conferir(
    /getState\(\)\.session[\s\S]*\.end\(\)/.test(sair) && /montado\.current\) return/.test(sair),
    "SairDoVR encerra a sessão viva ao desmontar, e não no remonte do StrictMode/Fast Refresh",
  );
}

async function principal() {
  // ------------------------------------------------------------ 3. sairENavegar
  function sessaoFalsa(resultado: "resolve" | "rejeita") {
    let chamadasEnd = 0;
    let concluir!: () => void;
    const sessao = {
      end() {
        chamadasEnd += 1;
        return new Promise<void>((resolve, reject) => {
          concluir = resultado === "resolve" ? resolve : () => reject(new Error("InvalidStateError"));
        });
      },
    };
    return { sessao, chamadasEnd: () => chamadasEnd, concluir: () => concluir() };
  }
  const esperar = () => new Promise((r) => setTimeout(r, 0));

  {
    const idas: string[] = [];
    const s = sessaoFalsa("resolve");
    sairENavegar(s.sessao, "/viewer", (u) => idas.push(u), () => "/duelo");
    sairENavegar(s.sessao, "/viewer", (u) => idas.push(u), () => "/duelo");
    conferir(s.chamadasEnd() === 1, "clique duplo em Sair chama end() uma vez só");
    conferir(idas.length === 0, "não navega antes de o end() resolver");
    s.concluir();
    await esperar();
    conferir(idas.length === 1 && idas[0] === "/viewer", "navega uma vez depois do end()");
  }
  {
    const idas: string[] = [];
    const s = sessaoFalsa("rejeita");
    sairENavegar(s.sessao, "/viewer", (u) => idas.push(u), () => "/sala");
    s.concluir();
    await esperar();
    conferir(idas.length === 1, "navega mesmo se o end() rejeitar (sessão já encerrada)");
  }
  {
    const idas: string[] = [];
    const s = sessaoFalsa("resolve");
    sairENavegar(s.sessao, "/viewer", (u) => idas.push(u), () => "/viewer");
    s.concluir();
    await esperar();
    conferir(idas.length === 0 && s.chamadasEnd() === 1, "já no destino: encerra e não recarrega");
  }
  {
    const idas: string[] = [];
    sairENavegar(null, "/duelo", (u) => idas.push(u), () => "/sala");
    conferir(idas.length === 1, "sem sessão: navega direto");
  }

  // -------------------------------------------------------------- 4. entrarNoXR
  {
    let pedidos = 0;
    let liberar!: () => void;
    const store = { getState: () => ({ session: null }) };
    const entrar = () =>
      new Promise<string>((resolve) => {
        pedidos += 1;
        liberar = () => resolve("sessão");
      });
    const a = entrarNoXR(store, entrar);
    const b = entrarNoXR(store, entrar);
    await esperar();
    conferir(a === b && pedidos === 1, "clique duplo em Entrar faz um pedido só");
    liberar();
    assert.equal(await a, "sessão");
    entrarNoXR(store, entrar);
    await esperar();
    conferir(pedidos === 2, "terminado o pedido, um novo clique pede de novo");
    liberar();
    await esperar(); // a trava solta um microtask depois de o pedido terminar
  }
  {
    const ordem: string[] = [];
    const viva = {
      end: () => {
        ordem.push("end");
        return Promise.reject(new Error("já encerrada"));
      },
    };
    await entrarNoXR({ getState: () => ({ session: viva }) }, async () => {
      ordem.push("request");
    });
    conferir(ordem.join(",") === "end,request", "com sessão viva: encerra antes de pedir outra, mesmo se o end() falhar");
  }
  {
    let tentativas = 0;
    const store = { getState: () => ({ session: null }) };
    await entrarNoXR(store, () => {
      tentativas += 1;
      return Promise.reject(new Error("NotSupportedError"));
    }).catch(() => {});
    await entrarNoXR(store, async () => {
      tentativas += 1;
    });
    conferir(tentativas === 2, "pedido que falhou não trava os próximos");
  }

  // ----------------------------------------------------- 5. registro diagnóstico
  {
    const dados = new Map<string, string>();
    Object.assign(globalThis, {
      localStorage: {
        getItem: (k: string) => dados.get(k) ?? null,
        setItem: (k: string, v: string) => void dados.set(k, v),
        removeItem: (k: string) => void dados.delete(k),
      },
      location: { search: "?debug=xrlog", pathname: "/viewer" },
    });
    console.info = () => {}; // o registro também escreve no console
    const registro = await import("../lib/xr-log.ts");
    conferir(registro.XR_LOG_LIGADO, "?debug=xrlog liga o registro");

    class SessaoFalsa extends EventTarget {
      visibilityState = "visible";
      environmentBlendMode = "opaque";
      inputSources: unknown[] = [];
      end(): Promise<void> {
        this.dispatchEvent(new Event("end"));
        return Promise.resolve();
      }
      requestAnimationFrame(): number {
        return 0;
      }
    }
    class SistemaFalso extends EventTarget {
      requestSession() {
        return Promise.resolve(new SessaoFalsa());
      }
    }
    const sistema = new SistemaFalso();
    registro.instalarRegistroXR(
      sistema as unknown as XRSystem,
      SessaoFalsa.prototype as unknown as XRSession,
    );

    const pelaPagina = (await sistema.requestSession()) as SessaoFalsa;
    await pelaPagina.end();
    const peloSistema = (await sistema.requestSession()) as SessaoFalsa;
    peloSistema.dispatchEvent(new Event("end"));
    await esperar();

    const linhas = registro.lerRegistro().join("\n");
    conferir(linhas.includes("offerSession não existe"), "registra que o navegador não tem offerSession");
    conferir(/sessão #1 criada via requestSession/.test(linhas), "registra a sessão criada");
    conferir(/sessão #1 evento 'end' \(a página chamou end\)/.test(linhas), "fim pedido pela página identificado");
    conferir(/sessão #2 evento 'end' \(SEM end da página/.test(linhas), "fim vindo do sistema identificado");
  }

  console.log(falhas.length ? `\n${falhas.length} falha(s)` : "\nok: ciclo de vida WebXR");
  process.exit(falhas.length ? 1 : 0);
}

void principal();
