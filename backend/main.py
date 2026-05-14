import os
import io
import re
import base64
import mimetypes
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader

from anthropic import Anthropic as AnthropicClient

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.tools import QueryEngineTool, FunctionTool
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.agent.workflow import ReActAgent


load_dotenv()

app = FastAPI(title="ClinicOps LlamaIndex Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://138.128.246.211",
        "http://138.128.246.211:8000",
        "http://ananya-clinicops.stackyon.com",
        "https://ananya-clinicops.stackyon.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data"
DATA_PATH.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY is missing in .env")

Settings.llm = Anthropic(
    model=ANTHROPIC_MODEL,
    api_key=ANTHROPIC_API_KEY,
)

Settings.embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

anthropic_client = AnthropicClient(api_key=ANTHROPIC_API_KEY)


class QueryRequest(BaseModel):
    question: str


class DocumentUpdateRequest(BaseModel):
    content: str


@app.get("/")
def home():
    return {
        "message": "ClinicOps LlamaIndex Backend is running",
        "available_routes": [
            "/health",
            "/exercises",
            "/documents",
            "/documents/{filename}",
            "/documents/upload",
            "/basic-rag/query",
            "/router-rag/query",
            "/subquestion-rag/query",
            "/react-agent/query",
            "/multi-doc-agent/query",
            "/multimodal-rag/query",
        ],
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "ClinicOps LlamaIndex backend is running successfully",
    }


@app.get("/exercises")
def list_exercises():
    return {
        "exercises": [
            {
                "id": 1,
                "name": "Basic RAG",
                "route": "/basic-rag/query",
                "description": "Searches all uploaded, created, and edited text documents.",
            },
            {
                "id": 2,
                "name": "Dynamic Router RAG",
                "route": "/router-rag/query",
                "description": "Routes the question to the most relevant document dynamically.",
            },
            {
                "id": 3,
                "name": "Dynamic SubQuestion RAG",
                "route": "/subquestion-rag/query",
                "description": "Classifies documents as relevant or not relevant, then checks relevant documents.",
            },
            {
                "id": 4,
                "name": "ReAct Agent",
                "route": "/react-agent/query",
                "description": "Uses document search, calculator, and general LLM knowledge when needed.",
            },
            {
                "id": 5,
                "name": "Dynamic Multi Document Agent",
                "route": "/multi-doc-agent/query",
                "description": "Creates a tool for every uploaded text document dynamically.",
            },
            {
                "id": 6,
                "name": "Multimodal RAG",
                "route": "/multimodal-rag/query",
                "description": "Analyzes uploaded images or PDFs. PDFs are also saved as extracted text.",
            },
        ]
    }


# ---------------------------------------------------------
# File and Document Helpers
# ---------------------------------------------------------

def clean_filename(filename: str) -> str:
    filename = filename.replace(" ", "_")
    filename = re.sub(r"[^a-zA-Z0-9_.-]", "", filename)
    return filename


def safe_document_path(filename: str) -> Path:
    filename = clean_filename(filename)
    file_path = (DATA_PATH / filename).resolve()

    if DATA_PATH.resolve() not in file_path.parents and file_path != DATA_PATH.resolve():
        raise HTTPException(status_code=400, detail="Invalid file path.")

    if file_path.suffix.lower() != ".txt":
        raise HTTPException(status_code=400, detail="Only editable .txt files are supported.")

    return file_path


def get_txt_files() -> List[Path]:
    if not DATA_PATH.exists():
        return []

    return sorted(
        file_path
        for file_path in DATA_PATH.glob("*.txt")
        if file_path.is_file()
    )


def get_all_document_names() -> List[str]:
    return [file_path.name for file_path in get_txt_files()]


def get_document_preview(file_path: Path, max_chars: int = 900) -> str:
    try:
        preview_text = file_path.read_text(encoding="utf-8", errors="ignore")
        preview_text = " ".join(preview_text.split())
        return preview_text[:max_chars]
    except Exception:
        return ""


def extract_pdf_text(file_bytes: bytes, max_pages: Optional[int] = None) -> str:
    pdf_reader = PdfReader(io.BytesIO(file_bytes))
    pages = pdf_reader.pages

    if max_pages is not None:
        pages = pages[:max_pages]

    extracted_pages = []

    for page_num, page in enumerate(pages, start=1):
        page_text = page.extract_text() or ""

        if page_text.strip():
            extracted_pages.append(f"\n--- Page {page_num} ---\n{page_text.strip()}")

    return "\n".join(extracted_pages).strip()


def save_pdf_as_extracted_txt(original_filename: str, file_bytes: bytes) -> Tuple[str, str]:
    cleaned_name = clean_filename(original_filename)
    pdf_stem = Path(cleaned_name).stem
    final_filename = f"{pdf_stem}_extracted.txt"

    content = extract_pdf_text(file_bytes)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from this PDF. It may be scanned/image-based.",
        )

    file_path = safe_document_path(final_filename)
    file_path.write_text(content, encoding="utf-8")

    return final_filename, content


# ---------------------------------------------------------
# Document Management APIs
# ---------------------------------------------------------

@app.get("/documents")
def list_documents():
    try:
        documents = [
            {
                "filename": file_path.name,
                "path": str(file_path),
            }
            for file_path in get_txt_files()
        ]

        documents.sort(key=lambda x: x["filename"])

        return {"documents": documents}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{filename}")
def get_document(filename: str):
    try:
        file_path = safe_document_path(filename)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document not found.")

        return {
            "filename": file_path.name,
            "content": file_path.read_text(encoding="utf-8", errors="ignore"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/documents/{filename}")
def update_document(filename: str, request: DocumentUpdateRequest):
    try:
        file_path = safe_document_path(filename)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document not found.")

        file_path.write_text(request.content, encoding="utf-8")

        return {
            "message": "Document updated successfully",
            "filename": file_path.name,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{filename}")
def delete_document(filename: str):
    try:
        file_path = safe_document_path(filename)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document not found.")

        file_path.unlink()

        return {
            "message": "Document deleted successfully",
            "filename": file_path.name,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        original_filename = file.filename

        if not original_filename:
            raise HTTPException(status_code=400, detail="Filename is missing.")

        cleaned_name = clean_filename(original_filename)
        suffix = Path(cleaned_name).suffix.lower()
        file_bytes = await file.read()

        if suffix == ".txt":
            try:
                content = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = file_bytes.decode("latin-1")

            final_filename = cleaned_name
            file_path = safe_document_path(final_filename)
            file_path.write_text(content, encoding="utf-8")

        elif suffix == ".pdf":
            final_filename, content = save_pdf_as_extracted_txt(original_filename, file_bytes)

        else:
            raise HTTPException(
                status_code=400,
                detail="Only .txt and .pdf files are supported.",
            )

        return {
            "message": "Document uploaded successfully",
            "original_filename": original_filename,
            "saved_as": final_filename,
            "size_bytes": len(file_bytes),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# Source Helpers
# ---------------------------------------------------------

def extract_sources_from_response(
    response,
    max_sources: int = 5,
    min_score: Optional[float] = None,
):
    sources = []
    seen = set()

    source_nodes = getattr(response, "source_nodes", []) or []

    for source_node in source_nodes:
        node = getattr(source_node, "node", None)

        if node is None:
            continue

        score = getattr(source_node, "score", None)

        if min_score is not None and score is not None and float(score) < min_score:
            continue

        metadata = getattr(node, "metadata", {}) or {}

        file_name = (
            metadata.get("file_name")
            or metadata.get("filename")
            or Path(metadata.get("file_path", "")).name
            or "Unknown document"
        )

        try:
            text = node.get_content()
        except Exception:
            text = getattr(node, "text", "")

        excerpt = " ".join((text or "").split())[:700]

        if not excerpt:
            continue

        key = f"{file_name}:{excerpt[:120]}"

        if key in seen:
            continue

        seen.add(key)

        sources.append(
            {
                "document": file_name,
                "score": round(float(score), 4) if score is not None else None,
                "excerpt": excerpt,
            }
        )

        if len(sources) >= max_sources:
            break

    return sources


def unique_documents_from_sources(sources: List[Dict[str, Any]]) -> List[str]:
    documents = []

    for source in sources:
        document = source.get("document")

        if document and document not in documents:
            documents.append(document)

    return documents


def general_llm_source():
    return [
        {
            "document": "General LLM knowledge",
            "score": None,
            "excerpt": (
                "The ReAct agent answered using the LLM's general knowledge because "
                "the uploaded documents did not contain strong matching evidence for this question."
            ),
        }
    ]


def clean_final_answer_prompt(question: str, raw_answer: str) -> str:
    return f"""
User question:
{question}

Raw answer:
{raw_answer}

Rewrite the answer in clean, professional plain English.

Rules:
- Do not use markdown tables.
- Do not use # headings.
- Do not use **bold markdown**.
- Do not use unnecessary symbols.
- Keep the answer concise and clear.
"""


# ---------------------------------------------------------
# Relevance Classification
# ---------------------------------------------------------

def classify_document_relevance(question: str, file_path: Path) -> dict:
    """
    Generic relevance classifier.
    No hardcoded document types.
    It decides relevance only from the user question, document name, and document preview.
    """
    try:
        preview = get_document_preview(file_path, max_chars=1200)

        prompt = f"""
User question:
{question}

Document name:
{file_path.name}

Document preview:
{preview}

Decide if this document is relevant for answering the user's question.

Return exactly in this format:
Label: Relevant or Not Relevant
Reason: one short sentence

Rules:
- Mark Relevant only if this document can directly help answer the user's specific question.
- Mark Not Relevant if this document does not contain useful information for this specific question.
- Do not mark a document relevant just because it shares one broad or generic word with the question.
- Do not use the document as evidence unless it provides meaningful support for the answer.
- Classify based only on the user question, document name, and document preview.
"""

        response = Settings.llm.complete(prompt)
        text = str(response).strip()
        lower_text = text.lower()

        if "label: not relevant" in lower_text:
            label = "Not Relevant"
        elif "label: relevant" in lower_text:
            label = "Relevant"
        else:
            label = "Not Relevant"

        reason = ""

        for line in text.splitlines():
            if line.lower().startswith("reason:"):
                reason = line.split(":", 1)[1].strip()
                break

        if not reason:
            reason = text[:250]

        return {
            "document": file_path.name,
            "label": label,
            "reason": reason,
        }

    except Exception as e:
        return {
            "document": file_path.name,
            "label": "Not Relevant",
            "reason": f"Could not classify relevance: {str(e)}",
        }


def classify_all_documents(question: str):
    relevance_results = []
    relevant_files = []
    irrelevant_documents = []

    for file_path in get_txt_files():
        relevance = classify_document_relevance(question, file_path)
        relevance_results.append(relevance)

        if relevance["label"] == "Relevant":
            relevant_files.append(file_path)
        else:
            irrelevant_documents.append(
                {
                    "document": file_path.name,
                    "reason": relevance["reason"],
                }
            )

    return relevance_results, relevant_files, irrelevant_documents


# ---------------------------------------------------------
# Query Engine Helpers
# ---------------------------------------------------------

def build_query_engine_from_files(files: List[Path], similarity_top_k: int = 3):
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No relevant documents found.")

        documents = SimpleDirectoryReader(
            input_files=[str(file_path) for file_path in files]
        ).load_data()

        if not documents:
            raise HTTPException(status_code=400, detail="No readable documents found.")

        index = VectorStoreIndex.from_documents(documents)
        return index.as_query_engine(similarity_top_k=similarity_top_k)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def build_single_file_query_engine(file_path: Path):
    return build_query_engine_from_files([file_path], similarity_top_k=3)


def build_basic_rag_engine():
    """
    Reads only clean .txt files.
    Raw PDFs are not indexed directly.
    PDFs are converted into *_extracted.txt during upload.
    """
    return build_query_engine_from_files(get_txt_files(), similarity_top_k=3)


# ---------------------------------------------------------
# Dynamic Router Tools
# ---------------------------------------------------------

def build_router_tools():
    try:
        tools = []

        txt_files = get_txt_files()

        if not txt_files:
            raise HTTPException(status_code=400, detail="No .txt documents found.")

        for file_path in txt_files:
            document_engine = build_single_file_query_engine(file_path)

            tool_name = file_path.stem.replace("-", "_").replace(" ", "_")
            tool_name = re.sub(r"[^a-zA-Z0-9_]", "_", tool_name)

            preview_text = get_document_preview(file_path)

            description = f"""
Use this tool only when the user question is related to this uploaded document.

Document name:
{file_path.name}

Document preview:
{preview_text}

Choose this tool only if the document name or preview contains meaningful information
that can help answer the user's specific question.
Do not choose this tool only because of a broad or generic word overlap.
"""

            document_tool = QueryEngineTool.from_defaults(
                query_engine=document_engine,
                name=f"{tool_name}_router_tool",
                description=description,
            )

            tools.append(document_tool)

        return tools

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# Exercise 1: Basic RAG
# ---------------------------------------------------------

@app.post("/basic-rag/query")
def basic_rag_query(request: QueryRequest):
    try:
        query_engine = build_basic_rag_engine()
        response = query_engine.query(request.question)

        clean_response = Settings.llm.complete(
            clean_final_answer_prompt(request.question, str(response))
        )

        sources = extract_sources_from_response(response)

        return {
            "exercise": "Basic RAG",
            "question": request.question,
            "answer": str(clean_response),
            "accessed_documents": get_all_document_names(),
            "source_documents": unique_documents_from_sources(sources),
            "sources": sources,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# Exercise 2: Dynamic Router RAG
# ---------------------------------------------------------

@app.post("/router-rag/query")
def router_rag_query(request: QueryRequest):
    try:
        tools = build_router_tools()

        router_engine = RouterQueryEngine(
            selector=LLMSingleSelector.from_defaults(),
            query_engine_tools=tools,
        )

        response = router_engine.query(request.question)

        clean_response = Settings.llm.complete(
            clean_final_answer_prompt(request.question, str(response))
        )

        sources = extract_sources_from_response(response)

        return {
            "exercise": "Dynamic Router RAG",
            "question": request.question,
            "answer": str(clean_response),
            "accessed_documents": unique_documents_from_sources(sources),
            "source_documents": unique_documents_from_sources(sources),
            "sources": sources,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# Exercise 3: Dynamic SubQuestion RAG with Generic Relevance Filtering
# ---------------------------------------------------------

def build_custom_subquestion_response(question: str):
    try:
        txt_files = get_txt_files()

        if not txt_files:
            raise HTTPException(status_code=400, detail="No .txt documents found.")

        relevance_results, relevant_files, irrelevant_documents = classify_all_documents(question)

        sub_answers = {}
        all_sources = []
        relevant_documents = []

        for file_path in relevant_files:
            relevant_documents.append(file_path.name)

            try:
                engine = build_single_file_query_engine(file_path)

                doc_question = f"""
User question:
{question}

Use only this document:
{file_path.name}

Document preview:
{get_document_preview(file_path, max_chars=700)}

Instructions:
- Answer briefly using only this document.
- If this document does not actually contain useful evidence, say exactly: Not relevant.
"""

                doc_response = engine.query(doc_question)
                doc_answer = str(doc_response).strip()

                if "not relevant" in doc_answer.lower():
                    irrelevant_documents.append(
                        {
                            "document": file_path.name,
                            "reason": "The document was initially classified as relevant but did not provide useful answer evidence.",
                        }
                    )
                    continue

                sub_answers[file_path.name] = doc_answer

                sources = extract_sources_from_response(
                    doc_response,
                    max_sources=2,
                    min_score=0.25,
                )

                if sources:
                    all_sources.extend(sources)

            except Exception as e:
                sub_answers[file_path.name] = f"Error checking document: {str(e)}"

        if not sub_answers:
            final_answer = f"""
I checked the uploaded documents, but none of them were relevant enough to answer this question.

Document relevance results:
{relevance_results}
"""
        else:
            synthesis_prompt = f"""
User question:
{question}

Relevant document-level answers:
{sub_answers}

Documents classified as not relevant:
{irrelevant_documents}

Create one final answer.

Rules:
- Use only the relevant document-level answers as evidence.
- Clearly mention which documents were relevant.
- Clearly mention which documents were not relevant if the user asks about relevance.
- Do not use irrelevant documents as evidence.
- Do not use markdown tables.
- Do not use # headings.
- Keep it clear and concise.
"""

            final_response = Settings.llm.complete(synthesis_prompt)
            final_answer = str(final_response)

        return {
            "sub_answers": sub_answers,
            "final_answer": final_answer,
            "sources": all_sources,
            "accessed_documents": relevant_documents,
            "relevant_documents": relevant_documents,
            "irrelevant_documents": irrelevant_documents,
            "relevance_results": relevance_results,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/subquestion-rag/query")
def subquestion_rag_query(request: QueryRequest):
    try:
        result = build_custom_subquestion_response(request.question)

        clean_response = Settings.llm.complete(
            clean_final_answer_prompt(request.question, result["final_answer"])
        )

        sources = result["sources"]

        return {
            "exercise": "Dynamic SubQuestion RAG",
            "question": request.question,
            "sub_answers": result["sub_answers"],
            "answer": str(clean_response),
            "accessed_documents": result["relevant_documents"],
            "source_documents": unique_documents_from_sources(sources),
            "relevant_documents": result["relevant_documents"],
            "irrelevant_documents": result["irrelevant_documents"],
            "relevance_results": result["relevance_results"],
            "sources": sources,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# Exercise 4: ReAct Agent
# ---------------------------------------------------------

def calculate_patient_payment(total_fee: float, insurance_coverage_percent: float) -> str:
    patient_percent = 100 - insurance_coverage_percent
    patient_payment = total_fee * (patient_percent / 100)

    return (
        f"Total fee: ${total_fee:.2f}. "
        f"Insurance covers {insurance_coverage_percent:.1f}%. "
        f"Patient responsibility is {patient_percent:.1f}%, "
        f"so the patient pays ${patient_payment:.2f}."
    )


def general_llm_answer(question: str) -> str:
    prompt = f"""
User question:
{question}

Answer using your general knowledge.

Rules:
- Clearly say this answer is based on general LLM knowledge, not uploaded documents.
- Do not claim to access live internet.
- If the question needs current/live facts, say that a live API or web search tool would be needed.
- Keep it concise and clear.
"""

    response = Settings.llm.complete(prompt)
    return str(response)


async def build_react_agent_response(question: str):
    try:
        tools = []

        txt_files = get_txt_files()

        if txt_files:
            document_query_engine = build_basic_rag_engine()

            uploaded_document_search_tool = QueryEngineTool.from_defaults(
                query_engine=document_query_engine,
                name="uploaded_document_search",
                description=(
                    "Use this tool only when the answer may be found in uploaded, created, or edited documents. "
                    "Uploaded PDFs are available only after being extracted into text documents."
                ),
            )

            tools.append(uploaded_document_search_tool)
        else:
            document_query_engine = None

        payment_calculator_tool = FunctionTool.from_defaults(
            fn=calculate_patient_payment,
            name="patient_payment_calculator",
            description=(
                "Use this tool to calculate patient payment. "
                "Inputs should include total_fee and insurance_coverage_percent."
            ),
        )

        general_knowledge_tool = FunctionTool.from_defaults(
            fn=general_llm_answer,
            name="general_llm_knowledge",
            description=(
                "Use this tool when uploaded documents do not contain enough information "
                "or when the question is general knowledge. This does not access live internet."
            ),
        )

        tools.extend([payment_calculator_tool, general_knowledge_tool])

        agent = ReActAgent(
            tools=tools,
            llm=Settings.llm,
        )

        agent_question = f"""
User question:
{question}

You can use:
1. uploaded_document_search if the answer may be in uploaded documents,
2. patient_payment_calculator for payment calculations,
3. general_llm_knowledge when uploaded documents do not contain enough information.

Important:
- Do not restrict yourself to one domain.
- Uploaded documents can be about any topic.
- If you use general knowledge, say it is based on general LLM knowledge.
- Do not claim live internet access.
- For live/current information, say a live API or web search tool would be needed.
- Answer in clean professional plain English.
- Do not use markdown tables, # headings, or **bold markdown**.
"""

        response = await agent.run(agent_question)

        clean_response = Settings.llm.complete(
            clean_final_answer_prompt(question, str(response))
        )

        sources = []

        if txt_files and document_query_engine is not None:
            relevance_results, relevant_files, _ = classify_all_documents(question)

            if relevant_files:
                for file_path in relevant_files:
                    try:
                        engine = build_single_file_query_engine(file_path)
                        source_probe_response = engine.query(question)
                        file_sources = extract_sources_from_response(
                            source_probe_response,
                            max_sources=1,
                            min_score=0.30,
                        )
                        sources.extend(file_sources)
                    except Exception:
                        continue

        if not sources:
            sources = general_llm_source()

        return {
            "answer": str(clean_response),
            "sources": sources,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/react-agent/query")
async def react_agent_query(request: QueryRequest):
    try:
        result = await build_react_agent_response(request.question)

        return {
            "exercise": "ReAct Agent",
            "question": request.question,
            "answer": result["answer"],
            "accessed_documents": get_all_document_names(),
            "source_documents": unique_documents_from_sources(result["sources"]),
            "sources": result["sources"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# Exercise 5: Dynamic Multi Document Agent
# ---------------------------------------------------------

def build_dynamic_document_tools():
    try:
        tools = []
        txt_files = get_txt_files()

        if not txt_files:
            raise HTTPException(status_code=400, detail="No .txt documents found.")

        for file_path in txt_files:
            document_engine = build_single_file_query_engine(file_path)

            tool_name = file_path.stem.replace("-", "_").replace(" ", "_")
            tool_name = re.sub(r"[^a-zA-Z0-9_]", "_", tool_name)

            preview_text = get_document_preview(file_path)

            document_tool = QueryEngineTool.from_defaults(
                query_engine=document_engine,
                name=f"{tool_name}_document_tool",
                description=f"""
Use this tool only when the user question is related to the document named {file_path.name}.

Document preview:
{preview_text}

Choose this tool only when the document provides meaningful support for the user's specific question.
""",
            )

            tools.append(document_tool)

        return tools

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def collect_sources_from_relevant_documents(question: str):
    all_sources = []
    accessed_documents = []

    _, relevant_files, _ = classify_all_documents(question)

    for file_path in relevant_files:
        accessed_documents.append(file_path.name)

        try:
            engine = build_single_file_query_engine(file_path)
            response = engine.query(question)
            sources = extract_sources_from_response(response, max_sources=1, min_score=0.25)
            all_sources.extend(sources)
        except Exception:
            continue

    return accessed_documents, all_sources


async def build_multi_doc_agent_response(question: str):
    try:
        relevance_results, relevant_files, irrelevant_documents = classify_all_documents(question)

        if not relevant_files:
            return {
                "answer": "I checked the uploaded documents, but none of them were relevant enough to answer this question.",
                "accessed_documents": [],
                "sources": [],
                "relevant_documents": [],
                "irrelevant_documents": irrelevant_documents,
                "relevance_results": relevance_results,
            }

        tools = []

        for file_path in relevant_files:
            document_engine = build_single_file_query_engine(file_path)

            tool_name = file_path.stem.replace("-", "_").replace(" ", "_")
            tool_name = re.sub(r"[^a-zA-Z0-9_]", "_", tool_name)

            preview_text = get_document_preview(file_path)

            document_tool = QueryEngineTool.from_defaults(
                query_engine=document_engine,
                name=f"{tool_name}_document_tool",
                description=f"""
Use this tool only when the user question is related to this document.

Document name:
{file_path.name}

Document preview:
{preview_text}
""",
            )

            tools.append(document_tool)

        agent = ReActAgent(
            tools=tools,
            llm=Settings.llm,
        )

        clean_question = f"""
User question:
{question}

Answer clearly in plain English.

Rules:
- Use only the relevant document tools.
- Mention which documents were useful.
- Do not use unrelated documents as evidence.
- If the user asks which documents are irrelevant, mention the irrelevant documents separately.
- Do not use markdown tables.
- Do not use # headings.
- Do not use **bold markdown**.
- Keep the answer concise and professional.

Documents classified as not relevant:
{irrelevant_documents}
"""

        response = await agent.run(clean_question)

        clean_response = Settings.llm.complete(
            clean_final_answer_prompt(question, str(response))
        )

        accessed_documents, sources = collect_sources_from_relevant_documents(question)

        return {
            "answer": str(clean_response),
            "accessed_documents": accessed_documents,
            "sources": sources,
            "relevant_documents": [file_path.name for file_path in relevant_files],
            "irrelevant_documents": irrelevant_documents,
            "relevance_results": relevance_results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/multi-doc-agent/query")
async def multi_doc_agent_query(request: QueryRequest):
    try:
        result = await build_multi_doc_agent_response(request.question)

        return {
            "exercise": "Dynamic Multi Document Agent",
            "question": request.question,
            "answer": result["answer"],

            "accessed_documents": result["accessed_documents"],
            "source_documents": unique_documents_from_sources(result["sources"]),
            "sources": result["sources"],

            "relevant_documents": result["relevant_documents"],
            "irrelevant_documents": result["irrelevant_documents"],
            "relevance_results": result["relevance_results"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# Exercise 6: Multimodal RAG
# ---------------------------------------------------------

@app.post("/multimodal-rag/query")
async def multimodal_rag_query(
    question: str = Form(...),
    file: UploadFile = File(...),
):
    try:
        file_bytes = await file.read()

        mime_type = file.content_type

        if not mime_type:
            mime_type = mimetypes.guess_type(file.filename)[0]

        filename = file.filename or "uploaded_file"

        if mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
            pdf_text = extract_pdf_text(file_bytes, max_pages=10)

            if not pdf_text:
                raise HTTPException(
                    status_code=400,
                    detail="Could not extract readable text from this PDF. It may be scanned/image-based.",
                )

            saved_as, full_pdf_text = save_pdf_as_extracted_txt(filename, file_bytes)

            prompt = f"""
You are a document analysis assistant.

The user uploaded a PDF document.

User question:
{question}

PDF text:
{pdf_text}

Answer clearly in clean plain English.

Formatting rules:
- Do not use markdown headings.
- Do not use #, **, or ---.
- Use short bullet points only if needed.
- Keep the answer concise and easy to read.
- If the PDF does not contain enough information, say what is missing.
"""

            response = anthropic_client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            answer_parts = []

            for block in response.content:
                if hasattr(block, "text"):
                    answer_parts.append(block.text)

            answer = "\n".join(answer_parts)

            clean_response = Settings.llm.complete(
                clean_final_answer_prompt(question, answer)
            )

            return {
                "exercise": "Multimodal RAG",
                "filename": filename,
                "saved_as": saved_as,
                "mime_type": "application/pdf",
                "question": question,
                "answer": str(clean_response),
                "accessed_documents": [saved_as],
                "source_documents": [saved_as],
                "sources": [
                    {
                        "document": saved_as,
                        "score": None,
                        "excerpt": full_pdf_text[:900],
                    }
                ],
            }

        if not mime_type:
            mime_type = "image/png"

        if not mime_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Please upload an image or PDF file.",
            )

        encoded_image = base64.b64encode(file_bytes).decode("utf-8")

        prompt = f"""
You are a document analysis assistant.

The user uploaded an image.

User question:
{question}

Carefully inspect the image and answer in clean plain English.

Formatting rules:
- Do not use markdown headings.
- Do not use #, **, or ---.
- Use short bullet points only if needed.
- Keep the answer concise and easy to read.
- If the image has multiple sections, summarize them clearly.
"""

        response = anthropic_client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=700,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": encoded_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )

        answer_parts = []

        for block in response.content:
            if hasattr(block, "text"):
                answer_parts.append(block.text)

        answer = "\n".join(answer_parts)

        clean_response = Settings.llm.complete(
            clean_final_answer_prompt(question, answer)
        )

        return {
            "exercise": "Multimodal RAG",
            "filename": filename,
            "mime_type": mime_type,
            "question": question,
            "answer": str(clean_response),
            "accessed_documents": [filename],
            "source_documents": [filename],
            "sources": [
                {
                    "document": filename,
                    "score": None,
                    "excerpt": "This answer was generated from the uploaded image file.",
                }
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))