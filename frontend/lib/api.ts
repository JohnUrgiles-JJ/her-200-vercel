// Requests go to /api/* on this origin and are proxied to the Railway backend (see next.config.ts).
// Set NEXT_PUBLIC_API_URL to call a backend directly instead (it must allow CORS).
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export type Role = "mentor" | "mentee";
export type Status = "sent" | "answered";

export type User = { id: number; email: string; full_name: string; role: Role; has_mentor_profile: boolean };
export type AuthResponse = { token: string; user: User };
export type Answer = { id: number; text: string; created_at: string };
export type Match = {
  match_id: number; mentor_id: number; name: string; headline: string; company: string;
  reason: string; rank?: number; status?: Status; answers: Answer[];
  /** 0–100. Not sent by the backend yet; shown when present. */
  match_score?: number;
};
export type Question = { id: number; text: string; created_at: string; matches: Match[] };
export type InboxItem = {
  match_id: number; question_id: number; question_text: string; mentee_name: string;
  reason: string; status?: Status; created_at: string; answers: Answer[];
  /** 0–100. Not sent by the backend yet; shown when present. */
  match_score?: number;
};
export type FeedPost = { id: number; text: string; created_at: string; author_name: string; answer_count: number };
export type MentorProfile = {
  headline: string; company?: string; fields: string; open_to: string; bio?: string; experience_years?: number;
};
export type MentorListItem = MentorProfile & { mentor_id: number; name: string };

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

export function getToken() {
  return typeof window === "undefined" ? null : localStorage.getItem("token");
}

export function saveToken(token: string) {
  localStorage.setItem("token", token);
}

export function clearToken() {
  localStorage.removeItem("token");
}

function errorMessage(data: unknown): string {
  if (typeof data === "string") return data;
  if (Array.isArray(data)) return data.map(errorMessage).join(" ");
  if (data && typeof data === "object") return Object.values(data).map(errorMessage).join(" ");
  return "";
}

export async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers.Authorization = `Token ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(errorMessage(data) || "Something went wrong.", res.status);
  return data as T;
}

export const getJSON = <T>(path: string) => request<T>("GET", path);
export const postJSON = <T>(path: string, body: unknown) => request<T>("POST", path, body);
export const putJSON = <T>(path: string, body: unknown) => request<T>("PUT", path, body);

export const initials = (name: string) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]!.toUpperCase()).join("") || "?";

export function timeAgo(iso: string) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "now";
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  if (s < 604800) return `${Math.floor(s / 86400)}d`;
  return new Date(iso).toLocaleDateString();
}
