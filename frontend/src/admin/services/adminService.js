const API_BASE = "/api";

async function request(path) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { credentials: "include" });
  } catch {
    const error = new Error(
      "We couldn't reach the server. Please check your connection and try again."
    );
    error.isNetworkError = true;
    throw error;
  }

  const payload = response.headers.get("content-type")?.includes("json")
    ? await response.json()
    : null;

  if (!response.ok) {
    const error = new Error(
      typeof payload?.detail === "string" ? payload.detail : "Request failed"
    );
    error.status = response.status;
    throw error;
  }
  return payload;
}

export const adminService = {
  getDashboard: () => request("/admin/dashboard"),

  listCases: () => request("/admin/issues"),
};
