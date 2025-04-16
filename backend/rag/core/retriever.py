"""
Enhanced retrieval functionality for the structured RAG system.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Type
from pydantic import BaseModel, Field
from llama_index.core.base.response.schema import RESPONSE_TYPE
from llama_index.llms.groq import Groq
from llama_index.core.llms import LLM
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.embeddings import BaseEmbedding
from config import RETRIEVAL_CONFIG
from utils.context_processing import prune_context_to_fit_tokens

logger = logging.getLogger(__name__)

class DatasetItem(BaseModel):
    """Custom data schema from the user"""
    pass


# Define Pydantic models for our structured output with citations
class CitationMetadata(BaseModel):
    """Metadata about the source document for a citation"""

    title: Optional[str] = Field(
        description="Title of the source document", default=None
    )
    page_number: Optional[int] = Field(
        description="Page number in the source document", default=None
    )
    doi: Optional[str] = Field(
        description="DOI identifier for the source", default=None
    )
    authors: Optional[List[str]] = Field(description="List of authors", default=None)
    url: Optional[str] = Field(description="URL of the source", default=None)
    published_date: Optional[str] = Field(
        description="Publication date of the source", default=None
    )


class Citation(BaseModel):
    """Citation information for a piece of content"""

    source_id: str = Field(description="ID of the source document")
    text_span: str = Field(description="Text span from the document used as evidence")
    confidence: float = Field(description="Confidence score (0-1)")
    metadata: CitationMetadata = Field(
        description="Additional metadata from the source",
        default_factory=CitationMetadata,
    )


class StructuredOutputItem(BaseModel):
    """A single structured output item with citations"""

    item: DatasetItem = Field(description="The content or finding as a structured item")
    citations: List[Citation] = Field(description="Citations supporting the item")


class CustomRetriever:
    """Retriever for documents with context management."""

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        embed_model: BaseEmbedding,
        similarity_top_k: int = RETRIEVAL_CONFIG["initial_similarity_top_k"],
        max_context_tokens: int = RETRIEVAL_CONFIG["max_context_tokens"],
    ):
        """
        Initialize the enhanced retriever.

        Args:
            vector_store: The vector store to retrieve from
            embed_model: Embedding model to use
            similarity_top_k: Number of similar documents to retrieve
            max_context_tokens: Maximum token count for context
        """
        self.vector_store = vector_store
        self.embed_model = embed_model
        self.similarity_top_k = similarity_top_k
        self.max_context_tokens = max_context_tokens

        # Create the vector index
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=embed_model,
        )

    def query_structured_response_with_citations(
        self, query: str, llm: LLM, output_cls: Type[BaseModel]
    ) -> RESPONSE_TYPE:
        """
        Generate a structured response from the query using llama-index's structured llm and query engine.
        The response will include citations to the source nodes (nodes with metadata) that were used to generate the response.

        Args:
            query: The query to generate a structured response for
            llm: The llm to use for the structured response
            output_cls: The pydantic model to use for the structured response

        Returns:
            The structured response
        """
        # TODO: add custom qa template and refine template to the query engine
        structured_llm = llm.as_structured_llm(output_cls=output_cls)
        query_engine = self.index.as_query_engine(
            llm=structured_llm, similarity_top_k=self.similarity_top_k, node_postprocessors=None
        )
        query_response = query_engine.query(query)
        return query_response

    def retrieve_for_specific_fields(
        self, original_query: str, field_queries: List[str], existing_context: str
    ) -> str:
        """
        Perform targeted retrieval for specific schema fields.

        Args:
            original_query: The original user query
            field_queries: List of queries for specific fields
            existing_context: Context already retrieved

        Returns:
            str: Additional context for the missing fields
        """
        # Use fewer results for follow-up queries to avoid context bloat
        follow_up_k = RETRIEVAL_CONFIG["follow_up_similarity_top_k"]
        additional_contexts = []

        for field_query in field_queries:
            # Create a combined query that maintains original context
            combined_query = f"{original_query} - Specifically: {field_query}"

            # Create field-specific retriever with smaller k
            field_retriever = self.index.as_retriever(similarity_top_k=follow_up_k)

            try:
                field_nodes = field_retriever.retrieve(combined_query)

                if field_nodes:
                    # Format the retrieved context for this field
                    field_context = "\n\n".join(
                        [
                            f"[Field: {field_query}] {node.get_content(metadata_mode='none')}"
                            for node in field_nodes
                        ]
                    )
                    additional_contexts.append(field_context)

            except Exception as e:
                logger.error(f"Error retrieving for field query '{field_query}': {e}")
                continue

        # Combine all additional contexts
        if not additional_contexts:
            return ""

        additional_context_str = "\n\n".join(additional_contexts)

        # Ensure the combined context fits within token limits
        total_context = f"{existing_context}\n\n--- ADDITIONAL FIELD-SPECIFIC INFORMATION ---\n\n{additional_context_str}"
        return prune_context_to_fit_tokens(total_context, self.max_context_tokens)
