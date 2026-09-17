"use client";

import { useEffect, useRef } from "react";
import { useThree } from "@react-three/fiber";
import { useXR, useXRStore } from "@react-three/xr";
import { Button3D } from "@/components/arena/ui3d";
// Instala o registro de diagnóstico (só age com `?debug=xrlog`). Fica aqui
// porque este botão é carregado nas cinco cenas com XR antes de qualquer store.
import { XR_LOG_LIGADO, xrLog } from "@/lib/xr-log";
import { sairENavegar } from "@/lib/xr-sessao";

/**
 * Para onde a pessoa volta ao sair de um modo imersivo.
 *
 * Antes isto era `history.back()`, e o resultado era quase sempre a landing
 * page: quem entra na sala, no duelo ou na clínica costuma chegar pela home,
 * então "a página anterior" é a página de marketing. Sair do VR e cair num
 * hero com botão "Começar agora" não é voltar para o app — é sair dele.
 *
 * O `/viewer` é a tela inicial do app: traz a barra lateral com todas as
 * seções e o seletor de modelos. É de lá que se escolhe o que fazer em
 * seguida, e é para lá que sair leva.
 */
const DESTINO_AO_SAIR = "/viewer";

/** Registra o que o renderer do three.js achou do início e do fim da sessão. */
function RegistroDoRenderer() {
  const gl = useThree((s) => s.gl);
  useEffect(() => {
    const inicio = () =>
      xrLog(`renderer sessionstart: isPresenting=${gl.xr.isPresenting}`);
    // Um tique depois: o WebXRManager zera a sessão e para o loop XR dentro
    // do próprio onSessionEnd, antes de avisar.
    const fim = () =>
      setTimeout(
        () =>
          xrLog(
            `renderer sessionend: isPresenting=${gl.xr.isPresenting} getSession()=${
              gl.xr.getSession() ? "AINDA EXISTE" : "null"
            }`,
          ),
        0,
      );
    gl.xr.addEventListener("sessionstart", inicio);
    gl.xr.addEventListener("sessionend", fim);
    return () => {
      gl.xr.removeEventListener("sessionstart", inicio);
      gl.xr.removeEventListener("sessionend", fim);
    };
  }, [gl]);
  return null;
}

/**
 * Botão 3D "Sair do VR" / "Sair do AR". Dentro da sessão imersiva o DOM não
 * existe, então o link "← VRmed" da página some e a pessoa ficava presa no
 * modo. Este botão encerra a sessão e leva para a tela inicial do app.
 *
 * Colocar como FILHO do <XROrigin>: a posição fica relativa aos pés do
 * usuário e vale para qualquer cenário (sentado ou de pé, basta a altura).
 * Fora da sessão não desenha nada — o DOM já tem o botão de voltar.
 */
export function SairDoVR({
  position = [-0.45, 1.0, -0.5],
  rotationY = 0.35,
}: {
  /** À esquerda e à frente do usuário; y ≈ 0,95 sentado, 1,25 de pé. */
  position?: [number, number, number];
  /** Vira o botão para o usuário (ele fica à esquerda). */
  rotationY?: number;
}) {
  const store = useXRStore();
  const session = useXR((state) => state.session);
  // O rótulo segue o modo da sessão: quem entrou em AR procura "Sair do AR".
  // Nas cenas que só existem em VR (sala, arena, duelo, clínica) o modo é
  // sempre `immersive-vr`, então o texto não muda.
  const emAR = useXR((state) => state.mode === "immersive-ar");

  // Cena desmontando com a sessão viva: encerrar. Nem o <XR> nem o R3F fazem
  // isso — o WebXRManager.dispose é vazio e o R3F só perde o contexto WebGL
  // depois. Acontecia ao apertar o botão Meta (a sessão fica pausada e a
  // página 2D, clicável) e então navegar pelo menu: sobrava uma sessão sem
  // ninguém para desenhá-la, e o Retomar/Sair da tarja do navegador não tinha
  // o que retomar. Este botão é montado junto com o <XR> nas cinco cenas.
  //
  // A decisão fica para depois do commit: em `next dev`, o StrictMode (ao
  // reexibir um Suspense — a fonte do botão 3D suspende na 1ª entrada) e o
  // Fast Refresh rodam cleanup + efeito de novo no mesmo flush, sem
  // desmontar. Encerrar ali derrubava a sessão logo depois de entrar.
  const montado = useRef(false);
  useEffect(() => {
    montado.current = true;
    return () => {
      montado.current = false;
      setTimeout(() => {
        if (montado.current) return; // reconectou: não era desmontagem
        const viva = store.getState().session;
        if (!viva) return;
        xrLog("cena desmontou com a sessão viva → end()");
        viva.end().catch(() => {});
      }, 0);
    };
  }, [store]);

  return (
    <>
      {XR_LOG_LIGADO && <RegistroDoRenderer />}
      {session && (
        <group position={position} rotation={[0, rotationY, 0]}>
          <Button3D
            label={emAR ? "Sair do AR" : "Sair do VR"}
            width={0.42}
            height={0.1}
            color="#5c6b7a"
            onClick={() => sairENavegar(session, DESTINO_AO_SAIR)}
          />
        </group>
      )}
    </>
  );
}
