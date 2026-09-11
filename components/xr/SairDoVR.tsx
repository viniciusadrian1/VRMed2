"use client";

import { useXR } from "@react-three/xr";
import { Button3D } from "@/components/arena/ui3d";

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

/**
 * Botão 3D "Sair do VR" / "Sair do AR". Dentro da sessão imersiva o DOM não
 * existe, então o link "← VRmed" da página some e a pessoa ficava presa no
 * modo. Este botão encerra a sessão e leva para a tela inicial do app.
 *
 * Colocar como FILHO do <XROrigin>: a posição fica relativa aos pés do
 * usuário e vale para qualquer cenário (sentado ou de pé, basta a altura).
 * Fora da sessão não renderiza nada — o DOM já tem o botão de voltar.
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
  const session = useXR((state) => state.session);
  // O rótulo segue o modo da sessão: quem entrou em AR procura "Sair do AR".
  // Nas cenas que só existem em VR (sala, arena, duelo, clínica) o modo é
  // sempre `immersive-vr`, então o texto não muda.
  const emAR = useXR((state) => state.mode === "immersive-ar");
  if (!session) return null;

  const sair = () => {
    const voltar = () => {
      // Já estando no destino (sair do AR/VR dentro do próprio visualizador),
      // navegar recarregaria a cena 3D inteira à toa.
      if (window.location.pathname !== DESTINO_AO_SAIR) {
        window.location.assign(DESTINO_AO_SAIR);
      }
    };
    session.end().then(voltar, voltar);
  };

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      <Button3D
        label={emAR ? "Sair do AR" : "Sair do VR"}
        width={0.42}
        height={0.1}
        color="#5c6b7a"
        onClick={sair}
      />
    </group>
  );
}
