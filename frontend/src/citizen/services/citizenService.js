const API_BASE = "/api";

function normaliseError(status, payload, fallback) {
  const detail = payload?.detail;

  if (Array.isArray(detail)) {
    const fieldErrors = {};
    for (const item of detail) {
      const field = item.loc?.[item.loc.length - 1];
      if (field && !fieldErrors[field]) fieldErrors[field] = item.msg;
    }
    const error = new Error("Please correct the highlighted fields.");
    error.status = status;
    error.fieldErrors = fieldErrors;
    return error;
  }

  const error = new Error(typeof detail === "string" ? detail : fallback);
  error.status = status;
  return error;
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      credentials: "include",
      ...options,
    });
  } catch {
    const error = new Error(
      "We couldn't reach the server. Please check your connection and try again."
    );
    error.isNetworkError = true;
    throw error;
  }

  const isJson = response.headers.get("content-type")?.includes("json");
  const payload = response.status !== 204 && isJson ? await response.json() : null;

  if (!response.ok) {
    throw normaliseError(response.status, payload, "Request failed");
  }
  return payload;
}

function buildQuery(params) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, value);
    }
  }
  const string = query.toString();
  return string ? `?${string}` : "";
}

export const citizenService = {
  getDashboard: () => request("/citizen/dashboard"),

  getCityMap: () => request("/citizen/map"),

  getStats: () => request("/citizen/issues/stats"),

  listIssues: ({ status, search, page = 1, pageSize = 20 } = {}) =>
    request(`/citizen/issues${buildQuery({ status, search, page, page_size: pageSize })}`),

  getIssue: (id) => request(`/citizen/issues/${id}`),

  confirmIssue: (id) => request(`/citizen/issues/${id}/confirm`, { method: "POST" }),

  reopenIssue: (id) => request(`/citizen/issues/${id}/reopen`, { method: "POST" }),

  createIssue(values, { onProgress } = {}) {
    const form = new FormData();
    form.append("category", values.category);
    form.append("description", values.description);
    form.append("latitude", String(values.latitude));
    form.append("longitude", String(values.longitude));
    if (values.address) form.append("address", values.address);
    if (values.photo) form.append("photo", values.photo, values.photo.name);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE}/citizen/issues`);
      xhr.withCredentials = true;

      if (xhr.upload && onProgress) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            onProgress(Math.round((event.loaded / event.total) * 100));
          }
        };
      }

      xhr.onload = () => {
        let payload = null;
        try {
          payload = JSON.parse(xhr.responseText);
        } catch {
          payload = null;
        }

        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(payload);
        } else {
          reject(
            normaliseError(xhr.status, payload, "We couldn't submit your report.")
          );
        }
      };

      xhr.onerror = () => {
        const error = new Error(
          "We couldn't submit your report. Please check your connection and try again."
        );
        error.isNetworkError = true;
        reject(error);
      };

      xhr.send(form);
    });
  },
};
