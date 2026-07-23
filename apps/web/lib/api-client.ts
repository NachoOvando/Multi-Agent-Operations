/**
 * Helpers de fetch tipados y puros (sin imports de `next`/`react`) contra el
 * proxy BFF propio (`app/api/backend/[...path]/route.ts`) — nunca contra la
 * URL de Railway directamente. El proxy es quien adjunta
 * `Authorization: Bearer <backendToken>` a partir de la sesión de NextAuth;
 * estos helpers no manejan tokens ni sesión, solo arman/parsean requests.
 *
 * Contrato consumido, definido por backend-especialista
 * (`apps/api/src/schemas/agents.py`, `routers/agents.py`):
 *
 *   POST /api/agents/messages
 *   body: { query: string }
 *   200 -> { reply: string }
 *   401 -> no autenticado (sesión ausente o backend rechazó el token)
 *   403 -> el operador autenticado no corresponde al dominio de la acción
 */

const BFF_BASE_PATH = "/api/backend";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (
      body &&
      typeof body === "object" &&
      "detail" in body &&
      typeof (body as { detail: unknown }).detail === "string"
    ) {
      return (body as { detail: string }).detail;
    }
  } catch {
    // Respuesta sin body JSON parseable — se usa el mensaje genérico abajo.
  }
  return `Error inesperado del servidor (status ${response.status}).`;
}

async function bffFetch(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(`${BFF_BASE_PATH}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const detail = await parseErrorDetail(response);
    throw new ApiError(response.status, detail);
  }

  return response;
}

export interface AgentMessageResponse {
  reply: string;
}

/**
 * Envía una consulta al agente del dominio del operador autenticado
 * (`POST /api/agents/messages`, vía el proxy BFF). El backend resuelve el
 * dominio a partir del JWT — este helper nunca envía `operator_id` ni
 * `domain` en el body.
 */
export async function sendAgentMessage(
  query: string
): Promise<AgentMessageResponse> {
  const response = await bffFetch("/agents/messages", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
  return (await response.json()) as AgentMessageResponse;
}
