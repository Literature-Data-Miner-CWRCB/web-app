import json
import time
import enum
import logging
import tiktoken
from typing import List, Dict, Any, Optional, Union, TypeVar, Generic
from pydantic import BaseModel, Field, create_model
import instructor
from qdrant_client import QdrantClient
from groq import Groq
from config.settings import settings
from llama_index.core.schema import BaseNode, MetadataMode
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex
from core.embeddings.gemini import GoogleGenAIEmbedding

logger = logging.getLogger(__name__)

# Configuration
MAX_TOKENS = 120000  # Llama 3.3 70B context window
EXTRACTION_HEADROOM = 0.15  # Reserve 15% for schema instructions
CHUNK_OVERLAP = 0.15  # Default overlap between chunks
MAX_RETRIEVED_CHUNKS = 50  # Maximum chunks to retrieve initially
BATCH_SIZE = 10  # Number of chunks to process together
SIMILARITY_THRESHOLD = 0.85  # Threshold for semantic similarity
LLM_MODEL = "llama-3.3-70b-versatile"  # Groq model ID


class ContextManager:
    """Component to manage document contexts for efficient processing."""

    def __init__(
        self,
        max_tokens: int = MAX_TOKENS,
        context_headroom: float = EXTRACTION_HEADROOM,
    ):
        self.max_tokens = max_tokens
        self.context_headroom = context_headroom
        self.effective_token_limit = int(max_tokens * (1 - context_headroom))

    def prepare_context(self, nodes: List[BaseNode]) -> str:
        context_parts = []
        for node in nodes:
            title = node.metadata.get("TITLE")
            authors = node.metadata.get("AUTHORS")
            year = node.metadata.get("YEAR")
            source = node.metadata.get("SOURCE")
            doi = node.metadata.get("DOI")
            page_number = node.metadata.get("PAGE")
            text = node.get_content(metadata_mode=MetadataMode.NONE)
            context = f"""
            [DOCUMENT METADATA]
            -------------------
            Title: {title}
            Page: {page_number}
            Authors: {authors}
            Year: {year}
            Source: {source}
            DOI: {doi}
            -------------------
            [DOCUMENT TEXT]
            -------------------
            {text}
            -------------------
            """.strip()
            context_parts.append(context)

        return "\n\n".join(context_parts)

    def prepare_group_context(
        self,
        batch: List[Dict[str, Any]],
        previously_extracted_entities: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Prepare context from a batch of chunks for LLM processing.

        Args:
            batch: List of chunks to include in context
            previously_extracted_entities: Optional entities from previous batches

        Returns:
            Formatted context string
        """
        context_parts = []

        # Add previously extracted entities if provided
        if previously_extracted_entities and len(previously_extracted_entities) > 0:
            context_parts.append("# Previously Extracted Information")
            context_parts.append(json.dumps(previously_extracted_entities, indent=2))
            context_parts.append("\n# Current Document Content")

        # Group chunks by document
        chunks_by_doc = {}
        for chunk in batch:
            doc_id = chunk["metadata"].get("document_id", "unknown")
            doc_title = chunk["metadata"].get("title", f"Document {doc_id}")

            if doc_id not in chunks_by_doc:
                chunks_by_doc[doc_id] = {"title": doc_title, "chunks": []}
            chunks_by_doc[doc_id]["chunks"].append(chunk)

        # Format each document's chunks
        for doc_id, doc_info in chunks_by_doc.items():
            context_parts.append(f"## {doc_info['title']}")

            # Sort chunks by position if available
            doc_info["chunks"].sort(key=lambda x: x["metadata"].get("chunk_index", 0))

            # Add each chunk with metadata
            for i, chunk in enumerate(doc_info["chunks"]):
                chunk_index = chunk["metadata"].get("chunk_index", i)
                context_parts.append(f"[Chunk {chunk_index}]")
                context_parts.append(chunk["content"])
                context_parts.append("")  # Empty line

        return "\n".join(context_parts)


# class Deduplicator:
#     """Component for entity deduplication across extraction results."""

#     def __init__(self, similarity_threshold: float = SIMILARITY_THRESHOLD):
#         self.similarity_threshold = similarity_threshold

#     def deduplicate_entities(
#         self, entities: List[Dict[str, Any]], entity_keys: Optional[List[str]] = None
#     ) -> List[Dict[str, Any]]:
#         """
#         Deduplicate entities based on semantic similarity.

#         Args:
#             entities: List of extracted entities
#             entity_keys: Optional list of keys to use for deduplication

#         Returns:
#             Deduplicated entities
#         """
#         if not entities:
#             return []

#         # Initialize LSH index for this deduplication run
#         lsh_index = MinHashLSH(threshold=self.similarity_threshold, num_perm=128)

#         # If no keys provided, use all keys from first entity
#         if not entity_keys and entities:
#             entity_keys = list(entities[0].keys())

#         unique_entities = []
#         entity_minhashes = {}

#         for i, entity in enumerate(entities):
#             # Create MinHash of entity
#             minhash = self._create_entity_minhash(entity, entity_keys)
#             entity_id = f"entity_{i}"

#             # Check if similar entity already exists
#             similar_ids = []
#             is_duplicate = False

#             try:
#                 # First check before inserting to avoid self-matches
#                 for j, unique_entity in enumerate(unique_entities):
#                     unique_id = f"entity_{j}"
#                     if unique_id in lsh_index:
#                         unique_minhash = entity_minhashes[unique_id]
#                         if (
#                             self._calculate_jaccard(minhash, unique_minhash)
#                             >= self.similarity_threshold
#                         ):
#                             similar_ids.append(unique_id)

#                 if similar_ids:
#                     # Found similar entities, merge with the first one
#                     similar_id = similar_ids[0]
#                     similar_entity_idx = int(similar_id.split("_")[1])

#                     # Merge entities
#                     merged_entity = self._merge_entities(
#                         unique_entities[similar_entity_idx], entity
#                     )
#                     unique_entities[similar_entity_idx] = merged_entity
#                     is_duplicate = True
#                 else:
#                     # No similar entities, add to index
#                     lsh_index.insert(entity_id, minhash)
#                     entity_minhashes[entity_id] = minhash
#             except Exception as e:
#                 logger.warning(f"Entity deduplication error: {str(e)}")

#             if not is_duplicate:
#                 unique_entities.append(entity)

#         logger.info(f"Deduplicated entities: {len(entities)} -> {len(unique_entities)}")
#         return unique_entities

#     def _create_entity_minhash(
#         self, entity: Dict[str, Any], keys: List[str], num_perm: int = 128
#     ) -> MinHash:
#         """
#         Create MinHash for an entity based on specified keys.

#         Args:
#             entity: Entity to hash
#             keys: Keys to include in the hash
#             num_perm: Number of permutations for MinHash

#         Returns:
#             MinHash of the entity
#         """
#         m = MinHash(num_perm=num_perm)

#         # Normalize and hash entity fields
#         entity_str = self._normalize_entity(entity, keys)

#         # Update MinHash with normalized string
#         for token in entity_str.split():
#             m.update(token.encode("utf-8"))

#         return m

#     def _normalize_entity(self, entity: Dict[str, Any], keys: List[str]) -> str:
#         """Normalize entity to string for comparison."""
#         parts = []

#         for key in keys:
#             if key in entity and entity[key]:
#                 value = entity[key]
#                 # Normalize value based on type
#                 if isinstance(value, (list, tuple)):
#                     # Sort lists for consistent comparison
#                     if all(isinstance(x, str) for x in value):
#                         norm_value = " ".join(
#                             sorted(v.lower().strip() for v in value if v)
#                         )
#                     else:
#                         # For complex lists, use string representation
#                         norm_value = str(sorted(str(v) for v in value if v))
#                 elif isinstance(value, dict):
#                     # For dicts, use sorted key-value pairs
#                     norm_value = " ".join(
#                         f"{k}:{v}" for k, v in sorted(value.items()) if v
#                     )
#                 else:
#                     # For simple values, use string representation
#                     norm_value = str(value).lower().strip()

#                 if norm_value:
#                     parts.append(f"{key}:{norm_value}")

#         return " ".join(parts)

#     def _calculate_jaccard(self, minhash1: MinHash, minhash2: MinHash) -> float:
#         """Calculate Jaccard similarity between two MinHashes."""
#         return minhash1.jaccard(minhash2)

#     def _merge_entities(
#         self, entity1: Dict[str, Any], entity2: Dict[str, Any]
#     ) -> Dict[str, Any]:
#         """
#         Merge two similar entities, keeping the most complete information.

#         Args:
#             entity1: First entity
#             entity2: Second entity

#         Returns:
#             Merged entity
#         """
#         merged = entity1.copy()

#         # For each field in entity2, merge with entity1
#         for key, value in entity2.items():
#             # Skip empty values
#             if value is None or value == "" or value == [] or value == {}:
#                 continue

#             # If key doesn't exist in merged or is empty, use value from entity2
#             if (
#                 key not in merged
#                 or merged[key] is None
#                 or merged[key] == ""
#                 or merged[key] == []
#                 or merged[key] == {}
#             ):
#                 merged[key] = value
#             # If both have values and they're different types, keep entity1's value
#             elif type(merged[key]) != type(value):
#                 continue
#             # If both are lists, combine them
#             elif isinstance(value, list):
#                 # Combine lists without duplicates
#                 merged_list = merged[key].copy()
#                 for item in value:
#                     if item not in merged_list:
#                         merged_list.append(item)
#                 merged[key] = merged_list
#             # If both are dicts, recursively merge
#             elif isinstance(value, dict):
#                 merged[key] = self._merge_entities(merged[key], value)

#         return merged


class ExtractionPipeline:
    """End-to-end pipeline for structured data extraction."""

    DEFAULT_TOP_K = 20
    DEFAULT_QDRANT_TEXT_COLLECTION = "lit_miner_text_collection"
    DEFAULT_EMBEDDING_MODEL = "gemini-embedding-exp-03-07"
    DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"

    def __init__(self):
        # Initialize components
        self._init_components()

    def _init_components(self):
        """Initialize all required components."""
        try:
            # Initialize Qdrant client
            self.qdrant_client = QdrantClient(
                url=settings.QDRANT_HOST_URL, api_key=settings.QDRANT_API_KEY
            )

            # Initialize embedding model
            self.embedding_model = GoogleGenAIEmbedding(
                model_name=self.DEFAULT_EMBEDDING_MODEL,
                api_key=settings.GOOGLE_GEMINI_API_KEY,
                embed_batch_size=10,
            )

            # Initialize vector store and index
            self.text_vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=self.DEFAULT_QDRANT_TEXT_COLLECTION,
                dense_vector_name="dense",
            )
            self.text_index = VectorStoreIndex.from_vector_store(
                vector_store=self.text_vector_store,
                embed_model=self.embedding_model,
            )
            self.text_retriever = self.text_index.as_retriever(
                similarity_top_k=self.DEFAULT_TOP_K
            )

            # Initialize context manager
            self.context_manager = ContextManager()
            # self.deduplicator = Deduplicator()

            # Initialize LLM client
            groq_client = Groq(api_key=settings.GROQ_API_KEY)
            self.instructor_client = instructor.from_groq(groq_client)

            # Initialize web search tool if enabled
            # enabling web search allows the multi-hop agent to search the web for missing information
            self.web_search_tool = None
            # if self.enable_web_search:
            #     self.web_search_tool = WebSearchTool(api_key=settings.WEB_SEARCH_API_KEY)

            # Initialize multi-hop agent
            # self.multi_hop_agent = MultiHopAgent(
            #     llm=self.llm,
            #     retriever=self.retriever,
            #     web_search_tool=self.web_search_tool,
            #     max_iterations=MULTI_HOP_CONFIG["max_iterations"],
            #     enable_web_search=self.enable_web_search,
            # )

            logger.info("All components initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing components: {e}", exc_info=True)
            raise

    def _create_extraction_prompt(
        self,
        query: str,
        context: str,
        output_schema: BaseModel,
        memory_context: Optional[str] = None,
        examples: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Create a prompt for extraction based on the query and output schema.

        Args:
            query: User query
            context: Document context to extract from
            output_schema: Pydantic model defining the output schema
            examples: Optional examples of expected output

        Returns:
            Formatted extraction prompt
        """
        prompt = f"""
        Extract structured data from the provided context and format it according to the specified JSON schema. Each extracted data point must include citations to the source information.

        INSTRUCTIONS:
        1. Carefully analyze the provided [CONTEXT] to identify relevant information matching the schema requirements.
        2. Examine the [MEMORY] section to avoid creating duplicates. Consider an entry duplicate if it shares the same key identifiers and major characteristics with an existing entry.
        3. Extract information that satisfies the fields specified in the [JSON_SCHEMA].
        4. For each extracted data point, include a "citations" field that references the specific part of the context supporting this information.
        5. If information for a required field is missing, explicitly indicate this with a null value and a note in the citations.
        6. If you find conflicting information in the context, select the most reliable source based on recency and specificity.
        7. Format your output precisely according to the JSON schema.
        8. Do not hallucinate or include information not present in the provided [CONTEXT].

        [CONTEXT]
        ---------------------
        {context}
        ---------------------
        [MEMORY] - Previously extracted data (avoid duplication):
        ---------------------
        {memory_context}
        ---------------------
        [JSON_SCHEMA]
        ---------------------
        {json.dumps(output_schema.model_json_schema(), indent=2)}
        ---------------------
        [QUERY]
        ---------------------
        {query}
        ---------------------
        """.strip()

        # Add examples if provided
        # if examples and len(examples) > 0:
        #     prompt.append("\nHere are some examples of the expected output format:")
        #     for i, example in enumerate(examples):
        #         prompt.append(f"\nExample {i+1}:")
        #         prompt.append(json.dumps(example, indent=2))

        return prompt

    def _extract_data(
        self,
        context: str,
        schema_model: BaseModel,
        query: str,
        examples: Optional[List[Dict[str, Any]]] = None,
    ) -> BaseModel:
        """
        Extract structured data from context according to schema.

        Args:
            context: Document context to extract from
            schema_model: Pydantic model defining the output schema
            query: User query to guide extraction
            examples: Optional examples of expected output format

        Returns:
            Structured data as specified by schema_model
        """
        try:
            # Prepare system prompt for extraction
            system_prompt = self._create_extraction_prompt(
                query=query, context=context, output_schema=schema_model
            )

            # Extract structured data
            logger.info(f"Extracting data with schema: {schema_model.__name__}")

            response = self.instructor_client.chat.completions.create(
                model=self.DEFAULT_LLM_MODEL,
                response_model=schema_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                ],
                temperature=0.1,
                max_retries=3,
            )

            return response

        except Exception as e:
            logger.error(f"Error extracting data: {str(e)}")
            raise e

    def extract(
        self,
        query: str,
        schema_model: BaseModel,
        filters: Optional[Dict[str, Any]] = None,
        max_chunks: int = MAX_RETRIEVED_CHUNKS,
        examples: Optional[List[Dict[str, Any]]] = None,
    ) -> BaseModel:
        """
        Extract structured data based on query and schema.

        Args:
            query: User query
            schema_model: Pydantic model defining the output schema
            filters: Optional metadata filters for retrieval
            max_chunks: Maximum chunks to retrieve
            examples: Optional examples of expected output

        Returns:
            Extracted and structured data
        """
        try:
            # Step 1: Retrieve relevant chunks
            chunks = self.text_retriever.retrieve(query)
            if not chunks:
                logger.warning("No relevant chunks found")
                return schema_model()

            # Prepare context for this batch, including previously extracted entities
            context = self.context_manager.prepare_context(chunks)

            # Extract data according to schema
            return self._extract_data(
                context=context,
                schema_model=schema_model,
                query=query,
                examples=examples,
            )
        except Exception as e:
            logger.error(f"Error in extraction pipeline: {str(e)}")
            raise e

    def _find_list_fields(self, schema_model: BaseModel) -> List[str]:
        """Find all list fields in the schema model."""
        list_fields = []

        for field_name, field_info in schema_model.__annotations__.items():
            # Check if field is a List
            origin = getattr(field_info, "__origin__", None)
            if origin == list or origin == List:
                list_fields.append(field_name)

        return list_fields
