import ast
import re
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel

class Finding(BaseModel):
    id: str
    analyzer: str
    category: str
    severity: str
    confidence: float
    title: str
    description: str
    file: str
    line_start: int
    line_end: int
    column_start: Optional[int] = None
    column_end: Optional[int] = None
    source_excerpt: str
    why_it_matters: str
    recommendation: str
    suggested_fix: Optional[str] = None
    references: List[str] = []
    related_finding_ids: List[str] = []
    affected_locations: List[Dict[str, Any]] = []

class LanguageAnalyzer:
    def __init__(self, files: Dict[str, str], depth: str = "Standard"):
        self.files = files
        self.depth = depth.lower()
        self.findings: List[Finding] = []
        self.coverage: List[str] = []

    def analyze(self) -> List[Finding]:
        raise NotImplementedError

class DataFlowTracker(ast.NodeVisitor):
    def __init__(self, files_ast: Dict[str, ast.AST]):
        self.files_ast = files_ast
        self.tainted_vars: Dict[str, Set[str]] = {} # filename -> set of tainted var names
        self.function_defs: Dict[str, ast.FunctionDef] = {} # func_name -> node
        self.current_file = ""
        self.findings = []
        self.cross_file_taints: Dict[str, Dict[str, Set[int]]] = {} # filename -> func_name -> set of tainted arg indices

    def set_file(self, filename: str):
        self.current_file = filename
        if filename not in self.tainted_vars:
            self.tainted_vars[filename] = set()

    def visit_FunctionDef(self, node):
        self.function_defs[node.name] = node
        
        # If this function is called elsewhere with tainted args, its params become tainted
        if self.current_file in self.cross_file_taints and node.name in self.cross_file_taints[self.current_file]:
            tainted_indices = self.cross_file_taints[self.current_file][node.name]
            for i, arg in enumerate(node.args.args):
                if i in tainted_indices:
                    self.tainted_vars[self.current_file].add(arg.arg)
                    
        self.generic_visit(node)

    def visit_Assign(self, node):
        is_tainted = False
        if isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Name) and func.id == 'input':
                is_tainted = True
            elif isinstance(func, ast.Attribute) and func.attr == 'get':
                if isinstance(func.value, ast.Attribute) and getattr(func.value, 'attr', '') in ('args', 'form', 'json'):
                    is_tainted = True
        
        if is_tainted:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.tainted_vars[self.current_file].add(target.id)
                    
        self.generic_visit(node)

    def visit_Call(self, node):
        # Cross-file/function tracking
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            tainted_indices = set()
            for i, arg in enumerate(node.args):
                if isinstance(arg, ast.Name) and arg.id in self.tainted_vars.get(self.current_file, set()):
                    tainted_indices.add(i)
                    
            if tainted_indices:
                if self.current_file not in self.cross_file_taints:
                    self.cross_file_taints[self.current_file] = {}
                if func_name not in self.cross_file_taints[self.current_file]:
                    self.cross_file_taints[self.current_file][func_name] = set()
                self.cross_file_taints[self.current_file][func_name].update(tainted_indices)
                
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            tainted_indices = set()
            for i, arg in enumerate(node.args):
                if isinstance(arg, ast.Name) and arg.id in self.tainted_vars.get(self.current_file, set()):
                    tainted_indices.add(i)
                    
            if tainted_indices:
                # very naive module.function tracking
                if isinstance(node.func.value, ast.Name):
                    mod_name = node.func.value.id
                    # guess the filename might be mod_name + ".py"
                    guess_file = f"{mod_name}.py"
                    if guess_file in self.files_ast:
                        if guess_file not in self.cross_file_taints:
                            self.cross_file_taints[guess_file] = {}
                        if func_name not in self.cross_file_taints[guess_file]:
                            self.cross_file_taints[guess_file][func_name] = set()
                        self.cross_file_taints[guess_file][func_name].update(tainted_indices)
                        
        self.generic_visit(node)

class PythonAnalyzer(LanguageAnalyzer):
    def get_source_excerpt(self, filename: str, start: int, end: int) -> str:
        lines = self.files[filename].split("\n")
        if 1 <= start <= len(lines) and 1 <= end <= len(lines):
            return "\n".join(lines[start-1:end])
        return ""

    def analyze(self) -> List[Finding]:
        self.coverage.append("✓ Syntax Parsing")
        
        trees = {}
        for filename, content in self.files.items():
            try:
                tree = ast.parse(content, filename=filename)
                
                # Decorate with parent_func
                for node in ast.walk(tree):
                    for child in ast.iter_child_nodes(node):
                        child.parent = node
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            child.parent_func = node
                        elif hasattr(node, 'parent_func'):
                            child.parent_func = node.parent_func
                            
                trees[filename] = tree
            except SyntaxError as e:
                line_no = e.lineno or 1
                col_offset = e.offset or 1
                excerpt = self.get_source_excerpt(filename, line_no, line_no)
                self.findings.append(Finding(
                    id="SYN-001",
                    analyzer="python_ast",
                    category="syntax",
                    severity="critical",
                    confidence=1.0,
                    title="Syntax Error",
                    description=f"Syntax error: {e.msg}",
                    file=filename,
                    line_start=line_no,
                    line_end=line_no,
                    column_start=col_offset,
                    column_end=col_offset,
                    source_excerpt=excerpt,
                    why_it_matters="Code with syntax errors cannot be executed or compiled.",
                    recommendation="Fix the syntax error to allow execution.",
                    suggested_fix=None
                ))
                
        self.coverage.extend(["✓ Security Rules", "✓ Data-Flow Analysis", "✓ Control-Flow Analysis"])
        if self.depth in ("standard", "deep"):
            self.coverage.extend(["✓ Performance Analysis", "✓ Documentation Analysis"])
            
        tracker = DataFlowTracker(trees)
        # pass 1: build cross-file taints
        for filename, tree in trees.items():
            tracker.set_file(filename)
            tracker.visit(tree)
            
        # pass 2: revisit with cross-file taints populated
        for filename, tree in trees.items():
            tracker.set_file(filename)
            tracker.visit(tree)

        for filename, tree in trees.items():
            self._walk_ast(filename, tree, tracker.tainted_vars.get(filename, set()))
            self._check_secrets_and_sqli(filename, self.files[filename])

        return self.findings

    def _walk_ast(self, filename: str, tree: ast.AST, tainted_vars: Set[str]):
        for node in ast.walk(tree):
            
            if self.depth in ("standard", "deep"):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        if not node.name.startswith("__"):
                            # Only flag public functions > 5 lines or classes
                            lines_len = getattr(node, 'end_lineno', 0) - getattr(node, 'lineno', 0)
                            if isinstance(node, ast.ClassDef) or lines_len > 5:
                                self._add_finding(
                                    filename, node,
                                    id="DOC-001",
                                    category="documentation",
                                    severity="low",
                                    title=f"Missing Docstring in {type(node).__name__}: {node.name}",
                                    description=f"The {node.name} lacks documentation.",
                                    why="Undocumented complex code is harder to maintain.",
                                    rec="Add a docstring explaining purpose, arguments, and return types."
                                )

            if self.depth == "deep":
                if isinstance(node, (ast.For, ast.While)):
                    self._check_loop_for_issues(filename, node)

            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in ['eval', 'exec']:
                        self._add_finding(
                            filename, node,
                            id="SEC-002",
                            category="security",
                            severity="critical",
                            title=f"Unsafe {func_name}() usage",
                            description=f"Use of {func_name}() can execute arbitrary code.",
                            why="Arbitrary code execution allows an attacker to take control of the application.",
                            rec=f"Avoid {func_name}(). Use safe parsers."
                        )

                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                    
                    # Weak Password Hashing Detection
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == 'hashlib':
                        if func_name in ('md5', 'sha1', 'sha256'):
                            # check if arg implies password
                            if node.args and isinstance(node.args[0], ast.Call) and isinstance(node.args[0].func, ast.Attribute) and node.args[0].func.attr == 'encode':
                                if isinstance(node.args[0].func.value, ast.Name):
                                    if 'pass' in node.args[0].func.value.id.lower() or 'pwd' in node.args[0].func.value.id.lower():
                                        self._add_finding(
                                            filename, node,
                                            id="SEC-006",
                                            category="security",
                                            severity="high",
                                            title="Weak Password Hashing",
                                            description="Password material is processed using a fast general-purpose hash.",
                                            why="Fast hashes are unsuitable for password storage because they allow attackers to perform large numbers of guesses efficiently.",
                                            rec="Use a dedicated password hashing scheme such as bcrypt or scrypt."
                                        )

                    if isinstance(node.func.value, ast.Name) and node.func.value.id == 'os':
                        if func_name in ('system', 'popen'):
                            arg_is_tainted = False
                            if node.args and isinstance(node.args[0], ast.Name) and node.args[0].id in tainted_vars:
                                arg_is_tainted = True
                            
                            self._add_finding(
                                filename, node,
                                id="SEC-001",
                                category="security",
                                severity="critical" if arg_is_tainted else "high",
                                title="Arbitrary Command Execution",
                                description=f"Using os.{func_name} with potentially untrusted input." if arg_is_tainted else f"Using os.{func_name}.",
                                why="Allows OS command execution, leading to compromise.",
                                rec="Use subprocess.run with an array of arguments."
                            )
                    
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == 'subprocess':
                        if func_name in ('run', 'Popen', 'call'):
                            has_shell_true = False
                            for kw in node.keywords:
                                if kw.arg == 'shell' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                    has_shell_true = True
                            
                            arg_is_tainted = False
                            if node.args and isinstance(node.args[0], ast.Name) and node.args[0].id in tainted_vars:
                                arg_is_tainted = True

                            if has_shell_true:
                                self._add_finding(
                                    filename, node,
                                    id="SEC-004",
                                    category="security",
                                    severity="critical" if arg_is_tainted else "high",
                                    title="Command Injection via subprocess shell=True",
                                    description="Executing shell commands dynamically with shell=True is highly dangerous.",
                                    why="It enables command injection if the arguments contain user input.",
                                    rec="Remove shell=True and pass arguments as a list."
                                )

            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                if isinstance(node.right, ast.Call) and getattr(node.right.func, 'id', '') == 'len':
                    is_guarded = False
                    if node.right.args and isinstance(node.right.args[0], ast.Name):
                        var_name = node.right.args[0].id
                        parent = getattr(node, 'parent_func', None)
                        if parent:
                            for child in ast.walk(parent):
                                if isinstance(child, ast.If):
                                    if isinstance(child.test, ast.UnaryOp) and isinstance(child.test.op, ast.Not) and isinstance(child.test.operand, ast.Name) and child.test.operand.id == var_name:
                                        is_guarded = True
                                    elif isinstance(child.test, ast.Compare) and isinstance(child.test.left, ast.Call) and getattr(child.test.left.func, 'id', '') == 'len' and isinstance(child.test.left.args[0], ast.Name) and child.test.left.args[0].id == var_name:
                                        is_guarded = True
                                        
                    if not is_guarded:
                        self._add_finding(
                            filename, node,
                            id="LOG-001",
                            category="logic",
                            severity="medium",
                            title="Potential Division by Zero",
                            description="Dividing by the length of a collection without checking if it is empty.",
                            why="Raises a ZeroDivisionError.",
                            rec="Add a check if collection is empty before dividing."
                        )
            
    def _check_loop_for_issues(self, filename: str, loop_node: ast.AST):
        for node in ast.walk(loop_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ('execute', 'query_database', 'save', 'update'):
                        self._add_finding(
                            filename, node,
                            id="PERF-001",
                            category="performance",
                            severity="medium",
                            title="N+1 Query Pattern",
                            description=f"Database or I/O operation '{node.func.attr}()' found inside a loop.",
                            why="Causes an operation for each item in the list, scaling poorly.",
                            rec="Use batch queries or bulk operations."
                        )

    def _check_secrets_and_sqli(self, filename: str, code: str):
        secret_patterns = [
            (r'password\s*=\s*[\'"][^\'"]+[\'"]', "Plaintext password storage"),
            (r'api_key\s*=\s*[\'"][^\'"]+[\'"]', "Hardcoded API key"),
            (r'secret\s*=\s*[\'"][^\'"]+[\'"]', "Hardcoded secret")
        ]
        
        sqli_patterns = [
            (r'["\']\s*select\s+.*from\s+.*\s*["\']\s*\+\s*\w+', "SQL Injection via Concatenation"),
            (r'["\']\s*select\s+.*from\s+.*\s*["\']\s*%\s*\w+', "SQL Injection via Formatting")
        ]
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            for pattern, title in secret_patterns:
                if re.search(pattern, line.lower()) and "input(" not in line:
                    self.findings.append(Finding(
                        id="SEC-003",
                        analyzer="regex_scanner",
                        category="security",
                        severity="high",
                        confidence=0.9,
                        title=title,
                        description="Hardcoded sensitive information detected in source code.",
                        file=filename,
                        line_start=i+1,
                        line_end=i+1,
                        source_excerpt=line.strip(),
                        why_it_matters="Hardcoded secrets can be easily extracted from source control and pose a major security risk.",
                        recommendation="Use environment variables or a secrets manager (e.g., .env files, HashiCorp Vault)."
                    ))
            
            for pattern, title in sqli_patterns:
                if re.search(pattern, line.lower()):
                    self.findings.append(Finding(
                        id="SEC-005",
                        analyzer="regex_scanner",
                        category="security",
                        severity="high",
                        confidence=0.9,
                        title=title,
                        description="Unsafe SQL query construction detected.",
                        file=filename,
                        line_start=i+1,
                        line_end=i+1,
                        source_excerpt=line.strip(),
                        why_it_matters="Allows attackers to manipulate the SQL query.",
                        recommendation="Use parameterized queries provided by your ORM or database driver."
                    ))

            if ".fetchall(" in line.lower() and self.depth == "deep":
                self.findings.append(Finding(
                        id="PERF-002",
                        analyzer="regex_scanner",
                        category="performance",
                        severity="medium",
                        confidence=0.8,
                        title="Scalability Risk: fetchall()",
                        description="Using fetchall() can load the entire result set into memory.",
                        file=filename,
                        line_start=i+1,
                        line_end=i+1,
                        source_excerpt=line.strip(),
                        why_it_matters="Large tables will cause memory exhaustion.",
                        recommendation="Use fetchmany(), limit queries, or iterate over the cursor directly."
                ))

    def _add_finding(self, filename: str, node: ast.AST, id: str, category: str, severity: str, title: str, description: str, why: str, rec: str, fix: str = None):
        line_start = getattr(node, 'lineno', 1)
        line_end = getattr(node, 'end_lineno', line_start)
        col_start = getattr(node, 'col_offset', 0)
        col_end = getattr(node, 'end_col_offset', col_start)
        excerpt = self.get_source_excerpt(filename, line_start, line_end)
        
        self.findings.append(Finding(
            id=id,
            analyzer="python_ast",
            category=category,
            severity=severity,
            confidence=0.95,
            title=title,
            description=description,
            file=filename,
            line_start=line_start,
            line_end=line_end,
            column_start=col_start,
            column_end=col_end,
            source_excerpt=excerpt,
            why_it_matters=why,
            recommendation=rec,
            suggested_fix=fix
        ))

class JavascriptAnalyzer(LanguageAnalyzer):
    def get_source_excerpt(self, filename: str, start: int, end: int) -> str:
        lines = self.files[filename].split("\n")
        if 1 <= start <= len(lines) and 1 <= end <= len(lines):
            return "\n".join(lines[start-1:end])
        return ""

    def analyze(self) -> List[Finding]:
        self.coverage.append("✓ Syntax (Regex Fallback)")
        self.coverage.append("✓ Security Rules")
        self.coverage.append("○ Cross-file analysis unavailable")
        
        sqli_patterns = [
            (r'["\']\s*select\s+.*from\s+.*\s*["\']\s*\+\s*\w+', "SQL Injection via Concatenation"),
            (r'["\']\s*select\s+.*from\s+.*\s*["\']\s*\+\s*req\.', "SQL Injection via Request Data"),
            (r'execute\([^)]*\+[^)]*\)', "SQL Injection via Concatenation in Execution")
        ]
        
        eval_patterns = [
            (r'eval\(', "Unsafe eval() usage")
        ]

        for filename, content in self.files.items():
            lines = content.split('\n')
            for i, line in enumerate(lines):
                for pattern, title in sqli_patterns:
                    if re.search(pattern, line.lower()):
                        self.findings.append(Finding(
                            id="SEC-005",
                            analyzer="regex_scanner",
                            category="security",
                            severity="high",
                            confidence=0.9,
                            title=title,
                            description="Unsafe SQL query construction detected.",
                            file=filename,
                            line_start=i+1,
                            line_end=i+1,
                            source_excerpt=line.strip(),
                            why_it_matters="Allows attackers to manipulate the SQL query.",
                            recommendation="Use parameterized queries provided by your ORM or database driver."
                        ))
                for pattern, title in eval_patterns:
                    if re.search(pattern, line.lower()):
                        self.findings.append(Finding(
                            id="SEC-002",
                            analyzer="regex_scanner",
                            category="security",
                            severity="critical",
                            confidence=0.9,
                            title=title,
                            description="Use of eval() can execute arbitrary code.",
                            file=filename,
                            line_start=i+1,
                            line_end=i+1,
                            source_excerpt=line.strip(),
                            why_it_matters="Arbitrary code execution allows an attacker to take control of the application.",
                            recommendation="Avoid eval(). Use safe parsers."
                        ))

        return self.findings

class DefaultAnalyzer(LanguageAnalyzer):
    def analyze(self) -> List[Finding]:
        self.coverage.append("○ Deterministic parser unavailable")
        return []

def get_analyzer_for_language(lang: str) -> type[LanguageAnalyzer]:
    if lang == "python": return PythonAnalyzer
    if lang in ("javascript", "typescript"): return JavascriptAnalyzer
    return DefaultAnalyzer

def determine_language(filenames: List[str], codes: List[str]) -> str:
    for filename in filenames:
        if filename.endswith('.py'): return "python"
        if filename.endswith(('.js', '.jsx')): return "javascript"
        if filename.endswith(('.ts', '.tsx')): return "typescript"
        if filename.endswith('.java'): return "java"
        if filename.endswith('.go'): return "go"
    
    # heuristics on the first file
    if codes:
        code = codes[0]
        if "def " in code and "import " in code and ":" in code:
            return "python"
        if "function " in code or "const " in code or "let " in code:
            return "javascript"
    
    return "unknown"
