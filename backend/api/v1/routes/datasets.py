import logging
import json
from typing import Annotated, List, Dict, Type
from pydantic import create_model, Field, BaseModel
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse
from rag.main import DatasetGenerator

logger = logging.getLogger(__name__)

router = APIRouter()


def create_model_from_json(
    json_str: str, model_name: str = "DynamicModel"
) -> Type[BaseModel]:
    """
    Create a Pydantic model dynamically from a JSON string that defines fields.

    Args:
        json_str: JSON string containing field definitions with name, type and description
        model_name: Name for the dynamically created model

    Returns:
        A dynamically created Pydantic model class
    """
    try:
        # Log the input for debugging
        logger.debug(f"Received JSON string (first 50 chars): {json_str[:50]}...")

        # Check for common JSON issues
        json_str = json_str.strip()

        # Parse the JSON
        field_definitions = json.loads(json_str)
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
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        # Log the problematic part of the string
        char_pos = e.pos
        start = max(0, char_pos - 20)
        end = min(len(json_str), char_pos + 20)
        logger.error(
            f"JSON fragment around error (pos {char_pos}): '{json_str[start:end]}'"
        )
        raise ValueError(f"Invalid JSON format: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating model from JSON: {e}", exc_info=True)
        raise ValueError(f"Failed to create model: {str(e)}")


@router.post("/generate")
def generate_dataset(
    user_query: Annotated[str, Form(description="User query")],
    rows: Annotated[int, Form(description="Number of rows to generate")],
    model_name: Annotated[str, Form(description="Model name for the row schema")],
    field_definitions_json_str: Annotated[
        str, Form(description="Field definitions in JSON format")
    ],
) -> JSONResponse:
    try:
        logger.info(f"Generating dataset with model: {model_name}, rows: {rows}")
        logger.debug(f"User query: {user_query}")

        dataset_generator = DatasetGenerator()

        row_schema = create_model_from_json(
            field_definitions_json_str, model_name=model_name
        )

        # convert table_schema_json_str to a Pydantic model
        response = dataset_generator.generate(user_query, row_schema, rows=rows)
        return JSONResponse(
            content={"message": "Dataset generated successfully", "response": response}
        )
    except Exception as e:
        logger.error(f"Error generating dataset: {e}", exc_info=True)
        return JSONResponse(
            content={"message": f"Error generating dataset: {str(e)}"}, status_code=500
        )
