import os
import uuid
import streamlit as st
from backend import run_travel_agent

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="TripMate AI - Multi-Agent Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())[:8]

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "user_prompt" not in st.session_state:
    st.session_state.user_prompt = "Plan a 7 day Nepal trip from Bangladesh under 2 lakhs"


# Helper for prompt sample buttons
def set_prompt(text: str):
    st.session_state.user_prompt = text


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
with st.sidebar:
    st.title("✈️ TripMate AI")
    st.caption("Autonomous Travel Orchestrator")
    st.markdown("---")

    # API Keys & System Status
    st.subheader("System Status")
    groq_ok = bool(os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY") != "your_groq_key")
    tavily_ok = bool(os.getenv("TAVILY_API_KEY") and os.getenv("TAVILY_API_KEY") != "your_tavily_key")
    aviation_ok = bool(os.getenv("AVIATIONSTACK_API_KEY") and os.getenv("AVIATIONSTACK_API_KEY") != "your_aviationstack_key")
    db_ok = bool(os.getenv("DATABASE_URL") and "render.com" in os.getenv("DATABASE_URL", ""))
    smith_ok = bool(
        (os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))
        and (os.getenv("LANGSMITH_TRACING") == "true" or os.getenv("LANGCHAIN_TRACING_V2") == "true")
    )

    st.write(f"🧠 **Groq LLM:** {'🟢 Connected' if groq_ok else '🟡 Fallback Mode'}")
    st.write(f"🔎 **Tavily Search:** {'🟢 Ready' if tavily_ok else '🟡 Fallback Mode'}")
    st.write(f"🛫 **Aviationstack:** {'🟢 Ready' if aviation_ok else '🟡 Fallback Mode'}")
    st.write(f"💾 **PostgreSQL:** {'🟢 Configured' if db_ok else '🟡 In-Memory'}")
    st.write(f"📊 **LangSmith:** {'🟢 Tracing Active' if smith_ok else '⚪ Disabled'}")
    if smith_ok:
        st.markdown("[🔗 Open LangSmith Dashboard](https://smith.langchain.com/)", help="Inspect agent traces, latencies, and token consumption")

    st.markdown("---")
    st.subheader("Conversation Memory")
    thread_input = st.text_input(
        "Thread ID (Checkpointer Key)",
        value=st.session_state.thread_id,
        help="Reusing a Thread ID restores prior checkpoints from PostgreSQL.",
    )
    if st.button("🔄 Generate New Thread ID"):
        st.session_state.thread_id = str(uuid.uuid4())[:8]
        st.session_state.last_result = None
        st.rerun()

    st.markdown("---")
    st.subheader("Quick Example Prompts")
    if st.button("🏔️ 7 Days Nepal from Bangladesh"):
        set_prompt("Plan a 7 day Nepal trip from Bangladesh under 2 lakhs")
        st.rerun()
    if st.button("🏖️ 5 Days Thailand from India"):
        set_prompt("Plan a 5 days Thailand trip from India under 60k INR with beach hotels")
        st.rerun()
    if st.button("🗼 8 Days Japan from USA"):
        set_prompt("Plan an 8 days Japan vacation from USA on a moderate budget")
        st.rerun()
    if st.button("🏙️ 4 Days Dubai from UK"):
        set_prompt("Plan a 4 days Dubai luxury trip from United Kingdom under 2000 GBP")
        st.rerun()

    st.markdown("---")
    st.markdown(
        """
        ### Architecture
        ```
        User Query
           │
           ▼
        Flight Agent (Aviationstack)
           │
           ▼
        Hotel Agent (Tavily)
           │
           ▼
        Itinerary Agent (Groq Llama 3)
           │
           ▼
        Final Agent (Synthesis)
        ```
        """
    )

# ---------------------------------------------------------
# Main Page Content
# ---------------------------------------------------------
st.title("TripMate AI: Multi-Agent Travel Planner ✈️🗺️")
st.markdown(
    "Enter a single sentence describing your desired vacation. "
    "**Four specialized agents** will collaborate to discover flights, inspect hotels, "
    "build a day-by-day itinerary, and assemble your complete travel dossier."
)

# Prompt input
user_query = st.text_area(
    "What kind of trip are you planning?",
    value=st.session_state.user_prompt,
    height=90,
    placeholder="e.g. Plan a 7 day Nepal trip from Bangladesh under 2 lakhs",
)

col_run, col_clear = st.columns([1, 6])
with col_run:
    run_btn = st.button("🚀 Generate Travel Plan", type="primary", use_container_width=True)

# ---------------------------------------------------------
# Agent Execution
# ---------------------------------------------------------
if run_btn:
    if not user_query.strip():
        st.warning("Please provide a travel request.")
    else:
        # Show animated steps using Streamlit status container
        with st.status("Executing Multi-Agent Workflow...", expanded=True) as status:
            st.write("🛫 **Flight Agent:** Resolving origin and destination IATA codes with Aviationstack...")
            # We call the backend agent
            try:
                result = run_travel_agent(user_query.strip(), thread_id=thread_input)
                st.write("🏨 **Hotel Agent:** Querying Tavily for top accommodations and cost ranges...")
                st.write("📅 **Itinerary Agent:** Formulating day-by-day plan using Groq Llama 3.3 70B...")
                st.write("✨ **Final Agent:** Assembling executive travel dossier...")
                status.update(label="Travel Plan Generated Successfully!", state="complete", expanded=False)
                st.session_state.last_result = result
            except Exception as e:
                status.update(label=f"Execution error: {str(e)}", state="error", expanded=True)
                st.error(f"Error executing agent graph: {str(e)}")

# ---------------------------------------------------------
# Display Results
# ---------------------------------------------------------
if st.session_state.last_result:
    res = st.session_state.last_result

    st.markdown("---")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(label="Thread ID", value=res.get("thread_id", "N/A"))
    with col_m2:
        st.metric(label="LLM Invocations", value=f"{res.get('llm_calls', 0)} calls")
    with col_m3:
        st.metric(label="Workflow Status", value="Complete ✅")

    # Tabs for formatted output and raw agent data
    tab_itinerary, tab_flights, tab_hotels = st.tabs([
        "📋 Complete Travel Dossier",
        "🛫 Flight Data",
        "🏨 Hotel Search Data",
    ])

    with tab_itinerary:
        st.markdown(res.get("answer", "No answer generated."))

        # Download Markdown / Text Dossier
        dossier_text = res.get("answer", "")
        st.download_button(
            label="📄 Download Travel Dossier (.md)",
            data=dossier_text,
            file_name=f"TripMate_Itinerary_{res.get('thread_id', 'trip')}.md",
            mime="text/markdown",
        )

    with tab_flights:
        st.subheader("Raw Flight Findings (Aviationstack)")
        st.code(res.get("flight_result", "No flight data recorded."), language="json")

    with tab_hotels:
        st.subheader("Raw Accommodation Findings (Tavily)")
        st.code(res.get("hotel_result", "No hotel data recorded."), language="json")
