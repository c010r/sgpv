export async function apiRequest({ baseUrl, path, method = "GET", token = "", body = null }) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });

  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }

  if (!response.ok) {
    const detail = data?.detail || JSON.stringify(data) || response.statusText;
    throw new Error(`${response.status} ${detail}`);
  }
  return data;
}

export function asList(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.results)) return payload.results;
  return [];
}
