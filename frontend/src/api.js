const API_BASE_URL = "http://127.0.0.1:8000";

export async function analyzeCrop(formData) {
  const token = localStorage.getItem("farmflow_token");
  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers,
    body: formData,
  });

  const data = await response.json().catch(() => ({}));
  if (response.status === 401) {
    localStorage.removeItem("farmflow_token");
    localStorage.removeItem("farmflow_email");
    window.location.reload();
  }
  if (!response.ok) {
    throw new Error(data.detail || "Could not analyze the crop.");
  }
  return data;
}
