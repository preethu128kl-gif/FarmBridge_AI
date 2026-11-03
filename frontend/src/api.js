const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:5000/api").replace(/\/+$/, "");

export async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem("farmbridge_token");

  let response;
  try {
    response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {})
      }
    });
  } catch (error) {
    if (error.name === "AbortError") throw new Error("The FarmBridge API request was cancelled.");
    throw new Error("Cannot reach the FarmBridge API. Confirm Flask is running and the API URL is correct, then try again.");
  }

  let data;
  try {
    data = await response.json();
  } catch {
    data = { error: `The API returned an unreadable response (HTTP ${response.status}).` };
  }

  if (!response.ok) {
    const jwtFailure = token && (
      response.status === 401 ||
      (response.status === 422 && typeof data.msg === "string")
    );
    if (jwtFailure) {
      let role = "consumer";
      try {
        role = JSON.parse(localStorage.getItem("farmbridge_user") || "{}").role || role;
      } catch {
        role = "consumer";
      }
      localStorage.removeItem("farmbridge_token");
      localStorage.removeItem("farmbridge_user");
      window.dispatchEvent(new CustomEvent("farmbridge:session-expired", { detail: { role } }));
      throw new Error("Your session is invalid or expired. Please sign in again.");
    }
    throw new Error(data.message || data.error || "Something went wrong");
  }

  return data;
}

export { API_URL };
