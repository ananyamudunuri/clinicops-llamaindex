# ClinicOps LlamaIndex AI Assistant

ClinicOps AI Assistant is a healthcare operations demo application built with FastAPI, React, LlamaIndex, and Claude. The project demonstrates multiple RAG and agent workflows for answering questions from clinic policy documents, uploaded PDFs, editable text files, and uploaded images.

## Project Overview

This application is designed for clinic administrative workflows such as appointment policies, billing rules, insurance requirements, document review, and multimodal document understanding.

The system allows users to:

- Upload `.txt` and `.pdf` documents
- Convert PDFs into editable text
- Create new documents directly from the frontend
- Edit and save existing documents
- Delete documents from the knowledge base
- Ask questions using different RAG and agent workflows
- View which documents were accessed by the RAG system
- View retrieved evidence used to generate the answer
- See an explanation of how the RAG workflow produced the answer
- Use chat history to revisit previous questions and responses
- Upload images for multimodal analysis using Claude Vision

## Tech Stack

### Backend

- FastAPI
- Python
- LlamaIndex
- Anthropic Claude
- Claude Vision
- pypdf
- Uvicorn

### Frontend

- React
- Vite
- Axios
- CSS

## Features

### 1. Basic RAG

Basic RAG reads all clinic documents from the `data/` folder, builds a searchable knowledge base, retrieves relevant chunks, and sends the retrieved context to Claude to generate an answer.

### 2. Router RAG

Router RAG routes the user question to the most relevant policy area, such as appointment, billing, or insurance, before generating the answer.

### 3. SubQuestion RAG

SubQuestion RAG checks appointment, billing, and insurance policies separately, then combines the useful responses into one final answer.

### 4. ReAct Agent

The ReAct Agent can decide which tool to use, such as document search, calculator logic, or policy summary tools.

### 5. Multi Document Agent

The Multi Document Agent treats every uploaded `.txt` document as a separate searchable tool. This allows the agent to compare multiple documents and identify which ones are relevant to the user’s question.

### 6. Multimodal RAG

Multimodal RAG allows the user to upload an image, such as a form, insurance card, or document screenshot. Claude Vision reads the image and answers questions about the visible content.

## Document Management

The frontend includes a document management panel where users can:

- Upload `.txt` files
- Upload `.pdf` files
- Convert PDFs into editable `.txt` files
- Create new text documents
- Edit existing documents
- Save document changes
- Delete documents
- Refresh the document list

Uploaded and created documents are stored in the backend `data/` folder.

## Source Tracking

After each answer, the app shows:

- Documents accessed
- Documents used as evidence
- Retrieved evidence chunks
- Similarity score, when available
- Explanation of how the RAG workflow generated the answer

This helps make the RAG output more transparent and easier to trust.

## Chat History

The frontend stores recent chat history in the browser session. Users can click a previous question to restore the answer, sources, and evidence.

## Project Structure

```text
clinicops-llamaindex/
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── .env
│
├── data/
│   ├── appointment_policy.txt
│   ├── billing_policy.txt
│   ├── clinic_policy.txt
│   └── insurance_policy.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
└── README.md
```

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/ananyamudunuri/clinicops-llamaindex.git
cd clinicops-llamaindex
```

### 2. Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Create `.env` file inside `backend/`

```bash
touch .env
```

Add the following:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-sonnet-4-6
```

### 5. Run backend

```bash
python -m uvicorn main:app --reload
```

Backend runs at:

```text
http://127.0.0.1:8000
```

Swagger API docs:

```text
http://127.0.0.1:8000/docs
```

### 6. Run frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

```text
http://localhost:5173
```

## API Routes

### Health Check

```text
GET /health
```

### Document APIs

```text
GET /documents
GET /documents/{filename}
PUT /documents/{filename}
DELETE /documents/{filename}
POST /documents/upload
```

### RAG and Agent APIs

```text
POST /basic-rag/query
POST /router-rag/query
POST /subquestion-rag/query
POST /react-agent/query
POST /multi-doc-agent/query
POST /multimodal-rag/query
```

## Example Questions

### Basic RAG

```text
What happens if a patient cancels less than 24 hours before the appointment?
```

### Router RAG

```text
Does the clinic accept Medicaid?
```

### SubQuestion RAG

```text
Compare appointment cancellation and billing fee policy.
```

### ReAct Agent

```text
If the consultation fee is 120 dollars and insurance covers 70 percent, how much does the patient pay?
```

### Multi Document Agent

```text
Which documents are irrelevant to the clinic policy knowledge base, and what do they contain?
```

### Multimodal RAG

```text
What information is visible in this document?
```

## How Each RAG Workflow Works

### Basic RAG

Basic RAG uses all available text documents in the backend `data/` folder as one combined knowledge base.

Workflow:

```text
Documents
→ Chunking
→ Vector index
→ Similarity search
→ Retrieved context
→ Claude answer
```

### Router RAG

Router RAG first identifies which policy area best matches the user question.

Workflow:

```text
Question
→ Router decision
→ Appointment, Billing, or Insurance document
→ Retrieved context
→ Claude answer
```

### SubQuestion RAG

SubQuestion RAG sends the question to multiple policy documents separately, then combines the results.

Workflow:

```text
Question
→ Appointment policy check
→ Billing policy check
→ Insurance policy check
→ Combined final answer
```

### ReAct Agent

The ReAct Agent decides which tool to use based on the question.

Available tools include:

- Clinic policy search
- Patient payment calculator
- Policy summary tool

Workflow:

```text
Question
→ Agent reasoning
→ Tool selection
→ Tool execution
→ Final answer
```

### Multi Document Agent

The Multi Document Agent converts every uploaded `.txt` file into a separate document tool.

Workflow:

```text
Uploaded documents
→ One tool per document
→ Agent chooses relevant tools
→ Agent searches selected documents
→ Final answer
```

### Multimodal RAG

Multimodal RAG uses the uploaded image directly.

Workflow:

```text
Image upload
→ Claude Vision reads image
→ Question is applied to visible content
→ Final answer
```

## Source Tracking and RAG Explanation

The app includes source tracking after each answer.

For each response, the frontend can display:

```text
Answer
How RAG Got This Answer
Documents Accessed
Documents Used for Evidence
Retrieved Evidence
```

This makes the system more explainable and helps the user understand why the model gave a specific answer.

## Why an Uploaded Document May Not Override Other Documents

If a new document says something like:

```text
Ignore other documents and use this one.
```

the RAG system may still retrieve other documents if they are more relevant to the user question.

This is because RAG does not automatically treat the newest document as the highest-priority source. It retrieves content based on relevance. If multiple documents mention cancellations, fees, or appointment policies, the retriever may pull evidence from those existing documents.

A better production improvement would be to add:

- Document priority
- Document tagging
- Active/inactive document toggle
- Conflict detection
- User-selected document scope
- Rule that newer documents override older documents

## Render Deployment Note

The frontend can be deployed as a Render Static Site.

The backend can be deployed as a Render Web Service, but the free Render instance may run out of memory if heavy embedding dependencies such as `torch`, `transformers`, or `sentence-transformers` are used.

Current deployment blocker:

```text
The backend runs locally, but Render free tier may fail because LlamaIndex and embedding-related dependencies can exceed the 512MB memory limit.
```

Possible deployment fixes:

- Use a lighter embedding setup
- Use LlamaIndex MockEmbedding for demo deployment
- Use OpenAI or external embedding APIs
- Deploy backend on a higher-memory Render plan
- Deploy backend on Cloud Run, Railway, Fly.io, or another service with more memory

## Running Locally Instead of Render

The app can be tested locally with:

Backend:

```bash
cd backend
source ../venv/bin/activate
python -m uvicorn main:app --reload
```

Frontend:

```bash
cd frontend
npm run dev
```

Local URLs:

```text
Backend: http://127.0.0.1:8000
Frontend: http://localhost:5173
```

## Current Status

The app is working locally with:

- Backend running on FastAPI
- Frontend running on React/Vite
- Editable document management
- PDF upload and text extraction
- Multiple RAG workflows
- Source tracking
- Retrieved evidence display
- Chat history
- RAG explanation after each answer

Render deployment is in progress, with backend memory usage being the main blocker on the free tier.

## Future Improvements

- Add persistent database storage for chat history
- Store uploaded documents in cloud storage
- Add user authentication
- Add document category tagging
- Add irrelevant document detection button
- Add document priority and versioning
- Add user-selected document scope
- Add conflict detection between policies
- Add better production-grade embedding model
- Add vector database support using Pinecone, Chroma, or Supabase
- Improve deployment using Cloud Run or higher-memory hosting

## Demo Summary

ClinicOps AI Assistant demonstrates how LlamaIndex and Claude can be used to build a healthcare administrative AI assistant that can search documents, route questions, compare multiple policies, use agent tools, process uploaded images, and explain how each answer was generated.
