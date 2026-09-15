"""
modules/documentation_generator/drawio_parser.py
────────────────────────────────────────────────
Parses Mermaid graphs from markdown and generates a valid, editable Draw.io XML file (.drawio).
If no Mermaid diagram is present, it constructs a flowchart representation based on the main headers.
"""

import re
import uuid
import xml.etree.ElementTree as ET
from typing import List, Dict, Any


def parse_mermaid_flowchart(mermaid_code: str) -> Dict[str, Any]:
    """
    Parses a simple Mermaid graph/flowchart syntax and returns nodes and edges.
    Example:
      graph TD
        A[Client] -->|HTTP| B(API Gateway)
        B --> C[(Database)]
    """
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    # Clean lines
    lines = [line.strip() for line in mermaid_code.splitlines() if line.strip()]

    # Skip diagram definition line (e.g., graph TD, flowchart LR)
    if lines and (lines[0].startswith("graph") or lines[0].startswith("flowchart")):
        lines.pop(0)

    # Patterns
    # Match node definitions like: A[Client] or B(API Gateway) or C[(Database)] or D{Decision} or E((Circle))
    # Or simple node identifiers like A
    node_def_pattern = re.compile(
        r"([a-zA-Z0-9_\-]+)"               # Node ID
        r"(?:"
        r"\[\"?(.*?)\"?\]|"                # Box [Client] or ["Client"]
        r"\(\(\"?(.*?)\"?\)\)|"            # Circle ((Label))
        r"\(\"?(.*?)\"?\)|"                # Rounded (Label)
        r"\{\"?(.*?)\"?\}|"                # Rhombus/Decision {Label}
        r"\[\(\"?(.*?)\"?\)\]"             # Cylinder/Database [(Database)]
        r")"
    )

    # Match edge lines: A --> B or A -->|label| B or A -- label --> B
    edge_pattern = re.compile(
        r"([a-zA-Z0-9_\-]+)"               # Source Node ID
        r"\s*(?:-->|---|-.->|==>)"         # Connector
        r"(?:\s*\|(.*?)\||\s*--\s*(.*?)\s*-->)?"  # Optional label: |label| or -- label -->
        r"\s*([a-zA-Z0-9_\-]+)"             # Target Node ID
    )

    for line in lines:
        # Check for node definitions first
        for match in node_def_pattern.finditer(line):
            node_id = match.group(1)
            # Find the first non-None group matching the label
            label = ""
            shape = "rectangle"
            
            if match.group(2) is not None:
                label = match.group(2)
                shape = "rectangle"
            elif match.group(3) is not None:
                label = match.group(3)
                shape = "circle"
            elif match.group(4) is not None:
                label = match.group(4)
                shape = "rounded"
            elif match.group(5) is not None:
                label = match.group(5)
                shape = "rhombus"
            elif match.group(6) is not None:
                label = match.group(6)
                shape = "database"
            
            if not label:
                label = node_id
                
            nodes[node_id] = {
                "id": node_id,
                "label": label,
                "shape": shape
            }

        # Check for edges
        # Strip brackets/shapes from line for easier edge matching (e.g. A[Client] -> A)
        edge_line = re.sub(r"\[\(\"?.*?\"?\)\]|\[\"?.*?\"?\]|\(\(\"?.*?\"?\)\)|\(\"?.*?\"?\)|\{\"?.*?\"?\}", "", line)
        edge_matches = edge_pattern.findall(edge_line)
        for source, link_lbl1, link_lbl2, target in edge_matches:
            # If nodes are mentioned in edge but not defined, add them
            if source not in nodes:
                nodes[source] = {"id": source, "label": source, "shape": "rectangle"}
            if target not in nodes:
                nodes[target] = {"id": target, "label": target, "shape": "rectangle"}
            
            label = link_lbl1 or link_lbl2 or ""
            edges.append({
                "source": source,
                "target": target,
                "label": label.strip()
            })

    return {"nodes": list(nodes.values()), "edges": edges}


def build_drawio_xml(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
    """
    Builds a valid, editable Draw.io XML string from structured nodes and edges.
    """
    mxfile = ET.Element("mxfile", {
        "host": "Electron",
        "modified": "2026-07-28T23:09:19.000Z",
        "agent": "Mozilla/5.0",
        "version": "21.6.8",
        "type": "device"
    })
    
    diagram_id = f"d-{uuid.uuid4().hex[:8]}"
    diagram = ET.SubElement(mxfile, "diagram", {
        "id": diagram_id,
        "name": "Architecture/Workflow Diagram"
    })
    
    mxGraphModel = ET.SubElement(diagram, "mxGraphModel", {
        "dx": "1000",
        "dy": "1000",
        "grid": "1",
        "gridSize": "10",
        "guides": "1",
        "tooltips": "1",
        "connect": "1",
        "arrows": "1",
        "fold": "1",
        "page": "1",
        "pageScale": "1",
        "pageWidth": "827",
        "pageHeight": "1169",
        "math": "0",
        "shadow": "0"
    })
    
    root = ET.SubElement(mxGraphModel, "root")
    
    # Required base cells
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    
    # Calculate layouts (horizontal grid layout)
    start_x = 80
    start_y = 100
    spacing_x = 220
    spacing_y = 140
    cols = 3
    
    # Shapes styles configuration
    styles = {
        "rectangle": "rounded=0;whiteSpace=wrap;html=1;fillColor=#f8f9fa;strokeColor=#bdc1c6;strokeWidth=2;fontColor=#3c4043;fontStyle=1;",
        "rounded": "rounded=1;whiteSpace=wrap;html=1;arcSize=15;fillColor=#e8f0fe;strokeColor=#1a73e8;strokeWidth=2;fontColor=#174ea6;fontStyle=1;",
        "circle": "ellipse;whiteSpace=wrap;html=1;fillColor=#e6f4ea;strokeColor=#137333;strokeWidth=2;fontColor=#137333;fontStyle=1;",
        "rhombus": "rhombus;whiteSpace=wrap;html=1;fillColor=#fef7e0;strokeColor=#b06000;strokeWidth=2;fontColor=#b06000;fontStyle=1;",
        "database": "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=15;whiteSpace=wrap;html=1;fillColor=#f3e8fd;strokeColor=#8ab4f8;strokeWidth=2;fontColor=#8430d9;fontStyle=1;"
    }
    
    node_positions = {}
    for idx, node in enumerate(nodes):
        node_id = node["id"]
        label = node["label"]
        shape = node.get("shape", "rectangle")
        style = styles.get(shape, styles["rectangle"])
        
        # Position calculation
        col = idx % cols
        row = idx // cols
        x = start_x + col * spacing_x
        y = start_y + row * spacing_y
        
        width = 130
        height = 60
        if shape == "circle":
            width = 80
            height = 80
        elif shape == "rhombus":
            width = 100
            height = 100
            
        node_positions[node_id] = (x, y, width, height)
        
        mxCell = ET.SubElement(root, "mxCell", {
            "id": node_id,
            "value": label,
            "style": style,
            "vertex": "1",
            "parent": "1"
        })
        
        ET.SubElement(mxCell, "mxGeometry", {
            "x": str(x),
            "y": str(y),
            "width": str(width),
            "height": str(height),
            "as": "geometry"
        })
        
    for idx, edge in enumerate(edges):
        source = edge["source"]
        target = edge["target"]
        label = edge.get("label", "")
        edge_id = f"e-{idx}-{uuid.uuid4().hex[:4]}"
        
        style = "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#5f6368;strokeWidth=2;fontColor=#3c4043;"
        
        mxCell = ET.SubElement(root, "mxCell", {
            "id": edge_id,
            "value": label,
            "style": style,
            "edge": "1",
            "parent": "1",
            "source": source,
            "target": target
        })
        
        ET.SubElement(mxCell, "mxGeometry", {
            "relative": "1",
            "as": "geometry"
        })
        
    # Return XML as string
    return ET.tostring(mxfile, encoding="utf-8", xml_declaration=True).decode("utf-8")


def generate_drawio_from_markdown(markdown_content: str, doc_title: str = "Documentation Flow") -> str:
    """
    Extracts Mermaid block from markdown content and translates it to Draw.io XML.
    If no Mermaid block exists, creates a sequential workflow using headings.
    """
    # 1. Search for Mermaid code blocks
    pattern = re.compile(r"```mermaid\s*\n(.*?)\n\s*```", re.DOTALL)
    match = pattern.search(markdown_content)
    
    if match:
        mermaid_code = match.group(1)
        # Parse it
        parsed = parse_mermaid_flowchart(mermaid_code)
        if parsed["nodes"]:
            return build_drawio_xml(parsed["nodes"], parsed["edges"])
            
    # 2. Fallback: Parse Markdown headings into sequential flow nodes
    lines = markdown_content.splitlines()
    headings = []
    for line in lines:
        stripped = line.strip()
        h_match = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if h_match:
            text = h_match.group(2).strip()
            # Clean formatting markers
            text = re.sub(r"\*\*|__", "", text)
            text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
            if text and text.lower() not in ("table of contents", "toc"):
                headings.append(text)
                
    # Build list of sequential nodes
    nodes = []
    edges = []
    
    if not headings:
        # Generic absolute fallback
        headings = [doc_title, "Analysis", "Implementation", "Verification", "Conclusion"]
        
    for idx, heading in enumerate(headings[:10]):  # Limit to 10 nodes for clean layout
        node_id = f"node_{idx}"
        shape = "rounded" if idx == 0 or idx == len(headings[:10]) - 1 else "rectangle"
        nodes.append({
            "id": node_id,
            "label": heading,
            "shape": shape
        })
        if idx > 0:
            edges.append({
                "source": f"node_{idx-1}",
                "target": node_id,
                "label": "Next"
            })
            
    return build_drawio_xml(nodes, edges)
