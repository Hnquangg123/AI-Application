# Assignment 11 - Weather and Search AI Agent

This project implements a LangChain conversational agent that chooses between two real-time tools:

- OpenWeather for current weather questions.
- Tavily Search for current news and general web-search questions.

The language model is GPT-4o-mini, accessed through an OpenAI-compatible API gateway with `ChatOpenAI`. The program uses a fixed list of questions, as required by the assignment, and does not call Python's `input()` function.

## How it works

```text
Dummy question list
        |
        v
LangChain create_agent + GPT-4o-mini
        |
        +--> get_weather(city) --> OpenWeather
        |
        +--> search_web(query) --> Tavily Search
        |
        v
Formatted assistant response and retained chat history
```

The system prompt instructs the agent to use `get_weather` for weather requests and `search_web` for current or factual web queries. Tool calls are printed to the console so routing is visible during the demonstration.

## Project files

- `assignment_11.py` - complete agent, tool definitions, and automatic conversation loop.
- `requirements.txt` - Python dependencies.
- `.env.example` - configuration template containing placeholders only.
- `.gitignore` - prevents credentials, virtual environments, and generated files from being committed.

## Requirements

- Python 3.10 or newer.
- An OpenAI-compatible API key and endpoint with access to GPT-4o-mini.
- An [OpenWeather API key](https://openweathermap.org/api).
- A [Tavily API key](https://app.tavily.com/).

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Copy the environment template:

```powershell
Copy-Item .env.example .env
```

Fill in `.env` with your own credentials:

```dotenv
OPENAI_API_KEY=your-openai-compatible-api-key
OPENAI_ENDPOINT=https://aiportalapi.stu-platform.live/jpefor
OPENAI_MODEL=gpt-4o-mini
OPENWEATHERMAP_API_KEY=your-openweather-api-key
TAVILY_API_KEY=your-tavily-api-key
```

`OPENAI_ENDPOINT` may be supplied with or without a version suffix. The program appends `/v1` when the URL does not already end in `/v1` or `/v2`.

## Run

```powershell
python assignment_11.py
```

The program automatically processes these demonstration inputs:

1. `What's the weather in Hanoi?`
2. `Tell me about the latest news in AI.`
3. `Who won the last World Cup?`
4. `exit`

The output follows this structure; live results vary:

```text
Welcome to the AI assistant. Type 'exit' to stop.

User: What's the weather in Hanoi?
[Tool] get_weather called for: Hanoi
AI: <current Hanoi weather>

User: Tell me about the latest news in AI.
[Tool] search_web called for: latest news in AI
AI: <summary with source URLs>

User: exit
Goodbye!
```

## Approach

1. Load and validate all required environment variables before creating API clients.
2. Configure `ChatOpenAI` with GPT-4o-mini and the custom OpenAI-compatible base URL.
3. Wrap OpenWeather and Tavily as LangChain tools with clear descriptions for tool selection.
4. Build the agent using the supported `langchain.agents.create_agent` API.
5. Pass the accumulated message history into each turn so the conversation retains context.
6. Catch errors per tool and per question so a failed API call does not terminate the remaining demonstration.

## Challenges and decisions

- The assignment sample uses `AzureChatOpenAI`; this implementation replaces it with `ChatOpenAI` and a configurable `base_url`.
- The sample's `langgraph.prebuilt.create_react_agent` is deprecated, so this project uses LangChain's supported `create_agent` API.
- Real-time answers must come from tools rather than model memory. The routing prompt explicitly requires OpenWeather for weather and Tavily for search questions.
- External services can fail because of invalid credentials, quotas, or network problems. Tools return concise error messages without revealing secret values.

## Security

- Never commit `.env` or paste real API keys into Python or README files.
- `.env` is ignored by Git; only `.env.example` should be committed.
- If a key is shared publicly or pasted into a chat, revoke it and issue a replacement.

## Assignment checklist

- [x] Single Python agent file.
- [x] API configuration through environment variables with placeholders.
- [x] OpenWeather tool definition.
- [x] Tavily Search tool definition.
- [x] LangChain agent initialization and tool routing.
- [x] Automatic dummy input list with no `input()` call.
- [x] Conversation history.
- [x] User-friendly output and resilient error handling.
- [x] Documented approach and challenges.
