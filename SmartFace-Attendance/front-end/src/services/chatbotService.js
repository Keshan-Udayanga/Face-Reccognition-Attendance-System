const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000/api`;

export async function sendChatMessage(messages) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    });
  } catch {
    throw new Error(
      "Could not reach the SmartFace API. Start the Python backend and check your connection.",
    );
  }

  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const error = await response.json();
      if (typeof error.detail === "string") {
        message = error.detail;
      }
    } catch {
      // Keep the HTTP status message when the server does not return JSON.
    }
    throw new Error(message);
  }

  return response.json();
}
