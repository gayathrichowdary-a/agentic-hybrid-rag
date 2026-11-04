# tools/web_search.py

import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def search_web(query):
    if not TAVILY_API_KEY:
        return "Web search is unavailable because TAVILY_API_KEY is missing."

    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)

        response = client.search(
            query=query,
            search_depth="basic",
            max_results=3
        )

        results = response.get("results", [])

        if not results:
            return "No web results found."

        context = ""

        for item in results:
            title = item.get("title", "")
            content = item.get("content", "")
            url = item.get("url", "")

            context += f"""
TITLE: {title}

CONTENT:
{content}

SOURCE:
{url}

-------------------------
"""

        return context

    except Exception as e:
        return f"Web search failed: {str(e)}"