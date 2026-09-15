services = [
    ('requirement_analyzer', 'AI Requirement Analyzer', 'Input unstructured requirements and generate structured functional/technical requirements.', 'ti-clipboard-list'),
    ('code_generation', 'Code Generation', 'Generate production-ready code in multiple languages and frameworks.', 'ti-code'),
    ('code_review', 'Code Review', 'Analyze source code for quality, security, and best-practice recommendations.', 'ti-search'),
    ('database_schema', 'Database Schema Creation', 'Generate ER diagrams, SQL scripts, and normalization suggestions.', 'ti-database'),
    ('system_design', 'System Design Generator', 'Produce architecture diagrams, APIs, and infrastructure recommendations.', 'ti-sitemap'),
    ('test_case_generator', 'Test Case Generator', 'Generate manual and automated test cases based on requirements or code.', 'ti-flask'),
    ('documentation_generator', 'Documentation Generator', 'Create professional technical documentation and API specifications.', 'ti-book'),
    ('sql_query_generator', 'SQL Query Generator', 'Convert natural language requirements into optimized SQL queries.', 'ti-terminal-2'),
]

template = """{% extends "base.html" %}

{% block title %}TITLE - E-to-E Agent{% endblock %}

{% block content %}
<div style="text-align: center; margin-bottom: 2rem;">
  <div class="logo-badge" style="display: inline-flex; align-items: center; gap: 8px; background: rgba(124,58,237,0.15); border: 1px solid var(--border-glow); border-radius: 100px; padding: 6px 16px; font-size: 0.75rem; color: var(--accent-2); font-weight: 600; text-transform: uppercase; margin-bottom: 1rem;"><i class="ti ICON"></i> TITLE</div>
  <h1 style="font-size: 2.5rem; margin-bottom: 1rem;">TITLE</h1>
  <p style="color: var(--text-muted);">DESC</p>
</div>

<div class="input-card">
  <label class="input-label"><i class="ti ti-pencil"></i> Input</label>
  <textarea id="input-text" placeholder="Enter your input here..." style="width: 100%; background: transparent; border: none; outline: none; resize: none; color: var(--text); font-family: var(--font); font-size: 1rem; line-height: 1.6; min-height: 120px;"></textarea>
</div>

<button class="run-btn" onclick="runService()">
  <i class="ti ti-sparkles"></i> Run TITLE
</button>

<div class="result-card" id="result-card" style="display: none; background: var(--surface); border: 1px solid var(--success); border-radius: var(--radius); padding: 1.75rem;">
  <div class="result-title" style="font-size: 1.1rem; font-weight: 700; color: var(--success); margin-bottom: 1.25rem; display: flex; align-items: center; gap: 8px;"><i class="ti ti-circle-check"></i> Result</div>
  <div class="result-grid" id="result-grid"></div>
</div>
{% endblock %}

{% block extra_js %}
<script>
  function runService() {
    const btn = document.querySelector('.run-btn');
    btn.innerHTML = '<i class="ti ti-loader ti-spin"></i> Processing...';
    btn.disabled = true;
    
    // Mock processing
    setTimeout(() => {
      btn.innerHTML = '<i class="ti ti-sparkles"></i> Run TITLE';
      btn.disabled = false;
      document.getElementById('result-card').style.display = 'block';
      document.getElementById('result-grid').innerHTML = '<div style="padding: 10px 14px; background: var(--surface-2); border-radius: var(--radius-sm); border: 1px solid var(--border);">Output generated successfully! (Backend integration pending)</div>';
    }, 2000);
  }
</script>
{% endblock %}
"""

for file_name, title, desc, icon in services:
    content = template.replace('TITLE', title).replace('DESC', desc).replace('ICON', icon)
    with open(f'ui/static/{file_name}.html', 'w', encoding='utf-8') as f:
        f.write(content)
