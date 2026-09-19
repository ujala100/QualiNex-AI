import React, { useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { applyAIResult } from "../store/complaintSlice";
import { addMessage, startProcessing, setProgress, finishProcessing, setError } from "../store/copilotSlice";
import { logComplaint, extractDocument, editComplaint } from "../api/api";
import RiskAssessmentPanel from "./RiskAssessmentPanel";

/**
 * Houses all 3 mandatory AI tools:
 *   1. Log Complaint tool      -> paste text
 *   2. Document Extraction     -> drag & drop / browse PDF/DOCX/TXT/EML
 *   3. AI Edit Complaint tool  -> chat input, once a complaint already exists
 *
 * The upload/paste controls stay available at ALL times (previously they
 * were hidden once the form had content, which made it look like document
 * upload had stopped working after the first extraction or a manual edit --
 * that was a bug, not intended behavior). Re-uploading/re-pasting once a
 * complaint already has data asks for confirmation before overwriting it,
 * since that runs a fresh extraction rather than a targeted edit.
 *
 * Routing rule for the chat box: if the form is still empty, a typed
 * message goes through the Log Complaint tool. Once a complaint already
 * has data, chat messages are treated as edit instructions (AI Edit tool),
 * which preserves every field the instruction doesn't mention.
 */
export default function AICopilotPanel() {
  const dispatch = useDispatch();
  const { messages, isProcessing, progress, progressLabel } = useSelector((s) => s.copilot);
  const { formData, hasContent, complaintId } = useSelector((s) => s.complaint);

  const [pasteMode, setPasteMode] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [chatText, setChatText] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(true);
  const fileInputRef = useRef(null);

  const simulateProgress = () => {
    let p = 5;
    const interval = setInterval(() => {
      p = Math.min(p + 12, 90);
      dispatch(setProgress(p));
    }, 250);
    return () => clearInterval(interval);
  };

  const confirmOverwriteIfNeeded = () => {
    if (!hasContent) return true;
    return window.confirm(
      "This will run a fresh extraction and overwrite the current form. Continue? " +
        "(Tip: to change a single field instead, type an instruction in the chat box below.)"
    );
  };

  const runLogComplaint = async (text) => {
    dispatch(addMessage({ role: "user", text }));
    dispatch(startProcessing("Analyzing text and extracting key details..."));
    const stop = simulateProgress();
    try {
      const result = await logComplaint(text);
      dispatch(applyAIResult(result));
      dispatch(addMessage({ role: "assistant", text: result.assistant_message }));
    } catch (e) {
      dispatch(setError(e.message));
      dispatch(addMessage({ role: "error", text: `Extraction failed: ${e.message}` }));
    } finally {
      stop();
      dispatch(finishProcessing());
    }
  };

  const runDocumentExtraction = async (file) => {
    dispatch(addMessage({ role: "user", text: `📎 Uploaded: ${file.name}` }));
    dispatch(startProcessing(`Reading ${file.name} and extracting complaint details...`));
    const stop = simulateProgress();
    try {
      const result = await extractDocument(file);
      dispatch(applyAIResult(result));
      dispatch(addMessage({ role: "assistant", text: result.assistant_message }));
      setUploadOpen(false);
    } catch (e) {
      dispatch(setError(e.message));
      const hint = /no readable text|scanned\/image/i.test(e.message)
        ? " This is an image-only PDF. OCR must be enabled on the backend for scanned documents."
        : "";
      dispatch(addMessage({ role: "error", text: `Document extraction failed: ${e.message}${hint}` }));
    } finally {
      stop();
      dispatch(finishProcessing());
    }
  };

  const runEditComplaint = async (instruction) => {
    dispatch(addMessage({ role: "user", text: instruction }));
    dispatch(startProcessing("Applying your edit and re-running risk assessment..."));
    const stop = simulateProgress();
    try {
      const result = await editComplaint(formData, instruction, complaintId);
      dispatch(applyAIResult(result));
      dispatch(addMessage({ role: "assistant", text: result.assistant_message }));
    } catch (e) {
      dispatch(setError(e.message));
      dispatch(addMessage({ role: "error", text: `Edit failed: ${e.message}` }));
    } finally {
      stop();
      dispatch(finishProcessing());
    }
  };

  const handleFile = (file) => {
    if (!file) return;
    if (!confirmOverwriteIfNeeded()) return;
    runDocumentExtraction(file);
  };

  const handleChatSubmit = (e) => {
    e.preventDefault();
    const text = chatText.trim();
    if (!text || isProcessing) return;
    setChatText("");
    if (hasContent) {
      runEditComplaint(text);
    } else {
      runLogComplaint(text);
    }
  };

  const handlePasteSubmit = () => {
    const text = pasteText.trim();
    if (!text) return;
    if (!confirmOverwriteIfNeeded()) return;
    setPasteText("");
    setPasteMode(false);
    runLogComplaint(text);
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>AI Complaint Intake Assistant</h2>
          <div className="subtitle">Extraction, editing &amp; risk assessment — powered by Groq + LangGraph</div>
        </div>
        <span className="badge badge-beta">BETA</span>
      </div>

      {hasContent && (
        <button
          className="paste-btn"
          style={{ marginBottom: 12, justifyContent: "space-between" }}
          onClick={() => setUploadOpen((v) => !v)}
        >
          <span>📎 Upload / paste a document to re-extract</span>
          <span>{uploadOpen ? "▲" : "▼"}</span>
        </button>
      )}

      {(uploadOpen || !hasContent) && (
        <>
          <div
            className={`dropzone ${dragOver ? "dragover" : ""}`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleFile(e.dataTransfer.files?.[0]);
            }}
          >
            📄 Drag &amp; drop complaint document here
            <br />
            or <span className="browse">click to browse</span>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            hidden
            accept=".pdf,.docx,.txt,.eml"
            onChange={(e) => {
              handleFile(e.target.files?.[0]);
              e.target.value = ""; // allow re-selecting the same file later
            }}
          />

          <div className="divider-or">OR</div>

          {!pasteMode ? (
            <button className="paste-btn" onClick={() => setPasteMode(true)}>
              📝 Paste Complaint Text / Email
            </button>
          ) : (
            <div className="field">
              <textarea
                autoFocus
                placeholder="Paste the complaint email or description here..."
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                style={{ minHeight: 100 }}
              />
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <button className="btn btn-primary" onClick={handlePasteSubmit} disabled={isProcessing}>
                  Extract &amp; Populate
                </button>
                <button className="btn btn-secondary" onClick={() => setPasteMode(false)}>
                  Cancel
                </button>
              </div>
            </div>
          )}

          <div className="file-hint">✓ Supported formats: PDF (including OCR-enabled scans), DOCX, TXT, EML · Max file size: 10MB</div>
        </>
      )}

      {isProcessing && (
        <div className="progress-wrap">
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="progress-label">{progressLabel}</div>
        </div>
      )}

      <div className="chat-log">
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role}`}>
            {m.text}
          </div>
        ))}
      </div>

      <form className="chat-input-row" onSubmit={handleChatSubmit}>
        <input
          placeholder={hasContent ? "Ask me to edit anything about this complaint..." : "Ask me anything about this complaint..."}
          value={chatText}
          onChange={(e) => setChatText(e.target.value)}
          disabled={isProcessing}
        />
        <button className="chat-send-btn" type="submit" disabled={isProcessing || !chatText.trim()}>
          ➤
        </button>
      </form>
      <div className="disclaimer">AI responses may contain errors. Please verify information.</div>

      <RiskAssessmentPanel />
    </div>
  );
}
