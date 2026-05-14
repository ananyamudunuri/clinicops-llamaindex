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
  const [sources, setSources] = useState([]);
  const [accessedDocuments, setAccessedDocuments] = useState([]);
  const [sourceDocuments, setSourceDocuments] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const [listening, setListening] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState("");
  const [documentContent, setDocumentContent] = useState("");
  const [docMessage, setDocMessage] = useState("");
  const [docLoading, setDocLoading] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadMessage, setUploadMessage] = useState("");
  const [isCreatingDocument, setIsCreatingDocument] = useState(false);
  const [newDocumentName, setNewDocumentName] = useState("new_policy.txt");
  const [leftView, setLeftView] = useState("library");

  const tabs = [
    { id: "basic", label: "Basic RAG", route: "/basic-rag/query" },
    { id: "router", label: "Router RAG", route: "/router-rag/query" },
    { id: "subquestion", label: "Sub-Question", route: "/subquestion-rag/query" },
    { id: "react", label: "ReAct Agent", route: "/react-agent/query" },
    { id: "multidoc", label: "Multi-Doc Agent", route: "/multi-doc-agent/query" },
    { id: "multimodal", label: "Multimodal", route: "/multimodal-rag/query" },
  ];

  const sampleQuestions = {
    basic: "What happens if a patient cancels less than 24 hours before the appointment?",
    router: "Does the clinic accept Medicaid?",
    subquestion: "Compare appointment cancellation and billing fee policy.",
    react: "If the consultation fee is 120 dollars and insurance covers 70 percent, how much does the patient pay?",
    multidoc: "Which documents are irrelevant to the clinic policy knowledge base, and what do they contain?",
    multimodal: "What information is visible in this document?",
  };

  const exerciseInfo = {
    basic: {
      title: "Basic RAG",
      desc: "Searches all uploaded documents as one combined knowledge base and retrieves the most relevant chunks.",
      icon: "▰",
    },
    router: {
      title: "Router RAG",
      desc: "Classifies your question and routes it to the single most relevant document index.",
      icon: "⌁",
    },
    subquestion: {
      title: "Sub-Question RAG",
      desc: "Decomposes your question, checks each document separately, then synthesises a final answer.",
      icon: "◇",
    },
    react: {
      title: "ReAct Agent",
      desc: "Picks from document search, calculator, or general LLM knowledge based on what the question needs.",
      icon: "✦",
    },
    multidoc: {
      title: "Multi-Doc Agent",
      desc: "Turns every uploaded document into its own tool and decides which ones to query.",
      icon: "▣",
    },
    multimodal: {
      title: "Multimodal RAG",
      desc: "Accepts an image or PDF and answers using Claude Vision or extracted PDF text.",
      icon: "◉",
    },
  };

  const loadingSteps = {
    basic: ["Loading documents", "Splitting into chunks", "Finding relevant chunks", "Sending to Claude", "Generating answer"],
    router: ["Reading question", "Selecting best index", "Routing query", "Retrieving context", "Generating answer"],
    subquestion: ["Decomposing question", "Checking each document", "Collecting sub-answers", "Synthesising", "Finalising answer"],
    react: ["Reading question", "Choosing a tool", "Running tool", "Reviewing output", "Generating answer"],
    multidoc: ["Scanning documents", "Building tool per doc", "Selecting relevant tools", "Querying", "Summarising"],
    multimodal: ["Reading file", "Detecting type", "Extracting content", "Matching question", "Generating answer"],
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    if (!loading) {
      setLoadingStep(0);
      return;
    }
    const iv = setInterval(() => {
      setLoadingStep((p) => {
        const max = (loadingSteps[activeTab] || []).length - 1;
        return p < max ? p + 1 : p;
      });
    }, 1200);
    return () => clearInterval(iv);
  }, [loading, activeTab]);

  const loadDocuments = async () => {
    try {
      const res = await axios.get(`${API_BASE}/documents`);
      setDocuments(res.data.documents || []);
      setDocMessage("");
    } catch {
      setDocMessage("Could not load documents. Is the backend running?");
    }
  };

  const startNewDocument = () => {
    setIsCreatingDocument(true);
    setSelectedDocument("");
    setNewDocumentName("new_policy.txt");
    setDocumentContent("");
    setDocMessage("Write your content and click Save.");
    setLeftView("editor");
  };

  const cancelNewDocument = () => {
    setIsCreatingDocument(false);
    setSelectedDocument("");
    setNewDocumentName("new_policy.txt");
    setDocumentContent("");
    setDocMessage("");
    setLeftView("library");
  };

  const loadDocumentContent = async (filename) => {
    if (!filename) return;
    setDocLoading(true);
    setDocMessage("");
    setIsCreatingDocument(false);
    try {
      const res = await axios.get(`${API_BASE}/documents/${filename}`);
      setSelectedDocument(filename);
      setDocumentContent(res.data.content);
      setLeftView("editor");
    } catch {
      setDocMessage("Could not load document.");
    } finally {
      setDocLoading(false);
    }
  };

  const saveNewDocument = async () => {
    let filename = newDocumentName.trim();
    if (!filename) {
      alert("Enter a file name.");
      return;
    }
    if (!filename.toLowerCase().endsWith(".txt")) {
      filename += ".txt";
      setNewDocumentName(filename);
    }
    if (!documentContent.trim()) {
      alert("Add some content first.");
      return;
    }
    setDocLoading(true);
    try {
      const blob = new Blob([documentContent], { type: "text/plain" });
      const file = new File([blob], filename, { type: "text/plain" });
      const fd = new FormData();
      fd.append("file", file);
      const res = await axios.post(`${API_BASE}/documents/upload`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const savedAs = res.data.saved_as || filename;
      await loadDocuments();
      setSelectedDocument(savedAs);
      setIsCreatingDocument(false);
      setDocMessage(`Saved as ${savedAs}`);
    } catch (e) {
      setDocMessage(`Save failed: ${e.response?.data?.detail || e.message}`);
    } finally {
      setDocLoading(false);
    }
  };

  const saveExistingDocument = async () => {
    if (!selectedDocument) {
      alert("Select a document first.");
      return;
    }
    setDocLoading(true);
    try {
      await axios.put(`${API_BASE}/documents/${selectedDocument}`, { content: documentContent });
      setDocMessage("Saved — RAG will use the updated content.");
    } catch {
      setDocMessage("Could not save.");
    } finally {
      setDocLoading(false);
    }
  };

  const saveDocumentContent = () => (isCreatingDocument ? saveNewDocument() : saveExistingDocument());

  const uploadNewDocument = async () => {
    if (!uploadFile) {
      alert("Choose a file.");
      return;
    }
    const lower = uploadFile.name.toLowerCase();
    if (!lower.endsWith(".txt") && !lower.endsWith(".pdf")) {
      alert("Only .txt and .pdf supported.");
      return;
    }
    setDocLoading(true);
    setUploadMessage("");
    try {
      const fd = new FormData();
      fd.append("file", uploadFile);
      const res = await axios.post(`${API_BASE}/documents/upload`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadMessage(`Uploaded as ${res.data.saved_as || uploadFile.name}`);
      setUploadFile(null);
      await loadDocuments();
    } catch (e) {
      setUploadMessage(`Upload failed: ${e.response?.data?.detail || e.message}`);
    } finally {
      setDocLoading(false);
    }
  };

  const deleteDocument = async (filename) => {
    if (!window.confirm(`Delete ${filename}?`)) return;
    setDocLoading(true);
    try {
      await axios.delete(`${API_BASE}/documents/${filename}`);
      if (selectedDocument === filename) {
        setSelectedDocument("");
        setDocumentContent("");
        setLeftView("library");
      }
      await loadDocuments();
      setDocMessage(`${filename} deleted.`);
    } catch (e) {
      setDocMessage(e.response?.data?.detail || "Could not delete.");
    } finally {
      setDocLoading(false);
    }
  };

  const handleTabChange = (id) => {
    setActiveTab(id);
    setQuestion(sampleQuestions[id]);
    setAnswer("");
    setSources([]);
    setAccessedDocuments([]);
    setSourceDocuments([]);
    setSelectedFile(null);
    setListening(false);
    setLoadingStep(0);
  };

  const handleVoiceInput = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      alert("Voice input requires Chrome.");
      return;
    }
    const r = new SR();
    r.lang = "en-US";
    r.interimResults = false;
    r.maxAlternatives = 1;
    setListening(true);
    r.start();
    r.onresult = (e) => {
      setQuestion(e.results[0][0].transcript);
      setListening(false);
    };
    r.onerror = () => setListening(false);
    r.onend = () => setListening(false);
  };

  const saveToChatHistory = (entry) => setChatHistory((prev) => [entry, ...prev].slice(0, 10));

  const restoreHistoryItem = (item) => {
    setActiveTab(item.tabId);
    setQuestion(item.question);
    setAnswer(item.answer);
    setSources(item.sources || []);
    setAccessedDocuments(item.accessedDocuments || []);
    setSourceDocuments(item.sourceDocuments || []);
    setSelectedFile(null);
    setLoadingStep(0);
  };

  const getRagExplanation = () => {
    if (!answer || answer.startsWith("Error:")) return null;
    const accessed = accessedDocuments.length > 0 ? accessedDocuments.join(", ") : "none";
    const used = sourceDocuments.length > 0 ? sourceDocuments.join(", ") : "none";
    const n = sources.length;
    return (
      {
        basic: [`Searched all documents: ${accessed}.`, `Found ${n} evidence chunk(s).`, `Strongest evidence from: ${used}.`],
        router: ["Routed to the most relevant index.", `Evidence from: ${used}.`],
        subquestion: [`Checked documents: ${accessed}.`, `Evidence from: ${used}.`],
        react: [`Accessed: ${accessed}.`, `Evidence from: ${used}.`],
        multidoc: [`Document tools accessed: ${accessed}.`, `Evidence from: ${used}.`],
        multimodal: [`File analysed: ${used}.`, "Vision or PDF extraction was used."],
      }[activeTab] || []
    );
  };

  const handleSubmit = async () => {
    if (!question.trim()) {
      alert("Enter a question.");
      return;
    }
    setLoading(true);
    setLoadingStep(0);
    setAnswer("");
    setSources([]);
    setAccessedDocuments([]);
    setSourceDocuments([]);
    try {
      const tab = tabs.find((t) => t.id === activeTab);
      let res;
      if (activeTab === "multimodal") {
        if (!selectedFile) {
          alert("Upload an image or PDF.");
          setLoading(false);
          return;
        }
        const fd = new FormData();
        fd.append("question", question);
        fd.append("file", selectedFile);
        res = await axios.post(`${API_BASE}${tab.route}`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      } else {
        res = await axios.post(`${API_BASE}${tab.route}`, { question });
      }
      const a = res.data.answer || "";
      const s = res.data.sources || [];
      const ad = res.data.accessed_documents || [];
      const sd = res.data.source_documents || [];
      setAnswer(a);
      setSources(s);
      setAccessedDocuments(ad);
      setSourceDocuments(sd);
      saveToChatHistory({
        id: Date.now(),
        tabId: activeTab,
        tabLabel: tab.label,
        question,
        answer: a,
        sources: s,
        accessedDocuments: ad,
        sourceDocuments: sd,
        createdAt: new Date().toLocaleTimeString(),
      });
    } catch (e) {
      setAnswer(`Error: ${e.response?.data?.detail || e.message || "Check backend."}`);
    } finally {
      setLoading(false);
    }
  };

  const ragExplanation = getRagExplanation();
  const currentTab = tabs.find((t) => t.id === activeTab);
  const currentInfo = exerciseInfo[activeTab];

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">♡</div>
          <div>
            <div className="brand-name">ClinicOps</div>
          </div>
        </div>

        <nav className="topnav">
          {tabs.map((t) => (
            <button
              key={t.id}
              className={`nav-tab${activeTab === t.id ? " nav-tab-active" : ""}`}
              onClick={() => handleTabChange(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <div className="top-actions">
          <button className="model-select">Claude Sonnet 4 <span>⌄</span></button>
          <button className="settings-btn">⚙</button>
          <div className="avatar">AK</div>
        </div>
      </header>

      <div className="app-grid">
        <aside className="sidebar left-panel">
          <div className="panel-head">
            <div className="panel-title">
              <span>Library</span>
              <span className="count-pill">{documents.length}</span>
            </div>
            <div className="panel-actions">
              <button className="square-btn" onClick={loadDocuments} disabled={docLoading} title="Refresh">↻</button>
              <button className="square-btn primary" onClick={startNewDocument} title="New document">+</button>
            </div>
          </div>

          {leftView === "library" && (
            <>
              <div className="upload-card">
                <label className="upload-drop">
                  <input type="file" accept=".txt,.pdf" onChange={(e) => setUploadFile(e.target.files[0])} />
                  <span className="upload-icon">☁</span>
                  <span className="upload-main">{uploadFile ? uploadFile.name : "Drag & drop files here"}</span>
                  <span className="upload-sub">or</span>
                </label>
                <button className="upload-btn" onClick={uploadNewDocument} disabled={docLoading || !uploadFile}>
                  {docLoading ? "Uploading..." : "Upload"}
                </button>
              </div>

              {uploadMessage && <p className="side-message">{uploadMessage}</p>}

              <div className="search-box">
                <span>⌕</span>
                <input placeholder="Search documents..." readOnly />
              </div>

              <div className="doc-list">
                {documents.length === 0 && <p className="left-empty">No documents yet.</p>}
                {documents.map((doc) => {
                  const isPdf = doc.filename.toLowerCase().endsWith(".pdf");
                  return (
                    <div key={doc.filename} className={`doc-row${selectedDocument === doc.filename ? " doc-row-active" : ""}`}>
                      <button className="doc-row-btn" onClick={() => loadDocumentContent(doc.filename)}>
                        <span className={`file-icon ${isPdf ? "pdf" : "txt"}`}>{isPdf ? "▣" : "▤"}</span>
                        <span className="doc-row-name">{doc.filename}</span>
                      </button>
                      <button className="doc-row-del" onClick={(e) => { e.stopPropagation(); deleteDocument(doc.filename); }}>⋮</button>
                    </div>
                  );
                })}
              </div>

              <div className="sidebar-footer">
                <div className="storage-card">
                  <div className="storage-icon">▰</div>
                  <div className="storage-content">
                    <div>Storage used</div>
                    <span>128.4 MB of 5 GB</span>
                    <div className="progress-line"><i /></div>
                  </div>
                  <span className="storage-percent">2%</span>
                </div>
                <button className="manage-btn"><span>⚙</span> Manage library <b>›</b></button>
              </div>

              {docMessage && <p className="side-message bottom-msg">{docMessage}</p>}
            </>
          )}

          {leftView === "editor" && (
            <div className="editor-view">
              <div className="editor-view-top">
                <button className="back-btn" onClick={() => setLeftView("library")}>← Library</button>
                <span className="editor-view-status">{isCreatingDocument ? "New file" : "Editing"}</span>
              </div>

              {isCreatingDocument ? (
                <input
                  className="filename-input"
                  value={newDocumentName}
                  onChange={(e) => setNewDocumentName(e.target.value)}
                  placeholder="filename.txt"
                />
              ) : (
                <div className="filename-display">{selectedDocument}</div>
              )}

              <textarea
                className="editor-ta"
                value={documentContent}
                onChange={(e) => setDocumentContent(e.target.value)}
                placeholder={isCreatingDocument ? "Start writing..." : "Document content..."}
              />

              <div className="editor-view-footer">
                <button className="save-btn" onClick={saveDocumentContent} disabled={docLoading}>
                  {docLoading ? "Saving..." : isCreatingDocument ? "Save File" : "Save Changes"}
                </button>
                {isCreatingDocument && <button className="cancel-btn" onClick={cancelNewDocument}>Cancel</button>}
                {docMessage && <span className="editor-msg">{docMessage}</span>}
              </div>
            </div>
          )}
        </aside>

        <main className="main-panel">
          <section className="hero-card">
            <div className="hero-copy">
              <div className="hero-icon">{currentInfo.icon}</div>
              <div>
                <div className="hero-title-row">
                  <h1>{currentInfo.title}</h1>
                  <code>{currentTab.route}</code>
                </div>
                <p>{currentInfo.desc}</p>
              </div>
            </div>
            <div className="hero-art" aria-hidden="true">
              <div className="paper-shape">▤</div>
              <div className="cube cube-1" />
              <div className="cube cube-2" />
              <div className="cube cube-3" />
              <div className="lens" />
            </div>

            <div className="steps-card">
              {loadingSteps[activeTab].map((s, i) => (
                <div key={i} className={`step-item${loading && i <= loadingStep ? " step-on" : ""}`}>
                  <span className="step-num">{loading && i < loadingStep ? "✓" : i + 1}</span>
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="question-card">
            <h2>Ask a question about your documents</h2>
            <div className="question-input-shell">
              <textarea
                className="q-input"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Type your question here..."
                rows={4}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit();
                  }
                }}
              />

              {activeTab === "multimodal" && (
                <label className="mm-label">
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/jpg,image/webp,.pdf,application/pdf"
                    onChange={(e) => setSelectedFile(e.target.files[0])}
                  />
                  <span>{selectedFile ? `📎 ${selectedFile.name}` : "Attach image or PDF..."}</span>
                </label>
              )}

              <div className="q-actions">
                <button className="light-action" onClick={handleVoiceInput}>{listening ? "🔴 Listening..." : "⌕ Voice input"}</button>
                <button className="light-action" onClick={() => setQuestion(sampleQuestions[activeTab])}>☰ Sample questions</button>
                <span className="enter-hint">Press Enter to send</span>
                <button className="ask-btn" onClick={handleSubmit} disabled={loading}>{loading ? "Thinking..." : "Ask AI  ▶"}</button>
              </div>
            </div>
          </section>

          {loading && (
            <div className="loading-bar">
              <span className="loading-dot" />
              <span>{loadingSteps[activeTab][loadingStep]}</span>
            </div>
          )}

          {answer ? (
            <section className="answer-card">
              <div className="answer-head">
                <span>Answer</span>
                {sourceDocuments.length > 0 && (
                  <b>{sourceDocuments.length} source{sourceDocuments.length !== 1 ? "s" : ""}</b>
                )}
              </div>
              <div className="answer-text">{answer}</div>

              {ragExplanation && ragExplanation.length > 0 && (
                <details className="rag-trace">
                  <summary>How RAG got this answer</summary>
                  <ul>{ragExplanation.map((s, i) => <li key={i}>{s}</li>)}</ul>
                </details>
              )}

              {(accessedDocuments.length > 0 || sourceDocuments.length > 0) && (
                <div className="tag-section">
                  {accessedDocuments.length > 0 && (
                    <div className="tag-group">
                      <span className="tag-label">Accessed</span>
                      {accessedDocuments.map((d) => <span key={d} className="tag">{d}</span>)}
                    </div>
                  )}
                  {sourceDocuments.length > 0 && (
                    <div className="tag-group">
                      <span className="tag-label">Used as evidence</span>
                      {sourceDocuments.map((d) => <span key={d} className="tag green">{d}</span>)}
                    </div>
                  )}
                </div>
              )}

              {sources.length > 0 && (
                <div className="evidence">
                  <span className="evidence-heading">Retrieved evidence</span>
                  {sources.map((s, i) => (
                    <div key={i} className="ev-card">
                      <div className="ev-card-top">
                        <strong>{s.document}</strong>
                        {s.score != null && <span>score {s.score}</span>}
                      </div>
                      <p>{s.excerpt}</p>
                    </div>
                  ))}
                </div>
              )}
            </section>
          ) : (
            !loading && (
              <section className="empty-answer-card">
                <div className="empty-bubble">☁</div>
                <h3>Your answer will appear here</h3>
                <p>Ask a question above — the AI will retrieve and reason over your documents.</p>
              </section>
            )
          )}
        </main>

        <aside className="sidebar right-panel">
          <div className="panel-head history-head">
            <div className="panel-title">History</div>
            <button className="clear-btn" onClick={() => setChatHistory([])}>Clear</button>
          </div>

          {chatHistory.length === 0 ? (
            <div className="history-empty">
              <div className="clock-icon">◷</div>
              <h3>No queries yet</h3>
              <p>Your recent queries and answers will appear here.</p>
            </div>
          ) : (
            <div className="right-list">
              {chatHistory.map((item) => (
                <button key={item.id} className="hist-item" onClick={() => restoreHistoryItem(item)}>
                  <span>{item.tabLabel}</span>
                  <p>{item.question}</p>
                  <small>{item.createdAt}</small>
                </button>
              ))}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

export default App;
