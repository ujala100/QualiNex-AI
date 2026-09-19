import { createSlice } from "@reduxjs/toolkit";

/**
 * The "Log Customer Complaint" form supports BOTH:
 *   - AI population/updates via `applyAIResult` (Log/Edit/Document tools)
 *   - direct manual edits via `updateField` (the analyst typing/correcting
 *     a field by hand)
 * Both paths write to the same `formData`, so Save always persists
 * whichever is most current, and the AI Edit tool always edits against
 * the latest values regardless of who last touched them.
 */

export const EMPTY_FORM = {
  complaint_source: "",
  customer_name: "",
  product_name: "",
  product_strength_grade: "",
  batch_lot_number: "",
  manufacturing_date: "",
  expiry_date: "",
  quantity_affected: "",
  complaint_type: "",
  complaint_date: "",
  detailed_complaint_description: "",
  initial_severity: "",
  priority: "",
};

const initialState = {
  formData: { ...EMPTY_FORM },
  riskAssessment: {},
  completeness: {},
  duplicateCheck: {},
  rootCause: {},
  capa: {},
  summary: "",
  complaintId: null,
  hasContent: false,
  saveStatus: "unsaved", // 'unsaved' | 'saving' | 'saved'
};

const complaintSlice = createSlice({
  name: "complaint",
  initialState,
  reducers: {
    // A full AI tool result (Log / Document Extraction / Edit) is applied wholesale.
    applyAIResult(state, action) {
      const result = action.payload;
      state.formData = { ...EMPTY_FORM, ...result.form_data };
      state.riskAssessment = result.risk_assessment || {};
      state.completeness = result.completeness || {};
      state.duplicateCheck = result.duplicate_check || {};
      state.rootCause = result.root_cause || {};
      state.capa = result.capa || {};
      state.summary = result.summary || "";
      state.hasContent = true;
      state.saveStatus = "unsaved";
      if (result.complaint_id) state.complaintId = result.complaint_id;
    },
    // A single field is edited by hand.
    updateField(state, action) {
      const { field, value } = action.payload;
      if (field in state.formData) {
        state.formData[field] = value;
        state.hasContent = Object.values(state.formData).some((v) => v && v.trim && v.trim());
        state.saveStatus = "unsaved";
      }
    },
    setComplaintId(state, action) {
      state.complaintId = action.payload;
    },
    setSaveStatus(state, action) {
      state.saveStatus = action.payload;
    },
    resetForm() {
      return { ...initialState, formData: { ...EMPTY_FORM } };
    },
  },
});

export const { applyAIResult, updateField, setComplaintId, setSaveStatus, resetForm } = complaintSlice.actions;
export default complaintSlice.reducer;
