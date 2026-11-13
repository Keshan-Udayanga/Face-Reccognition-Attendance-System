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

function mapEmployeeData(employee) {
  return {
    employee_name: employee.fullName,
    department: employee.department,
    email: employee.email,
    contact_number: employee.contactNumber,
    designation: employee.designation,
    address: employee.address,
  };
}

async function appendPhoto(formData, photoUrl) {
  if (!photoUrl?.startsWith("data:image/")) {
    return;
  }

  const response = await fetch(photoUrl);
  const image = await response.blob();
  const extension = image.type === "image/png" ? "png" : "jpg";
  formData.append("photo", image, `employee-profile.${extension}`);
}

export async function getEmployees() {
  return request("/employees");
}

export async function getEmployeeById(id) {
  try {
    return await request(`/employees/${encodeURIComponent(id)}`);
  } catch (error) {
    if (error.message === "Employee not found.") {
      return null;
    }
    throw error;
  }
}

export async function createEmployee(employeeData) {
  const formData = new FormData();
  Object.entries(mapEmployeeData(employeeData)).forEach(([key, value]) => {
    formData.append(key, value);
  });
  await appendPhoto(formData, employeeData.photoUrl);
  return request("/employees", {
    method: "POST",
    body: formData,
  });
}

export async function updateEmployee(id, employeeData) {
  const formData = new FormData();
  Object.entries(mapEmployeeData(employeeData)).forEach(([key, value]) => {
    formData.append(key, value);
  });
  formData.append("remove_photo", String(Boolean(employeeData.removePhoto)));
  await appendPhoto(formData, employeeData.photoUrl);
  return request(`/employees/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: formData,
  });
}

export async function deleteEmployee(id) {
  return request(`/employees/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}
