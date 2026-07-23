"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, sendAgentMessage } from "@/lib/api-client";

const SMOKE_TEST_QUERY = "¿Qué puedo hacer con este agente?";

type RequestState =
  | { status: "loading" }
  | { status: "success"; reply: string }
  | { status: "error"; message: string };

/**
 * Smoke-test mínimo de la cadena de auth end-to-end: sesión de NextAuth ->
 * proxy BFF (`app/api/backend/[...path]/route.ts`) -> `POST
 * /api/agents/messages` en `apps/api`. No es la UI de chat final (fuera de
 * este pedido) — solo valida que un operador logueado recibe respuesta real
 * de su agente de dominio, o un error controlado (por ejemplo si falta
 * `ANTHROPIC_API_KEY` en el backend).
 */
export default function AgentSmokeTest() {
  const [state, setState] = useState<RequestState>({ status: "loading" });

  const runSmokeTest = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const result = await sendAgentMessage(SMOKE_TEST_QUERY);
      setState({ status: "success", reply: result.reply });
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.detail
          : "No se pudo contactar al agente. Intentá de nuevo.";
      setState({ status: "error", message });
    }
  }, []);

  useEffect(() => {
    void runSmokeTest();
  }, [runSmokeTest]);

  return (
    <section
      aria-labelledby="smoke-test-heading"
      className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
    >
      <h2 id="smoke-test-heading" className="text-sm font-semibold text-slate-900">
        Prueba de conexión con el agente
      </h2>
      <p className="mt-1 text-sm text-slate-500">
        Consulta fija: <span className="italic">&quot;{SMOKE_TEST_QUERY}&quot;</span>
      </p>

      <div className="mt-4">
        {state.status === "loading" && (
          <p role="status" aria-live="polite" className="text-sm text-slate-500">
            Consultando al agente…
          </p>
        )}

        {state.status === "success" && (
          <p
            role="status"
            aria-live="polite"
            className="whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-sm text-slate-800"
          >
            {state.reply}
          </p>
        )}

        {state.status === "error" && (
          <div role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">
            <p>{state.message}</p>
            <button
              type="button"
              onClick={() => void runSmokeTest()}
              className="mt-2 rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1"
            >
              Reintentar
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
