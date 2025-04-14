"""
Main application interface for the structured RAG system.
"""

import logging
from typing import Type, Dict, Any, List, Optional, Union

# Import Pydantic for schema definition
from pydantic import BaseModel, Field

from core.rag.extraction import StructuredExtractor
from utils.pydantic_utils import (
    wrap_row_schema_with_citations,
    create_dataset_model,
)

logger = logging.getLogger(__name__)


class DatasetGenerator:
    """
    Main application for generating structured dataset items using advanced RAG methods such as multi-hop retrieval and web search.
    """

    DEFAULT_MAX_ROWS = 100  # Default maximum number of rows to generate

    def __init__(
        self,
        row_model: BaseModel,
        enable_web_search: bool = False,
    ):
        """
        Initialize the StructuredRAG application.

        Args:
            enable_web_search: Whether to enable web search for missing information
        """
        self.enable_web_search = enable_web_search
        self.output_model = wrap_row_schema_with_citations(row_model)
        self.dataset_model = create_dataset_model(self.output_model)
        self.extractor = StructuredExtractor(self.dataset_model)

    def generate(
        self,
        query: str,
        rows: int = 100,
        progress_callback=None,
    ):
        """
        Generate structured data based on a query using RAG.

        Args:
            query: User query describing the data to generate.
            row_schema: Pydantic schema defining the row structure in the dataset
            rows: Number of items to be generated.
            progress_callback: Optional callback function to report progress

        Returns:
            Dict containing the generated data and metadata.
        """
        # validate the number of rows
        if not (0 < rows <= self.DEFAULT_MAX_ROWS):
            raise ValueError(
                f"Invalid number of rows: {rows}. Must be between 0 and {self.DEFAULT_MAX_ROWS}."
            )

        # initialize the result dictionary
        result = {
            "success": False,
            "query": query,
            "dataset_schema_name": None,
            "dataset_schema": None,
            "items": None,
            "metadata": {
                "retrieval_stats": {},
                "missing_fields": [],
                "field_completion": {},
                "max_rows_limit": rows,
                "actual_rows_generated": 0,
            },
        }

        try:
            # Report initial progress
            if progress_callback:
                progress_callback(
                    {
                        "status": "started",
                        "message": "Initializing dataset generation",
                        "progress": 0,
                        "total": 100,
                        "stage": "initialization",
                    }
                )

            # extract structured items
            extracted_items = self.extractor.extract(
                query=query,
            )

            result["items"] = extracted_items.model_dump()
            result["success"] = True
            return result
        except Exception as e:
            logger.error(f"Error generating structured data: {e}", exc_info=True)

            if progress_callback:
                progress_callback(
                    {
                        "status": "error",
                        "message": f"Error generating dataset: {str(e)}",
                        "progress": 0,
                        "total": 100,
                        "stage": "error",
                        "error": str(e),
                    }
                )

            return result
