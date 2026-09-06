"""
Assignment 14 (Retail): Building a RAG Chatbot for Product and Policy Support
==============================================================================

A Retrieval-Augmented Generation (RAG) chatbot that helps retail employees and
customers quickly get accurate answers about product details, store policies,
and return/exchange guidelines for Walmart.

Pipeline (LangGraph):
    question --> [retrieve] --(FAISS + text-embedding-3-small)--> context
             --> [generate] --(ChatOpenAI, GPT-4o-mini)--> answer

Submission notes (per the assignment checklist):
  - Single .py file with the full RAG chatbot and the 15 Walmart data entries.
  - Realistic Q&A demos showing input question, retrieved context, and
    generated answer.
  - Driven by a dummy input list (auto input) -- no manual input() built-in.
  - A brief reflection on RAG vs. traditional static FAQs is included at the
    bottom of this file.

Install dependencies:
  pip install langchain langchain-openai langchain-community langgraph faiss-cpu
"""

import os
import warnings
from typing import Optional, TypedDict

warnings.filterwarnings("ignore")  # keep demo output clean

from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, StateGraph

# Re-apply after the LangChain imports, which register their own warning filters.
warnings.filterwarnings("ignore")

# =====================================================================
# Step 0: Environment setup (OpenAI-compatible endpoint)
# =====================================================================
os.environ.setdefault("OPENAI_BASE_URL", "https://aiportalapi.stu-platform.live/jpe")

os.environ.setdefault("OPENAI_LLM_API_KEY", "sk-OP5ycn2-7wrwt3TrpjVwXQ")
os.environ.setdefault("OPENAI_LLM_MODEL", "GPT-4o-mini")

os.environ.setdefault("OPENAI_EMBEDDING_API_KEY", "sk-HQ8pODJJNBTUpWvxFE3Xbw")
os.environ.setdefault("OPENAI_EMBED_MODEL", "text-embedding-3-small")

# =====================================================================
# Step 1: Mock dataset -- 15 Walmart policy and product documents
# =====================================================================
docs = [
    Document(page_content="Walmart customers may return electronics within 30 days with a receipt and original packaging."),
    Document(page_content="Grocery items at Walmart can be returned within 90 days with proof of purchase, except perishable products."),
    Document(page_content="Walmart offers a 1-year warranty on most electronics and appliances. See product details for exceptions."),
    Document(page_content="Walmart Plus members get free shipping with no minimum order amount."),
    Document(page_content="Prescription medications purchased at Walmart are not eligible for return or exchange."),
    Document(page_content="Open-box items are eligible for return at Walmart within the standard return period, but must include all original accessories."),
    Document(page_content="If a Walmart customer does not have a receipt, most returns are eligible for store credit with valid photo identification."),
    Document(page_content="Walmart allows price matching for identical items found on Walmart.com and local competitor ads."),
    Document(page_content="Walmart Vision Center purchases may be returned or exchanged within 60 days with a receipt."),
    Document(page_content="Returns on cell phones at Walmart require the device to be unlocked and all personal data erased."),
    Document(page_content="Walmart gift cards cannot be redeemed for cash except where required by law."),
    Document(page_content="Seasonal merchandise at Walmart (e.g., holiday decorations) may have modified return windows, see in-store signage."),
    Document(page_content="Bicycles purchased at Walmart can be returned within 90 days if not used outdoors and with all accessories present."),
    Document(page_content="For online Walmart orders, customers can return items in store or by mail using the prepaid label."),
    Document(page_content="Walmart reserves the right to deny returns suspected of fraud or abuse."),
]


# =====================================================================
# Step 2: Typed state for LangGraph
# =====================================================================
class RAGState(TypedDict):
    question: str
    context: Optional[str]
    answer: Optional[str]


# =====================================================================
# Step 3: Embeddings & vector store (FAISS)
# =====================================================================
embeddings = OpenAIEmbeddings(
    model=os.environ["OPENAI_EMBED_MODEL"],
    api_key=os.environ["OPENAI_EMBEDDING_API_KEY"],
    base_url=os.environ["OPENAI_BASE_URL"],
    # Send texts directly to the endpoint instead of tokenizing locally
    # (avoids a tiktoken download and works with proxy endpoints).
    check_embedding_ctx_length=False,
)

vectorstore = FAISS.from_documents(
    docs,
    embeddings,
    docstore=InMemoryDocstore({str(i): doc for i, doc in enumerate(docs)}),
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

# =====================================================================
# Step 4: Chat model (ChatOpenAI through LangChain)
# =====================================================================
llm = ChatOpenAI(
    model=os.environ["OPENAI_LLM_MODEL"],
    api_key=os.environ["OPENAI_LLM_API_KEY"],
    base_url=os.environ["OPENAI_BASE_URL"],
    temperature=0,
)

# =====================================================================
# Step 5: Prompt template
# =====================================================================
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful Walmart support assistant. Use the provided "
            "information to answer product and policy questions. Always cite "
            "the retrieved info in your answer. If the retrieved information "
            "does not cover the question, say so honestly.",
        ),
        ("human", "{context}\n\nUser question: {question}"),
    ]
)


# =====================================================================
# Step 6: Graph nodes
# =====================================================================
def retrieve_node(state: RAGState) -> RAGState:
    """Retrieves the most relevant policy/product passages for the question."""
    relevant_docs = retriever.invoke(state["question"])
    context = "\n".join(f"- {doc.page_content}" for doc in relevant_docs)
    return {**state, "context": context}


def generate_node(state: RAGState) -> RAGState:
    """Generates a clear, human-friendly answer grounded in the context."""
    formatted_prompt = prompt.format(
        context=state["context"], question=state["question"]
    )
    answer = llm.invoke(formatted_prompt)
    return {**state, "answer": answer.content}


# =====================================================================
# Step 7: Build the LangGraph pipeline (retrieve -> generate)
# =====================================================================
builder = StateGraph(RAGState)

builder.add_node("retrieve", retrieve_node)
builder.add_node("generate", generate_node)

builder.set_entry_point("retrieve")
builder.add_edge("retrieve", "generate")
builder.set_finish_point("generate")

rag_graph = builder.compile()


# =====================================================================
# Step 8: Q&A demo driven by a dummy input list (auto input)
# =====================================================================
if __name__ == "__main__":
    dummy_questions = [
        "Can I return a Walmart bicycle if I've ridden it outdoors?",
        "I lost my receipt. Can I still return the blender I bought?",
        "Do Walmart Plus members have to pay for shipping on small orders?",
        "Can I return my prescription medication?",
        "What do I need to do before returning a cell phone to Walmart?",
    ]

    for i, user_question in enumerate(dummy_questions, start=1):
        result = rag_graph.invoke({"question": user_question})

        print("=" * 70)
        print(f"Q&A Demo #{i}")
        print(f"\nUser Question:\n  {user_question}")
        print(f"\nRetrieved Context:\n{result['context']}")
        print(f"\nGenerated Answer:\n  {result['answer']}\n")


# =====================================================================
# Reflection: How RAG improves retail support vs. static FAQs / keyword search
# =====================================================================
"""
REFLECTION

Traditional static FAQs and keyword search force the user to guess the exact
wording a policy page uses: a customer asking "Can I bring back my bike if
I've ridden it?" will not match an FAQ entry titled "Bicycle return window",
and a keyword search for "bring back bike" may return nothing at all.

RAG improves retail support in several concrete ways:

1. Semantic retrieval: embeddings match by meaning, not exact words, so
   "bring back my bike" still retrieves the bicycle return policy. Staff and
   customers do not need to know internal policy vocabulary.

2. Synthesized, contextual answers: instead of dumping a whole policy page,
   the LLM combines the retrieved passages into one direct answer tailored to
   the actual question (e.g., it can say "no, because it was used outdoors").

3. Grounded and up to date: answers cite the retrieved documents, which
   reduces hallucination, and updating the answer for a policy change only
   requires re-indexing the document -- no retraining and no rewriting of
   hundreds of FAQ entries.

4. Consistency and speed: every store associate gets the same policy answer
   in seconds, rather than searching manuals or waiting for a manager's
   approval, which shortens customer wait times.

OPTIONAL EXTENSIONS

- Product recommendations: index the product catalog alongside policies and
  add a recommendation node ("customers who need X also buy Y").
- Multi-turn conversations: switch the graph state to a message list (as in
  LangGraph's MessagesState) so the bot remembers the customer's earlier
  turns, enabling follow-ups like "and what if I opened the box?".
- Query rewriting / routing nodes, re-ranking of retrieved chunks, and a
  confidence threshold that escalates to a human agent when retrieval is weak.


SAMPLE OUTPUT (representative transcript of `python rag_chatbot.py`):

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
  within 90 days only if they have NOT been used outdoors and all accessories
  are present. Since you've ridden the bicycle outdoors, it would not be
  eligible for return under the standard policy.

======================================================================
Q&A Demo #2

User Question:
  I lost my receipt. Can I still return the blender I bought?

Retrieved Context:
- If a Walmart customer does not have a receipt, most returns are eligible
  for store credit with valid photo identification.
- Walmart reserves the right to deny returns suspected of fraud or abuse.

Generated Answer:
  Yes, you can still return the blender without a receipt. Per Walmart's
  policy, most returns without a receipt are eligible for store credit as
  long as you present a valid photo ID. Note that Walmart reserves the right
  to deny returns suspected of fraud or abuse.

(...demos #3-#5 follow the same format for shipping, prescriptions, and
cell-phone returns...)
"""
