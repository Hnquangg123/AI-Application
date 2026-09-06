# Assignment 14 — RAG Chatbot for Product and Policy Support in Retail

A Retrieval-Augmented Generation (RAG) chatbot that helps Walmart employees and customers quickly get accurate answers about product details, store policies, and return/exchange guidelines — built with **LangGraph**, **FAISS**, and **ChatOpenAI (GPT-4o-mini)** through **LangChain**.

## Description

Retail staff and customers often have questions about product specifications, warranties, in-store services, and return/exchange policies. Without instant access to information, staff spend time searching manuals or waiting for approvals, and customers face longer wait times. This project deploys a RAG chatbot that delivers fast, reliable, context-aware answers grounded in real policy documents.

The chatbot references an in-memory knowledge base of **15 Walmart policy and product documents** (the mock dataset from the assignment) and answers any natural-language question in two steps:

1. **Retrieve** — the question is embedded with `text-embedding-3-small` and the top-k most relevant policy passages are fetched from a **FAISS** vector store (semantic search, not keyword matching).
2. **Generate** — `GPT-4o-mini` composes a clear, human-friendly answer that cites the retrieved passages, honestly saying so when the documents don't cover the question.

### Architecture

```
question ──> [retrieve] ──> context ──> [generate] ──> answer
              FAISS +                    ChatOpenAI
              text-embedding-3-small     (GPT-4o-mini)
```

The pipeline is a LangGraph `StateGraph` over a typed state (`RAGState`: question, context, answer) with `retrieve` as the entry point, an edge to `generate`, and `generate` as the finish point.

## Requirements

- Python 3.10+
- Packages: `langchain`, `langchain-openai`, `langchain-community`, `langgraph`, `faiss-cpu`
- Access to an OpenAI-compatible endpoint with a `GPT-4o-mini` chat deployment and a `text-embedding-3-small` embedding deployment

## Installation

```bash
# 1. Create and activate a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt
```

## Configuration

The script reads its configuration from environment variables (defaults are set in the file for the course's API portal endpoint `https://aiportalapi.stu-platform.live/jpe`):

| Variable | Purpose |
|---|---|
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint base URL |
| `OPENAI_LLM_API_KEY` / `OPENAI_LLM_MODEL` | API key and model name for the chat model (GPT-4o-mini) |
| `OPENAI_EMBEDDING_API_KEY` / `OPENAI_EMBED_MODEL` | API key and model name for embeddings (text-embedding-3-small) |

## Usage

```bash
python rag_chatbot.py
```

Per the submission checklist, the demo is driven by a **dummy input list** (auto input) — no manual `input()` is used. Five realistic customer questions are run through the RAG pipeline, and for each one the script prints the **user question**, the **retrieved context**, and the **generated answer**:

```
======================================================================
Q&A Demo #1

User Question:
  Can I return a Walmart bicycle if I've ridden it outdoors?

Retrieved Context:
- Bicycles purchased at Walmart can be returned within 90 days if not used
  outdoors and with all accessories present.
- Walmart reserves the right to deny returns suspected of fraud or abuse.

Generated Answer:
  Unfortunately, no. According to Walmart's policy, bicycles can be returned
  within 90 days only if they have NOT been used outdoors...
```

A full representative transcript is included at the bottom of `rag_chatbot.py`.

## Reflection: RAG vs. static FAQs / keyword search

Static FAQs and keyword search force users to guess the exact wording a policy page uses. RAG retrieves by meaning instead: "can I bring back my bike?" still finds the bicycle return policy. The LLM then synthesizes the retrieved passages into one direct, contextual answer instead of dumping a policy page, stays grounded in (and cites) the source documents, and picks up policy changes by simply re-indexing a document — no retraining, no rewriting hundreds of FAQ entries. Every associate gets the same answer in seconds, improving service consistency and cutting customer wait times. The full reflection, plus optional extension ideas (product recommendations, multi-turn memory, query rewriting and human escalation), is included at the bottom of `rag_chatbot.py`.

## Project structure

| File | Description |
|---|---|
| `rag_chatbot.py` | Full implementation in a single file: the 15 Walmart data entries, embeddings + FAISS vector store, LangGraph retrieve→generate pipeline, auto-input Q&A demos, reflection, and a sample transcript |
| `requirements.txt` | Python dependencies |
| `fake_openai_server.py` | Development helper: a local mock of the OpenAI API used to test the full code path (client wiring, FAISS build, graph flow) without network access |

## Concepts covered

OpenAI-compatible chat & embedding APIs, prompt engineering, vector stores and embeddings (FAISS), and Retrieval-Augmented Generation (RAG) orchestrated with LangGraph.

## Author

Dylan (quanghn17) — FPT AI Application Engineer program, Assignment 14.
