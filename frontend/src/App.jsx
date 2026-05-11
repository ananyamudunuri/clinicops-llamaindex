import { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [activeTab, setActiveTab] = useState("basic");
  const [question, setQuestion] = useState(
    "What happens if a patient cancels less than 24 hours before the appointment?"
  );
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [listening, setListening] = useState(false);

  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState("");
  const [documentContent, setDocumentContent] = useState("");
  const [docMessage, setDocMessage] = useState("");
  const [docLoading, setDocLoading] = useState(false);

  const tabs = [
    { id: "basic", label: "Basic RAG", route: "/basic-rag/query" },
    { id: "router", label: "Router RAG", route: "/router-rag/query" },
    { id: "subquestion", label: "SubQuestion RAG", route: "/subquestion-rag/query" },
    { id: "react", label: "ReAct Agent", route: "/react-agent/query" },
    { id: "multidoc", label: "Multi Document Agent", route: "/multi-doc-agent/query" },
    { id: "multimodal", label: "Multimodal RAG", route: "/multimodal-rag/query" },
  ];

  const sampleQuestions = {
    basic: "What happens if a patient cancels less than 24 hours before the appointment?",
    router: "Does the clinic accept Medicaid?",
    subquestion: "Compare appointment cancellation and billing fee policy.",
    react:
      "If the consultation fee is 120 dollars and insurance covers 70 percent, how much does the patient pay?",
    multidoc: "Which documents talk about late cancellation and what do they say?",
    multimodal: "What information is visible in this document?",
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE}/documents`);
      setDocuments(response.data.documents || []);
    } catch (error) {
      console.error(error);
      setDocMessage("Could not load documents. Check if backend is running.");
    }
  };

  const loadDocumentContent = async (filename) => {
    if (!filename) return;

    setDocLoading(true);
    setDocMessage("");

    try {
      const response = await axios.get(`${API_BASE}/documents/${filename}`);
      setSelectedDocument(filename);
      setDocumentContent(response.data.content);
    } catch (error) {
      console.error(error);
      setDocMessage("Could not load document content.");
    } finally {
      setDocLoading(false);
    }
  };

  const saveDocumentContent = async () => {
    if (!selectedDocument) {
      alert("Please select a document first.");
      return;
    }

    setDocLoading(true);
    setDocMessage("");

    try {
      await axios.put(`${API_BASE}/documents/${selectedDocument}`, {
        content: documentContent,
      });

      setDocMessage(
        "Document saved successfully. New RAG answers will use this updated content."
      );
    } catch (error) {
      console.error(error);
      setDocMessage("Could not save document.");
    } finally {
      setDocLoading(false);
    }
  };

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    setQuestion(sampleQuestions[tabId]);
    setAnswer("");
    setSelectedFile(null);
    setListening(false);
  };

  const handleVoiceInput = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Voice input is not supported in this browser. Please use Chrome.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    setListening(true);
    recognition.start();

    recognition.onresult = (event) => {
      const spokenText = event.results[0][0].transcript;
      setQuestion(spokenText);
      setListening(false);
    };

    recognition.onerror = (event) => {
      setListening(false);
      alert("Voice input error: " + event.error);
    };

    recognition.onend = () => {
      setListening(false);
    };
  };

  const handleSubmit = async () => {
    if (!question.trim()) {
      alert("Please enter a question.");
      return;
    }

    setLoading(true);
    setAnswer("");

    try {
      const currentTab = tabs.find((tab) => tab.id === activeTab);

      if (activeTab === "multimodal") {
        if (!selectedFile) {
          alert("Please upload an image file.");
          setLoading(false);
          return;
        }

        const formData = new FormData();
        formData.append("question", question);
        formData.append("file", selectedFile);

        const response = await axios.post(
          `${API_BASE}${currentTab.route}`,
          formData,
          {
            headers: {
              "Content-Type": "multipart/form-data",
            },
          }
        );

        setAnswer(response.data.answer);
      } else {
        const response = await axios.post(`${API_BASE}${currentTab.route}`, {
          question,
        });

        setAnswer(response.data.answer);
      }
    } catch (error) {
      console.error(error);

      const errorMessage =
        error.response?.data?.detail ||
        error.message ||
        "Something went wrong. Please check if backend is running.";

      setAnswer(`Error: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  const currentTab = tabs.find((tab) => tab.id === activeTab);

  return (
    <div className="app">
      <header className="header">
        <h1>ClinicOps AI Assistant</h1>
        <p>Intelligent document search and workflow support for clinic operations</p>
      </header>

      <section className="documents-card">
        <div className="documents-header">
          <div>
            <h2>Clinic Documents</h2>
            <p>View and edit the local text documents used by the RAG backend.</p>
          </div>

          <button className="refresh-btn" onClick={loadDocuments}>
            Refresh Documents
          </button>
        </div>

        <div className="documents-layout">
          <div className="documents-list">
            <h3>Available Documents</h3>

            {documents.length === 0 && (
              <p className="muted">No documents found.</p>
            )}

            {documents.map((doc) => (
              <button
                key={doc.filename}
                className={
                  selectedDocument === doc.filename
                    ? "doc-item active-doc"
                    : "doc-item"
                }
                onClick={() => loadDocumentContent(doc.filename)}
              >
                {doc.filename}
              </button>
            ))}
          </div>

          <div className="document-editor">
            <h3>
              {selectedDocument
                ? `Editing: ${selectedDocument}`
                : "Select a document to view/edit"}
            </h3>

            <textarea
              className="document-textarea"
              value={documentContent}
              onChange={(e) => setDocumentContent(e.target.value)}
              placeholder="Document content will appear here..."
              disabled={!selectedDocument || docLoading}
            />

            <div className="document-actions">
              <button
                className="save-doc-btn"
                onClick={saveDocumentContent}
                disabled={!selectedDocument || docLoading}
              >
                {docLoading ? "Working..." : "Save Document"}
              </button>
            </div>

            {docMessage && <p className="doc-message">{docMessage}</p>}
          </div>
        </div>
      </section>

      <div className="tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={activeTab === tab.id ? "tab active" : "tab"}
            onClick={() => handleTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <main className="card">
        <div className="section-title">
          <h2>{currentTab.label}</h2>
          <p>Route: {currentTab.route}</p>
        </div>

        <label>Question</label>

        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a clinic operations question..."
        />

        <div className="action-row">
          <button className="voice-btn" onClick={handleVoiceInput}>
            {listening ? "Listening..." : "🎤 Speak Question"}
          </button>

          <button
            className="sample-btn"
            onClick={() => setQuestion(sampleQuestions[activeTab])}
          >
            Use Sample Question
          </button>
        </div>

        {activeTab === "multimodal" && (
          <div className="upload-box">
            <label>Upload Image</label>

            <input
              type="file"
              accept="image/png,image/jpeg,image/jpg,image/webp"
              onChange={(e) => setSelectedFile(e.target.files[0])}
            />

            {selectedFile && (
              <p className="file-name">Selected file: {selectedFile.name}</p>
            )}
          </div>
        )}

        <button className="submit-btn" onClick={handleSubmit} disabled={loading}>
          {loading ? "Thinking..." : "Ask AI"}
        </button>

        <div className="answer-box">
          <h3>Answer</h3>
          <div className="answer-text">
            {answer || "Answer will appear here..."}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;