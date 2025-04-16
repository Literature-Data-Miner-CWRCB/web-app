# """
# Multi-hop retrieval agent for improving context completeness.
# """

# from typing import List, Dict, Any, Optional, Type, Tuple
# import logging
# import json

# from pydantic import BaseModel
# from llama_index.llms.base import LLM
# from llama_index.llms.groq import Groq

# from ..config import MULTI_HOP_CONFIG, SYSTEM_PROMPTS
# from ..utils.web_search import WebSearchTool
# from .retriever import EnhancedRetriever

# logger = logging.getLogger(__name__)


# class MultiHopAgent:
#     """
#     Agent that analyzes context completeness and performs follow-up retrievals.
#     """

#     def __init__(
#         self,
#         llm: LLM,
#         retriever: EnhancedRetriever,
#         web_search_tool: Optional[WebSearchTool] = None,
#         max_iterations: int = MULTI_HOP_CONFIG["max_iterations"],
#         enable_web_search: bool = MULTI_HOP_CONFIG["enable_web_search"],
#     ):
#         """
#         Initialize the multi-hop agent.

#         Args:
#             llm: Language model for analyzing missing information
#             retriever: Enhanced retriever for follow-up queries
#             web_search_tool: Optional tool for web searches
#             max_iterations: Maximum follow-up iterations
#             enable_web_search: Whether to enable web search
#         """
#         self.llm = llm
#         self.retriever = retriever
#         self.web_search_tool = web_search_tool
#         self.max_iterations = max_iterations
#         self.enable_web_search = enable_web_search and web_search_tool is not None

#     def analyze_missing_fields(
#         self, context: str, schema: Type[BaseModel], user_query: str
#     ) -> List[Dict[str, Any]]:
#         """
#         Analyze which schema fields are missing from the context.

#         Args:
#             context: The retrieved context
#             schema: The Pydantic schema
#             user_query: Original user query

#         Returns:
#             List of dicts with field name, description, and follow-up query
#         """
#         # Get schema field information
#         schema_fields = []
#         for field_name, field in schema.__annotations__.items():
#             field_info = schema.model_fields.get(field_name)
#             if field_info:
#                 schema_fields.append(
#                     {
#                         "name": field_name,
#                         "type": str(field),
#                         "description": field_info.description or "",
#                         "required": field_info.is_required(),
#                     }
#                 )

#         # Create prompt for the LLM
#         prompt = f"""
#         {SYSTEM_PROMPTS['missing_field_analyzer']}
        
#         USER QUERY:
#         {user_query}
        
#         SCHEMA FIELDS:
#         {json.dumps(schema_fields, indent=2)}
        
#         RETRIEVED CONTEXT:
#         {context}
        
#         Analyze which fields from the schema are missing in the context or have insufficient information.
#         For each missing field, generate a specific follow-up query that would help find the missing information.
        
#         Return your analysis in the following JSON format:
#         ```
#         {{
#             "missing_fields": [
#                 {{
#                     "field_name": "name of the missing field",
#                     "field_description": "description of the field",
#                     "follow_up_query": "specific query to find information for this field"
#                 }}
#             ]
#         }}
#         ```
        
#         Only include fields that are truly missing or have insufficient information. If all fields have adequate information, return an empty list.
#         """

#         try:
#             # Get LLM response
#             response = self.llm.complete(prompt)

#             # Extract JSON from the response
#             json_str = response.text
#             if "```json" in json_str:
#                 json_str = json_str.split("```json")[1].split("```")[0]
#             elif "```" in json_str:
#                 json_str = json_str.split("```")[1].split("```")[0]

#             # Parse JSON
#             result = json.loads(json_str)
#             missing_fields = result.get("missing_fields", [])

#             logger.info(
#                 f"Identified {len(missing_fields)} missing fields: {[f['field_name'] for f in missing_fields]}"
#             )
#             return missing_fields

#         except Exception as e:
#             logger.error(f"Error analyzing missing fields: {e}", exc_info=True)
#             return []

#     def enhance_context(
#         self, initial_context: str, schema: Type[BaseModel], user_query: str
#     ) -> str:
#         """
#         Enhance context through multi-hop retrieval.

#         Args:
#             initial_context: Initially retrieved context
#             schema: The Pydantic schema
#             user_query: Original user query

#         Returns:
#             Enhanced context with follow-up retrievals
#         """
#         current_context = initial_context

#         for iteration in range(self.max_iterations):
#             # Check if we've reached maximum iterations
#             if iteration >= self.max_iterations:
#                 logger.info(f"Reached maximum iterations ({self.max_iterations})")
#                 break

#             # Analyze missing fields
#             missing_fields = self.analyze_missing_fields(
#                 current_context, schema, user_query
#             )

#             # If no missing fields, we're done
#             if not missing_fields:
#                 logger.info("No missing fields identified, context is complete")
#                 break

#             logger.info(
#                 f"Iteration {iteration+1}: Found {len(missing_fields)} missing fields"
#             )

#             # Extract follow-up queries
#             follow_up_queries = [field["follow_up_query"] for field in missing_fields]

#             # Perform follow-up retrievals
#             enhanced_context = self.retriever.retrieve_for_specific_fields(
#                 user_query, follow_up_queries, current_context
#             )

#             # If we got useful additional context, update current context
#             if enhanced_context and enhanced_context != current_context:
#                 current_context = enhanced_context
#                 logger.info("Updated context with additional information")
#             else:
#                 logger.info(
#                     "No additional relevant information found in knowledge base"
#                 )

#                 # Try web search if enabled and we still have missing fields
#                 if self.enable_web_search and self.web_search_tool:
#                     web_context = self._try_web_search(missing_fields, user_query)
#                     if web_context:
#                         current_context = f"{current_context}\n\n--- WEB SEARCH RESULTS ---\n\n{web_context}"
#                         logger.info("Added information from web search")
#                     else:
#                         logger.info("Web search did not yield useful results")

#                 # Break after web search attempt
#                 break

#         return current_context

#     def _try_web_search(
#         self, missing_fields: List[Dict[str, Any]], user_query: str
#     ) -> str:
#         """
#         Attempt to fill missing information via web search.

#         Args:
#             missing_fields: List of missing fields with their queries
#             user_query: Original user query

#         Returns:
#             Context from web search or empty string
#         """
#         if not self.web_search_tool:
#             return ""

#         web_results = []

#         for field in missing_fields:
#             field_name = field["field_name"]
#             search_query = f"{user_query} {field['follow_up_query']}"

#             try:
#                 # Perform web search
#                 results = self.web_search_tool.search(search_query)

#                 if results:
#                     # Format web results
#                     formatted_result = f"[Web Search for {field_name}]\n"
#                     for i, result in enumerate(results):
#                         formatted_result += f"Source: {result['source']}\n"
#                         formatted_result += f"Content: {result['content']}\n\n"

#                     web_results.append(formatted_result)

#             except Exception as e:
#                 logger.error(f"Error during web search for {field_name}: {e}")
#                 continue

#         return "\n\n".join(web_results) if web_results else ""
