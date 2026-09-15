"""
modules/common/logger.py
─────────────────────────
Centralized color-coded logging system for Cytron.AI.
Handles console color rendering, structured JSON log rotation,
non-blocking asynchronous queue logging, context propagation,
LLM callbacks, and background performance monitoring.
"""

import os
import sys
import time
import json
import re
import queue
import logging
import logging.handlers
import threading
import contextvars
from datetime import datetime
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

# Enable ANSI escape sequences on Windows
if sys.platform == "win32":
    os.system("")

# ── Context Variables for Correlation ─────────────────────────────────────────
user_id_var = contextvars.ContextVar("user_id", default="")
session_id_var = contextvars.ContextVar("session_id", default="")
request_id_var = contextvars.ContextVar("request_id", default="")
agent_name_var = contextvars.ContextVar("agent_name", default="")
workflow_step_var = contextvars.ContextVar("workflow_step", default="")
correlation_id_var = contextvars.ContextVar("correlation_id", default="")
db_run_id_var = contextvars.ContextVar("db_run_id", default=0)

# Active agents tracking
active_agents = set()

# ANSI Color Chart
ANSI_COLORS = {
    "SYSTEM": "\033[97m",          # Bright White
    "STARTUP": "\033[96m",         # Bright Cyan
    "SHUTDOWN": "\033[95m",        # Bright Magenta
    "INFO": "\033[34m",            # Blue
    "SUCCESS": "\033[32m",         # Green
    "WARNING": "\033[33m",         # Yellow
    "ERROR": "\033[31m",           # Red
    "CRITICAL": "\033[1;31m",      # Bright Red (Bold)
    "USER ACTION": "\033[36m",     # Cyan
    "AGENT ACTION": "\033[35m",    # Purple
    "TOOL CALL": "\033[94m",       # Light Blue
    "API CALL": "\033[35m",        # Magenta
    "DATABASE": "\033[38;5;208m",  # Orange (256-color)
    "VECTOR DB": "\033[38;5;177m",  # Light Purple
    "CACHE": "\033[92m",           # Light Green
    "FILE SYSTEM": "\033[90m",     # Gray
    "NETWORK": "\033[94m",         # Bright Blue
    "SECURITY": "\033[93m",        # Bright Yellow
    "LLM REQUEST": "\033[38;5;205m", # Pink
    "LLM RESPONSE": "\033[32m",    # Green
    "TOKEN USAGE": "\033[36m",     # Cyan
    "PERFORMANCE": "\033[37m",     # White
    "DEBUG": "\033[90m",           # Dark Gray
    "RESET": "\033[0m"
}

# Logger component mappings
LOGGER_TO_COMPONENT = {
    "agents.project_planner": ("AGENT ACTION", "Project Planner"),
    "agents.requirement_analyzer": ("AGENT ACTION", "Requirement Analyzer"),
    "agents.system_design_agent": ("AGENT ACTION", "System Design Agent"),
    "agents.database_agent": ("AGENT ACTION", "Database Agent"),
    "agents.backend_agent": ("AGENT ACTION", "Backend Agent"),
    "agents.frontend_agent": ("AGENT ACTION", "Frontend Agent"),
    "agents.testing_agent": ("AGENT ACTION", "Testing Agent"),
    "agents.test_case_agent": ("AGENT ACTION", "Test Case Agent"),
    "agents.code_review_agent": ("AGENT ACTION", "Code Review Agent"),
    "agents.deployment_agent": ("AGENT ACTION", "Deployment Agent"),
    "agents.bug_fixing_agent": ("AGENT ACTION", "Bug Fixing Agent"),
    "agents.documentation_agent": ("AGENT ACTION", "Documentation Agent"),
    "agents.repository_agent": ("AGENT ACTION", "Repository Agent"),
    "agents.sql_query_agent": ("AGENT ACTION", "SQL Query Agent"),
    "tools.file_writer": ("FILE SYSTEM", "File Writer"),
    "tools.chroma_store": ("VECTOR DB", "ChromaDB"),
    "tools.github_tool": ("NETWORK", "GitHub Tool"),
    "tools.docker_builder": ("SYSTEM", "Docker Builder"),
    "tools.cloud_deployer": ("NETWORK", "Cloud Deployer"),
    "tools.test_runner": ("SYSTEM", "Test Runner"),
    "orchestrator.graph": ("SYSTEM", "Orchestrator"),
    "orchestrator.runner": ("SYSTEM", "Runner"),
    "ui.main": ("API CALL", "FastAPI UI"),
}


# ── Secrets Masking ───────────────────────────────────────────────────────────
_secret_regex = None
_secrets_cached = False

def _build_secrets_regex():
    global _secret_regex, _secrets_cached
    if _secrets_cached:
        return
    try:
        from config.settings import settings
        secrets_list = []
        for key in ["groq_api_key", "github_token", "chroma_api_key", "google_application_credentials"]:
            val = getattr(settings, key, None)
            if val and isinstance(val, str) and len(val) > 4:
                # Add the secret and raw token characters if it has a pattern
                secrets_list.append(re.escape(val))
        if secrets_list:
            _secret_regex = re.compile("|".join(secrets_list))
    except Exception:
        pass
    _secrets_cached = True

def mask_secrets(text: str) -> str:
    """Mask sensitive tokens or API keys dynamically."""
    if not isinstance(text, str):
        return text
    _build_secrets_regex()
    if _secret_regex:
        return _secret_regex.sub("[MASKED]", text)
    return text


# ── Performance Metrics Collector ─────────────────────────────────────────────
class PerformanceMetrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.api_requests = deque()
        self.llm_latencies = deque(maxlen=100)
        self.api_latencies = deque(maxlen=100)
        self.total_tokens = 0
        self.llm_calls = 0
        self.tools_used = set()
        self.db_queries_count = 0
        self.warnings_count = 0
        self.errors_count = 0
        self.peak_cpu = 0.0
        self.peak_ram = 0.0

    def record_api_request(self, duration_ms):
        with self.lock:
            now = time.time()
            self.api_requests.append(now)
            self.api_latencies.append(duration_ms / 1000.0)

    def record_llm_call(self, duration_seconds, tokens):
        with self.lock:
            self.llm_latencies.append(duration_seconds)
            self.total_tokens += tokens
            self.llm_calls += 1

    def record_tool_call(self, tool_name):
        with self.lock:
            self.tools_used.add(tool_name)

    def record_db_query(self):
        with self.lock:
            self.db_queries_count += 1

    def record_warning(self):
        with self.lock:
            self.warnings_count += 1

    def record_error(self):
        with self.lock:
            self.errors_count += 1

    def update_peaks(self, cpu, ram):
        with self.lock:
            if cpu > self.peak_cpu:
                self.peak_cpu = cpu
            if ram > self.peak_ram:
                self.peak_ram = ram

    def get_api_requests_per_second(self, window_seconds=10):
        with self.lock:
            now = time.time()
            while self.api_requests and self.api_requests[0] < now - window_seconds:
                self.api_requests.popleft()
            return len(self.api_requests) / float(window_seconds) if window_seconds > 0 else 0.0

    def get_average_latency(self):
        with self.lock:
            all_lats = list(self.llm_latencies) + list(self.api_latencies)
            if not all_lats:
                return 0.0
            return sum(all_lats) / len(all_lats)

metrics_collector = PerformanceMetrics()


# ── Metadata Resolver ─────────────────────────────────────────────────────────
def resolve_metadata(record):
    """Resolve component name and log category from record properties or naming."""
    category = getattr(record, "category", None)
    component = getattr(record, "component", None)
    
    if not category or not component:
        name = record.name
        for pattern, (cat, comp) in LOGGER_TO_COMPONENT.items():
            if name == pattern or name.startswith(pattern + "."):
                if not category: category = cat
                if not component: component = comp
                break
                
    if not category:
        category = "INFO" if record.levelname == "INFO" else record.levelname
    if not component:
        component = record.name
        
    return category, component


# ── Console Coloured Formatter ────────────────────────────────────────────────
class ConsoleColouredFormatter(logging.Formatter):
    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        category, component = resolve_metadata(record)
        
        user_id = user_id_var.get("")
        session_id = session_id_var.get("")
        request_id = request_id_var.get("")
        workflow_step = workflow_step_var.get("")
        
        color = ANSI_COLORS.get(category, ANSI_COLORS.get(record.levelname, ANSI_COLORS["INFO"]))
        reset = ANSI_COLORS["RESET"]
        dim_gray = ANSI_COLORS["DEBUG"]
        
        parts = []
        # Timestamp
        parts.append(f"{dim_gray}[{reset}{timestamp}{dim_gray}]{reset}")
        
        # Level / Category
        parts.append(f"{dim_gray}[{reset}{color}{category}{reset}{dim_gray}]{reset}")
        
        # Component / Module
        if component:
            parts.append(f"{dim_gray}[{reset}{color}{component}{reset}{dim_gray}]{reset}")
            
        # Session ID
        if session_id:
            parts.append(f"{dim_gray}[{reset}Session: {session_id}{dim_gray}]{reset}")
            
        # User ID
        if user_id:
            parts.append(f"{dim_gray}[{reset}User: {user_id}{dim_gray}]{reset}")
            
        # Request ID
        if request_id and request_id != session_id:
            parts.append(f"{dim_gray}[{reset}Req: {request_id}{dim_gray}]{reset}")
            
        # Workflow Step
        if workflow_step and workflow_step not in ("start", ""):
            parts.append(f"{dim_gray}[{reset}Step: {workflow_step}{dim_gray}]{reset}")
            
        # Duration (if available)
        duration = getattr(record, "duration", None)
        if duration is not None:
            parts.append(f"{dim_gray}[{reset}{ANSI_COLORS['PERFORMANCE']}Duration: {duration:.3f}s{reset}{dim_gray}]{reset}")

        prefix = " ".join(parts)
        message = record.getMessage()
        message = mask_secrets(message)
        
        # Colorize execution results
        if category in ("SUCCESS", "ERROR", "CRITICAL"):
            message = f"{color}{message}{reset}"
            
        # Append traceback if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            exc_text = mask_secrets(exc_text)
            message += f"\n{ANSI_COLORS['ERROR']}{exc_text}{reset}"
            
        formatted_message = f"{prefix} {message}"
        encoding = sys.stdout.encoding or "utf-8"
        try:
            formatted_message.encode(encoding)
        except UnicodeEncodeError:
            formatted_message = (
                formatted_message
                .replace("❌", "[FAIL]")
                .replace("✓", "[PASS]")
                .replace("✔", "[PASS]")
                .replace("▶", ">")
                .replace("➔", "->")
                .replace("↓", " | ")
                .replace("•", "*")
            )
            formatted_message = formatted_message.encode(encoding, errors="replace").decode(encoding)
        return formatted_message


# ── JSON Formatter ────────────────────────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    def format(self, record):
        category, component = resolve_metadata(record)
        
        user_id = user_id_var.get("")
        session_id = session_id_var.get("")
        request_id = request_id_var.get("")
        workflow_step = workflow_step_var.get("")
        correlation_id = correlation_id_var.get("")
        
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "category": category,
            "component": component,
            "session_id": session_id,
            "user_id": user_id,
            "request_id": request_id,
            "workflow_step": workflow_step,
            "correlation_id": correlation_id,
            "message": mask_secrets(record.getMessage()),
            "logger": record.name,
            "line_number": record.lineno,
            "file_name": record.filename,
        }
        
        # Append duration
        duration = getattr(record, "duration", None)
        if duration is not None:
            log_data["duration_seconds"] = duration
            
        # Append any extra fields
        for key, val in record.__dict__.items():
            if key not in ("args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName", 
                           "levelname", "levelno", "lineno", "module", "msecs", "message", "msg", "name", 
                           "pathname", "process", "processName", "relativeCreated", "stack_info", "thread", 
                           "threadName", "category", "component", "duration"):
                log_data[key] = val
                
        if record.exc_info:
            log_data["exception"] = mask_secrets(self.formatException(record.exc_info))
            
        return json.dumps(log_data)


# ── Platform Logger Wrapper ───────────────────────────────────────────────────
class PlatformLogger:
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        metrics_collector.record_warning()
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        metrics_collector.record_error()
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        metrics_collector.record_error()
        self._logger.critical(msg, *args, **kwargs)

    def system(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["category"] = "SYSTEM"
        self._logger.info(msg, *args, **kwargs)

    def startup(self, msg, duration_ms=None, *args, **kwargs):
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "STARTUP"
        if duration_ms is not None:
            extra["duration"] = duration_ms / 1000.0
        self._logger.info(msg, *args, **kwargs)

    def shutdown(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["category"] = "SHUTDOWN"
        self._logger.info(msg, *args, **kwargs)

    def success(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["category"] = "SUCCESS"
        self._logger.info(msg, *args, **kwargs)

    def user_action(self, msg, username=None, session_id=None, user_id=None, request_id=None, details=None, *args, **kwargs):
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "USER ACTION"
        if username: extra["username"] = username
        if session_id: extra["session_id"] = session_id
        if user_id: extra["user_id"] = user_id
        if request_id: extra["request_id"] = request_id
        if details: extra["details"] = details
        self._logger.info(msg, *args, **kwargs)

    def agent_action(self, agent_name, action, task_id=None, duration=None, memory_mb=None, status=None, *args, **kwargs):
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "AGENT ACTION"
        extra["component"] = agent_name
        if task_id: extra["task_id"] = task_id
        if duration is not None: extra["duration"] = duration
        if memory_mb is not None: extra["memory"] = f"{memory_mb:.1f} MB"
        if status: extra["status"] = status
        self._logger.info(action, *args, **kwargs)

    def agent_comm(self, sender, receiver, reason, payload_size=None, duration=None, *args, **kwargs):
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "AGENT ACTION"
        extra["sender"] = sender
        extra["receiver"] = receiver
        extra["reason"] = reason
        if payload_size is not None: extra["payload_size"] = payload_size
        if duration is not None: extra["duration"] = duration
        msg = f"Agent Comm: {sender} ➔ {receiver} | Reason: {reason}"
        self._logger.info(msg, *args, **kwargs)

    def tool_call(self, tool_name, action, duration=None, status=None, result_size=None, params=None, *args, **kwargs):
        metrics_collector.record_tool_call(tool_name)
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "TOOL CALL"
        extra["component"] = tool_name
        if duration is not None: extra["duration"] = duration
        if status: extra["status"] = status
        if result_size is not None: extra["result_size"] = result_size
        if params: extra["params"] = params
        self._logger.info(f"{action}", *args, **kwargs)

    def llm_call(self, model, provider, prompt_tokens, completion_tokens, latency, cost=None, temp=None, *args, **kwargs):
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "LLM RESPONSE"
        extra["model"] = model
        extra["provider"] = provider
        extra["prompt_tokens"] = prompt_tokens
        extra["completion_tokens"] = completion_tokens
        extra["total_tokens"] = prompt_tokens + completion_tokens
        extra["latency"] = latency
        if cost is not None: extra["cost"] = cost
        if temp is not None: extra["temperature"] = temp
        msg = f"Response Received | Latency: {latency:.2f}s | Tokens: {prompt_tokens + completion_tokens}"
        self._logger.info(msg, *args, **kwargs)

    def api_call(self, method, endpoint, status_code, duration_ms, payload_size=None, response_size=None, *args, **kwargs):
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "API CALL"
        extra["method"] = method
        extra["endpoint"] = endpoint
        extra["status_code"] = status_code
        extra["duration"] = duration_ms / 1000.0
        if payload_size is not None: extra["payload_size"] = payload_size
        if response_size is not None: extra["response_size"] = response_size
        msg = f"{method} {endpoint} | Status: {status_code} | Duration: {duration_ms}ms"
        self._logger.info(msg, *args, **kwargs)

    def database(self, action, query=None, duration_ms=None, *args, **kwargs):
        metrics_collector.record_db_query()
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "DATABASE"
        extra["component"] = "Database"
        if duration_ms is not None: extra["duration"] = duration_ms / 1000.0
        if query: extra["query"] = query
        msg = f"{action}"
        if query: msg += f" | Query: {query}"
        if duration_ms is not None: msg += f" | Duration: {duration_ms}ms"
        self._logger.info(msg, *args, **kwargs)

    def vector_db(self, action, details=None, *args, **kwargs):
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "VECTOR DB"
        extra["component"] = "Vector DB"
        if details: extra["details"] = details
        msg = f"{action}"
        if details: msg += f" | {details}"
        self._logger.info(msg, *args, **kwargs)

    def memory(self, action, details=None, *args, **kwargs):
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "CACHE"
        extra["component"] = "Memory Manager"
        if details: extra["details"] = details
        msg = f"{action}"
        if details: msg += f" | {details}"
        self._logger.info(msg, *args, **kwargs)

    def file_system(self, action, path=None, *args, **kwargs):
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "FILE SYSTEM"
        extra["component"] = "File System"
        if path: extra["path"] = str(path)
        msg = f"{action}"
        if path: msg += f" | Path: {path}"
        self._logger.info(msg, *args, **kwargs)

    def git(self, action, repo=None, *args, **kwargs):
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "NETWORK"
        extra["component"] = "Git Tool"
        if repo: extra["repo"] = repo
        msg = f"{action}"
        if repo: msg += f" | Repo: {repo}"
        self._logger.info(msg, *args, **kwargs)

    def performance(self, cpu, ram, gpu=None, disk=None, threads=None, running_agents=None, queue_size=None, api_req_sec=None, avg_latency=None, *args, **kwargs):
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "PERFORMANCE"
        extra["component"] = "Monitor"
        extra["cpu"] = cpu
        extra["ram"] = ram
        if gpu: extra["gpu"] = gpu
        if disk: extra["disk"] = disk
        if threads: extra["threads"] = threads
        if running_agents is not None: extra["running_agents"] = running_agents
        if queue_size is not None: extra["queue_size"] = queue_size
        if api_req_sec is not None: extra["api_req_sec"] = api_req_sec
        if avg_latency is not None: extra["avg_latency"] = avg_latency
        
        lines = [
            "--- PERFORMANCE MONITOR ---",
            f"CPU Usage: {cpu}%",
            f"RAM Usage: {ram}%",
            f"GPU Usage (if available): {gpu or 'N/A'}",
            f"Disk Usage: {disk}%",
            f"Open Threads: {threads}",
            f"Running Agents: {running_agents}",
            f"Queue Size: {queue_size}",
            f"API Requests/sec: {api_req_sec:.2f}",
            f"Average Latency: {avg_latency:.2f}s",
            "---------------------------"
        ]
        msg = "\n".join(lines)
        self._logger.info(msg, *args, **kwargs)

    def workflow(self, nodes, active_node=None, *args, **kwargs):
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "SYSTEM"
        extra["component"] = "Workflow"
        
        node_mapping = {
            "requirement_analyzer": "Requirement Analyzer",
            "project_planner": "Project Planner",
            "frontend_agent": "Frontend Agent",
            "backend_agent": "Backend Agent",
            "database_agent": "Database Agent",
            "code_review": "Code Review",
            "testing_agent": "Testing Agent",
            "bug_fixing": "Bug Fixing",
            "deployment": "Deployment",
            "documentation": "Documentation",
            "repository": "Repository"
        }
        
        display_active = node_mapping.get(active_node, active_node) if active_node else None
        
        lines = ["", "--- ACTIVE WORKFLOW ---"]
        for i, node in enumerate(nodes):
            disp = node_mapping.get(node, node)
            if disp == display_active:
                lines.append(f"  \033[1;92m▶ [{disp.upper()}]\033[0m")
            else:
                lines.append(f"    {disp}")
            if i < len(nodes) - 1:
                lines.append("        ↓")
        lines.append("-----------------------")
        
        msg = "\n".join(lines)
        self._logger.info(msg, *args, **kwargs)

    def execution_summary(self, summary, *args, **kwargs):
        extra = kwargs.setdefault("extra", {})
        extra["category"] = "PERFORMANCE"
        extra["component"] = "Summary"
        
        lines = [
            "",
            "==============================",
            "EXECUTION SUMMARY",
            "==============================",
            f"Project: {summary.get('Project', 'N/A')}",
            f"Execution Time: {summary.get('Execution Time', 'N/A')}",
            f"Agents Used: {summary.get('Agents Used', 'N/A')}",
            f"Tools Used: {summary.get('Tools Used', 'N/A')}",
            f"LLM Calls: {summary.get('LLM Calls', 0)}",
            f"API Calls: {summary.get('API Calls', 0)}",
            f"Database Queries: {summary.get('Database Queries', 0)}",
            f"Files Generated: {summary.get('Files Generated', 0)}",
            f"Warnings: {summary.get('Warnings', 0)}",
            f"Errors: {summary.get('Errors', 0)}",
            f"Total Tokens: {summary.get('Total Tokens', 0)}",
            f"Average Latency: {summary.get('Average Latency', 'N/A')}",
            f"Peak RAM Usage: {summary.get('Peak RAM Usage', 'N/A')}",
            f"Peak CPU Usage: {summary.get('Peak CPU Usage', 'N/A')}",
            "",
            f"Status: {summary.get('Status', 'SUCCESS')}",
            "=============================="
        ]
        msg = "\n".join(lines)
        self._logger.info(msg, *args, **kwargs)

platform_logger = PlatformLogger(logging.getLogger("platform"))


def get_logger(name: str) -> PlatformLogger:
    """Import wrapper that returns a wrapped Logger instance."""
    return PlatformLogger(logging.getLogger(name))


# ── LangChain LLM Callback Handler ────────────────────────────────────────────
from langchain_core.callbacks import BaseCallbackHandler

class PlatformLLMCallback(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        self.start_time = time.time()
        model_name = serialized.get("kwargs", {}).get("model_name", "groq-model")
        platform_logger.info(f"Sending Prompt to {model_name}...", extra={"category": "LLM REQUEST"})

    def on_llm_end(self, response, **kwargs):
        latency = time.time() - self.start_time
        token_usage = response.llm_output.get("token_usage", {}) if response.llm_output else {}
        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)
        model_name = response.llm_output.get("model_name", "groq-model") if response.llm_output else "groq-model"
        
        metrics_collector.record_llm_call(latency, prompt_tokens + completion_tokens)
        
        platform_logger.llm_call(
            model=model_name,
            provider="Groq",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency=latency
        )


# ── Monkey Patch LangChain Groq ───────────────────────────────────────────────
def monkey_patch_langchain():
    """Dynamically register LLM callbacks for all Groq instances at runtime."""
    try:
        import langchain_groq
        original_init = langchain_groq.ChatGroq.__init__
        
        def patched_init(self, *args, **kwargs):
            callbacks = kwargs.get("callbacks", []) or []
            if not any(isinstance(c, PlatformLLMCallback) for c in callbacks):
                callbacks.append(PlatformLLMCallback())
            kwargs["callbacks"] = callbacks
            original_init(self, *args, **kwargs)
            
        langchain_groq.ChatGroq.__init__ = patched_init
    except Exception:
        pass


# ── Agent Execution Context Manager ───────────────────────────────────────────
@asynccontextmanager
async def log_agent_execution(agent_name: str, task_id: str = None):
    """Context manager to trace execution times, active agent lists, and RAM."""
    import psutil
    token = agent_name_var.set(agent_name)
    workflow_token = workflow_step_var.set(agent_name.lower())
    active_agents.add(agent_name)
    
    start_time = time.time()
    process = psutil.Process()
    mem_before = process.memory_info().rss / (1024.0 * 1024.0)
    
    platform_logger.agent_action(
        agent_name=agent_name,
        action=f"{agent_name} Started",
        task_id=task_id,
        status="STARTED"
    )
    
    db_run_id = db_run_id_var.get(0)
    db_task_id = None
    if db_run_id > 0:
        try:
            from modules.database.connection import SessionLocal
            from modules.database.models import AgentTask
            db_session = SessionLocal()
            task = AgentTask(
                run_id=db_run_id,
                agent_name=agent_name,
                status="running",
                progress_pct=10.0,
                cpu_usage=float(process.cpu_percent() or 0.0),
                memory_usage=float(process.memory_percent() or 0.0)
            )
            db_session.add(task)
            db_session.commit()
            db_session.refresh(task)
            db_task_id = task.id
            db_session.close()
        except Exception as e:
            platform_logger.warning(f"Failed to create AgentTask in DB: {e}")
            
    try:
        yield
        duration = time.time() - start_time
        mem_after = process.memory_info().rss / (1024.0 * 1024.0)
        platform_logger.agent_action(
            agent_name=agent_name,
            action=f"{agent_name} Completed",
            task_id=task_id,
            duration=duration,
            memory_mb=mem_after,
            status="SUCCESS"
        )
        
        if db_run_id > 0 and db_task_id:
            try:
                from modules.database.connection import SessionLocal
                from modules.database.models import AgentTask
                db_session = SessionLocal()
                task = db_session.query(AgentTask).filter(AgentTask.id == db_task_id).first()
                if task:
                    task.status = "completed"
                    task.progress_pct = 100.0
                    task.execution_duration_ms = int(duration * 1000)
                    task.cpu_usage = float(process.cpu_percent() or 0.0)
                    task.memory_usage = float(process.memory_percent() or 0.0)
                    db_session.commit()
                db_session.close()
            except Exception as e:
                platform_logger.warning(f"Failed to update AgentTask completed state in DB: {e}")
                
    except Exception as exc:
        duration = time.time() - start_time
        mem_after = process.memory_info().rss / (1024.0 * 1024.0)
        platform_logger.agent_action(
            agent_name=agent_name,
            action=f"{agent_name} Failed: {exc}",
            task_id=task_id,
            duration=duration,
            memory_mb=mem_after,
            status="FAILED"
        )
        
        if db_run_id > 0 and db_task_id:
            try:
                from modules.database.connection import SessionLocal
                from modules.database.models import AgentTask
                db_session = SessionLocal()
                task = db_session.query(AgentTask).filter(AgentTask.id == db_task_id).first()
                if task:
                    task.status = "failed"
                    task.progress_pct = 100.0
                    task.execution_duration_ms = int(duration * 1000)
                    task.cpu_usage = float(process.cpu_percent() or 0.0)
                    task.memory_usage = float(process.memory_percent() or 0.0)
                    db_session.commit()
                db_session.close()
            except Exception as e:
                platform_logger.warning(f"Failed to update AgentTask failed state in DB: {e}")
        raise
    finally:
        active_agents.discard(agent_name)
        try:
            agent_name_var.reset(token)
        except ValueError:
            agent_name_var.set("")
        try:
            workflow_step_var.reset(workflow_token)
        except ValueError:
            workflow_step_var.set("")


# ── Logging Setup ─────────────────────────────────────────────────────────────
_logging_configured = False
_logging_lock = threading.Lock()
_queue_listener = None

def setup_logging():
    """Initialise non-blocking logging, JSON rotation, and system monitoring."""
    global _logging_configured, _queue_listener
    with _logging_lock:
        if _logging_configured:
            return
            
        monkey_patch_langchain()
        
        # Configure root logger
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        
        # Create output logs directory
        Path("logs").mkdir(parents=True, exist_ok=True)
        
        # Formatter setup
        console_fmt = ConsoleColouredFormatter()
        json_fmt = JSONFormatter()
        
        # Target handlers
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_fmt)
        
        file_handler = logging.handlers.RotatingFileHandler(
            "logs/platform.json",
            maxBytes=10*1024*1024, # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(json_fmt)
        
        # Non-blocking Queue Handler Setup
        log_queue = queue.Queue(-1)
        queue_handler = logging.handlers.QueueHandler(log_queue)
        
        # Remove existing handlers
        for h in list(root.handlers):
            root.removeHandler(h)
            
        root.addHandler(queue_handler)
        
        # Asynchronous Queue Listener
        _queue_listener = logging.handlers.QueueListener(
            log_queue, console_handler, file_handler, respect_handler_level=True
        )
        _queue_listener.start()
        
        # Performance Monitoring Thread
        def _performance_daemon():
            import psutil
            while True:
                time.sleep(10)
                try:
                    cpu = psutil.cpu_percent()
                    ram = psutil.virtual_memory().percent
                    metrics_collector.update_peaks(cpu, ram)
                    
                    try:
                        disk = psutil.disk_usage(".").percent
                    except Exception:
                        disk = 0.0
                        
                    threads = threading.active_count()
                    queue_size = log_queue.qsize()
                    
                    api_req_sec = metrics_collector.get_api_requests_per_second()
                    avg_latency = metrics_collector.get_average_latency()
                    
                    platform_logger.performance(
                        cpu=cpu,
                        ram=ram,
                        disk=disk,
                        threads=threads,
                        running_agents=len(active_agents),
                        queue_size=queue_size,
                        api_req_sec=api_req_sec,
                        avg_latency=avg_latency
                    )
                except Exception:
                    pass
                    
        monitor_thread = threading.Thread(target=_performance_daemon, daemon=True, name="PerfDaemon")
        monitor_thread.start()
        
        _logging_configured = True


def shutdown_logging():
    """Gracefully terminate background listener queue processing."""
    global _queue_listener
    if _queue_listener:
        _queue_listener.stop()
        _queue_listener = None
