import React from "react";
import LogComplaintForm from "./components/LogComplaintForm";
import AICopilotPanel from "./components/AICopilotPanel";

export default function App() {
  return (
    <div className="app-shell">
      <div className="app-header">
        <h1>AIVOA — AI-Powered Customer Complaint Management</h1>
        <p>Pharmaceutical Manufacturing QMS · API &amp; FDF Quality Assurance Module</p>
      </div>
      <div className="grid-2col">
        <LogComplaintForm />
        <AICopilotPanel />
      </div>
    </div>
  );
}
