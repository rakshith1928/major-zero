const BASE: string = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("zb_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
}

async function request<T>(path: string, { method = "GET", body, auth = true }: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) Object.assign(headers, authHeaders());
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text.slice(0, 200)}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface TokenResponse { access_token: string; token_type: string }
export interface MeResponse { id: number; email: string; is_admin: boolean }
export interface BusCard {
  id: number; operator: string; bus_type: string; origin: string; destination: string;
  departure: string; arrival: string; arrival_day_offset: number; duration_minutes: number;
  fare: number; total_seats: number; seats_left: number; crowd_level: number; fare_indicator: string;
}
export interface ChatReply {
  state: string; slots: Record<string, string | number | null>; buses: BusCard[];
  assistant_text: string; messages: { role: string; content: string }[];
  fare_comparison?: FareComparison;
  negotiation?: { dropped: string[]; relaxed_slots: Record<string, string | number | null> };
}
export interface FareOption {
  date: string; min_fare: number | null; buses: number;
  cheapest_operator?: string; cheapest_departure?: string;
}
export interface FareComparison { options: FareOption[]; cheapest: FareOption | null }
export interface BookingCreated {
  booking_ref: string; status: string; bus: BusCard;
  passenger: { name: string; age: number; gender: string; phone: string };
  fare: number; boarding_point: string; warnings: Warning[];
}
export interface Warning { code: string; message: string; alternative_bus_id?: number }
export interface Ticket { code: string; qr_payload: string; booking_ref: string }
export interface HistoryEntry {
  booking_ref: string; status: string; travel_date: string; fare: number;
  bus_id: number; origin: string; destination: string; deadline_time: string | null;
}
export interface GuardianStatus {
  booking_ref: string; status: "OK" | "AT_RISK" | "NO_DEADLINE";
  predicted_arrival?: string; deadline?: string; eta_minutes?: number;
  alternative_bus_id?: number | null;
}
export interface VerifyResult { valid: boolean; reason?: string; booking_ref?: string; travel_date?: string; passenger_name?: string }
export interface SavedPassenger { id: number; label: string; name: string; age: number; gender: string; phone: string }

export const api = {
  register: (payload: Record<string, unknown>) =>
    request<TokenResponse>("/api/auth/register", { method: "POST", body: payload, auth: false }),
  login: (payload: Record<string, unknown>) =>
    request<TokenResponse>("/api/auth/login", { method: "POST", body: payload, auth: false }),
  me: () => request<MeResponse>("/api/auth/me"),
  chat: (session_id: string, message: string) =>
    request<ChatReply>("/api/booking/chat", { method: "POST", body: { session_id, message } }),
  search: (params: Record<string, unknown>) =>
    request<{ buses: BusCard[] }>("/api/booking/search", { method: "POST", body: params }),
  select: (payload: Record<string, unknown>) =>
    request<BookingCreated>("/api/booking/select", { method: "POST", body: payload }),
  capturePassenger: (payload: Record<string, unknown>) =>
    request<{ passenger: Record<string, unknown>; needs_consent: boolean }>("/api/booking/passenger/capture", { method: "POST", body: payload }),
  consentPassenger: (payload: Record<string, unknown>) =>
    request<{ remembered: boolean; profile_id?: number }>("/api/booking/passenger/consent", { method: "POST", body: payload }),
  passengers: () => request<{ passengers: SavedPassenger[] }>("/api/passengers"),
  deletePassenger: (id: number) => request<null>(`/api/passengers/${id}`, { method: "DELETE" }),
  warningOutcome: (payload: Record<string, unknown>) =>
    request<{ ok: boolean }>("/api/warnings/outcome", { method: "POST", body: payload }),
  createOrder: (booking_ref: string) =>
    request<
      | { order_id: string; amount: number; currency: string; booking_ref: string; checkout_mode: "demo"; key_id?: never }
      | { order_id: string; amount: number; currency: string; booking_ref: string; checkout_mode: "razorpay_test"; key_id: string }
    >("/api/payments/order", { method: "POST", body: { booking_ref } }),
  verifyPayment: (payload: Record<string, unknown>) =>
    request<{ status: string; booking_ref: string }>("/api/payments/verify", { method: "POST", body: payload }),
  ticket: (booking_ref: string) => request<Ticket>(`/api/tickets/${booking_ref}`),
  history: () => request<{ bookings: HistoryEntry[] }>(`/api/tickets/history/list`),
  lookupByPayload: (qr_payload: string) => request<{ code: string; booking_ref: string }>(`/api/tickets/lookup`, { method: "POST", body: { qr_payload } }),
  verifyTicket: (code: string) => request<VerifyResult>("/api/tickets/verify", { method: "POST", body: { code } }),
  notifications: () =>
    request<{ notifications: { id: number; type: string; title: string; body: string; read: boolean }[] }>("/api/notifications"),
  demand: (origin: string, destination: string, date: string) =>
    request<{ route: string[]; date: string; curve: { bus_id: number; departure: string; predicted_occupancy: number; is_peak: boolean }[] }>(
      `/api/analytics/demand?origin=${origin}&destination=${destination}&date=${date}`, { auth: false }),
  positions: () =>
    request<{ simulated: boolean; as_of: string; buses: { bus_id: number; lat: number; lon: number; progress: number; status: string; remaining_minutes: number }[] }>("/api/tracking/positions", { auth: false }),
  eta: (bus_id: number, travel_date: string, stop: string) =>
    request<{ bus_id: number; stop: string; eta_minutes: number; status: string; simulated: boolean }>(
      `/api/tracking/eta?bus_id=${bus_id}&travel_date=${travel_date}&stop=${stop}`, { auth: false }),
  adminOverview: () => request<Record<string, unknown>>("/api/admin/overview"),
  metricsStart: (session_id: string, task: string) =>
    request<{ ok: boolean }>("/api/metrics/start", { method: "POST", body: { session_id, task } }),
  metricsFinish: (session_id: string, booking_ref: string, success: boolean) =>
    request<{ task: string; booking_seconds: number; manual_fields: number; success: boolean; booking_ref: string }>(
      "/api/metrics/finish", { method: "POST", body: { session_id, booking_ref, success } }),
  passkeyRegisterOptions: () => request<{ publicKey: unknown; challenge_token: string }>("/api/auth/passkeys/register/options"),
  passkeyRegister: (payload: Record<string, unknown>) =>
    request<{ ok: boolean }>("/api/auth/passkeys/register", { method: "POST", body: payload }),
  passkeyLoginOptions: (email: string) =>
    request<{ publicKey: unknown; challenge_token: string }>("/api/auth/passkeys/login/options", { method: "POST", body: { email }, auth: false }),
  passkeyLogin: (payload: Record<string, unknown>) =>
    request<TokenResponse>("/api/auth/passkeys/login", { method: "POST", body: payload, auth: false }),
  guardianCheck: (booking_ref: string) =>
    request<GuardianStatus>("/api/guardian/check", { method: "POST", body: { booking_ref } }),
  guardianRebook: (booking_ref: string, bus_id: number) =>
    request<{ booking_ref: string; status: string; supersedes: string; fare: number }>("/api/guardian/rebook", { method: "POST", body: { booking_ref, bus_id } }),
  guardianSimulateDelay: (bus_id: number, minutes: number) =>
    request<{ bus_id: number; delay_minutes: number }>("/api/guardian/simulate-delay", { method: "POST", body: { bus_id, minutes } }),
};
