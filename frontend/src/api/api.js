// Port 8000 is frequently occupied by other local FastAPI projects. AIVOA's
// documented development backend runs on 8001; deployments can still override
// this with REACT_APP_API_BASE_URL.
const BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8001";

async function handleResponse(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) {
      /* ignore parse errors */
    }
    throw new Error(detail);
  }
  return res.json();
}

/** Tool 1: Log Complaint - free text -> populated form + risk assessment */
export function logComplaint(text) {
  return fetch(`${BASE_URL}/api/copilot/log-complaint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  }).then(handleResponse);
}

/** Tool 2: Document Extraction - uploaded PDF/DOCX/TXT/EML -> populated form */
export function extractDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  return fetch(`${BASE_URL}/api/copilot/extract-document`, {
    method: "POST",
    body: formData,
  }).then(handleResponse);
}

/** Tool 3: AI Edit Complaint - instruction + current form -> updated form, preserving the rest */
export function editComplaint(currentForm, instruction, complaintId) {
  return fetch(`${BASE_URL}/api/copilot/edit-complaint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ current_form: currentForm, instruction, complaint_id: complaintId }),
  }).then(handleResponse);
}

export function saveComplaint(payload) {
  return fetch(`${BASE_URL}/api/complaints`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then(handleResponse);
}

export function listComplaints() {
  return fetch(`${BASE_URL}/api/complaints`).then(handleResponse);
}
