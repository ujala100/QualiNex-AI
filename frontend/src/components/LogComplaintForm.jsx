import React from "react";
import { useSelector, useDispatch } from "react-redux";
import { resetForm, setSaveStatus, setComplaintId, updateField } from "../store/complaintSlice";
import { saveComplaint } from "../api/api";

const SEVERITY_OPTIONS = ["", "Critical", "Major", "Minor"];
const PRIORITY_OPTIONS = ["", "High", "Medium", "Low"];

/**
 * Fields here are editable directly (manual entry/correction) AND get
 * overwritten whenever the AI Copilot on the right returns a result
 * (Log Complaint / Document Extraction / AI Edit Complaint). Both paths
 * write to the same Redux field via `updateField` / `applyAIResult`, so
 * Save always persists whatever is currently on screen.
 */
function TextField({ id, label, value, dispatch, textarea }) {
  const onChange = (e) => dispatch(updateField({ field: id, value: e.target.value }));
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {textarea ? (
        <textarea id={id} value={value || ""} placeholder="Type or let AI extract this..." onChange={onChange} />
      ) : (
        <input id={id} value={value || ""} placeholder="Type or let AI extract this..." onChange={onChange} />
      )}
    </div>
  );
}

function SelectField({ id, label, value, options, dispatch }) {
  const onChange = (e) => dispatch(updateField({ field: id, value: e.target.value }));
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value || ""} onChange={onChange}>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt || "Select..."}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function LogComplaintForm() {
  const dispatch = useDispatch();
  const { formData, riskAssessment, completeness, duplicateCheck, rootCause, capa, summary, complaintId, hasContent, saveStatus } =
    useSelector((s) => s.complaint);

  const severityBadgeClass =
    formData.initial_severity === "Critical"
      ? "badge-critical"
      : formData.initial_severity === "Major"
      ? "badge-major"
      : formData.initial_severity
      ? "badge-minor"
      : "badge-pending";

  const handleSave = async () => {
    dispatch(setSaveStatus("saving"));
    try {
      const res = await saveComplaint({
        form_data: formData,
        risk_assessment: riskAssessment,
        completeness,
        duplicate_check: duplicateCheck,
        root_cause: rootCause,
        capa,
        summary,
        complaint_id: complaintId,
      });
      dispatch(setComplaintId(res.complaint_id));
      dispatch(setSaveStatus("saved"));
    } catch (e) {
      dispatch(setSaveStatus("unsaved"));
      alert("Failed to save: " + e.message);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Log Customer Complaint</h2>
          <div className="subtitle">API &amp; FDF Quality Assurance Module</div>
        </div>
        <span className={`badge ${hasContent ? severityBadgeClass : "badge-pending"}`}>
          {hasContent ? formData.initial_severity || "Pending Triage" : "Pending Triage"}
        </span>
      </div>

      <div className="ai-lock-hint">✏️ Edit any field directly, or use the AI Copilot on the right to fill/update it for you.</div>

      <div className="section-label">1. Origin &amp; Customer Details</div>
      <div className="field-row">
        <TextField id="complaint_source" label="Complaint Source" value={formData.complaint_source} dispatch={dispatch} />
        <TextField id="customer_name" label="Customer Name" value={formData.customer_name} dispatch={dispatch} />
      </div>

      <div className="section-label">2. Product &amp; Batch Identification</div>
      <div className="field-row">
        <TextField id="product_name" label="Product Name" value={formData.product_name} dispatch={dispatch} />
        <TextField
          id="product_strength_grade"
          label="Product Strength/Grade"
          value={formData.product_strength_grade}
          dispatch={dispatch}
        />
      </div>
      <div className="field-row">
        <TextField id="batch_lot_number" label="Batch/Lot Number" value={formData.batch_lot_number} dispatch={dispatch} />
        <TextField id="manufacturing_date" label="Manufacturing Date" value={formData.manufacturing_date} dispatch={dispatch} />
      </div>
      <div className="field-row">
        <TextField id="expiry_date" label="Expiry Date" value={formData.expiry_date} dispatch={dispatch} />
        <TextField id="quantity_affected" label="Quantity Affected" value={formData.quantity_affected} dispatch={dispatch} />
      </div>

      <div className="section-label">3. Complaint Details</div>
      <div className="field-row">
        <TextField id="complaint_type" label="Complaint Type" value={formData.complaint_type} dispatch={dispatch} />
        <TextField id="complaint_date" label="Complaint Date" value={formData.complaint_date} dispatch={dispatch} />
      </div>
      <div className="field-row single">
        <TextField
          id="detailed_complaint_description"
          label="Detailed Complaint Description"
          value={formData.detailed_complaint_description}
          dispatch={dispatch}
          textarea
        />
      </div>

      <div className="section-label">4. Initial Assessment &amp; Priority</div>
      <div className="field-row">
        <SelectField
          id="initial_severity"
          label="Initial Severity"
          value={formData.initial_severity}
          options={SEVERITY_OPTIONS}
          dispatch={dispatch}
        />
        <SelectField id="priority" label="Priority" value={formData.priority} options={PRIORITY_OPTIONS} dispatch={dispatch} />
      </div>

      <div className="form-actions">
        <button className="btn btn-secondary" onClick={() => dispatch(resetForm())}>
          ↺ Reset Form
        </button>
        <button className="btn btn-primary" onClick={handleSave} disabled={saveStatus === "saving"}>
          💾 {saveStatus === "saving" ? "Saving..." : saveStatus === "saved" ? "Saved ✓" : "Save Complaint"}
        </button>
      </div>
    </div>
  );
}
