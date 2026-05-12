import os
import io
import re
import base64
import mimetypes
from pathlib import Path

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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data"
DATA_DIR = str(DATA_PATH)

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

anthropic_client = AnthropicClient(
    api_key=ANTHROPIC_API_KEY
)


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
                "description": "Answers questions from all clinic documents using vector search.",
            },
            {
                "id": 2,
                "name": "Router Query Engine",
                "route": "/router-rag/query",
                "description": "Routes the question to appointment, billing, or insurance policy.",
            },
            {
                "id": 3,
                "name": "SubQuestion RAG",
                "route": "/subquestion-rag/query",
                "description": "Checks multiple policy documents and combines the answer.",
            },
            {
                "id": 4,
                "name": "ReAct Agent",
                "route": "/react-agent/query",
                "description": "Uses tools like document search, calculator, and policy summarizer.",
            },
            {
                "id": 5,
                "name": "Dynamic Multi Document Agent",
                "route": "/multi-doc-agent/query",
                "description": "Automatically creates tools from every .txt document in the data folder.",
            },
            {
                "id": 6,
                "name": "Multimodal RAG",
                "route": "/multimodal-rag/query",
                "description": "Reads uploaded images like forms, insurance cards, and workflow diagrams.",
            },
        ]
    }


# ---------------------------------------------------------
# Document Management APIs
# ---------------------------------------------------------

ALLOWED_DOC_EXTENSIONS = [".txt"]


def clean_filename(filename: str) -> str:
    filename = filename.replace(" ", "_")
    filename = re.sub(r"[^a-zA-Z0-9_.-]", "", filename)
    return filename


def safe_document_path(filename: str) -> Path:
    filename = clean_filename(filename)
    file_path = (DATA_PATH / filename).resolve()

    if DATA_PATH.resolve() not in file_path.parents and file_path != DATA_PATH.resolve():
        raise HTTPException(status_code=400, detail="Invalid file path")

    if file_path.suffix not in ALLOWED_DOC_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only editable .txt files are supported")

    return file_path


def get_all_document_names():
    if not DATA_PATH.exists():
        return []

    return sorted(
        [
            file_path.name
            for file_path in DATA_PATH.iterdir()
            if file_path.is_file() and file_path.suffix == ".txt"
        ]
    )


@app.get("/documents")
def list_documents():
    try:
        documents = []

        if not DATA_PATH.exists():
            DATA_PATH.mkdir(parents=True, exist_ok=True)

        for file_path in DATA_PATH.iterdir():
            if file_path.is_file() and file_path.suffix == ".txt":
                documents.append(
                    {
                        "filename": file_path.name,
                        "path": str(file_path),
                    }
                )

        documents.sort(key=lambda x: x["filename"])

        return {"documents": documents}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{filename}")
def get_document(filename: str):
    try:
        file_path = safe_document_path(filename)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document not found")

        content = file_path.read_text(encoding="utf-8")

        return {
            "filename": filename,
            "content": content,
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
            raise HTTPException(status_code=404, detail="Document not found")

        file_path.write_text(request.content, encoding="utf-8")

        return {
            "message": "Document updated successfully",
            "filename": filename,
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
            raise HTTPException(status_code=404, detail="Document not found")

        file_path.unlink()

        return {
            "message": "Document deleted successfully",
            "filename": filename,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        if not DATA_PATH.exists():
            DATA_PATH.mkdir(parents=True, exist_ok=True)

        original_filename = file.filename

        if not original_filename:
            raise HTTPException(status_code=400, detail="Filename is missing")

        cleaned_name = clean_filename(original_filename)
        suffix = Path(cleaned_name).suffix.lower()

        file_bytes = await file.read()

        if suffix == ".txt":
            try:
                content = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = file_bytes.decode("latin-1")

            final_filename = cleaned_name

        elif suffix == ".pdf":
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            extracted_pages = []

            for page_num, page in enumerate(pdf_reader.pages, start=1):
                page_text = page.extract_text() or ""
                extracted_pages.append(f"\n--- Page {page_num} ---\n{page_text}")

            content = "\n".join(extracted_pages).strip()

            if not content:
                raise HTTPException(
                    status_code=400,
                    detail="Could not extract text from this PDF. It may be scanned/image-based.",
                )

            pdf_stem = Path(cleaned_name).stem
            final_filename = f"{pdf_stem}_extracted.txt"

        else:
            raise HTTPException(
                status_code=400,
                detail="Only .txt and .pdf files are supported.",
            )

        file_path = safe_document_path(final_filename)
        file_path.write_text(content, encoding="utf-8")

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
# Source Tracking Helpers
# ---------------------------------------------------------

def extract_sources_from_response(response, max_sources: int = 5):
    sources = []
    seen = set()

    source_nodes = getattr(response, "source_nodes", []) or []

    for source_node in source_nodes:
        node = getattr(source_node, "node", None)
        if node is None:
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

        excerpt = " ".join((text or "").split())
        excerpt = excerpt[:700]

        if not excerpt:
            continue

        key = f"{file_name}:{excerpt[:120]}"

        if key in seen:
            continue

        seen.add(key)

        score = getattr(source_node, "score", None)

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


def unique_documents_from_sources(sources):
    documents = []

    for source in sources:
        document = source.get("document")

        if document and document not in documents:
            documents.append(document)

    return documents


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
# Helper Functions
# ---------------------------------------------------------

def build_single_file_query_engine(file_path: str):
    try:
        documents = SimpleDirectoryReader(input_files=[file_path]).load_data()

        if not documents:
            raise HTTPException(
                status_code=400,
                detail=f"No documents found in file: {file_path}",
            )

        index = VectorStoreIndex.from_documents(documents)
        return index.as_query_engine(similarity_top_k=3)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def build_policy_tools():
    appointment_engine = build_single_file_query_engine(
        str(DATA_PATH / "appointment_policy.txt")
    )

    billing_engine = build_single_file_query_engine(
        str(DATA_PATH / "billing_policy.txt")
    )

    insurance_engine = build_single_file_query_engine(
        str(DATA_PATH / "insurance_policy.txt")
    )

    appointment_tool = QueryEngineTool.from_defaults(
        query_engine=appointment_engine,
        name="appointment_policy",
        description=(
            "Useful for questions about appointments, cancellations, "
            "rescheduling, no-shows, and patient arrival time."
        ),
    )

    billing_tool = QueryEngineTool.from_defaults(
        query_engine=billing_engine,
        name="billing_policy",
        description=(
            "Useful for questions about billing, fees, payment plans, "
            "out-of-pocket costs, and billing support."
        ),
    )

    insurance_tool = QueryEngineTool.from_defaults(
        query_engine=insurance_engine,
        name="insurance_policy",
        description=(
            "Useful for questions about insurance, Medicaid, prior authorization, "
            "coverage, and plan networks."
        ),
    )

    return [appointment_tool, billing_tool, insurance_tool]


# ---------------------------------------------------------
# Exercise 1: Basic RAG
# ---------------------------------------------------------

def build_basic_rag_engine():
    try:
        documents = SimpleDirectoryReader(DATA_DIR).load_data()

        if not documents:
            raise HTTPException(
                status_code=400,
                detail="No documents found in data folder.",
            )

        index = VectorStoreIndex.from_documents(documents)
        query_engine = index.as_query_engine(similarity_top_k=3)

        return query_engine

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
# Exercise 2: Router Query Engine
# ---------------------------------------------------------

def build_router_query_engine():
    try:
        tools = build_policy_tools()

        router_engine = RouterQueryEngine(
            selector=LLMSingleSelector.from_defaults(),
            query_engine_tools=tools,
        )

        return router_engine

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/router-rag/query")
def router_rag_query(request: QueryRequest):
    try:
        router_engine = build_router_query_engine()
        response = router_engine.query(request.question)

        clean_response = Settings.llm.complete(
            clean_final_answer_prompt(request.question, str(response))
        )

        sources = extract_sources_from_response(response)

        return {
            "exercise": "Router Query Engine",
            "question": request.question,
            "answer": str(clean_response),
            "accessed_documents": unique_documents_from_sources(sources),
            "source_documents": unique_documents_from_sources(sources),
            "sources": sources,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# Exercise 3: Custom SubQuestion RAG
# ---------------------------------------------------------

def build_custom_subquestion_response(question: str):
    try:
        appointment_engine = build_single_file_query_engine(
            str(DATA_PATH / "appointment_policy.txt")
        )

        billing_engine = build_single_file_query_engine(
            str(DATA_PATH / "billing_policy.txt")
        )

        insurance_engine = build_single_file_query_engine(
            str(DATA_PATH / "insurance_policy.txt")
        )

        appointment_answer = appointment_engine.query(question)
        billing_answer = billing_engine.query(question)
        insurance_answer = insurance_engine.query(question)

        all_sources = []
        all_sources.extend(extract_sources_from_response(appointment_answer, max_sources=2))
        all_sources.extend(extract_sources_from_response(billing_answer, max_sources=2))
        all_sources.extend(extract_sources_from_response(insurance_answer, max_sources=2))

        synthesis_prompt = f"""
User question:
{question}

Appointment policy answer:
{appointment_answer}

Billing policy answer:
{billing_answer}

Insurance policy answer:
{insurance_answer}

Combine the useful information into one clear final answer.
If one policy is not relevant, ignore it.
Do not use markdown formatting.
"""

        final_response = Settings.llm.complete(synthesis_prompt)

        return {
            "appointment_answer": str(appointment_answer),
            "billing_answer": str(billing_answer),
            "insurance_answer": str(insurance_answer),
            "final_answer": str(final_response),
            "sources": all_sources,
        }

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
            "exercise": "Custom SubQuestion RAG",
            "question": request.question,
            "sub_answers": {
                "appointment_policy": result["appointment_answer"],
                "billing_policy": result["billing_answer"],
                "insurance_policy": result["insurance_answer"],
            },
            "answer": str(clean_response),
            "accessed_documents": [
                "appointment_policy.txt",
                "billing_policy.txt",
                "insurance_policy.txt",
            ],
            "source_documents": unique_documents_from_sources(sources),
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


def summarize_policy_area(policy_area: str) -> str:
    policy_area = policy_area.lower()

    if "appointment" in policy_area:
        return (
            "Appointment policy summary: Patients should arrive 15 minutes early. "
            "Cancellations should happen at least 24 hours before the visit. "
            "After three no-shows, administrator approval may be required."
        )

    if "billing" in policy_area:
        return (
            "Billing policy summary: Late cancellations may result in a $25 fee. "
            "Patients may pay out of pocket if insurance cannot be verified. "
            "Billing support is available Monday through Friday from 9 AM to 5 PM."
        )

    if "insurance" in policy_area:
        return (
            "Insurance policy summary: Patients must provide insurance details before the visit. "
            "The clinic accepts most major commercial plans. Medicaid depends on state and network, "
            "and prior authorization may be required for some services."
        )

    return "Please choose appointment, billing, or insurance."


async def build_react_agent_response(question: str):
    try:
        policy_query_engine = build_basic_rag_engine()

        policy_search_tool = QueryEngineTool.from_defaults(
            query_engine=policy_query_engine,
            name="clinic_policy_search",
            description=(
                "Use this tool to answer questions from clinic documents about "
                "appointments, billing, insurance, cancellations, no-shows, referrals, "
                "prior authorization, and admin policies."
            ),
        )

        payment_calculator_tool = FunctionTool.from_defaults(
            fn=calculate_patient_payment,
            name="patient_payment_calculator",
            description=(
                "Use this tool to calculate patient payment. "
                "Inputs should include total_fee and insurance_coverage_percent."
            ),
        )

        policy_summary_tool = FunctionTool.from_defaults(
            fn=summarize_policy_area,
            name="policy_summary_tool",
            description=(
                "Use this tool to summarize appointment, billing, or insurance policy areas."
            ),
        )

        agent = ReActAgent(
            tools=[
                policy_search_tool,
                payment_calculator_tool,
                policy_summary_tool,
            ],
            llm=Settings.llm,
        )

        agent_question = f"""
{question}

Please answer in clean professional plain English.
Do not use markdown tables, # headings, or **bold markdown**.
"""

        response = await agent.run(agent_question)

        clean_response = Settings.llm.complete(
            clean_final_answer_prompt(question, str(response))
        )

        source_probe_response = policy_query_engine.query(question)
        sources = extract_sources_from_response(source_probe_response)

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

        if not DATA_PATH.exists():
            raise HTTPException(status_code=400, detail="Data folder not found.")

        txt_files = list(DATA_PATH.glob("*.txt"))

        if not txt_files:
            raise HTTPException(
                status_code=400,
                detail="No .txt documents found in data folder.",
            )

        for file_path in txt_files:
            document_engine = build_single_file_query_engine(str(file_path))

            tool_name = file_path.stem.replace("-", "_").replace(" ", "_")
            tool_name = re.sub(r"[^a-zA-Z0-9_]", "_", tool_name)

            document_tool = QueryEngineTool.from_defaults(
                query_engine=document_engine,
                name=f"{tool_name}_document_tool",
                description=(
                    f"Use this tool to answer questions from the document named "
                    f"{file_path.name}. This document may contain clinic policies, "
                    f"uploaded user documents, billing details, insurance rules, "
                    f"appointment information, or other clinic-related content."
                ),
            )

            tools.append(document_tool)

        return tools

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def collect_sources_from_all_documents(question: str):
    all_sources = []
    accessed_documents = []

    for file_path in sorted(DATA_PATH.glob("*.txt")):
        accessed_documents.append(file_path.name)

        try:
            engine = build_single_file_query_engine(str(file_path))
            response = engine.query(question)
            sources = extract_sources_from_response(response, max_sources=1)
            all_sources.extend(sources)
        except Exception:
            continue

    return accessed_documents, all_sources


async def build_multi_doc_agent_response(question: str):
    try:
        document_tools = build_dynamic_document_tools()

        agent = ReActAgent(
            tools=document_tools,
            llm=Settings.llm,
        )

        clean_question = f"""
User question:
{question}

Answer clearly in plain English.

Rules:
- Mention which document or documents were useful.
- Do not use markdown tables.
- Do not use # headings.
- Do not use **bold markdown**.
- Do not use unnecessary symbols.
- Keep the answer concise and professional.
"""

        response = await agent.run(clean_question)

        clean_response = Settings.llm.complete(
            clean_final_answer_prompt(question, str(response))
        )

        accessed_documents, sources = collect_sources_from_all_documents(question)

        return {
            "answer": str(clean_response),
            "accessed_documents": accessed_documents,
            "sources": sources,
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
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# Exercise 6: Multi Modal RAG
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

        if not mime_type:
            mime_type = "image/png"

        if not mime_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Please upload an image file such as PNG, JPG, JPEG, or WEBP.",
            )

        encoded_image = base64.b64encode(file_bytes).decode("utf-8")

        prompt = f"""
You are a healthcare admin AI assistant.

The user uploaded an image related to clinic operations.

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
            "exercise": "Multi Modal RAG",
            "filename": file.filename,
            "mime_type": mime_type,
            "question": question,
            "answer": str(clean_response),
            "accessed_documents": [file.filename],
            "source_documents": [file.filename],
            "sources": [
                {
                    "document": file.filename,
                    "score": None,
                    "excerpt": "This answer was generated from the uploaded image file.",
                }
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))