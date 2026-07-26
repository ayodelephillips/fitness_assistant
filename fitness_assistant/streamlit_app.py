"""Streamlit frontend for the Fitness Assistant RAG system."""

import streamlit as st
from fitness_assistant.rag.llm_interface import ManageVectorDb, LLMFlow
from fitness_assistant.rag.helper import format_vector_db_context


def run_rag_pipeline(query: str) -> tuple[str, str]:
    """Run the full RAG pipeline and return (context, answer).

    Args:
        query: The user's fitness question.

    Returns:
        A tuple of (formatted_context, llm_answer).
    """
    vector_db = ManageVectorDb()
    results = vector_db.search(query=query)
    context = format_vector_db_context(results.points)

    llm_flow = LLMFlow()
    answer = llm_flow.run(query=query, context=context)

    return context, answer


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fitness Assistant",
    page_icon="🏋️",
    layout="centered",
)

# ── Title ────────────────────────────────────────────────────────────────────
st.title("🏋️ Fitness Assistant")
st.markdown(
    "Ask me about exercises — I'll find the best matches from our database "
    "and give you instructions, equipment needs, and video links."
)

# ── Initialise chat history ──────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Display chat history ─────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("context"):
            with st.expander("📄 Retrieved context"):
                st.text(msg["context"])

# ── Chat input ───────────────────────────────────────────────────────────────
if prompt := st.chat_input("e.g. What's a good exercise for biceps?"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Run RAG pipeline
    with st.chat_message("assistant"):
        with st.spinner("Searching exercises and generating answer..."):
            try:
                context, answer = run_rag_pipeline(prompt)
            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"❌ Error: {e}"}
                )
                st.stop()

        st.markdown(answer)
        with st.expander("📄 Retrieved context"):
            st.text(context)

    # Persist assistant message
    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "context": context}
    )

# ── Sidebar info ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### About")
    st.markdown(
        "This assistant uses **Retrieval-Augmented Generation (RAG)** "
        "to answer your fitness questions.\n\n"
        "1. Your question is converted into a vector (semantic fingerprint)\n"
        "2. The 3 most relevant exercises are retrieved from Qdrant\n"
        "3. Gemini 2.5 Flash generates an answer using only those exercises"
    )
    st.markdown("---")
    st.caption("Built with Streamlit + Qdrant + Gemini")
