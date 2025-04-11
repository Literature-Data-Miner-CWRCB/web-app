import logging
import json
from pydantic import BaseModel, Field, create_model
from typing import Type, List, Dict

logger = logging.getLogger(__name__)


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
    except Exception as e:
        logger.error(f"Error creating model from JSON: {e}", exc_info=True)
        raise ValueError(f"Failed to create model: {str(e)}")
