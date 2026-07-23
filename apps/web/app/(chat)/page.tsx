import { auth, signOut } from "@/auth";
import AgentSmokeTest from "@/components/AgentSmokeTest";

const DOMAIN_LABELS: Record<string, string> = {
  compras: "Compras",
  almacen: "Almacén",
  planificacion: "Planificación",
};

/**
 * Página raíz protegida (smoke-test mínimo, no la UI de chat final — eso
 * queda fuera de este pedido). Confirma la cadena completa de auth:
 * middleware -> sesión de NextAuth -> `AgentSmokeTest` (proxy BFF ->
 * `POST /api/agents/messages` en `apps/api`). `session.role`/`domain` acá
 * solo se usan para mostrar contexto en pantalla — nunca para decidir qué
 * puede hacer el operador, esa decisión sigue siendo exclusiva del backend.
 */
export default async function ChatSmokeTestPage() {
  const session = await auth();
  const domainLabel = session?.domain
    ? DOMAIN_LABELS[session.domain] ?? session.domain
    : "—";

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-4 py-10">
      <header className="flex items-center justify-between border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">
            Agentes operativos
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {session ? (
              <>
                {session.operatorId} · {domainLabel} ({session.role})
              </>
            ) : (
              "Sin sesión"
            )}
          </p>
        </div>

        <form
          action={async () => {
            "use server";
            await signOut({ redirectTo: "/login" });
          }}
        >
          <button
            type="submit"
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-1"
          >
            Cerrar sesión
          </button>
        </form>
      </header>

      <AgentSmokeTest />
    </main>
  );
}
