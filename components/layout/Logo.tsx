import Link from "next/link";
import { cn } from "@/lib/utils";

/** Marca gráfica do VRmed: uma esfera anatômica seccionada (referência ao corte). */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      className={cn("size-8", className)}
      aria-hidden="true"
    >
      <rect width="32" height="32" rx="8" className="fill-primary" />
      <path
        d="M7.5 16 A8.5 8.5 0 0 0 24.5 16 Z"
        className="fill-primary-foreground"
        opacity="0.35"
      />
      <circle
        cx="16"
        cy="16"
        r="8.5"
        className="fill-none stroke-primary-foreground"
        strokeWidth="2"
      />
      <line
        x1="6"
        y1="16"
        x2="26"
        y2="16"
        className="stroke-primary-foreground"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="16" cy="16" r="2" className="fill-primary-foreground" />
    </svg>
  );
}

interface LogoProps {
  withText?: boolean;
  href?: string;
  className?: string;
}

/** Logotipo completo, opcionalmente com o nome do produto. */
export function Logo({ withText = true, href = "/", className }: LogoProps) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      aria-label="VRmed — página inicial"
    >
      <BrandMark />
      {withText && (
        <span className="font-serif text-xl font-medium tracking-tight">
          VRmed
        </span>
      )}
    </Link>
  );
}
