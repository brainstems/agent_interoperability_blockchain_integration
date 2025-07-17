"""
CSV Search Tool for CrewAI and Infrastructure Agents

This module provides a tool for searching CSV files that works with both
our infrastructure agents and crewAI agents.
"""

import os
import json
import pandas as pd
from typing import Dict, Optional, List, Any, Type, Union
from pydantic import BaseModel, Field, ConfigDict

# Import from the correct location based on your project structure
try:
    from crewai.tools import BaseTool
except ImportError:
    # Fallback for when crewai is not available
    class BaseTool:
        """Base class for tools when crewai is not available."""
        name: str = "base_tool"
        description: str = "Base tool description"
        
        def __init__(self, **kwargs):
            self.config = kwargs.get("config", {})


class CSVSearchInput(BaseModel):
    """Inputs for the csv_search tool."""
    model_config = ConfigDict(
        populate_by_name=True,  # let aliases work
        extra="ignore"  # ignore extra fields
    )

    # Accept either "search_query" or the shorter "query"
    search_query: str = Field(
        ...,
        alias="query",
        description="Natural-language text to search for in the CSV file"
    )
    
    # Optional CSV path if not bound at construction
    csv: Optional[str] = Field(
        None,
        description="Path to the CSV file to search (if not provided at tool creation)"
    )
    
    # Additional search parameters
    limit: Optional[int] = Field(
        10,
        description="Maximum number of results to return"
    )
    
    columns: Optional[List[str]] = Field(
        None,
        description="Specific columns to search in (default: all columns)"
    )


class CSVSearchTool(BaseTool):
    """
    A tool for searching and filtering CSV files.
    
    This tool allows agents to search through CSV files using natural language
    queries and filter results based on various criteria.
    """
    
    name: str = "csv_search"
    description: str = (
        "Search a CSV file for rows matching a query. "
        "Call with {'search_query':'your query', 'csv':'path/to/file.csv'}"
    )
    args_schema: Type[BaseModel] = CSVSearchInput
    
    def __init__(self, csv: Optional[str] = None, **kwargs):
        """
        Initialize the CSV search tool.
        
        Args:
            csv: Optional path to the CSV file to search
            **kwargs: Additional arguments to pass to BaseTool
        """
        super().__init__(**kwargs)
        self._csv = csv
        self._df_cache = None
    
    def _load_dataframe(self, csv_path: str) -> pd.DataFrame:
        """
        Load a CSV file into a pandas DataFrame with caching.
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            Loaded pandas DataFrame
        """
        # Use cached DataFrame if available and path matches
        if self._df_cache is not None and hasattr(self._df_cache, '_csv_path'):
            if self._df_cache._csv_path == csv_path:
                return self._df_cache
        
        # Load the CSV file
        try:
            df = pd.read_csv(csv_path)
            # Store the path for cache invalidation
            df._csv_path = csv_path
            self._df_cache = df
            return df
        except Exception as e:
            raise ValueError(f"Error loading CSV file {csv_path}: {str(e)}")
    
    def _run(
        self, 
        search_query: str, 
        csv: Optional[str] = None,
        limit: int = 10,
        columns: Optional[List[str]] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """
        Search the CSV file for the given query.
        
        Args:
            search_query: The search query
            csv: Optional path to the CSV if not bound at construction
            limit: Maximum number of results to return
            columns: Specific columns to search in
            **kwargs: Additional search parameters
            
        Returns:
            Search results as a formatted string or dictionary
        """
        # Determine which CSV to use
        csv_path = csv or self._csv
        if not csv_path:
            return {
                "error": "No CSV file specified",
                "message": "Please provide a 'csv' parameter or initialize with one."
            }
            
        # Check if the file exists
        if not os.path.exists(csv_path):
            return {
                "error": "File not found",
                "message": f"CSV file not found: {csv_path}"
            }
            
        try:
            # Load the CSV file
            df = self._load_dataframe(csv_path)
            
            # Filter columns if specified
            if columns:
                # Only include columns that exist in the DataFrame
                valid_columns = [col for col in columns if col in df.columns]
                if valid_columns:
                    df = df[valid_columns]
            
            # Convert all columns to string for searching
            df = df.astype(str)
            
            # Simple search: look for rows containing the query in any column
            mask = df.apply(
                lambda row: any(
                    str(search_query).lower() in cell.lower() 
                    for cell in row.values
                ),
                axis=1
            )
            
            results = df[mask]
            total_results = len(results)
            
            if results.empty:
                return {
                    "status": "success",
                    "query": search_query,
                    "csv_file": csv_path,
                    "total_results": 0,
                    "results": [],
                    "message": f"No results found for query: {search_query}"
                }
                
            # Convert results to a list of dictionaries
            results_list = results.head(limit).to_dict(orient='records')
            
            # Prepare the response
            response = {
                "status": "success",
                "query": search_query,
                "csv_file": csv_path,
                "total_results": total_results,
                "returned_results": len(results_list),
                "results": results_list
            }
            
            # If there are more results than the limit, add a note
            if total_results > limit:
                response["message"] = f"Showing top {limit} of {total_results} results"
            
            return response
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "An error occurred while searching the CSV file"
            }
    
    async def _arun(
        self, 
        search_query: str, 
        csv: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """
        Asynchronous version of _run.
        
        This is a simple wrapper around the synchronous _run method.
        In a production environment, you might want to implement proper async I/O.
        """
        return self._run(search_query, csv, **kwargs)


def create_csv_search_tool(
    csv_path: str, 
    description: str = "", 
    config: Optional[Dict] = None, 
    examples: Optional[List[str]] = None
) -> CSVSearchTool:
    """
    Factory function to create a CSV search tool.
    
    Args:
        csv_path: Path to the CSV file to search
        description: Optional description for the tool
        config: Optional configuration for the tool
        examples: Optional list of example search queries (for documentation only)
        
    Returns:
        A configured CSVSearchTool instance
    """
    # Create a default description if none provided
    if not description:
        description = f"Search the {os.path.basename(csv_path)} CSV file"
    
    # Add examples to the description if provided
    if examples:
        description += "\n\nExamples:\n" + "\n".join(f"- {ex}" for ex in examples)
    
    # Create and return the tool
    return CSVSearchTool(
        csv=csv_path,
        description=description,
        config=config or {}
    )
