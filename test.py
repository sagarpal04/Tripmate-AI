import sys
from backend import run_travel_agent

def main():
    print("=" * 60)
    print("TripMate AI - Local Multi-Agent Workflow Test")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        query = "Plan a complete 7 days India trip from Bangladesh including flights, hotel and sightseeing under 2 lakhs"
        print(f"Auto-running query: {query}\n")
    else:
        try:
            user_input = input("Enter your trip request (Press Enter for default): ").strip()
            query = user_input if user_input else "Plan a 7 day Nepal trip from Bangladesh under 2 lakhs"
        except (EOFError, KeyboardInterrupt):
            query = "Plan a 7 day Nepal trip from Bangladesh under 2 lakhs"
            print(f"\nUsing default query: {query}")

    print("\nExecuting LangGraph Multi-Agent Flow...")
    print("• Flight Agent -> Hotel Agent -> Itinerary Agent -> Final Agent\n")

    response = run_travel_agent(query, thread_id="test-user")

    print("\n" + "=" * 60)
    print("FINAL GENERATED TRAVEL PLAN")
    print("=" * 60)
    print(response["answer"])

    print("\n" + "-" * 60)
    print(f"Thread ID : {response['thread_id']}")
    print(f"LLM Calls : {response['llm_calls']}")
    print("-" * 60)

if __name__ == "__main__":
    main()
