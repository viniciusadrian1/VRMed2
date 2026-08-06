import { ImageResponse } from "next/og";

// Ícone para a tela inicial do iOS (180×180), gerado a partir da marca.
export const size = { width: 180, height: 180 };
export const contentType = "image/png";

const MARK = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>
  <path d='M7.5 16 A8.5 8.5 0 0 0 24.5 16 Z' fill='%23ffffff' opacity='0.35'/>
  <circle cx='16' cy='16' r='8.5' fill='none' stroke='%23ffffff' stroke-width='2'/>
  <line x1='6' y1='16' x2='26' y2='16' stroke='%23ffffff' stroke-width='2' stroke-linecap='round'/>
  <circle cx='16' cy='16' r='2' fill='%23ffffff'/>
</svg>`;

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0f4c81",
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          width={120}
          height={120}
          src={`data:image/svg+xml,${MARK.replace(/\n\s*/g, "")}`}
          alt=""
        />
      </div>
    ),
    { ...size },
  );
}
