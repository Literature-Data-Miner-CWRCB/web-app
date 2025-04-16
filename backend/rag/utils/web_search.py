"""
Web search utility for augmenting RAG with web results.
"""

from typing import List, Dict, Any, Optional
import logging
import time
import random

from ..config import WEB_SEARCH_CONFIG

logger = logging.getLogger(__name__)


class WebSearchTool:
    """
    Tool for searching the web to supplement RAG retrieval.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_results: int = WEB_SEARCH_CONFIG["max_results"],
    ):
        """
        Initialize the web search tool.

        Args:
            api_key: API key for search provider
            max_results: Maximum results to return
        """
        self.api_key = api_key or WEB_SEARCH_CONFIG["api_key"]
        self.max_results = max_results
        self._setup_search_client()

    def _setup_search_client(self):
        """Set up the search client based on available libraries."""
        self.search_client = None

        # Try to set up SERP API client
        try:
            from serpapi import GoogleSearch

            self.search_client = "serpapi"
            self.GoogleSearch = GoogleSearch
            logger.info("Using SerpAPI for web search")
        except ImportError:
            pass

        # Try to set up Tavily client if SERP API not available
        if not self.search_client:
            try:
                import tavily

                self.search_client = "tavily"
                tavily.api_key = self.api_key
                self.tavily = tavily
                logger.info("Using Tavily for web search")
            except ImportError:
                pass

        if not self.search_client:
            logger.warning("No web search client available. Install serpapi or tavily.")

    def search(self, query: str) -> List[Dict[str, str]]:
        """
        Search the web for relevant information.

        Args:
            query: The search query

        Returns:
            List of search results with source and content
        """
        if not self.search_client:
            logger.error("No web search client configured")
            return []

        try:
            if self.search_client == "serpapi":
                return self._search_with_serpapi(query)
            elif self.search_client == "tavily":
                return self._search_with_tavily(query)
            else:
                return []
        except Exception as e:
            logger.error(f"Error during web search: {e}", exc_info=True)
            return []

    def _search_with_serpapi(self, query: str) -> List[Dict[str, str]]:
        """
        Perform search using SerpAPI.

        Args:
            query: Search query

        Returns:
            Formatted search results
        """
        params = {"q": query, "hl": "en", "gl": "us", "api_key": self.api_key}

        search = self.GoogleSearch(params)
        results = search.get_dict()

        formatted_results = []

        # Process organic results
        if "organic_results" in results:
            for i, result in enumerate(results["organic_results"]):
                if i >= self.max_results:
                    break

                formatted_results.append(
                    {
                        "source": result.get("link", ""),
                        "title": result.get("title", ""),
                        "content": result.get("snippet", ""),
                    }
                )

        return formatted_results

    def _search_with_tavily(self, query: str) -> List[Dict[str, str]]:
        """
        Perform search using Tavily.

        Args:
            query: Search query

        Returns:
            Formatted search results
        """
        response = self.tavily.search(
            query=query, search_depth="basic", max_results=self.max_results
        )

        formatted_results = []

        if "results" in response:
            for result in response["results"]:
                formatted_results.append(
                    {
                        "source": result.get("url", ""),
                        "title": result.get("title", ""),
                        "content": result.get("content", ""),
                    }
                )

        return formatted_results
