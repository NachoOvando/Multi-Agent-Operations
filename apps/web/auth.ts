/**
 * Configuración de Auth.js (NextAuth v5).
 *
 * `CredentialsProvider.authorize()` es el único lugar del frontend que le
 * habla directo a `BACKEND_API_URL` (server-only, nunca `NEXT_PUBLIC_*`) —
 * hace `POST /api/auth/login` contra `apps/api` y, si el backend responde
 * 200, envuelve el JWT que emite FastAPI (`access_token`) dentro de la
 * sesión cifrada de NextAuth. Next.js nunca decodifica ese JWT — solo lo
 * transporta (ver `app/api/backend/[...path]/route.ts`, que es quien lo
 * reenvía al backend en cada llamada posterior).
 *
 * Contrato consumido (definido por backend-especialista, ya en producción
 * en `apps/api/src/routers/auth.py` + `schemas/auth.py`):
 *
 *   POST /api/auth/login
 *   body: { username: string, password: string }
 *   200 -> { access_token, token_type, expires_at, operator: { operator_id, role, domain } }
 *   401 -> { detail: "Usuario o contraseña incorrectos" } (mensaje genérico,
 *           nunca revela si falló el usuario o el password)
 */
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

interface BackendOperator {
  operator_id: string;
  role: string;
  domain: string;
}

interface BackendLoginResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  operator: BackendOperator;
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  session: {
    strategy: "jwt",
  },
  pages: {
    signIn: "/login",
  },
  providers: [
    Credentials({
      credentials: {
        username: { label: "Usuario", type: "text" },
        password: { label: "Contraseña", type: "password" },
      },
      async authorize(credentials) {
        const username =
          typeof credentials?.username === "string" ? credentials.username : "";
        const password =
          typeof credentials?.password === "string" ? credentials.password : "";

        if (!username || !password) {
          return null;
        }

        const backendUrl = process.env.BACKEND_API_URL;
        if (!backendUrl) {
          throw new Error("BACKEND_API_URL no está configurada en el servidor.");
        }

        let response: Response;
        try {
          response = await fetch(`${backendUrl}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
          });
        } catch {
          // Backend inalcanzable (red, DNS, etc.) — no distinguimos del caso
          // de credenciales inválidas para no filtrar información de estado
          // interno; NextAuth lo traduce igual a un error genérico en el UI.
          return null;
        }

        if (!response.ok) {
          // 401 (credenciales inválidas) u otro error del backend: siempre
          // `null`, nunca reenviamos el `detail` del backend al cliente acá
          // — el mensaje genérico se muestra en app/login/page.tsx.
          return null;
        }

        const data = (await response.json()) as BackendLoginResponse;

        return {
          id: data.operator.operator_id,
          operatorId: data.operator.operator_id,
          role: data.operator.role,
          domain: data.operator.domain,
          backendToken: data.access_token,
          backendTokenExpiresAt: data.expires_at,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.operatorId = user.operatorId;
        token.role = user.role;
        token.domain = user.domain;
        token.backendToken = user.backendToken;
        token.backendTokenExpiresAt = user.backendTokenExpiresAt;
      }
      return token;
    },
    async session({ session, token }) {
      session.operatorId = token.operatorId;
      session.role = token.role;
      session.domain = token.domain;
      session.backendToken = token.backendToken;
      session.backendTokenExpiresAt = token.backendTokenExpiresAt;
      return session;
    },
  },
});
