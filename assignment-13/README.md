# Assignment 13 — Patient Information Collection and Advisory Chatbot Agent

An AI-powered chatbot agent that interactively collects patient information (name, age, symptoms) and provides preliminary health advice, built with **LangGraph** for conversational flow management and **ChatOpenAI (GPT-4o-mini)** through **LangChain** as the language model.

## Description

Patients often need quick, preliminary health assessments before seeing healthcare professionals. This project builds an AI-driven chatbot agent that:

- Engages users in a natural conversational manner to gather essential patient details (full name, age, current symptoms), asking politely for any missing detail one step at a time.
- Analyzes the collected information to offer relevant, preliminary health advice tailored to the patient's age and symptoms, including self-care steps and warning signs that require seeing a doctor.
- Retrieves guidance from an internal medical knowledge base: five mock advice documents are embedded with `text-embedding-3-small` and indexed in a **FAISS** vector store, exposed to the agent as a `retrieve_advice` tool.
- Optionally enhances advice with real-time web information via **Tavily** (enabled automatically when `TAVILY_API_KEY` is set).
- Manages the whole dialogue with a **LangGraph** `StateGraph`: a model node calls the tool-bound LLM, a conditional edge routes to a `ToolNode` whenever the LLM requests a tool, and results are fed back to the model until it produces a final answer.

### Architecture

```
START ──> call_model ──(tool_calls?)──> tools (retrieve_advice / tavily) ──> call_model
              │
              └──(no tool calls)──> END
```

## Requirements

- Python 3.10+
- Packages: `langchain`, `langchain-openai`, `langchain-community`, `langgraph`, `faiss-cpu`
- Access to an OpenAI-compatible endpoint with a `GPT-4o-mini` chat deployment and a `text-embedding-3-small` embedding deployment
- (Optional) A Tavily API key for real-time web search

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
| `TAVILY_API_KEY` | Optional — enables the Tavily web-search tool when set |

## Usage

```bash
python patient_chatbot.py
```

Per the submission checklist, the conversation is driven by a **dummy input list** (auto input) — no manual `input()` is used. The script simulates a five-turn patient dialogue:

```python
dummy_inputs = [
    "Hi, I don't feel very well today and I'd like some advice.",
    "My name is Nguyen Van An.",
    "I'm 35 years old.",
    "I feel tired all the time and I also have a sore throat.",
    "Thank you! Is there anything I should watch out for?",
]
```

The chatbot greets the patient, asks for the missing details (name, then age, then symptoms), calls the `retrieve_advice` tool against the FAISS knowledge base once symptoms are known, and returns tailored preliminary advice with warning signs — always reminding the patient that this is not a medical diagnosis. A full sample transcript is included at the bottom of `patient_chatbot.py`.

## Project structure

| File | Description |
|---|---|
| `patient_chatbot.py` | Full implementation in a single file: configuration, FAISS knowledge base, tools, LLM setup, LangGraph graph, and the auto-input demo, with sample inputs/outputs documented at the bottom |
| `requirements.txt` | Python dependencies |
| `fake_openai_server.py` | Development helper: a local mock of the OpenAI API used to test the agent's full code path (client wiring, FAISS build, tool-calling loop, graph routing) without network access |

## Concepts covered

Conversational AI, conversation flow management with LangGraph, language model integration through LangChain, retrieval with FAISS embeddings, optional real-time data retrieval with Tavily, and prompt engineering for health-related advice generation.

## Author

Dylan (quanghn17) — FPT AI Application Engineer program, Assignment 13.

## Disclaimer

This chatbot provides preliminary, educational health information only. It is not a medical device and its output is not a diagnosis; always consult a qualified healthcare professional for medical concerns.
