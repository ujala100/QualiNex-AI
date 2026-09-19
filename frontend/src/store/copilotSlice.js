import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  messages: [
    {
      role: "assistant",
      text: "Upload a complaint document, paste complaint text, or type a message. I'll extract the details and populate the form for you.",
    },
  ],
  isProcessing: false,
  progress: 0,
  progressLabel: "",
  error: null,
};

const copilotSlice = createSlice({
  name: "copilot",
  initialState,
  reducers: {
    addMessage(state, action) {
      state.messages.push(action.payload);
    },
    startProcessing(state, action) {
      state.isProcessing = true;
      state.progress = 5;
      state.progressLabel = action.payload || "Analyzing document content and extracting key details...";
      state.error = null;
    },
    setProgress(state, action) {
      state.progress = action.payload;
    },
    finishProcessing(state) {
      state.isProcessing = false;
      state.progress = 100;
    },
    setError(state, action) {
      state.isProcessing = false;
      state.error = action.payload;
    },
    clearChat(state) {
      state.messages = initialState.messages;
      state.error = null;
    },
  },
});

export const { addMessage, startProcessing, setProgress, finishProcessing, setError, clearChat } =
  copilotSlice.actions;
export default copilotSlice.reducer;
