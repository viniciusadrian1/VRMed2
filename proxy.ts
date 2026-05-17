import { NextResponse, type NextRequest } from "next/server";

/**
 * Protege as rotas administrativas (/admin/*) com autenticação HTTP Basic.
 * A senha vem da variável de ambiente ADMIN_PASSWORD; sem ela, o acesso é
 * totalmente bloqueado. (No Next.js 16 o antigo `middleware` chama-se `proxy`.)
 */
export function proxy(request: NextRequest) {
  const password = process.env.ADMIN_PASSWORD;

  const challenge = (message: string) =>
    new NextResponse(message, {
      status: 401,
      headers: {
        "WWW-Authenticate": 'Basic realm="VRmed - Painel do pesquisador"',
      },
    });

  if (!password) {
    return challenge("ADMIN_PASSWORD não configurada no servidor.");
  }

  const header = request.headers.get("authorization");
  if (header?.startsWith("Basic ")) {
    try {
      const decoded = atob(header.slice(6));
      const provided = decoded.slice(decoded.indexOf(":") + 1);
      if (provided === password) {
        return NextResponse.next();
      }
    } catch {
      /* cabeçalho malformado — segue para o desafio 401 */
    }
  }

  return challenge("Autenticação necessária.");
}

export const config = {
  matcher: "/admin/:path*",
};
