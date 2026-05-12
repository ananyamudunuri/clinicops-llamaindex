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
    multidoc:
      "Which documents are irrelevant to the clinic policy knowledge base, and what do they contain?",
    multimodal: "What information is visible in this document?",
  };

  const exerciseInfo = {
    basic: {
      title: "What Basic RAG is doing",
      steps: [
        "Reads all clinic documents from the data folder.",
        "Splits the documents into searchable chunks.",
        "Finds the most relevant chunks for your question.",
        "Sends those chunks to Claude to generate the final answer.",
      ],
    },
    router: {
      title: "What Router RAG is doing",
      steps: [
        "Looks at your question first.",
        "Decides whether the question belongs to appointment, billing, or insurance.",
        "Routes the question to the most relevant document index.",
        "Generates an answer from the selected policy area.",
      ],
    },
    subquestion: {
      title: "What SubQuestion RAG is doing",
      steps: [
        "Sends the question to appointment, billing, and insurance documents separately.",
        "Gets separate answers from each policy document.",
        "Compares the useful parts.",
        "Combines everything into one final response.",
      ],
    },
    react: {
      title: "What ReAct Agent is doing",
      steps: [
        "Reads the question and decides which tool to use.",
        "Can use document search, calculator, or policy summary tool.",
        "Runs the selected tool.",
        "Returns the final answer based on the tool result.",
      ],
    },
    multidoc: {
      title: "What Multi Document Agent is doing",
      steps: [
        "Turns every uploaded .txt document into a separate searchable tool.",
        "The agent decides which document tools are relevant.",
        "It can check more than one document if needed.",
        "Returns which documents contain the answer and what they say.",
      ],
    },
    multimodal: {
      title: "What Multimodal RAG is doing",
      steps: [
        "Takes your uploaded image.",
        "Sends the image and your question to Claude Vision.",
        "Claude reads visible text, forms, cards, or diagrams.",
        "Returns a clean summary or extracted information.",
      ],
    },
  };

  const loadingMessage = {
    basic: "Running Basic RAG workflow...",
    router: "Running Router RAG workflow...",
    subquestion: "Running SubQuestion RAG workflow...",
    react: "Running ReAct Agent workflow...",
    multidoc: "Running Multi Document Agent workflow...",
    multimodal: "Running Multimodal RAG workflow...",
  };

  const loadingSteps = {
    basic: [
      "Reading all clinic documents from the data folder...",
      "Splitting documents into searchable chunks...",
      "Finding the most relevant context for your question...",
      "Sending retrieved context to Claude...",
      "Generating the final answer...",
    ],
    router: [
      "Reading your question...",
      "Identifying whether it belongs to appointment, billing, or insurance...",
      "Routing the question to the best document index...",
      "Retrieving relevant policy content...",
      "Generating a focused answer...",
    ],
    subquestion: [
      "Breaking the question into smaller policy checks...",
      "Searching appointment policy...",
      "Searching billing policy...",
      "Searching insurance policy...",
      "Combining the useful answers into one response...",
    ],
    react: [
      "Agent is reading your question...",
      "Agent is deciding which tool to use...",
      "Running document search, calculator, or summary tool...",
      "Reviewing the tool output...",
      "Generating the final response...",
    ],
    multidoc: [
      "Scanning all uploaded text documents...",
      "Creating a separate tool for each document...",
      "Choosing which documents are relevant...",
      "Searching selected document tools...",
      "Summarizing what each useful document says...",
    ],
    multimodal: [
      "Reading the uploaded image...",
      "Sending image and question to Claude Vision...",
      "Extracting visible text and document fields...",
      "Checking the image against your question...",
      "Generating a clean summary...",
    ],
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    if (!loading) {
      setLoadingStep(0);
      return;
    }

    const interval = setInterval(() => {
      setLoadingStep((prevStep) => {
        const steps = loadingSteps[activeTab] || [];

        if (prevStep < steps.length - 1) {
          return prevStep + 1;
        }

        return prevStep;
      });
    }, 1200);

    return () => clearInterval(interval);
  }, [loading, activeTab]);

  const loadDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE}/documents`);
      setDocuments(response.data.documents || []);
    } catch (error) {
      console.error(error);
      setDocMessage("Could not load documents. Check if backend is running.");
    }
  };

  const startNewDocument = () => {
    setIsCreatingDocument(true);
    setSelectedDocument("");
    setNewDocumentName("new_policy.txt");
    setDocumentContent("");
    setDocMessage("Write your new document content and click Save Document.");
  };

  const cancelNewDocument = () => {
    setIsCreatingDocument(false);
    setSelectedDocument("");
    setNewDocumentName("new_policy.txt");
    setDocumentContent("");
    setDocMessage("");
  };

  const loadDocumentContent = async (filename) => {
    if (!filename) return;

    setDocLoading(true);
    setDocMessage("");
    setIsCreatingDocument(false);

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

  const saveNewDocument = async () => {
    let filename = newDocumentName.trim();

    if (!filename) {
      alert("Please enter a file name.");
      return;
    }

    if (!filename.toLowerCase().endsWith(".txt")) {
      filename = `${filename}.txt`;
      setNewDocumentName(filename);
    }

    if (!documentContent.trim()) {
      alert("Please enter document content before saving.");
      return;
    }

    setDocLoading(true);
    setDocMessage("");

    try {
      const blob = new Blob([documentContent], { type: "text/plain" });
      const file = new File([blob], filename, { type: "text/plain" });

      const formData = new FormData();
      formData.append("file", file);

      const response = await axios.post(`${API_BASE}/documents/upload`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      const savedAs = response.data.saved_as || filename;

      await loadDocuments();

      setSelectedDocument(savedAs);
      setNewDocumentName(savedAs);
      setIsCreatingDocument(false);
      setDocMessage(`New document saved successfully as ${savedAs}.`);
    } catch (error) {
      console.error(error);

      const message =
        error.response?.data?.detail ||
        error.message ||
        "Could not create document.";

      setDocMessage(`Create failed: ${message}`);
    } finally {
      setDocLoading(false);
    }
  };

  const saveExistingDocument = async () => {
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

  const saveDocumentContent = async () => {
    if (isCreatingDocument) {
      await saveNewDocument();
    } else {
      await saveExistingDocument();
    }
  };

  const uploadNewDocument = async () => {
    if (!uploadFile) {
      alert("Please choose a .txt or .pdf file to upload.");
      return;
    }

    const lowerName = uploadFile.name.toLowerCase();

    if (!lowerName.endsWith(".txt") && !lowerName.endsWith(".pdf")) {
      alert("Only .txt and .pdf files are supported.");
      return;
    }

    setDocLoading(true);
    setUploadMessage("");

    try {
      const formData = new FormData();
      formData.append("file", uploadFile);

      const response = await axios.post(`${API_BASE}/documents/upload`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      const savedAs = response.data.saved_as || uploadFile.name;

      setUploadMessage(`Document uploaded successfully as ${savedAs}.`);
      setUploadFile(null);
      await loadDocuments();
    } catch (error) {
      console.error(error);

      const message =
        error.response?.data?.detail ||
        error.message ||
        "Could not upload document.";

      setUploadMessage(`Upload failed: ${message}`);
    } finally {
      setDocLoading(false);
    }
  };

  const deleteDocument = async (filename) => {
    const confirmDelete = window.confirm(
      `Are you sure you want to delete ${filename}?`
    );

    if (!confirmDelete) return;

    setDocLoading(true);
    setDocMessage("");

    try {
      await axios.delete(`${API_BASE}/documents/${filename}`);

      setDocMessage(`${filename} deleted successfully.`);

      if (selectedDocument === filename) {
        setSelectedDocument("");
        setDocumentContent("");
      }

      await loadDocuments();
    } catch (error) {
      console.error(error);
      setDocMessage(
        error.response?.data?.detail || "Could not delete document."
      );
    } finally {
      setDocLoading(false);
    }
  };

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    setQuestion(sampleQuestions[tabId]);
    setAnswer("");
    setSources([]);
    setAccessedDocuments([]);
    setSourceDocuments([]);
    setSelectedFile(null);
    setListening(false);
    setLoadingStep(0);
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

  const saveToChatHistory = (entry) => {
    setChatHistory((prevHistory) => [entry, ...prevHistory].slice(0, 10));
  };

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

  const clearChatHistory = () => {
    setChatHistory([]);
  };

  const getRagExplanation = () => {
    if (!answer || answer.startsWith("Error:")) {
      return null;
    }

    const accessed =
      accessedDocuments.length > 0
        ? accessedDocuments.join(", ")
        : "No accessed document metadata was returned.";

    const used =
      sourceDocuments.length > 0
        ? sourceDocuments.join(", ")
        : "No specific evidence document was returned.";

    const evidenceCount = sources.length;

    const explanations = {
      basic: [
        "Basic RAG treated all available clinic text documents as one combined knowledge base.",
        `It searched across these documents: ${accessed}.`,
        `The final answer was generated from the most relevant retrieved chunks. Evidence chunks found: ${evidenceCount}.`,
        `The strongest supporting document or documents were: ${used}.`,
      ],
      router: [
        "Router RAG first looked at the question and decided which policy area was most relevant.",
        "It then routed the question to the best matching document index, such as appointment, billing, or insurance.",
        `The document or documents used as evidence were: ${used}.`,
        "The final answer was generated only after retrieving context from that selected policy area.",
      ],
      subquestion: [
        "SubQuestion RAG checked appointment, billing, and insurance documents separately.",
        "It produced smaller document-level answers first, then combined the useful parts into one final answer.",
        `The documents checked were: ${accessed}.`,
        `The evidence used in the final answer came from: ${used}.`,
      ],
      react: [
        "The ReAct Agent read the question and selected a tool to help answer it.",
        "Depending on the question, it could use document search, calculator logic, or a policy summary tool.",
        `For document grounding, it searched these available documents: ${accessed}.`,
        `The retrieved evidence came from: ${used}.`,
      ],
      multidoc: [
        "The Multi Document Agent treated each uploaded text document as its own searchable tool.",
        "It decided which document tools were relevant to the question.",
        `It had access to these document tools: ${accessed}.`,
        `The most useful evidence came from: ${used}.`,
      ],
      multimodal: [
        "Multimodal RAG did not search the text document database.",
        "It used the uploaded image directly and sent the image with your question to Claude Vision.",
        `The file analyzed was: ${used}.`,
        "The answer was generated from visible text, fields, forms, or layout information in the uploaded image.",
      ],
    };

    return explanations[activeTab] || [];
  };

  const handleSubmit = async () => {
    if (!question.trim()) {
      alert("Please enter a question.");
      return;
    }

    setLoading(true);
    setLoadingStep(0);
    setAnswer("");
    setSources([]);
    setAccessedDocuments([]);
    setSourceDocuments([]);

    try {
      const currentTab = tabs.find((tab) => tab.id === activeTab);

      let response;

      if (activeTab === "multimodal") {
        if (!selectedFile) {
          alert("Please upload an image file.");
          setLoading(false);
          return;
        }

        const formData = new FormData();
        formData.append("question", question);
        formData.append("file", selectedFile);

        response = await axios.post(
          `${API_BASE}${currentTab.route}`,
          formData,
          {
            headers: {
              "Content-Type": "multipart/form-data",
            },
          }
        );
      } else {
        response = await axios.post(`${API_BASE}${currentTab.route}`, {
          question,
        });
      }

      const responseAnswer = response.data.answer || "";
      const responseSources = response.data.sources || [];
      const responseAccessedDocuments = response.data.accessed_documents || [];
      const responseSourceDocuments = response.data.source_documents || [];

      setAnswer(responseAnswer);
      setSources(responseSources);
      setAccessedDocuments(responseAccessedDocuments);
      setSourceDocuments(responseSourceDocuments);

      saveToChatHistory({
        id: Date.now(),
        tabId: activeTab,
        tabLabel: currentTab.label,
        question,
        answer: responseAnswer,
        sources: responseSources,
        accessedDocuments: responseAccessedDocuments,
        sourceDocuments: responseSourceDocuments,
        createdAt: new Date().toLocaleString(),
      });
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
  const ragExplanation = getRagExplanation();

  return (
    <div className="app">
      <header className="header">
        <h1>ClinicOps AI Assistant</h1>
      </header>

      <section className="documents-card">
        <div className="documents-header">
          <div>
            <h2>Clinic Documents</h2>
            <p>View, create, upload, edit, and delete documents used by the RAG backend.</p>
          </div>

          <button className="refresh-btn" onClick={loadDocuments}>
            Refresh Documents
          </button>
        </div>

        <div className="upload-document-box">
          <div>
            <h3>Upload New Document</h3>
            <p>Add a .txt document or upload a PDF. PDFs will be converted into editable text.</p>
          </div>

          <div className="upload-document-actions">
            <input
              type="file"
              accept=".txt,.pdf"
              onChange={(e) => setUploadFile(e.target.files[0])}
            />

            <button
              className="upload-doc-btn"
              onClick={uploadNewDocument}
              disabled={docLoading}
            >
              {docLoading ? "Uploading..." : "Upload Document"}
            </button>
          </div>

          {uploadMessage && <p className="doc-message">{uploadMessage}</p>}
        </div>

        <div className="documents-layout">
          <div className="documents-list">
            <div className="documents-list-header">
              <h3>Available Documents</h3>

              <button className="new-doc-btn" onClick={startNewDocument}>
                + New
              </button>
            </div>

            {documents.length === 0 && (
              <p className="muted">No documents found.</p>
            )}

            {documents.map((doc) => (
              <div
                key={doc.filename}
                className={
                  selectedDocument === doc.filename
                    ? "doc-row active-doc-row"
                    : "doc-row"
                }
              >
                <button
                  className="doc-item"
                  onClick={() => loadDocumentContent(doc.filename)}
                >
                  {doc.filename}
                </button>

                <button
                  className="delete-doc-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteDocument(doc.filename);
                  }}
                  title="Delete document"
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          <div className="document-editor">
            <div className="editor-title-row">
              <h3>
                {isCreatingDocument
                  ? "Create New Document"
                  : selectedDocument
                  ? `Editing: ${selectedDocument}`
                  : "Select a document to view or edit"}
              </h3>

              {isCreatingDocument && (
                <button className="cancel-doc-btn" onClick={cancelNewDocument}>
                  Cancel
                </button>
              )}
            </div>

            {isCreatingDocument && (
              <div className="new-document-name-box">
                <label>Document File Name</label>
                <input
                  type="text"
                  value={newDocumentName}
                  onChange={(e) => setNewDocumentName(e.target.value)}
                  placeholder="example_policy.txt"
                />
              </div>
            )}

            <textarea
              className="document-textarea"
              value={documentContent}
              onChange={(e) => setDocumentContent(e.target.value)}
              placeholder={
                isCreatingDocument
                  ? "Start writing your new clinic policy document here..."
                  : "Document content will appear here..."
              }
              disabled={!selectedDocument && !isCreatingDocument}
            />

            <div className="document-actions">
              <button
                className="save-doc-btn"
                onClick={saveDocumentContent}
                disabled={(!selectedDocument && !isCreatingDocument) || docLoading}
              >
                {docLoading
                  ? "Working..."
                  : isCreatingDocument
                  ? "Save New Document"
                  : "Save Document"}
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

      <div className="workspace-grid">
        <main className="card">
          <div className="section-title">
            <h2>{currentTab.label}</h2>
            <p>Route: {currentTab.route}</p>
          </div>

          <div className="explain-box">
            <h3>{exerciseInfo[activeTab].title}</h3>

            <div className="pipeline-steps">
              {exerciseInfo[activeTab].steps.map((step, index) => (
                <div key={index} className="pipeline-step">
                  <span>{index + 1}</span>
                  <p>{step}</p>
                </div>
              ))}
            </div>
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

            {loading && (
              <div className="thinking-box">
                <div className="thinking-header">
                  <div className="spinner"></div>
                  <p>{loadingMessage[activeTab]}</p>
                </div>

                <div className="thinking-steps">
                  {(loadingSteps[activeTab] || []).map((step, index) => (
                    <div
                      key={index}
                      className={
                        index <= loadingStep
                          ? "thinking-step active-thinking-step"
                          : "thinking-step"
                      }
                    >
                      <span>
                        {index < loadingStep ? "✓" : index === loadingStep ? "•" : ""}
                      </span>
                      <p>{step}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="answer-text">
              {answer || (!loading ? "Answer will appear here..." : "")}
            </div>

            {ragExplanation && (
              <div className="rag-explanation-box">
                <h3>How RAG Got This Answer</h3>

                <div className="rag-explanation-steps">
                  {ragExplanation.map((step, index) => (
                    <div key={index} className="rag-explanation-step">
                      <span>{index + 1}</span>
                      <p>{step}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(accessedDocuments.length > 0 || sourceDocuments.length > 0) && (
              <div className="source-summary-box">
                {accessedDocuments.length > 0 && (
                  <div>
                    <h4>Documents Accessed</h4>
                    <div className="source-tags">
                      {accessedDocuments.map((doc) => (
                        <span key={doc}>{doc}</span>
                      ))}
                    </div>
                  </div>
                )}

                {sourceDocuments.length > 0 && (
                  <div>
                    <h4>Documents Used for Evidence</h4>
                    <div className="source-tags used-tags">
                      {sourceDocuments.map((doc) => (
                        <span key={doc}>{doc}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {sources.length > 0 && (
              <div className="sources-box">
                <h3>Retrieved Evidence</h3>

                {sources.map((source, index) => (
                  <div key={index} className="source-card">
                    <div className="source-card-header">
                      <strong>{source.document}</strong>
                      {source.score !== null && source.score !== undefined && (
                        <span>Score: {source.score}</span>
                      )}
                    </div>
                    <p>{source.excerpt}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>

        <aside className="history-card">
          <div className="history-header">
            <h2>Chat History</h2>
            <button onClick={clearChatHistory}>Clear</button>
          </div>

          {chatHistory.length === 0 && (
            <p className="muted">No questions asked yet.</p>
          )}

          <div className="history-list">
            {chatHistory.map((item) => (
              <button
                key={item.id}
                className="history-item"
                onClick={() => restoreHistoryItem(item)}
              >
                <span>{item.tabLabel}</span>
                <p>{item.question}</p>
                <small>{item.createdAt}</small>
              </button>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}

export default App;