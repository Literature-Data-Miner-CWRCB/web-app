import logging
import json
from pydantic import BaseModel, Field, create_model
from typing import Type, List, Dict

logger = logging.getLogger(__name__)


# Define Pydantic models for our structured output with citations
class CitationMetadata(BaseModel):
    """Metadata about the source document for a citation"""

    title: str = Field(..., description="Title of the source document")
    page_number: int = Field(..., description="Page number in the source document")
    doi: str = Field(..., description="DOI identifier for the source")
    authors: List[str] = Field(..., description="List of authors")
    source: str = Field(..., description="Source of the document")


class Citation(BaseModel):
    """Citation information for a piece of content"""

    source_id: str = Field(..., description="ID of the source document")
    text_span: str = Field(
        ..., description="Text span from the document used as evidence"
    )
    metadata: CitationMetadata = Field(
        ...,
        description="Additional metadata from the source",
        default_factory=CitationMetadata,
    )


def wrap_row_schema_with_citations(row_model: Type[BaseModel]) -> Type[BaseModel]:
    """Helper function to wrap a row schema with citations"""

    class StructuredRowSchema(BaseModel):
        """A single structured row schema with citations"""

        row: row_model = Field(..., description="The row as a structured item")
        citations: List[Citation] = Field(
            ..., description="Citations supporting the row"
        )

    return StructuredRowSchema


def create_dataset_model(row_model: Type[BaseModel]) -> Type[BaseModel]:
    """Helper function to create a dataset model"""

    class DatasetSchema(BaseModel):
        """A dataset schema with a list of rows"""

        rows: List[row_model] = Field(..., description="A list of rows")

    return DatasetSchema


def convert_to_row_model(
    field_definitions_json_str: str, model_name: str = "DynamicModel"
) -> Type[BaseModel]:
    """
    Create a Pydantic model dynamically from a JSON string that defines fields.

    Args:
        field_definitions_json_str: JSON string containing field definitions with name, type and description.
        model_name: Name for the dynamically created model

    Returns:
        A dynamically created Pydantic model class
    """
    try:
        # Log the input for debugging
        logger.debug(
            f"Received JSON string (first 50 chars): {field_definitions_json_str[:50]}..."
        )

        # Check for common JSON issues
        field_definitions_json_str = field_definitions_json_str.strip()

        # Parse the JSON
        field_definitions = json.loads(field_definitions_json_str)
        logger.debug(f"Successfully parsed JSON: {type(field_definitions)}")

        # If not a list, wrap in a list
        if not isinstance(field_definitions, list):
            logger.warning("Field definitions is not a list, wrapping in list")
            field_definitions = [field_definitions]

        # Dictionary to hold field definitions for create_model
        fields = {}

        # Type mapping from string representations to actual types
        type_mapping = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": List,
            "dict": Dict,
            # Add more mappings as needed
        }

        for field_def in field_definitions:
            field_name = field_def["name"]
            field_type_str = field_def["type"]
            field_description = field_def["description"]
            required = field_def.get("required", True)
            default = field_def.get("default", ... if required else None)

            # Get the actual type from the mapping
            field_type = type_mapping.get(field_type_str)
            if not field_type:
                raise ValueError(f"Unsupported type: {field_type_str}")

            # Create the field with description
            field_obj = (field_type, Field(description=field_description))

            # Add to fields dictionary
            fields[field_name] = field_obj

        # Create the model dynamically
        model = create_model(model_name, **fields)

        return model
    except Exception as e:
        logger.error(f"Error creating model from JSON: {e}", exc_info=True)
        raise ValueError(f"Failed to create model: {str(e)}")
