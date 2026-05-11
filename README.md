# ClinicOps LlamaIndex Backend

A local FastAPI backend that implements six LlamaIndex cookbook-style exercises using a healthcare clinic operations use case.

## Project Idea

ClinicOps AI Assistant helps answer questions from clinic policy documents, route questions to the correct document, compare multiple policies, use agent tools, search multiple documents, and read image-based healthcare documents.

## Tech Stack

- FastAPI
- LlamaIndex
- Anthropic Claude
- HuggingFace Embeddings
- Python
- Local text documents
- Multimodal image input

## Implemented Exercises

### 1. Basic RAG

Route:

```txt
POST /basic-rag/query