"""
Embedding utilities using Google's Gemini models.
"""

from typing import List, Optional, Dict, Any
import logging
from google.genai import Client as GoogleGenAIClient, types as GoogleGenAITypes
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.callbacks.base import CallbackManager
from config.settings import settings

logger = logging.getLogger(__name__)


DEFAULT_TEXT_EMBEDDING_MODEL = "gemini-embedding-exp-03-07"
DEFAULT_TASK_TYPE = "RETRIEVAL_DOCUMENT"
DEFAULT_OUTPUT_DIMENSIONALITY = 1536
DEFAULT_EMBED_BATCH_SIZE = 10


class GoogleGenAIEmbedding(BaseEmbedding):
    def __init__(
        self,
        model_name: str = DEFAULT_TEXT_EMBEDDING_MODEL,
        embedding_config: Optional[GoogleGenAITypes.EmbedContentConfigOrDict] = None,
        embed_batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
        callback_manager: Optional[CallbackManager] = None,
        **kwargs: Any
    ):
        super().__init__(
            model_name=model_name,
            embedding_config=embedding_config,
            embed_batch_size=embed_batch_size,
            callback_manager=callback_manager,
            **kwargs,
        )
        self._client = GoogleGenAIClient(api_key=settings.GOOGLE_GEMINI_API_KEY)

    @classmethod
    def class_name(cls) -> str:
        return "GeminiEmbedding"

    def _embed_texts(
        self,
        texts: List[str],
        model_name: str = DEFAULT_TEXT_EMBEDDING_MODEL,
        task_type: str = DEFAULT_TASK_TYPE,
        output_dimensionality: int = DEFAULT_OUTPUT_DIMENSIONALITY,
    ) -> List[List[float]]:
        """
        Generate text embeddings for a single text or batch of texts.

        Args:
            contents: Single text string or list of text strings to embed
            task_type: The type of task for which embeddings are generated

        Returns:
            For a single input: A single embedding vector
            For a batch input: A list of embedding vectors, one for each input text
        """
        response = self._client.models.embed_content(
            model=model_name,
            contents=texts,
            config=GoogleGenAITypes.EmbedContentConfig(
                task_type=task_type, output_dimensionality=output_dimensionality
            ),
        )

        return [embedding.values for embedding in response.embeddings]

    def _get_query_embedding(self, query: str) -> List[float]:
        """Get query embedding."""
        return self._embed_texts([query], task_type="RETRIEVAL_QUERY")[0]

    def _get_text_embedding(self, text: str) -> List[float]:
        """Get text embedding."""
        return self._embed_texts([text])[0]

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get text embeddings."""
        return self._embed_texts(texts)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        """The asynchronous version of _get_query_embedding."""
        return (await self._aembed_texts([query], task_type="RETRIEVAL_QUERY"))[0]

    async def _aget_text_embedding(self, text: str) -> List[float]:
        """Asynchronously get text embedding."""
        return (await self._aembed_texts([text], task_type="RETRIEVAL_DOCUMENT"))[0]

    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Asynchronously get text embeddings."""
        return await self._aembed_texts(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

    def embed_text(self, text: str) -> List[float]:
        return self._get_text_embedding(text)
