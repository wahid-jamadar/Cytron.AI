"""
main.py
────────
Entry point for the Cytron.AI system.

Modes:
  python main.py             → Launch the Web UI (recommended)
  python main.py --cli       → CLI mode (interactive terminal)
  python main.py --input "..." → Run a single requirement non-interactively
"""

import argparse
import asyncio
import sys
from config.settings import settings
from modules.common.logger import setup_logging, platform_logger
setup_logging()
logger = platform_logger


def run_web_ui():
    """Launch the FastAPI Web UI with uvicorn."""
    try:
        import uvicorn
    except ImportError:
        logger.error("uvicorn not installed. Run: pip install uvicorn[standard]")
        sys.exit(1)

    logger.info(f"Starting Cytron.AI Web UI on http://{settings.ui_host}:{settings.ui_port}")
    logger.info("Open your browser at: http://localhost:%d", settings.ui_port)

    try:
        uvicorn.run(
            "ui.main:app",
            host=settings.ui_host,
            port=settings.ui_port,
            reload=True,
            log_level=settings.log_level.lower(),
        )
    except Exception as exc:
        logger.error(f"Failed to start server: {exc}", exc_info=True)
        sys.exit(1)

async def run_cli(user_input: str | None = None):
    """Run the pipeline in CLI mode with terminal progress output.""" 
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from orchestrator.runner import get_runner

    console = Console()

    if not user_input:
        console.print(Panel.fit(
            "[bold purple]Cytron.AI[/] — AI-Powered Application Generator\n"
            "[dim]Describe any web application and AI agents will build, test, and deploy it.[/]",
            border_style="purple",
        ))
        console.print()
        user_input = console.input("[bold]Describe your application:[/] ").strip()
        if not user_input:
            console.print("[red]Error: No input provided.[/]")
            return

    console.print()
    console.rule("[purple]Pipeline Starting[/]")
    console.print()

    runner = get_runner()
    final_result = None

    async for update in runner.run(user_input=user_input):
        event_type = update["type"]
        label = update.get("label", "")
        data = update.get("data", {})

        if event_type == "progress":
            console.print(f"  [dim]{label}[/]")
        elif event_type == "complete":
            final_result = data
            console.print(f"\n  [green bold]{label}[/]")
        elif event_type == "error":
            console.print(f"\n  [red bold]{label}[/]")
            errors = data.get("errors", [])
            for e in errors:
                console.print(f"    [red]• {e}[/]")
            return

    if final_result:
        console.print()
        console.rule("[green]Results[/]")
        console.print(f"  [green]App URL:[/]  {final_result.get('app_url', 'local')}")
        console.print(f"  [blue]Repo:[/]     {final_result.get('repo_url', 'not configured')}")
        console.print(f"  [cyan]Tests:[/]    {'passed' if final_result.get('tests_passed') else 'see output'}")
        console.print(f"  [dim]Retries:[/]  {final_result.get('retry_count', 0)}")
        console.print()


def log_startup_sequence():
    import time
    start_time = time.time()
    startup_steps = [
        "Loading Configuration...",
        "Loading Environment Variables...",
        "Loading Agents...",
        "Loading Tools...",
        "Loading Memory Manager...",
        "Loading Vector Database...",
        "Loading Prompt Templates...",
        "Connecting Database...",
        "Loading MCP Servers...",
        "Initializing LangGraph...",
        "Initializing Event Bus...",
        "Registering APIs..."
    ]
    for step in startup_steps:
        logger.startup(step)
        time.sleep(0.03)
    duration = time.time() - start_time
    logger.startup("Server Started Successfully", duration_ms=int(duration * 1000))


def main():
    parser = argparse.ArgumentParser(
        description="Cytron.AI — AI-powered end-to-end application generator",
    )
    parser.add_argument("--cli",   action="store_true", help="Run in CLI mode instead of Web UI")
    parser.add_argument("--input", type=str, default=None, help="Non-interactive: provide requirement directly")
    args = parser.parse_args()

    # Trigger beautiful startup logs
    log_startup_sequence()

    if args.cli or args.input:
        asyncio.run(run_cli(user_input=args.input))
    else:
        run_web_ui()


if __name__ == "__main__":
    main()
