import type { Metadata, Viewport } from "next";
import { Inter, Fraunces } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { ConsentBanner } from "@/components/analytics/ConsentBanner";
import { AnalyticsScript } from "@/components/analytics/AnalyticsScript";
import { SITE_URL } from "@/lib/site-url";

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

const SITE_DESCRIPTION =
  "Plataforma de estudo de anatomia com visualização 3D interativa, cortes anatômicos, comparação saudável × patológico, realidade virtual e um tutor de IA fundamentado em fontes médicas confiáveis.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "VRmed — Estudo de anatomia em 3D e realidade virtual",
    template: "%s · VRmed",
  },
  description: SITE_DESCRIPTION,
  applicationName: "VRmed",
  keywords: [
    "anatomia",
    "educação médica",
    "visualização 3D",
    "realidade virtual",
    "WebXR",
    "estudo de medicina",
    "tutor de IA",
    "anatomia 3D",
  ],
  authors: [{ name: "Projeto de Iniciação Científica VRmed" }],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    locale: "pt_BR",
    siteName: "VRmed",
    title: "VRmed — Estudo de anatomia em 3D e realidade virtual",
    description: SITE_DESCRIPTION,
    url: SITE_URL,
  },
  twitter: {
    card: "summary_large_image",
    title: "VRmed — Estudo de anatomia em 3D e realidade virtual",
    description: SITE_DESCRIPTION,
  },
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
