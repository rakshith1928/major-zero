/**
 * Turns raw API failure bodies into human sentences. FastAPI errors arrive
 * as JSON (`{"detail": ...}`); rendering that verbatim leaks `{...}` noise
 * into the UI. This is pure (no DOM, no imports) so unit tests can cover it.
 */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function friendlyError(status: number, bodyText: string): string {
  const text = (bodyText || "").trim();
  if (!text) {
    return status === 0 ? "Couldn't reach the server. Check your connection and retry." : `Request failed (${status}). Please retry.`;
  }
  let detail: unknown = null;
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    detail = parsed?.detail ?? null;
  } catch {
    detail = null;
  }
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { loc?: unknown[]; msg?: unknown };
    const field = Array.isArray(first?.loc)
      ? String(first.loc.filter((p) => p !== "body").pop() ?? "request")
      : "request";
    const msg = typeof first?.msg === "string" ? first.msg : "invalid value";
    return `Invalid ${field}: ${msg.toLowerCase()}`;
  }
  if (detail && typeof detail === "object") {
    const obj = detail as { message?: unknown; stops?: unknown };
    const message = typeof obj.message === "string" ? obj.message : "";
    const stops = Array.isArray(obj.stops) ? obj.stops.filter((s) => typeof s === "string") : [];
    if (message && stops.length > 0) return `${message}. Try: ${stops.join(", ")}.`;
    if (message) return message;
  }
  // Not JSON (proxy / gateway HTML): never paste markup into the UI.
  if (/^\s*</.test(text)) return `Request failed (${status}). Please retry.`;
  return text.slice(0, 200);
}
