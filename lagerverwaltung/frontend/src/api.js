// Zentrale Stelle für alle Serveranfragen.
let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => (onUnauthorized = fn);

// Anfragen, die innerhalb von inBackground() starten, zählen nicht als
// Benutzeraktivität (Live-Aktualisierungen halten die Sitzung nicht am Leben).
let background = false;
export function inBackground(fn) {
  background = true;
  try { return fn(); } finally { background = false; }
}

function message(detail, status) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return "Bitte die Eingaben prüfen.";
  return `Fehler ${status}`;
}

async function request(method, path, body) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (background) headers["X-Background"] = "1";
  const res = await fetch("/api" + path, {
    method, headers, credentials: "same-origin",
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith("/auth/")) onUnauthorized();
    const error = new Error(message(data?.detail, res.status));
    error.status = res.status;
    throw error;
  }
  return data;
}

export const api = {
  get: (p) => request("GET", p),
  post: (p, b) => request("POST", p, b ?? {}),
  put: (p, b) => request("PUT", p, b),
  del: (p) => request("DELETE", p),
};
