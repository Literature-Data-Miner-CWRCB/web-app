import logging
from typing import List, Dict, Any, Optional, Mapping
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Filter,
    FieldCondition,
    MatchValue,
    Range,
    Prefetch,
)
from config.settings import settings
from core.embeddings.gemini import GoogleGenAIEmbedding


logger = logging.getLogger(__name__)


class QdrantVectorStore:
    """Component to retrieve relevant document chunks from Qdrant."""

    MAX_RETRIEVED_CHUNKS = 10

    def __init__(self, collection_name: str):
        self.qdrant_client = QdrantClient(
            url=settings.QDRANT_HOST_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.collection_name = collection_name
        self.dense_embedding_model = GoogleGenAIEmbedding()
        # self.sparse_embedding_model = SparseEmbedding()
        # self.late_interaction_model = LateInteractionEmbedding()

    def _prepare_filter(self, filters: Optional[Dict[str, Any]]) -> Optional[Filter]:
        if not filters:
            return None

        filter_conditions = []
        for field, value in filters.items():
            if field == "source":  # Cross-ref, Scholarly, Arxiv, etc.
                filter_conditions.append(
                    FieldCondition(key=field, match=MatchValue(value=value))
                )
            elif field == "min_date":  # Filter by minimum date of publication
                filter_conditions.append(
                    FieldCondition(key=field, range=Range(gte=value))
                )
            elif field == "max_date":  # Filter by maximum date of publication
                filter_conditions.append(
                    FieldCondition(key=field, range=Range(lte=value))
                )

        if filter_conditions:
            return Filter(should=filter_conditions)
        return None

    def retrieve(
        self,
        query: str,
        top_k: int = MAX_RETRIEVED_CHUNKS,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """ """
        try:
            # Convert query to embedding vector
            query_vector = self.dense_embedding_model.embed_query(query)

            # Prepare Qdrant filter if provided
            query_filter = self._prepare_filter(filters)

            qdrant_response = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                using="dense",
                limit=top_k,
                with_payload=True,
                query_filter=query_filter,
            )

            chunks = []
            for result in qdrant_response.points:
                chunk = {
                    "id": result.id,
                    "score": result.score,
                    "content": result.payload.get("content", ""),
                    "metadata": {
                        k: v for k, v in result.payload.items() if k != "content"
                    },
                }
                chunks.append(chunk)

            logger.info(f"Retrieved {len(chunks)} chunks from vector database")
            return chunks

        except Exception as e:
            logger.error(f"Error retrieving chunks: {str(e)}")
            return []

    def retrieve_by_group(
        self,
        query: str,
        top_k: int = MAX_RETRIEVED_CHUNKS,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            # Convert query to embedding vector
            query_vector = self.dense_embedding_model.embed_query(query)

            # Prepare Qdrant filter if provided
            query_filter = self._prepare_filter(filters)

            query_response = self.qdrant_client.query_points_groups(
                collection_name=self.collection_name,
                group_by="doi",
                query=query_vector,
                using="dense",
                limit=top_k,
                with_payload=True,
                query_filter=query_filter,
            )

            pass

        except Exception as e:
            logger.error(f"Error retrieving chunks: {str(e)}")
            return []

    def hybrid_search(
        self,
        query: str,
        top_k: int = MAX_RETRIEVED_CHUNKS,
        filters: Optional[Mapping[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks based on vector similarity and optional filters using hybrid search with reranking.

        Args:
            query: The user query
            top_k: Maximum number of chunks to retrieve
            filters: Optional metadata filters

        Returns:
            List of document chunks with their metadata
        """
        try:
            # Convert query to embedding vector
            dense_query_vector = self.embedding_model.embed_query(query)
            sparse_query_vector = self.sparse_embedding_model.embed_query(query)
            late_query_vector = self.late_interaction_model.embed_query(query)

            # Prepare Qdrant filter if provided
            qdrant_filter = self._prepare_filter(filters)

            # Prepare query for hybrid search
            prefetch = [
                Prefetch(
                    query=dense_query_vector,
                    using="dense",
                    limit=20,
                    filter=qdrant_filter,
                ),
                Prefetch(
                    query=sparse_query_vector,
                    using="sparse",
                    limit=20,
                    filter=qdrant_filter,
                ),
            ]

            # Search in vector database
            qdrant_response = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                prefetch=prefetch,
                query=late_query_vector,
                using="late_interaction",
                limit=top_k,
                with_payload=True,
            )

            # Process results
            chunks = []
            for result in qdrant_response.points:
                chunk = {
                    "id": result.id,
                    "score": result.score,
                    "content": result.payload.get("content", ""),
                    "metadata": {
                        k: v for k, v in result.payload.items() if k != "content"
                    },
                }
                chunks.append(chunk)

            logger.info(f"Retrieved {len(chunks)} chunks from vector database")
            return chunks

        except Exception as e:
            logger.error(f"Error retrieving chunks: {str(e)}")
            return []
