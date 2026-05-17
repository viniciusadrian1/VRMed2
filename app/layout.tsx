import type { Metadata, Viewport } from "next";
import { Inter, Fraunces } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { ConsentBanner } from "@/components/analytics/ConsentBanner";
import { AnalyticsScript } from "@/components/analytics/AnalyticsScript";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://vrmed.local"),
  title: {
    default: "VRmed — Estudo de anatomia em 3D e realidade virtual",
    template: "%s · VRmed",
  },
  description:
    "Plataforma de estudo médico com visualização 3D interativa, cortes anatômicos, suporte a VR e um tutor de IA baseado em fontes médicas confiáveis.",
  applicationName: "VRmed",
  keywords: [
    "anatomia",
    "educação médica",
    "visualização 3D",
    "realidade virtual",
    "WebXR",
    "estudo de medicina",
  ],
  authors: [{ name: "Projeto de Iniciação Científica VRmed" }],
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8f7f4" },
    { media: "(prefers-color-scheme: dark)", color: "#121211" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="pt-BR"
      data-scroll-behavior="smooth"
      suppressHydrationWarning
      className={`${inter.variable} ${fraunces.variable} scroll-smooth`}
    >
      <body className="min-h-dvh">
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          {/* Atalho de acessibilidade para pular direto ao conteúdo */}
          <a
            href="#conteudo-principal"
            className="sr-only-focusable fixed left-4 top-4 z-[100] rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            Pular para o conteúdo
          </a>
          {children}
          <ConsentBanner />
          <AnalyticsScript />
        </ThemeProvider>
      </body>
    </html>
  );
}
