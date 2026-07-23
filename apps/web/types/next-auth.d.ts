/**
 * Module augmentation de Auth.js (NextAuth v5) para los campos custom que
 * `auth.ts` propaga desde el contrato de `POST /api/auth/login` del backend
 * (`apps/api/src/schemas/auth.py::LoginResponse`) hacia la sesión del
 * cliente: `operatorId`, `role`, `domain` (siempre reflejan lo que decidió
 * el backend, nunca se recalculan acá) y `backendToken` (el JWT propio de
 * FastAPI, opaco para Next.js — solo se transporta, nunca se decodifica en
 * el cliente).
 */
import type { DefaultSession, DefaultUser } from "next-auth";
import type { DefaultJWT } from "next-auth/jwt";

declare module "next-auth" {
  interface Session extends DefaultSession {
    operatorId: string;
    role: string;
    domain: string;
    backendToken: string;
    backendTokenExpiresAt: string;
  }

  interface User extends DefaultUser {
    operatorId: string;
    role: string;
    domain: string;
    backendToken: string;
    backendTokenExpiresAt: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT extends DefaultJWT {
    operatorId: string;
    role: string;
    domain: string;
    backendToken: string;
    backendTokenExpiresAt: string;
  }
}
