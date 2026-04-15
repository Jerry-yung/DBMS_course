const API_BASE = "/api/v1";

function getToken() {
  return localStorage.getItem("token") || "";
}

function authHeaders() {
  const t = getToken();
  const h = { "Content-Type": "application/json" };
  if (t) h["Authorization"] = "Bearer " + t;
  return h;
}

async function apiJson(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  });
  let body = null;
  try {
    body = await res.json();
  } catch (e) {
    body = null;
  }
  if (!res.ok) {
    const d = body && body.detail;
    const msg =
      typeof d === "object" && d && d.message
        ? d.message
        : typeof d === "string"
          ? d
          : res.statusText;
    throw new Error(msg || "请求失败");
  }
  return body;
}

function requireLogin() {
  if (!getToken()) {
    window.location.href = "/login.html";
  }
}
