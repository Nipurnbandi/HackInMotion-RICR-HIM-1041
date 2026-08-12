const API_BASE = "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  const data =
    response.status !== 204 && response.headers.get("content-type")?.includes("json")
      ? await response.json()
      : null;

  if (!response.ok) {
    const error = new Error(data?.detail || "Request failed");
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

export const api = {
  signup: (email, password) =>
    request("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email, password) =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  logout: () => request("/auth/logout", { method: "POST" }),

  getMe: () => request("/users/me"),
};

export function getDashboardPath(role) {
  return role === "ADMIN" ? "/admin" : "/citizen";
}
