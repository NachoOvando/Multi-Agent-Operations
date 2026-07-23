/**
 * Protege todas las rutas de la app salvo `/login` y `/api/auth/*` (las
 * rutas propias de Auth.js: login, callback, signout, etc.). Sin sesión de
 * NextAuth, redirige a `/login`. No reimplementa ninguna regla de permisos
 * de dominio/rol acá — eso sigue siendo responsabilidad exclusiva del
 * backend (`assert_can_perform`/`assert_can_read` en `permissions_service.py`
 * vía `Depends(get_current_operator)`); este middleware solo es el gate de
 * "¿hay una sesión de NextAuth?" antes de renderizar cualquier pantalla.
 */
import { NextResponse } from "next/server";

import { auth } from "@/auth";

const PUBLIC_PATHS = ["/login"];

export default auth((request) => {
  const { pathname } = request.nextUrl;

  const isPublicPath = PUBLIC_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`)
  );
  const isNextAuthApi = pathname.startsWith("/api/auth/");

  if (isPublicPath || isNextAuthApi) {
    return NextResponse.next();
  }

  if (!request.auth) {
    const loginUrl = new URL("/login", request.nextUrl.origin);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
});

export const config = {
  // Excluye assets estáticos de Next; el resto pasa por el gate de arriba.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
