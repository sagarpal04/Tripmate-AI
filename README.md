# TripMate AI: Multi-Agent Travel Planner ✈️🗺️

> **A beginner-friendly guide to building and deploying an end-to-end multi-agent AI travel planner** using **LangGraph**, **Groq (Llama 3.3 70B)**, **Tavily Search**, **Aviationstack API**, **PostgreSQL on Render**, and **Streamlit**.

---

## 1. What are we building?

TripMate AI takes a single natural language sentence such as:
> *"Plan a 7 day Nepal trip from Bangladesh under 2 lakhs"*

and autonomously orchestrates four specialized agents to return:
- **Trip Summary**
- **Live Flight Options & Schedules**
- **Hotel Suggestions with Estimated Price per Night**
- **Day-by-Day Practical Itinerary** (Morning, Afternoon, Evening)
- **Estimated Budget Breakdown**
- **Final Recommendations & Important Notes** (Visas, currency, local customs)
- **Downloadable Markdown Dossier Button**

### Why Multi-Agent?
A single LLM prompt attempting to search live flights, lookup recent hotel rates, construct an itinerary, and balance a budget frequently hallucinates or hits token limitations.

In a **multi-agent architecture**, each agent acts like a member of a travel agency team:

| Agent | Responsibility | Primary Tool / Engine |
| :--- | :--- | :--- |
| **Flight Agent** | Locates departure and destination routes and live flight status | Aviationstack API |
| **Hotel Agent** | Identifies top accommodations within budget | Tavily Search API |
| **Itinerary Agent** | Formulates realistic daily schedule and activities | Groq LLM (Llama 3.3 70B) |
| **Final Agent** | Synthesizes all findings into a clean, executive travel dossier | Groq LLM (Llama 3.3 70B) |

---

## 2. Architecture & Data Flow

```
   User Prompt
        │
        ▼
   ┌─────────┐
   │  START  │
   └────┬────┘
        │
        ▼
┌──────────────┐     queries     ┌──────────────────┐
│ Flight Agent ├────────────────►│ Aviationstack API│
└───────┬──────┘                 └──────────────────┘
        │
        ▼
┌──────────────┐     queries     ┌──────────────────┐
│ Hotel Agent  ├────────────────►│  Tavily Search   │
└───────┬──────┘                 └──────────────────┘
        │
        ▼
┌─────────────────┐  generates   ┌──────────────────┐
│ Itinerary Agent ├─────────────►│ Groq (Llama 3.3) │
└───────┬─────────┘              └──────────────────┘
        │
        ▼
┌──────────────┐     formats     ┌──────────────────┐
│ Final Agent  ├────────────────►│ Groq (Llama 3.3) │
└───────┬──────┘                 └──────────────────┘
        │
        ▼
   ┌─────────┐
   │   END   │
   └─────────┘
        │
        ▼
Checkpoints saved to PostgreSQL (Render) after each step
```

---

## 3. Technology Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Agent Orchestration** | LangGraph | Graph state machine with nodes, edges, and checkpointers |
| **LLM Inference** | Groq + Llama 3.3 70B | Ultra-fast inference with free tier |
| **Web Search** | Tavily | Real-time, token-optimized hotel and destination search |
| **Flight Tracking** | Aviationstack | Real-time global flight data and schedules |
| **Persistence / Memory** | PostgreSQL (Render) | Saves thread checkpoints after every node |
| **User Interface** | Streamlit | Pure Python responsive UI with live progress & tabbed view |
| **Containerization** | Docker | Container for local execution and cloud deployment |
| **Cloud Hosting** | Render | Managed web service and cloud database |

---

## 4. Clean Project Directory Structure

```
tripmate-ai/
├── tools/
│   ├── __init__.py
│   ├── flight_tools.py      # Aviationstack API search & country resolution
│   └── tavily_tool.py       # Tavily web search with token trimming
├── backend.py               # LangGraph workflow, 4 agent nodes & PostgresSaver
├── streamlit_app.py         # Streamlit UI (Pure Python interface)
├── test.py                  # CLI test runner for multi-agent graph
├── requirements.txt         # Dependencies
├── Dockerfile               # Container build file
├── .dockerignore            # Files excluded from Docker builds
├── .env.example             # Template for API keys and DB connection
├── .env                     # Local environment settings
├── .gitignore               # Ignored git files
└── README.md                # Documentation
```

---

## 5. Local Setup Guide

### Step 5.1: Create and activate virtual environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### Step 5.2: Install dependencies
```powershell
pip install -r requirements.txt
```

---

## 6. Running the Streamlit Application

```powershell
streamlit run streamlit_app.py
```
Streamlit opens automatically at **`http://localhost:8501`**.

To test via terminal CLI without the UI:
```powershell
python test.py --auto
```

---

## 7. Cloud Deployment on Render (with Docker)

1. Connect your repository to Render (**New Web Service**).
2. Render detects the `Dockerfile` automatically.
3. Add your environment variables in the Render dashboard:
   - `GROQ_API_KEY`
   - `TAVILY_API_KEY`
   - `AVIATIONSTACK_API_KEY`
   - `DEFAULT_ORIGIN`
   - `DATABASE_URL` (Internal database URL)
4. Deploy! The app will be live on port 8501.
