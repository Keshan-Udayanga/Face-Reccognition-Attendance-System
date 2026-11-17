const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000/api`;

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
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

  return response.status === 204 ? null : response.json();
}

export async function getTodayAttendance() {
  return request("/attendance/today");
}

export async function startRecognition() {
  return request("/attendance/recognition/start", { method: "POST" });
}

export async function stopRecognition(sessionId) {
  return request(`/attendance/recognition/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
}

export async function recognizeFrame(sessionId, frame) {
  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("frame", frame, "camera-frame.jpg");
  return request("/attendance/recognition/frame", {
    method: "POST",
    body: formData,
  });
}
