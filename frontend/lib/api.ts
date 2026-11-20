export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg =
      typeof data === "object" && data
        ? Object.values(data).flat().join(" ")
        : "Something went wrong.";
    throw new Error(msg || "Something went wrong.");
  }
  return data as T;
}

export function saveToken(token: string) {
  localStorage.setItem("token", token);
}
