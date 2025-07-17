"""
Tests for the CSV search tool.
"""

import os
import tempfile
import pandas as pd
import pytest
from infrastructure.crewai.tools.csv_search import CSVSearchTool, create_csv_search_tool

@pytest.fixture
def sample_csv():
    """Create a sample CSV file for testing."""
    data = {
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35],
        'city': ['New York', 'San Francisco', 'Los Angeles']
    }
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as f:
        df = pd.DataFrame(data)
        df.to_csv(f.name, index=False)
        yield f.name
    
    # Cleanup
    if os.path.exists(f.name):
        os.unlink(f.name)

class TestCSVSearchTool:
    """Tests for the CSVSearchTool class."""
    
    def test_initialization(self):
        """Test that the tool initializes correctly."""
        tool = CSVSearchTool(csv="test.csv")
        assert tool.name == "csv_search"
        assert "Search a CSV for rows containing a query" in tool.description
    
    def test_run_with_file_path(self, sample_csv):
        """Test running the tool with a file path."""
        tool = CSVSearchTool()
        result = tool._run(search_query="Alice", csv=sample_csv)
        assert "Alice" in result
        assert "Found 1 matches" in result
    
    def test_run_with_instance_path(self, sample_csv):
        """Test running the tool with instance file path."""
        tool = CSVSearchTool(csv=sample_csv)
        result = tool._run(search_query="Bob")
        assert "Bob" in result
        assert "Found 1 matches" in result
    
    def test_run_no_results(self, sample_csv):
        """Test running the tool with a query that returns no results."""
        tool = CSVSearchTool(csv=sample_csv)
        result = tool._run(search_query="Nonexistent")
        assert "No records found" in result
    
    def test_run_error_handling(self):
        """Test error handling when the CSV file doesn't exist."""
        tool = CSVSearchTool(csv="nonexistent.csv")
        result = tool._run(search_query="test")
        assert "Error reading CSV file" in result


def test_create_csv_search_tool():
    """Test the create_csv_search_tool factory function."""
    tool = create_csv_search_tool(
        csv_path="test.csv",
        description="Test tool",
        examples=["example1", "example2"]
    )
    
    assert tool.name == "csv_search"
    assert "Test tool" in tool.description
    assert "example1, example2" in tool.description
