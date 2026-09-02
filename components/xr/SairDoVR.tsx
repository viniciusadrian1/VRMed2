"use client";

import { useXR } from "@react-three/xr";
import { Button3D } from "@/components/arena/ui3d";

/**
 * Botão 3D "Sair do VR". Dentro da sessão imersiva o DOM não existe, então o
 * link "← VRmed" da página some e a pessoa ficava presa no modo. Este botão
 * encerra a sessão e volta para a página anterior.
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
  if (!session) return null;

  const sair = () => {
    const voltar = () => {
      if (window.history.length > 1) window.history.back();
      else window.location.assign("/");
    };
    session.end().then(voltar, voltar);
  };

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      <Button3D label="Sair do VR" width={0.42} height={0.1} color="#5c6b7a" onClick={sair} />
    </group>
  );
}
