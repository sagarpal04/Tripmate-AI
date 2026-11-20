import os
import uuid
import operator
import logging
from typing import TypedDict, Annotated, Optional

import certifi
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from tools.tavily_tool import tavily_search
from tools.flight_tools import search_flights

# ---------------------------------------------------------
# Part 1: Imports and Environment Setup
# ---------------------------------------------------------
load_dotenv()
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# Configure LangSmith / LangChain Tracing
langsmith_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
tracing_enabled = os.getenv("LANGSMITH_TRACING", "false").lower() in ("true", "1") or os.getenv("LANGCHAIN_TRACING_V2", "false").lower() in ("true", "1")
if langsmith_key and tracing_enabled:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_API_KEY"] = langsmith_key
    os.environ["LANGCHAIN_API_KEY"] = langsmith_key
    project_name = os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT") or "tripmate-ai"
    os.environ["LANGSMITH_PROJECT"] = project_name
    os.environ["LANGCHAIN_PROJECT"] = project_name
    endpoint = os.getenv("LANGSMITH_ENDPOINT") or os.getenv("LANGCHAIN_ENDPOINT") or "https://api.smith.langchain.com"
    os.environ["LANGSMITH_ENDPOINT"] = endpoint
    os.environ["LANGCHAIN_ENDPOINT"] = endpoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TripMateAI")
if langsmith_key and tracing_enabled:
    logger.info(f"LangSmith Tracing active for project: {os.getenv('LANGSMITH_PROJECT')}")


# ---------------------------------------------------------
# Part 2: Database URL Helper
# ---------------------------------------------------------
def get_database_url() -> Optional[str]:
    """
    Returns the PostgreSQL connection string.
    Ensures sslmode=require for Render hosted PostgreSQL.
    """
    url = os.getenv("DATABASE_URL")
    if not url or url.strip() in ("", "your_database_url_here"):
        return None
    if "sslmode" not in url and ("render.com" in url or "postgres" in url):
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


# ---------------------------------------------------------
# Part 3: LLM and State
# ---------------------------------------------------------
def get_llm():
    """
    Initializes ChatGroq with Llama-3.3-70b-versatile.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key.strip() in ("", "your_groq_key"):
        return None
    return ChatGroq(model="openai/gpt-oss-120b", api_key=api_key, temperature=0.3)


class TravelState(TypedDict):
    messages: Annotated[list, operator.add]  # Reducer: appends messages, does not overwrite
    user_query: str
    flight_result: str
    hotel_result: str
    itinerary_result: str
    llm_calls: int


# ---------------------------------------------------------
# Part 4: The Four Agents
# ---------------------------------------------------------
def flight_agent(state: TravelState):
    """
    Flight Agent: Queries Aviationstack to discover available flights.
    Does not consume LLM calls.
    """
    logger.info("[Flight Agent] Fetching flight options...")
    flights = search_flights(state["user_query"])
    return {
        "flight_result": str(flights),
        "messages": [AIMessage(content="Flight results fetched successfully")],
        "llm_calls": state.get("llm_calls", 0),
    }


def hotel_agent(state: TravelState):
    """
    Hotel Agent: Uses Tavily Web Search to find top-rated hotels within budget.
    Does not consume LLM calls.
    """
    logger.info("[Hotel Agent] Searching hotels & accommodations...")
    hotels = tavily_search("best hotels and accommodations for " + state["user_query"])
    return {
        "hotel_result": str(hotels),
        "messages": [AIMessage(content="Hotel information fetched successfully")],
    }


def itinerary_agent(state: TravelState):
    """
    Itinerary Agent: Synthesizes user requirements, flight schedules,
    and hotel locations into a practical, day-by-day plan using Groq LLM.
    """
    logger.info("[Itinerary Agent] Formulating day-by-day itinerary...")
    llm = get_llm()
    prompt = (
        "Create a comprehensive, day-by-day travel itinerary based on this data:\n\n"
        f"User request: {state['user_query']}\n\n"
        f"Flight information: {state['flight_result']}\n\n"
        f"Hotel information: {state['hotel_result']}\n\n"
        "Make the itinerary realistic, practical, budget-conscious, and easy to follow. "
        "Include morning, afternoon, and evening suggestions for each day."
    )

    if llm:
        reply = llm.invoke([
            SystemMessage(content="You are an expert travel planner and local tour guide."),
            HumanMessage(content=prompt),
        ])
        itinerary_text = reply.content
    else:
        itinerary_text = (
            "Day 1: Arrival, airport transfer, hotel check-in, and welcome dinner.\n"
            "Day 2: City landmark exploration, local culture and culinary tour.\n"
            "Day 3: Scenic nature tour, viewpoint visits, and evening leisure.\n"
            "Day 4: Heritage temples, local craft bazaars, and sunset panorama.\n"
            "Day 5: Adventure excursion or day trip to nearby valley.\n"
            "Day 6: Souvenir shopping, traditional spa or leisure activities.\n"
            "Day 7: Breakfast, hotel checkout, transfer to airport for departure."
        )

    return {
        "itinerary_result": itinerary_text,
        "messages": [AIMessage(content="Itinerary created successfully")],
        "llm_calls": state.get("llm_calls", 0) + (1 if llm else 0),
    }


def final_agent(state: TravelState):
    """
    Final Response Agent: Formats all findings into a polished,
    executive-ready travel package with 7 standardized sections.
    """
    logger.info("[Final Agent] Formatting complete travel plan...")
    llm = get_llm()
    prompt = (
        "Generate a complete, structured travel package for the user based on the gathered details.\n\n"
        f"User request: {state['user_query']}\n"
        f"Flights: {state['flight_result']}\n"
        f"Hotels: {state['hotel_result']}\n"
        f"Itinerary: {state['itinerary_result']}\n\n"
        "Format the answer beautifully using clear Markdown headings with these exact 7 sections:\n"
        "1. Trip Summary\n"
        "2. Flight Information\n"
        "3. Hotel Suggestions (with estimated price per night)\n"
        "4. Day-by-Day Itinerary\n"
        "5. Estimated Budget Breakdown\n"
        "6. Final Recommendations\n"
        "7. Important Notes (visas, currency, best time to visit)"
    )

    if llm:
        reply = llm.invoke([
            SystemMessage(content="You are a professional AI travel booking consultant."),
            HumanMessage(content=prompt),
        ])
        final_answer = reply.content
    else:
        final_answer = f"""# TripMate AI: Travel Plan
## 1. Trip Summary
Destination and Trip based on: {state['user_query']}

## 2. Flight Information
{state['flight_result']}

## 3. Hotel Suggestions
{state['hotel_result']}

## 4. Day-by-Day Itinerary
{state['itinerary_result']}

## 5. Estimated Budget Breakdown
- Flights: Approx 30-40% of budget
- Accommodation: Approx 30% of budget
- Food & Sightseeing: Approx 20% of budget
- Emergency & Local Transit: Approx 10% of budget

## 6. Final Recommendations
- Book tickets at least 3-4 weeks in advance for optimal pricing.
- Keep digital and printed copies of all passports and travel insurance.

## 7. Important Notes
- Check entry visa requirements prior to travel.
- Keep local currency cash on hand for local taxis and markets.
*(Note: To unlock live Groq LLM generations, add your GROQ_API_KEY to .env)*
"""

    return {
        "messages": [AIMessage(content=final_answer)],
        "llm_calls": state.get("llm_calls", 0) + (1 if llm else 0),
    }


# ---------------------------------------------------------
# Part 5: Build Graph and Attach PostgreSQL / Memory Checkpointer
# ---------------------------------------------------------
builder = StateGraph(TravelState)

builder.add_node("flight_agent", flight_agent)
builder.add_node("hotel_agent", hotel_agent)
builder.add_node("itinerary_agent", itinerary_agent)
builder.add_node("final_agent", final_agent)

builder.add_edge(START, "flight_agent")
builder.add_edge("flight_agent", "hotel_agent")
builder.add_edge("hotel_agent", "itinerary_agent")
builder.add_edge("itinerary_agent", "final_agent")
builder.add_edge("final_agent", END)


def initialize_graph():
    """
    Initializes checkpointer:
    Uses PostgresSaver when DATABASE_URL is configured and reachable;
    Gracefully falls back to MemorySaver for seamless local development.
    """
    db_url = get_database_url()
    if db_url:
        try:
            import psycopg
            from psycopg.rows import dict_row
            from langgraph.checkpoint.postgres import PostgresSaver

            logger.info("Connecting to PostgreSQL checkpointer on Render...")
            conn = psycopg.connect(db_url, autocommit=True, row_factory=dict_row)
            checkpointer = PostgresSaver(conn)
            checkpointer.setup()  # Creates checkpoints table if not present
            logger.info("PostgreSQL checkpointer connected & setup successfully.")
            return builder.compile(checkpointer=checkpointer)
        except Exception as e:
            logger.warning(
                f"Could not connect to PostgreSQL ({e}). Falling back to in-memory checkpointer."
            )

    from langgraph.checkpoint.memory import MemorySaver
    logger.info("Using in-memory MemorySaver checkpointer.")
    return builder.compile(checkpointer=MemorySaver())


travel_graph = initialize_graph()


# ---------------------------------------------------------
# Part 6: Execution Function Invoked by API / CLI
# ---------------------------------------------------------
def run_travel_agent(user_input: str, thread_id: Optional[str] = None):
    """
    Executes the travel agent workflow for a given user query and conversation thread_id.
    """
    if not thread_id:
        thread_id = str(uuid.uuid4())

    config = {
        "configurable": {"thread_id": thread_id},
        "run_name": "TripMate Multi-Agent Workflow",
        "metadata": {
            "thread_id": thread_id,
            "project": "tripmate-ai",
            "user_query": user_input,
        },
    }

    result = travel_graph.invoke(
        {
            "messages": [HumanMessage(content=user_input)],
            "user_query": user_input,
            "flight_result": "",
            "hotel_result": "",
            "itinerary_result": "",
            "llm_calls": 0,
        },
        config=config,
    )

    return {
        "thread_id": thread_id,
        "answer": result["messages"][-1].content,
        "flight_result": result.get("flight_result", ""),
        "hotel_result": result.get("hotel_result", ""),
        "itinerary_result": result.get("itinerary_result", ""),
        "llm_calls": result.get("llm_calls", 0),
    }
