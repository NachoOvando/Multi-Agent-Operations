import type { NextConfig } from "next";

// El proxy hacia el backend FastAPI (apps/api) NO se resuelve acá con
// `rewrites()`: un rewrite estático no puede inyectar un header
// `Authorization` dinámico por sesión. La solución real es un Route Handler
// server-side, ya implementado en `app/api/backend/[...path]/route.ts`
// (lee la sesión de NextAuth vía `auth()`, adjunta el JWT del backend y
// reenvía la request a `BACKEND_API_URL`). Ese Route Handler es la única
// puerta del navegador hacia `apps/api` — ver también `lib/api-client.ts`.
const nextConfig: NextConfig = {};

export default nextConfig;
