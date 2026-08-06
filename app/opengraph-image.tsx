import { ImageResponse } from "next/og";

// Imagem de pré-visualização ao compartilhar o link (Open Graph / Twitter).
export const alt = "VRmed — Estudo de anatomia em 3D e realidade virtual";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const MARK = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>
  <rect width='32' height='32' rx='8' fill='%230f4c81'/>
  <path d='M7.5 16 A8.5 8.5 0 0 0 24.5 16 Z' fill='%23ffffff' opacity='0.35'/>
  <circle cx='16' cy='16' r='8.5' fill='none' stroke='%23ffffff' stroke-width='2'/>
  <line x1='6' y1='16' x2='26' y2='16' stroke='%23ffffff' stroke-width='2' stroke-linecap='round'/>
  <circle cx='16' cy='16' r='2' fill='%23ffffff'/>
</svg>`;

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "80px",
          background:
            "radial-gradient(60% 55% at 50% 30%, #e9eef3, #f8f7f4 70%)",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            width={84}
            height={84}
            src={`data:image/svg+xml,${MARK.replace(/\n\s*/g, "")}`}
            alt=""
          />
          <span style={{ fontSize: 52, fontWeight: 600, color: "#1a1a1a" }}>
            VRmed
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <span
            style={{
              fontSize: 68,
              fontWeight: 600,
              color: "#1a1a1a",
              lineHeight: 1.1,
              maxWidth: 900,
            }}
          >
            A anatomia humana, em 3D e ao seu alcance.
          </span>
          <span style={{ fontSize: 30, color: "#6f6e69", maxWidth: 820 }}>
            Modelos 3D interativos, cortes anatômicos, realidade virtual e um
            tutor de IA com fontes confiáveis.
          </span>
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          {["18 modelos 3D", "VR no navegador", "100% em português"].map(
            (chip) => (
              <span
                key={chip}
                style={{
                  fontSize: 24,
                  color: "#0f4c81",
                  background: "#ffffff",
                  border: "1px solid #e5e2db",
                  borderRadius: 9999,
                  padding: "10px 22px",
                }}
              >
                {chip}
              </span>
            ),
          )}
        </div>
      </div>
    ),
    { ...size },
  );
}
