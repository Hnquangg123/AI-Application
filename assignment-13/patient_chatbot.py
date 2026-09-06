"""
Assignment 13: Building a Patient Information Collection and Advisory Chatbot Agent
====================================================================================

An AI-powered chatbot agent that:
  1. Interactively collects patient information (name, age, symptoms).
  2. Provides preliminary health advice based on the collected data.
  3. Uses LangGraph to manage the conversational flow and state.
  4. Uses ChatOpenAI (GPT-4o-mini) through LangChain as the language model.
  5. Retrieves internal medical advice with a FAISS vector store
     (text-embedding-3-small embeddings).
  6. Optionally integrates Tavily to fetch real-time web information.

Submission notes (per the assignment checklist):
  - Single .py file containing the full code.
  - Uses a dummy input list (auto input) -- no manual input() built-in.
  - Sample inputs and outputs are included at the bottom of this file.

Install dependencies:
  pip install langchain langchain-openai langchain-community langgraph faiss-cpu
"""

import os
import warnings

warnings.filterwarnings("ignore")  # keep demo output clean (deprecation notices)

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

# Re-apply after the LangChain imports, which register their own warning filters.
warnings.filterwarnings("ignore")

# =====================================================================
# 1. Configuration
# =====================================================================
os.environ.setdefault("OPENAI_BASE_URL", "https://aiportalapi.stu-platform.live/jpe")

os.environ.setdefault("OPENAI_LLM_API_KEY", "sk-OP5ycn2-7wrwt3TrpjVwXQ")
os.environ.setdefault("OPENAI_LLM_MODEL", "GPT-4o-mini")

os.environ.setdefault("OPENAI_EMBEDDING_API_KEY", "sk-HQ8pODJJNBTUpWvxFE3Xbw")
os.environ.setdefault("OPENAI_EMBED_MODEL", "text-embedding-3-small")

# Optional: Tavily API key enables the real-time web search tool.
os.environ.setdefault("TAVILY_API_KEY", "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")

# =====================================================================
# 2. Internal knowledge base (mock advice chunks) + FAISS retriever
# =====================================================================
mock_chunks = [
    Document(
        page_content="Patients with a sore throat should drink warm fluids and avoid cold beverages."
    ),
    Document(
        page_content="Mild fevers under 38.5°C can often be managed with rest and hydration."
    ),
    Document(
        page_content="If a patient reports dizziness, advise checking their blood pressure and hydration level."
    ),
    Document(
        page_content="Persistent coughs lasting more than 2 weeks should be evaluated for infections or allergies."
    ),
    Document(
        page_content="Patients experiencing fatigue should consider iron deficiency or poor sleep as potential causes."
    ),
]

embedding_model = OpenAIEmbeddings(
    model=os.environ["OPENAI_EMBED_MODEL"],
    api_key=os.environ["OPENAI_EMBEDDING_API_KEY"],
    base_url=os.environ["OPENAI_BASE_URL"],
    # Send texts directly to the endpoint instead of tokenizing locally
    # (avoids a tiktoken download and works with proxy endpoints).
    check_embedding_ctx_length=False,
)

db = FAISS.from_documents(mock_chunks, embedding_model)
retriever = db.as_retriever()


# =====================================================================
# 3. Tools
# =====================================================================
@tool
def retrieve_advice(user_input: str) -> str:
    """Searches internal medical documents for relevant patient advice."""
    docs = retriever.invoke(user_input)
    return "\n".join(doc.page_content for doc in docs)


tools = [retrieve_advice]

# --- Optional TOOL: Tavily real-time web search ---
if os.environ.get("TAVILY_API_KEY"):
    from langchain_community.tools.tavily_search import TavilySearchResults

    tavily_tool = TavilySearchResults(max_results=3)
    tools.append(tavily_tool)

# =====================================================================
# 4. LLM setup (ChatOpenAI through LangChain)
# =====================================================================
llm = ChatOpenAI(
    model=os.environ["OPENAI_LLM_MODEL"],
    api_key=os.environ["OPENAI_LLM_API_KEY"],
    base_url=os.environ["OPENAI_BASE_URL"],
    temperature=0.2,
)

llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are a helpful and friendly medical assistant chatbot.\n"
        "Your job:\n"
        "1. Interactively collect the patient's information: full name, age, and "
        "current symptoms. Ask politely for any detail that is still missing, "
        "one step at a time.\n"
        "2. Once you know the name, age, and symptoms, give clear, preliminary "
        "health advice. Use the `retrieve_advice` tool to look up relevant "
        "guidance from the internal medical knowledge base, and any web search "
        "tool if available for up-to-date information.\n"
        "3. Tailor the advice to the patient's age and symptoms, list simple "
        "self-care steps, and mention warning signs that would require seeing "
        "a doctor.\n"
        "4. Always remind the patient that this is preliminary advice, not a "
        "medical diagnosis.\n"
        "Keep responses concise and conversational."
    )
)


# =====================================================================
# 5. LangGraph: nodes, conditional routing, graph build
# =====================================================================
def call_model(state: MessagesState):
    """Model node: calls the LLM (with tools) on the running conversation."""
    messages = [SYSTEM_PROMPT] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: MessagesState):
    """Conditional routing: run tools if the LLM asked for them, else finish."""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


tool_node = ToolNode(tools)

graph_builder = StateGraph(MessagesState)
graph_builder.add_node("call_model", call_model)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "call_model")
graph_builder.add_conditional_edges("call_model", should_continue, ["tools", END])
graph_builder.add_edge("tools", "call_model")

graph = graph_builder.compile()


# =====================================================================
# 6. Demo conversation driven by a dummy input list (auto input)
# =====================================================================
def run_demo(dummy_inputs):
    """Feeds a list of scripted patient messages through the agent, turn by turn,
    carrying the full conversation state across turns."""
    conversation = []
    for turn, user_text in enumerate(dummy_inputs, start=1):
        print(f"\n{'=' * 70}")
        print(f"Patient (turn {turn}): {user_text}")
        conversation.append(HumanMessage(content=user_text))

        result = graph.invoke({"messages": conversation})
        conversation = result["messages"]

        reply = conversation[-1]
        print(f"\nChatbot: {reply.content}")
    return conversation


if __name__ == "__main__":
    # Dummy input list (auto input) -- simulates the patient typing.
    dummy_inputs = [
        "Hi, I don't feel very well today and I'd like some advice.",
        "My name is Nguyen Van An.",
        "I'm 35 years old.",
        "I feel tired all the time and I also have a sore throat.",
        "Thank you! Is there anything I should watch out for?",
    ]

    final_state = run_demo(dummy_inputs)

    print(f"\n{'=' * 70}")
    print("Final Response:")
    print(final_state[-1].content)


# =====================================================================
# 7. Sample inputs and outputs
# =====================================================================
"""
SAMPLE INPUTS (the dummy input list above):
  1. "Hi, I don't feel very well today and I'd like some advice."
  2. "My name is Nguyen Van An."
  3. "I'm 35 years old."
  4. "I feel tired all the time and I also have a sore throat."
  5. "Thank you! Is there anything I should watch out for?"

SAMPLE OUTPUT (representative transcript of `python patient_chatbot.py`):

======================================================================
Patient (turn 1): Hi, I don't feel very well today and I'd like some advice.

Chatbot: I'm sorry to hear that you're not feeling well. I'd be happy to
help with some preliminary advice. Could you start by telling me your
full name, please?

======================================================================
Patient (turn 2): My name is Nguyen Van An.

Chatbot: Nice to meet you, An. Could you tell me your age?

======================================================================
Patient (turn 3): I'm 35 years old.

Chatbot: Thank you! Now, could you describe the symptoms you're
experiencing today?

======================================================================
Patient (turn 4): I feel tired all the time and I also have a sore throat.

Chatbot: Thanks for sharing, An. Based on your symptoms (fatigue and a
sore throat) at age 35, here is some preliminary advice:

1. Sore throat: Drink warm fluids (tea with honey, warm water) and avoid
   cold beverages. Rest your voice when possible.
2. Fatigue: Ongoing tiredness can be related to iron deficiency or poor
   sleep. Try to keep a regular sleep schedule and eat iron-rich foods.
3. General care: Stay hydrated and rest as much as you can.

Please remember this is preliminary advice, not a medical diagnosis. If
symptoms persist or worsen, please see a healthcare professional.

======================================================================
Patient (turn 5): Thank you! Is there anything I should watch out for?

Chatbot: You're welcome, An! Watch out for these warning signs:
- Fever above 38.5°C or a fever lasting more than 2-3 days
- Difficulty swallowing or breathing
- A sore throat lasting longer than a week
- Fatigue that doesn't improve with rest, dizziness, or unexplained
  weight loss

If any of these occur, please see a doctor promptly. This is preliminary
advice, not a diagnosis. Take care and I hope you feel better soon!

======================================================================
Final Response:
(The chatbot's last reply above.)
"""
