# modules/test_case_generator/engine/exporters.py

import io
import csv
import json
import yaml
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

# Optional third-party imports
try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False


def export_markdown(test_cases: List[Dict[str, Any]], analysis: Dict[str, Any], info: Dict[str, Any]) -> str:
    md = []
    md.append(f"# Test Suite: {info.get('title', 'Enterprise Test Suite')}")
    md.append(f"**Framework**: {info.get('framework', 'Generic')} | **Language**: {info.get('language', 'Generic')} | **Priority**: {info.get('priority', 'Medium')}")
    md.append(f"**Coverage Strategy**: {info.get('coverage', 'Standard')} | **Style**: {info.get('style', 'Automated')}\n")
    md.append("## Executive Summary")
    md.append(f"- **Total Test Cases**: {len(test_cases)}")
    md.append(f"- **Execution Environment**: {info.get('environment', 'Local')}")
    md.append(f"- **Complexity**: {info.get('complexity', 'Standard')}\n")
    
    md.append("## Test Cases")
    for tc in test_cases:
        md.append(f"### {tc.get('id', 'TC')}: {tc.get('title', 'Untitled')}")
        md.append(f"- **Objective**: {tc.get('objective', '')}")
        md.append(f"- **Priority**: {tc.get('priority', 'Medium')} | **Category**: {tc.get('category', 'Functional')}")
        if tc.get('feature_mapping'):
            md.append(f"- **Feature Mapping**: {tc.get('feature_mapping')}")
        if tc.get('requirement_mapping'):
            md.append(f"- **Requirement Mapping**: {tc.get('requirement_mapping')}")
        if tc.get('preconditions'):
            md.append(f"- **Preconditions**: {tc.get('preconditions')}")
        if tc.get('dependencies'):
            md.append(f"- **Dependencies**: {tc.get('dependencies')}")
        if tc.get('environment_setup'):
            md.append(f"- **Environment Setup**: {tc.get('environment_setup')}")
        if tc.get('test_data'):
            md.append(f"- **Test Data**: `{tc.get('test_data')}`")
        if tc.get('estimated_execution_time'):
            md.append(f"- **Estimated Execution Time**: {tc.get('estimated_execution_time')}")
            
        md.append("\n#### Action Steps")
        steps = tc.get('steps', [])
        if steps:
            md.append("| Step | Action | Expected Result | Actual Result | Status |")
            md.append("| --- | --- | --- | --- | --- |")
            for s in steps:
                num = s.get('step_number', 1)
                act = s.get('action', '').replace('\n', ' ').replace('|', '\\|')
                exp = s.get('expected_result', '').replace('\n', ' ').replace('|', '\\|')
                act_p = tc.get('actual_result_placeholder', 'Pending execution')
                stat = tc.get('status_placeholder', 'Untested')
                md.append(f"| {num} | {act} | {exp} | {act_p} | {stat} |")
        else:
            md.append(f"- **Expected Result**: {tc.get('expected_result', '')}")
            
        if tc.get('cleanup_steps'):
            md.append(f"\n- **Cleanup Steps**: {tc.get('cleanup_steps')}")
            
        extras = []
        if tc.get('edge_cases'):
            extras.append(f"- **Edge Cases**: {tc.get('edge_cases')}")
        if tc.get('negative_scenarios'):
            extras.append(f"- **Negative Scenarios**: {tc.get('negative_scenarios')}")
        if tc.get('boundary_conditions'):
            extras.append(f"- **Boundary Conditions**: {tc.get('boundary_conditions')}")
        if tc.get('risk_assessment'):
            extras.append(f"- **Risk Assessment**: {tc.get('risk_assessment')}")
        if tc.get('automation_feasibility'):
            extras.append(f"- **Automation Feasibility**: {tc.get('automation_feasibility')}")
            
        if extras:
            md.append("\n#### Risk & Context Analysis")
            md.extend(extras)
            
        md.append("\n---\n")

    md.append("## AI-Powered Quality Analysis")
    for category, items in analysis.items():
        if items and isinstance(items, list):
            title = category.replace('_', ' ').title()
            md.append(f"### {title}")
            for item in items:
                md.append(f"- {item}")
    
    if info.get("code"):
        md.append("\n## Generated Automated Test Suite Code")
        md.append(f"```{info.get('language', 'python').lower()}")
        md.append(info.get("code"))
        md.append("```")
        
    return "\n".join(md)


def export_html(test_cases: List[Dict[str, Any]], analysis: Dict[str, Any], info: Dict[str, Any]) -> str:
    md_content = export_markdown(test_cases, analysis, info)
    # Simple conversion of markdown to basic styled HTML
    import html
    escaped_md = html.escape(md_content)
    
    # We will generate a beautifully styled HTML file directly
    rows = []
    for tc in test_cases:
        steps_rows = ""
        for s in tc.get('steps', []):
            steps_rows += f"""
            <tr>
                <td>{s.get('step_number', 1)}</td>
                <td>{html.escape(s.get('action', ''))}</td>
                <td>{html.escape(s.get('expected_result', ''))}</td>
                <td>{html.escape(tc.get('actual_result_placeholder', 'Pending'))}</td>
                <td><span class="badge badge-pending">{html.escape(tc.get('status_placeholder', 'Untested'))}</span></td>
            </tr>
            """
        
        rows.append(f"""
        <div class="card">
            <div class="card-header">
                <h3>{html.escape(tc.get('id', 'TC'))}: {html.escape(tc.get('title', 'Untitled'))}</h3>
                <span class="badge badge-priority">{html.escape(tc.get('priority', 'Medium'))}</span>
                <span class="badge badge-category">{html.escape(tc.get('category', 'Functional'))}</span>
            </div>
            <div class="card-body">
                <p><strong>Objective:</strong> {html.escape(tc.get('objective', ''))}</p>
                {f"<p><strong>Preconditions:</strong> {html.escape(tc.get('preconditions', ''))}</p>" if tc.get('preconditions') else ""}
                {f"<p><strong>Dependencies:</strong> {html.escape(tc.get('dependencies', ''))}</p>" if tc.get('dependencies') else ""}
                {f"<p><strong>Test Data:</strong> <code>{html.escape(tc.get('test_data', ''))}</code></p>" if tc.get('test_data') else ""}
                
                <h4>Action Steps</h4>
                <table>
                    <thead>
                        <tr>
                            <th style="width: 8%;">Step</th>
                            <th style="width: 42%;">Action</th>
                            <th style="width: 30%;">Expected Result</th>
                            <th style="width: 12%;">Actual Result</th>
                            <th style="width: 8%;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {steps_rows if steps_rows else f'<tr><td colspan="5">{html.escape(tc.get("expected_result", ""))}</td></tr>'}
                    </tbody>
                </table>
                
                <div class="meta-section">
                    {f"<div><strong>Edge Cases:</strong> {html.escape(tc.get('edge_cases', ''))}</div>" if tc.get('edge_cases') else ""}
                    {f"<div><strong>Negative Scenarios:</strong> {html.escape(tc.get('negative_scenarios', ''))}</div>" if tc.get('negative_scenarios') else ""}
                    {f"<div><strong>Boundary Conditions:</strong> {html.escape(tc.get('boundary_conditions', ''))}</div>" if tc.get('boundary_conditions') else ""}
                    {f"<div><strong>Risk Assessment:</strong> {html.escape(tc.get('risk_assessment', ''))}</div>" if tc.get('risk_assessment') else ""}
                    {f"<div><strong>Automation Feasibility:</strong> {html.escape(tc.get('automation_feasibility', ''))}</div>" if tc.get('automation_feasibility') else ""}
                    {f"<div><strong>Estimated Execution Time:</strong> {html.escape(tc.get('estimated_execution_time', ''))}</div>" if tc.get('estimated_execution_time') else ""}
                </div>
            </div>
        </div>
        """)
        
    analysis_sections = ""
    for category, items in analysis.items():
        if items and isinstance(items, list):
            list_items = "".join(f"<li>{html.escape(item)}</li>" for item in items)
            analysis_sections += f"""
            <div class="analysis-card">
                <h4>{category.replace('_', ' ').title()}</h4>
                <ul>{list_items}</ul>
            </div>
            """
            
    code_block = ""
    if info.get("code"):
        code_block = f"""
        <h2>Generated Automated Test Suite Code</h2>
        <pre><code class="language-{info.get('language', 'python').lower()}">{html.escape(info.get('code'))}</code></pre>
        """

    html_doc = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Test Suite - {html.escape(info.get('title', 'Enterprise Test Suite'))}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b; padding: 2rem; max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #0f172a; margin-bottom: 0.5rem; }}
        .meta-header {{ font-size: 0.95rem; color: #64748b; margin-bottom: 2rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 1rem; }}
        .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }}
        .card-header {{ background-color: #f1f5f9; padding: 1rem; border-bottom: 1px solid #e2e8f0; display: flex; align-items: center; justify-content: space-between; }}
        .card-header h3 {{ margin: 0; font-size: 1.15rem; color: #1e293b; }}
        .badge {{ padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
        .badge-priority {{ background-color: #fee2e2; color: #991b1b; }}
        .badge-category {{ background-color: #dbeafe; color: #1e40af; }}
        .badge-pending {{ background-color: #fef3c7; color: #92400e; }}
        .card-body {{ padding: 1.5rem; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1rem; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 0.9rem; }}
        th {{ background-color: #f8fafc; font-weight: 600; color: #475569; }}
        .meta-section {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px dotted #e2e8f0; font-size: 0.85rem; color: #475569; }}
        .analysis-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-top: 1.5rem; }}
        .analysis-card {{ background: #fff; border-left: 4px solid #ef4444; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; border-radius: 0 8px 8px 0; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .analysis-card h4 {{ margin-top: 0; margin-bottom: 0.5rem; color: #991b1b; }}
        pre {{ background-color: #1e293b; color: #f8fafc; padding: 1.5rem; border-radius: 8px; overflow-x: auto; font-family: Consolas, Monaco, monospace; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <h1>Test Suite: {html.escape(info.get('title', 'Enterprise Test Suite'))}</h1>
    <div class="meta-header">
        <strong>Framework:</strong> {html.escape(info.get('framework', 'Generic'))} | 
        <strong>Language:</strong> {html.escape(info.get('language', 'Generic'))} | 
        <strong>Coverage Strategy:</strong> {html.escape(info.get('coverage', 'Standard'))} | 
        <strong>Style:</strong> {html.escape(info.get('style', 'Automated'))} | 
        <strong>Complexity:</strong> {html.escape(info.get('complexity', 'Standard'))}
    </div>
    
    <h2>Test Cases ({len(test_cases)})</h2>
    {"".join(rows)}
    
    <h2>AI-Powered Quality Analysis</h2>
    <div class="analysis-container">
        {analysis_sections}
    </div>
    
    {code_block}
</body>
</html>
"""
    return html_doc


def export_docx(test_cases: List[Dict[str, Any]], analysis: Dict[str, Any], info: Dict[str, Any]) -> bytes:
    # Use python-docx if installed, otherwise fallback to HTML wrapped in docx or plain document bytes
    if not HAS_DOCX:
        # Fallback: Write HTML or a simple text format inside the byte stream
        html_content = export_html(test_cases, analysis, info)
        return html_content.encode('utf-8')
        
    doc = Document()
    doc.add_heading(f"Test Suite: {info.get('title', 'Enterprise Test Suite')}", level=0)
    
    p = doc.add_paragraph()
    p.add_run(f"Framework: {info.get('framework', 'Generic')} | Language: {info.get('language', 'Generic')} | Style: {info.get('style', 'Automated')}\n").italic = True
    p.add_run(f"Coverage: {info.get('coverage', 'Standard')} | Environment: {info.get('environment', 'Local')} | Complexity: {info.get('complexity', 'Standard')}")
    
    doc.add_heading("Test Cases Summary", level=1)
    
    # Add a table of test cases
    table = doc.add_table(rows=1, cols=4)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'ID'
    hdr_cells[1].text = 'Title'
    hdr_cells[2].text = 'Priority'
    hdr_cells[3].text = 'Category'
    
    for tc in test_cases:
        row_cells = table.add_row().cells
        row_cells[0].text = str(tc.get('id', 'TC'))
        row_cells[1].text = str(tc.get('title', 'Untitled'))
        row_cells[2].text = str(tc.get('priority', 'Medium'))
        row_cells[3].text = str(tc.get('category', 'Functional'))
        
    for tc in test_cases:
        doc.add_heading(f"{tc.get('id', 'TC')}: {tc.get('title', 'Untitled')}", level=2)
        doc.add_paragraph(f"Objective: {tc.get('objective', '')}")
        if tc.get('preconditions'):
            doc.add_paragraph(f"Preconditions: {tc.get('preconditions')}")
        if tc.get('test_data'):
            doc.add_paragraph(f"Test Data: {tc.get('test_data')}")
            
        doc.add_heading("Steps", level=3)
        steps_table = doc.add_table(rows=1, cols=3)
        s_headers = steps_table.rows[0].cells
        s_headers[0].text = 'Step'
        s_headers[1].text = 'Action'
        s_headers[2].text = 'Expected Result'
        
        for s in tc.get('steps', []):
            r_cells = steps_table.add_row().cells
            r_cells[0].text = str(s.get('step_number', 1))
            r_cells[1].text = str(s.get('action', ''))
            r_cells[2].text = str(s.get('expected_result', ''))
            
        if tc.get('cleanup_steps'):
            doc.add_paragraph(f"Cleanup Steps: {tc.get('cleanup_steps')}")
            
        # Analysis metadata
        meta = []
        if tc.get('edge_cases'):
            meta.append(f"Edge Cases: {tc.get('edge_cases')}")
        if tc.get('negative_scenarios'):
            meta.append(f"Negative Scenarios: {tc.get('negative_scenarios')}")
        if tc.get('boundary_conditions'):
            meta.append(f"Boundary Conditions: {tc.get('boundary_conditions')}")
        if tc.get('risk_assessment'):
            meta.append(f"Risk Assessment: {tc.get('risk_assessment')}")
            
        if meta:
            doc.add_heading("Additional Analysis", level=3)
            for m in meta:
                doc.add_paragraph(m)
                
    doc.add_heading("AI-Powered Quality Analysis", level=1)
    for category, items in analysis.items():
        if items and isinstance(items, list):
            doc.add_heading(category.replace('_', ' ').title(), level=2)
            for item in items:
                doc.add_paragraph(item, style='List Bullet')
                
    if info.get("code"):
        doc.add_heading("Automated Test Suite Code", level=1)
        doc.add_paragraph(info.get("code"))
        
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


def export_xlsx(test_cases: List[Dict[str, Any]], analysis: Dict[str, Any], info: Dict[str, Any]) -> bytes:
    if not HAS_OPENPYXL:
        # Fallback to CSV format encoded in bytes
        return export_csv(test_cases, analysis, info).encode('utf-8')
        
    wb = Workbook()
    
    # Sheet 1: Test Cases
    ws1 = wb.active
    ws1.title = "Test Cases"
    
    headers = [
        "Test Case ID", "Title", "Objective", "Priority", "Category", 
        "Feature Mapping", "Requirement Mapping", "Preconditions", 
        "Dependencies", "Test Data", "Steps", "Expected Results", 
        "Actual Result Placeholder", "Status Placeholder", "Cleanup Steps",
        "Edge Cases", "Negative Scenarios", "Boundary Conditions", 
        "Risk Assessment", "Automation Feasibility", "Estimated Execution Time"
    ]
    ws1.append(headers)
    
    # Formatting headers
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    for col_idx in range(1, len(headers) + 1):
        cell = ws1.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
    for tc in test_cases:
        steps_str = ""
        for s in tc.get('steps', []):
            steps_str += f"{s.get('step_number', 1)}. {s.get('action', '')}\n"
            
        exp_str = ""
        for s in tc.get('steps', []):
            exp_str += f"{s.get('step_number', 1)}. {s.get('expected_result', '')}\n"
        if not exp_str:
            exp_str = tc.get('expected_result', '')
            
        row = [
            tc.get("id", ""),
            tc.get("title", ""),
            tc.get("objective", ""),
            tc.get("priority", "Medium"),
            tc.get("category", "Functional"),
            tc.get("feature_mapping", ""),
            tc.get("requirement_mapping", ""),
            tc.get("preconditions", ""),
            tc.get("dependencies", ""),
            tc.get("test_data", ""),
            steps_str.strip(),
            exp_str.strip(),
            tc.get("actual_result_placeholder", "Pending execution"),
            tc.get("status_placeholder", "Untested"),
            tc.get("cleanup_steps", ""),
            tc.get("edge_cases", ""),
            tc.get("negative_scenarios", ""),
            tc.get("boundary_conditions", ""),
            tc.get("risk_assessment", ""),
            tc.get("automation_feasibility", ""),
            tc.get("estimated_execution_time", "")
        ]
        ws1.append(row)
        
    # Auto-adjust column widths
    for col in ws1.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = col[0].column_letter
        ws1.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)
        
    # Sheet 2: AI Analysis
    ws2 = wb.create_sheet(title="AI Analysis")
    ws2.append(["Category", "Analysis Scenario / Quality Risk Check"])
    ws2.cell(row=1, column=1).font = header_font
    ws2.cell(row=1, column=1).fill = header_fill
    ws2.cell(row=1, column=2).font = header_font
    ws2.cell(row=1, column=2).fill = header_fill
    
    for category, items in analysis.items():
        if items and isinstance(items, list):
            cat_title = category.replace('_', ' ').title()
            for item in items:
                ws2.append([cat_title, item])
                
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def export_pdf(test_cases: List[Dict[str, Any]], analysis: Dict[str, Any], info: Dict[str, Any]) -> bytes:
    if not HAS_FPDF:
        # Fallback: HTML content
        return export_html(test_cases, analysis, info).encode('utf-8')
        
    class PDFSuite(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 12)
            self.set_x(10)
            self.cell(190, 8, f"Test Suite: {info.get('title', 'Enterprise Test Suite')}", 0, 0, 'C')
            self.ln(8)
            self.set_font('Helvetica', 'I', 8)
            self.set_x(10)
            self.cell(190, 5, f"Framework: {info.get('framework', 'Generic')} | Language: {info.get('language', 'Generic')} | Style: {info.get('style', 'Automated')}", 0, 0, 'C')
            self.ln(10)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_x(10)
            self.cell(190, 10, f"Page {self.page_no()}", 0, 0, 'C')

    pdf = PDFSuite()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_x(10)
    pdf.cell(190, 10, "Test Cases Summary", 0, 0)
    pdf.ln(10)
    pdf.set_font("Helvetica", size=9)
    
    for tc in test_cases:
        # MultiCell handles long text and auto-wrapping
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_x(10)
        pdf.multi_cell(190, 8, f"{tc.get('id', 'TC')}: {tc.get('title', 'Untitled')} ({tc.get('priority', 'Medium')})")
        pdf.set_font("Helvetica", size=9)
        pdf.set_x(10)
        pdf.multi_cell(190, 5, f"Objective: {tc.get('objective', '')}")
        if tc.get('preconditions'):
            pdf.set_x(10)
            pdf.multi_cell(190, 5, f"Preconditions: {tc.get('preconditions')}")
            
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_x(10)
        pdf.cell(190, 6, "Steps:", 0, 0)
        pdf.ln(6)
        pdf.set_font("Helvetica", size=9)
        for s in tc.get('steps', []):
            step_txt = f"  Step {s.get('step_number', 1)}: {s.get('action', '')}\n  Expected: {s.get('expected_result', '')}"
            pdf.set_x(10)
            pdf.multi_cell(190, 5, step_txt)
            pdf.ln(1)
            
        pdf.ln(3)
        
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_x(10)
    pdf.cell(190, 10, "AI-Powered Quality Analysis", 0, 0)
    pdf.ln(10)
    pdf.set_font("Helvetica", size=9)
    
    for category, items in analysis.items():
        if items and isinstance(items, list):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_x(10)
            pdf.cell(190, 8, category.replace('_', ' ').title(), 0, 0)
            pdf.ln(8)
            pdf.set_font("Helvetica", size=9)
            for item in items:
                pdf.set_x(10)
                pdf.multi_cell(190, 5, f"- {item}")
            pdf.ln(2)
            
    return pdf.output()


def export_csv(test_cases: List[Dict[str, Any]], analysis: Dict[str, Any], info: Dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = [
        "Test Case ID", "Title", "Objective", "Priority", "Category", 
        "Preconditions", "Test Data", "Steps", "Expected Results", 
        "Actual Result Placeholder", "Status"
    ]
    writer.writerow(headers)
    
    for tc in test_cases:
        steps_str = "\n".join(f"{s.get('step_number', 1)}. {s.get('action', '')}" for s in tc.get('steps', []))
        exp_str = "\n".join(f"{s.get('step_number', 1)}. {s.get('expected_result', '')}" for s in tc.get('steps', []))
        if not exp_str:
            exp_str = tc.get('expected_result', '')
            
        writer.writerow([
            tc.get("id", ""),
            tc.get("title", ""),
            tc.get("objective", ""),
            tc.get("priority", "Medium"),
            tc.get("category", "Functional"),
            tc.get("preconditions", ""),
            tc.get("test_data", ""),
            steps_str,
            exp_str,
            tc.get("actual_result_placeholder", "Pending execution"),
            tc.get("status_placeholder", "Untested")
        ])
        
    return output.getvalue()


def export_xml(test_cases: List[Dict[str, Any]], analysis: Dict[str, Any], info: Dict[str, Any]) -> str:
    root = ET.Element("TestSuite")
    
    meta = ET.SubElement(root, "Metadata")
    for k, v in info.items():
        if k != "code":
            ET.SubElement(meta, k).text = str(v)
            
    tcs = ET.SubElement(root, "TestCases")
    for tc in test_cases:
        tc_el = ET.SubElement(tcs, "TestCase", id=tc.get("id", "TC"))
        ET.SubElement(tc_el, "Title").text = tc.get("title", "")
        ET.SubElement(tc_el, "Objective").text = tc.get("objective", "")
        ET.SubElement(tc_el, "Priority").text = tc.get("priority", "")
        ET.SubElement(tc_el, "Category").text = tc.get("category", "")
        ET.SubElement(tc_el, "Preconditions").text = tc.get("preconditions", "")
        ET.SubElement(tc_el, "TestData").text = tc.get("test_data", "")
        
        steps = ET.SubElement(tc_el, "Steps")
        for s in tc.get('steps', []):
            step_el = ET.SubElement(steps, "Step", number=str(s.get('step_number', 1)))
            ET.SubElement(step_el, "Action").text = s.get('action', '')
            ET.SubElement(step_el, "ExpectedResult").text = s.get('expected_result', '')
            
        ET.SubElement(tc_el, "ActualResultPlaceholder").text = tc.get("actual_result_placeholder", "")
        ET.SubElement(tc_el, "StatusPlaceholder").text = tc.get("status_placeholder", "")
        ET.SubElement(tc_el, "CleanupSteps").text = tc.get("cleanup_steps", "")
        ET.SubElement(tc_el, "RiskAssessment").text = tc.get("risk_assessment", "")
        
    quality = ET.SubElement(root, "QualityAnalysis")
    for cat, items in analysis.items():
        if items and isinstance(items, list):
            cat_el = ET.SubElement(quality, cat)
            for item in items:
                ET.SubElement(cat_el, "Item").text = item
                
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def export_junit_xml(test_cases: List[Dict[str, Any]], info: Dict[str, Any]) -> str:
    root = ET.Element("testsuite", name=info.get("title", "Enterprise Test Suite"), tests=str(len(test_cases)), failures="0", errors="0", skipped=str(len(test_cases)))
    
    for tc in test_cases:
        tc_el = ET.SubElement(root, "testcase", classname=tc.get("category", "Functional"), name=tc.get("title", ""), time="0.0")
        # Since it is a generated manual or placeholders test suite, mark it as skipped
        skipped_el = ET.SubElement(tc_el, "skipped", message="Placeholder/Manual execution pending")
        skipped_el.text = tc.get("objective", "")
        
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def export_allure_report_zip(test_cases: List[Dict[str, Any]], info: Dict[str, Any]) -> bytes:
    # Allure expects a set of JSON files detailing test results
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, 'w', zipfile.ZIP_DEFLATED) as zf:
        for idx, tc in enumerate(test_cases):
            import uuid
            case_uuid = str(uuid.uuid4())
            allure_case = {
                "uuid": case_uuid,
                "historyId": str(uuid.uuid5(uuid.NAMESPACE_DNS, tc.get('title', f"test_{idx}"))),
                "fullName": f"tests.{tc.get('category', 'Functional')}.{tc.get('id', 'TC')}",
                "labels": [
                    {"name": "suite", "value": info.get("title", "Enterprise Test Suite")},
                    {"name": "framework", "value": info.get("framework", "Generic")},
                    {"name": "language", "value": info.get("language", "Generic")},
                    {"name": "severity", "value": tc.get("priority", "normal").lower()}
                ],
                "name": tc.get("title", "Untitled"),
                "status": "skipped",
                "statusDetails": {"message": tc.get("objective", "Pending execution")},
                "steps": [
                    {
                        "name": s.get("action", ""),
                        "status": "passed",
                        "stage": "finished",
                        "steps": []
                    } for s in tc.get("steps", [])
                ],
                "start": 1700000000000,
                "stop": 1700000001000
            }
            zf.writestr(f"{case_uuid}-result.json", json.dumps(allure_case, indent=2))
    return bio.getvalue()


def export_testrail_csv(test_cases: List[Dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Standard columns for TestRail import
    writer.writerow(["Section", "Title", "Type", "Priority", "Preconditions", "Steps", "Expected Result"])
    for tc in test_cases:
        steps_str = "\n".join(f"Step {s.get('step_number', 1)}: {s.get('action', '')}" for s in tc.get('steps', []))
        exp_str = "\n".join(f"Expected: {s.get('expected_result', '')}" for s in tc.get('steps', []))
        
        writer.writerow([
            tc.get("category", "Functional"),
            tc.get("title", "Untitled"),
            "Automated" if tc.get("automation_feasibility") == "High" else "Manual",
            tc.get("priority", "Medium"),
            tc.get("preconditions", ""),
            steps_str,
            exp_str or tc.get("expected_result", "")
        ])
    return output.getvalue()


def export_xray_json(test_cases: List[Dict[str, Any]], info: Dict[str, Any]) -> str:
    # Xray JSON import format
    xray_tests = []
    for tc in test_cases:
        steps = []
        for s in tc.get('steps', []):
            steps.append({
                "action": s.get("action", ""),
                "result": s.get("expected_result", "")
            })
            
        xray_tests.append({
            "testKey": tc.get("id", ""),
            "info": {
                "summary": tc.get("title", ""),
                "description": tc.get("objective", ""),
                "requirementKeys": [tc.get("requirement_mapping", "")] if tc.get("requirement_mapping") else [],
                "labels": [tc.get("category", "Functional"), info.get("framework", "Generic")]
            },
            "steps": steps
        })
    return json.dumps({"tests": xray_tests}, indent=2)


def export_zephyr_csv(test_cases: List[Dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Zephyr CSV import fields
    writer.writerow(["Name", "Objective", "Pre-requisite", "Priority", "Steps", "Expected Result"])
    for tc in test_cases:
        steps_str = "\n".join(f"{s.get('step_number', 1)}. {s.get('action', '')}" for s in tc.get('steps', []))
        exp_str = "\n".join(f"{s.get('step_number', 1)}. {s.get('expected_result', '')}" for s in tc.get('steps', []))
        
        writer.writerow([
            tc.get("title", "Untitled"),
            tc.get("objective", ""),
            tc.get("preconditions", ""),
            tc.get("priority", "Medium"),
            steps_str,
            exp_str or tc.get("expected_result", "")
        ])
    return output.getvalue()


def export_azure_devops_csv(test_cases: List[Dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Azure DevOps Test Cases standard schema
    writer.writerow(["Title", "Description", "Priority", "Step Action", "Step Expected"])
    for tc in test_cases:
        steps = tc.get('steps', [])
        if steps:
            for idx, s in enumerate(steps):
                # For multiple steps in Azure DevOps import, first row contains title and details,
                # subsequent rows represent subsequent steps with same title or empty fields
                writer.writerow([
                    tc.get("title", "") if idx == 0 else "",
                    tc.get("objective", "") if idx == 0 else "",
                    tc.get("priority", "Medium") if idx == 0 else "",
                    s.get("action", ""),
                    s.get("expected_result", "")
                ])
        else:
            writer.writerow([
                tc.get("title", ""),
                tc.get("objective", ""),
                tc.get("priority", "Medium"),
                "",
                tc.get("expected_result", "")
            ])
    return output.getvalue()


def export_zip_package(test_cases: List[Dict[str, Any]], analysis: Dict[str, Any], info: Dict[str, Any]) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Include Markdown
        zf.writestr("test_suite.md", export_markdown(test_cases, analysis, info))
        # Include HTML
        zf.writestr("test_suite.html", export_html(test_cases, analysis, info))
        # Include JSON
        zf.writestr("test_suite.json", json.dumps({"test_cases": test_cases, "analysis": analysis, "info": info}, indent=2))
        # Include YAML
        zf.writestr("test_suite.yaml", yaml.dump({"test_cases": test_cases, "analysis": analysis, "info": info}, default_flow_style=False))
        # Include XML
        zf.writestr("test_suite.xml", export_xml(test_cases, analysis, info))
        # Include CSV
        zf.writestr("test_cases.csv", export_csv(test_cases, analysis, info))
        
        # Include Code if present
        if info.get("code"):
            ext = info.get("extension", ".txt")
            zf.writestr(f"automated_tests{ext}", info.get("code"))
            
    return bio.getvalue()
