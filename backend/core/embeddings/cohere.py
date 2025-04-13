import httpx
import logging
from config.settings import settings
from llama_index.core.schema import NodeWithScore, MetadataMode

COHERE_RERANK_API_ENDPOINT = "https://api.cohere.com/v2/rerank"
COHERE_RERANK_MODEL = "rerank-v3.5"

logger = logging.getLogger(__name__)


def rerank_nodes(query: str, nodes: list[NodeWithScore], top_n: int = 5) -> list[str]:
    """
    Rerank documents using Cohere's rerank API.

    Args:
        query: The query to rerank against
        nodes: List of llama_index nodes to rerank
        top_n: Number of top nodes to return

    Returns:
        List of reranked nodes
    """
    if not nodes:
        logger.warning("Empty documents list provided to rerank_documents")
        return []

    headers = {
        "Authorization": f"Bearer {settings.COHERE_API_KEY}",
        "Content-Type": "application/json",
    }

    docs = [node.get_content(metadata_mode=MetadataMode.NONE) for node in nodes]

    data = {
        "model": COHERE_RERANK_MODEL,
        "query": query,
        "documents": docs,
        "top_n": top_n,
    }

    try:
        _response = httpx.post(
            url=COHERE_RERANK_API_ENDPOINT,
            headers=headers,
            json=data,
            timeout=30.0,
        )
        _response.raise_for_status()

        response_data = _response.json()  # return results, id (opt) and meta (opt)

        # Extract the reranked nodes
        if "results" in response_data:
            # Return the nodes in reranked order
            return [nodes[result["index"]] for result in response_data["results"]]
        else:
            logger.error(
                f"Unexpected response structure from Cohere API: {response_data}"
            )
            return nodes[:top_n]  # Fallback to original order

    except httpx.HTTPStatusError as e:
        logger.error(f"Cohere API error: {str(e)}")
        logger.error(f"Response content: {e.response.content}")
        # Fallback to original order if API fails
        return nodes[:top_n]
    except Exception as e:
        logger.error(f"Error in rerank_nodes: {str(e)}")
        # Fallback to original order if any other error occurs
        return nodes[:top_n]
