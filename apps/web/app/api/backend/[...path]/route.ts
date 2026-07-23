/**
 * Proxy BFF (Backend For Frontend) — la ÚNICA ruta por la que el navegador
 * llega al backend de `apps/api`. `BACKEND_API_URL` es server-only (nunca
 * `NEXT_PUBLIC_*`) y por eso nunca puede importarse desde un componente
 * cliente; este Route Handler corre siempre en el servidor de Next.js.
 *
 * Flujo: lee la sesión de NextAuth server-side (`auth()`); si no hay sesión
 * o no tiene `backendToken` (el JWT propio de FastAPI, opaco acá — nunca se
 * decodifica en Node), responde 401 sin llamar al backend. Si hay sesión,
 * reenvía el request tal cual (método, path, query string, body — incluido
 * multipart, que se usa recién en el slice 2 de ingesta de Excel) agregando
 * `Authorization: Bearer <backendToken>`, y devuelve la respuesta del
 * backend (status + body) sin transformarla.
 *
 * `operator_id` nunca se agrega acá ni en ningún query/body — el backend lo
 * saca exclusivamente del JWT (`Depends(get_current_operator)`), como exige
 * el contrato entregado por backend-especialista.
 */
import { NextRequest, NextResponse } from "next/server";

import { auth } from "@/auth";

const HOP_BY_HOP_REQUEST_HEADERS = new Set([
  "host",
  "connection",
  "content-length",
  "cookie",
]);

const HOP_BY_HOP_RESPONSE_HEADERS = new Set([
  "connection",
  "content-encoding",
  "transfer-encoding",
]);

async function proxy(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const session = await auth();

  if (!session?.backendToken) {
    return NextResponse.json({ detail: "No autenticado" }, { status: 401 });
  }

  const backendUrl = process.env.BACKEND_API_URL;
  if (!backendUrl) {
    return NextResponse.json(
      { detail: "BACKEND_API_URL no está configurada en el servidor." },
      { status: 500 }
    );
  }

  const { path } = await params;
  const targetPath = path.join("/");
  const targetUrl = new URL(`/api/${targetPath}`, backendUrl);
  targetUrl.search = request.nextUrl.search;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_REQUEST_HEADERS.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });
  headers.set("Authorization", `Bearer ${session.backendToken}`);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";

  const backendResponse = await fetch(targetUrl, {
    method: request.method,
    headers,
    body: hasBody ? request.body : undefined,
    // Requerido por Node/undici cuando el body es un ReadableStream.
    duplex: hasBody ? "half" : undefined,
    redirect: "manual",
    cache: "no-store",
  } as RequestInit);

  const responseHeaders = new Headers();
  backendResponse.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_RESPONSE_HEADERS.has(key.toLowerCase())) {
      responseHeaders.set(key, value);
    }
  });

  return new NextResponse(backendResponse.body, {
    status: backendResponse.status,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
