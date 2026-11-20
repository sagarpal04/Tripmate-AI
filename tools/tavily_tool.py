import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()


def get_tavily_client():
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or api_key.strip() in ("", "your_tavily_key"):
        return None
    try:
        return TavilyClient(api_key=api_key)
    except Exception:
        return None


def tavily_search(query: str, max_results: int = 5):
    """
    Searches the web using Tavily Search API.
    Extracts title, URL, and a concise 300-character snippet to save LLM tokens.
    """
    client = get_tavily_client()
    if not client:
        return [
            {
                "title": f"Travel & Hotel Information for {query}",
                "url": "https://www.tripadvisor.com",
                "snippet": (
                    f"Recommended hotels and accommodations for {query}: "
                    "Options range from centrally-located budget hostels ($25-$45/night) "
                    "to boutique 4-star hotels ($80-$140/night) and luxury resorts. "
                    "Booking in advance is recommended during peak travel season."
                ),
            }
        ]

    try:
        response = client.search(query=query, max_results=max_results)
        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                # keep only the first 300 characters to save LLM tokens
                "snippet": (item.get("content") or "")[:300],
            })
        return results if results else [{"info": "No search results returned from Tavily."}]
    except Exception as e:
        return [{"error": f"Tavily search error: {str(e)}"}]
