import json
import os
import shutil
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from fastapi.testclient import TestClient

from modules.documentation_generator.parser import parse_markdown_to_blocks
from modules.documentation_generator.strategies import get_strategy, DocType
from modules.documentation_generator.exporters import get_exporter, EXPORTERS_MAP
from modules.documentation_generator.drawio_parser import generate_drawio_from_markdown, parse_mermaid_flowchart
from ui.main import app

client = TestClient(app)
client.headers.update({"Authorization": "Bearer mock-token"})

@pytest.fixture(autouse=True)
def mock_auth():
    with patch("ui.main.verify_token") as mock_verify:
        mock_verify.return_value = {"type": "access", "roles": ["ADMIN"], "sub": "test@example.com"}
        yield

SAMPLE_MARKDOWN = """# Project Title
This is a sample description paragraph.

## Sub Section
- Item 1
- Item 2
- Item 3

```python
def hello_world():
    print("hello")
```

| Header 1 | Header 2 |
|---|---|
| Value 1 | Value 2 |
| Value 3 | Value 4 |
"""

MERMAID_MD = """# Architecture Design
This document outlines our architecture.

```mermaid
graph TD
  A[Client] --> B(API Gateway)
  B --> C{Auth Required?}
  C -->|Yes| D[(Database)]
```
"""


def test_parser():
    blocks = parse_markdown_to_blocks(SAMPLE_MARKDOWN)
    
    assert len(blocks) >= 5
    
    # Assert Heading 1
    assert blocks[0]["type"] == "heading"
    assert blocks[0]["level"] == 1
    assert blocks[0]["text"] == "Project Title"
    
    # Assert Paragraph
    assert blocks[1]["type"] == "paragraph"
    assert "sample description" in blocks[1]["text"]
    
    # Assert Heading 2
    assert blocks[2]["type"] == "heading"
    assert blocks[2]["level"] == 2
    
    # Assert List
    assert blocks[3]["type"] == "list"
    assert not blocks[3]["ordered"]
    assert len(blocks[3]["items"]) == 3
    assert blocks[3]["items"][0] == "Item 1"
    
    # Assert Code Block
    assert blocks[4]["type"] == "code_block"
    assert blocks[4]["language"] == "python"
    assert "hello_world" in blocks[4]["code"]
    
    # Assert Table
    table_block = next(b for b in blocks if b["type"] == "table")
    assert table_block["headers"] == ["Header 1", "Header 2"]
    assert len(table_block["rows"]) == 2
    assert table_block["rows"][0] == ["Value 1", "Value 2"]


def test_strategies():
    # Verify that get_strategy returns valid strategies for different types
    strategy = get_strategy("README")
    sys_prompt = strategy.get_system_prompt("Professional")
    user_prompt = strategy.get_user_prompt("my source code", "none")
    
    assert "README" in sys_prompt
    assert "my source code" in user_prompt
    
    # Verify SRS
    srs_strat = get_strategy(DocType.SRS)
    assert "SRS" in srs_strat.get_system_prompt("Technical") or "Software Requirements" in srs_strat.get_system_prompt("Technical")


def test_exporters_resolution():
    # Verify exporter resolution
    assert get_exporter("Markdown") is not None
    assert get_exporter("DOCX") is not None
    assert get_exporter("PPTX") is not None
    assert get_exporter("PDF") is not None
    assert get_exporter("YAML") is not None


def test_mermaid_drawio_parser():
    parsed = parse_mermaid_flowchart("""
    graph TD
      A[Client] --> B(Gateway)
    """)
    assert len(parsed["nodes"]) == 2
    assert parsed["nodes"][0]["label"] == "Client"
    assert parsed["nodes"][1]["label"] == "Gateway"
    assert len(parsed["edges"]) == 1
    assert parsed["edges"][0]["source"] == "A"
    assert parsed["edges"][0]["target"] == "B"


def test_drawio_exporter_fallback():
    # Should fallback to headers when no mermaid block
    drawio_xml = generate_drawio_from_markdown(SAMPLE_MARKDOWN, "Test title")
    assert "<mxfile" in drawio_xml
    assert "Project Title" in drawio_xml
    assert "Sub Section" in drawio_xml


def test_drawio_exporter_mermaid():
    # Should translate mermaid structure when present
    drawio_xml = generate_drawio_from_markdown(MERMAID_MD, "Test title")
    assert "<mxfile" in drawio_xml
    assert "Client" in drawio_xml
    assert "API Gateway" in drawio_xml
    assert "Database" in drawio_xml


def test_all_exporters_run():
    temp_dir = Path("output/test_docs_run")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    metadata = {
        "title": "Test Document Title",
        "type": "README",
        "tone": "Professional",
        "date": "2026-07-28"
    }
    
    try:
        # Test markdown export
        get_exporter("Markdown").export(SAMPLE_MARKDOWN, metadata, temp_dir / "test.md")
        assert (temp_dir / "test.md").exists()
        
        # Test HTML export
        get_exporter("HTML").export(SAMPLE_MARKDOWN, metadata, temp_dir / "test.html")
        assert (temp_dir / "test.html").exists()
        
        # Test Plain Text export
        get_exporter("TXT").export(SAMPLE_MARKDOWN, metadata, temp_dir / "test.txt")
        assert (temp_dir / "test.txt").exists()
        
        # Test JSON export
        get_exporter("JSON").export(SAMPLE_MARKDOWN, metadata, temp_dir / "test.json")
        assert (temp_dir / "test.json").exists()
        
        # Test YAML export
        get_exporter("YAML").export(SAMPLE_MARKDOWN, metadata, temp_dir / "test.yaml")
        assert (temp_dir / "test.yaml").exists()
        
        # Test XML export
        get_exporter("XML").export(SAMPLE_MARKDOWN, metadata, temp_dir / "test.xml")
        assert (temp_dir / "test.xml").exists()
        
        # Test Draw.io export
        get_exporter("DRAWIO").export(MERMAID_MD, metadata, temp_dir / "test.drawio")
        assert (temp_dir / "test.drawio").exists()
        
        # Test Word export
        get_exporter("DOCX").export(SAMPLE_MARKDOWN, metadata, temp_dir / "test.docx")
        assert (temp_dir / "test.docx").exists()
        
        # Test PPTX export
        get_exporter("PPTX").export(SAMPLE_MARKDOWN, metadata, temp_dir / "test.pptx")
        assert (temp_dir / "test.pptx").exists()
        
        # Test PDF export
        get_exporter("PDF").export(SAMPLE_MARKDOWN, metadata, temp_dir / "test.pdf")
        assert (temp_dir / "test.pdf").exists()
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch("modules.documentation_generator.router.ChatGroq")
def test_api_generate_endpoint(mock_chat_groq):
    # Mock LLM response
    mock_llm_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.content = SAMPLE_MARKDOWN
    mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)
    mock_chat_groq.return_value = mock_llm_instance
    
    # Mock settings api key
    with patch("modules.documentation_generator.router.settings") as mock_settings:
        mock_settings.groq_api_key = "fake_api_key"
        mock_settings.groq_model = "llama3-70b-8192"
        
        # Call API
        payload = {
            "type": "README",
            "format": "Markdown",
            "tone": "Professional",
            "source": "Some source code input",
            "instructions": "Make it detailed"
        }
        
        response = client.post("/documentation-generator/api/generate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["format"] == "Markdown"
        assert "download_url" in data
        assert "Project Title" in data["content"]
        
        # Download the file to verify
        download_url = data["download_url"]
        dl_response = client.get(download_url)
        assert dl_response.status_code == 200
        assert b"Project Title" in dl_response.content
