"""
Configuration settings for the structured RAG system.
"""

import os
from typing import Dict, Any

# Vector store settings
VECTOR_STORE_CONFIG = {
    "qdrant_host": os.environ.get("QDRANT_HOST_URL", "localhost"),
    "qdrant_api_key": os.environ.get("QDRANT_API_KEY", ""),
    "text_collection": "lit_miner_text_collection",
    "image_collection": "image_collection",
    "dense_vector_name": "dense",
}

# Embedding model settings
EMBEDDING_CONFIG = {
    "model_name": "gemini-embedding-exp-03-07",
    "api_key": os.environ.get("GOOGLE_GEMINI_API_KEY", ""),
    "task_type": "RETRIEVAL_DOCUMENT",
    "output_dimensionality": 1536,
    "batch_size": 10,
}

# LLM settings
LLM_CONFIG = {
    "model": "llama-3.3-70b-versatile",
    "api_key": os.environ.get("GROQ_API_KEY", ""),
    "temperature": 0.1,
}

# Retrieval settings
RETRIEVAL_CONFIG = {
    "initial_similarity_top_k": 5,
    "follow_up_similarity_top_k": 3,
    "max_context_tokens": 8000,
    "chunk_overlap": 100,
}

# Multi-hop settings
MULTI_HOP_CONFIG = {
    "max_iterations": 2,
    "enable_web_search": True,
    "web_search_threshold": 0.7,  # Confidence threshold below which to try web search
    "max_web_results": 3,
}

# System prompts
SYSTEM_PROMPTS = {
    "missing_field_analyzer": """
    You are an expert data analyzer. Your task is to:
    1. Analyze the retrieved context to determine if it contains all the information required by the schema.
    2. Identify which specific fields from the schema are missing or have insufficient information.
    3. Generate targeted follow-up queries to find the missing information.
    
    Be precise in your analysis and focus only on the schema fields that are truly missing information.
    """,
    "structured_generator": """
    You are an expert in creating structured data from text. Your task is to:
    1. Extract precise information from the provided context to fill the requested schema.
    2. ONLY include information explicitly mentioned in the context.
    3. For fields where information is not found in the context, use null/None values or mark as "Information not available".
    4. Do not invent or hallucinate information that isn't in the context.
    
    Be accurate and precise, ensuring all data comes directly from the provided sources.
    """,
}

# Web search settings
WEB_SEARCH_CONFIG = {
    "api_key": os.environ.get("SERP_API_KEY", ""),
    "max_results": 3,
}
