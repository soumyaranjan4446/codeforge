"""CLI entrypoint: `codeforge run --spec "..."` or `--spec-file`."""
from __future__ import annotations
import asyncio
import json
import uuid
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from .schemas import SwarmState
from .graph.swarm import get_swarm

app = typer.Typer(help="CodeForge — autonomous coding swarm")
console = Console()


@app.command()
def run(
    spec: str = typer.Option(None, "--spec", "-s", help="Inline spec"),
    spec_file: Path = typer.Option(None, "--spec-file", "-f", help="Path to spec markdown"),
    language: str = typer.Option("python", "--lang", "-l"),
    save: Path = typer.Option(None, "--save", help="Save final state JSON"),
):
    spec_text = spec or (spec_file.read_text() if spec_file else None)
    if not spec_text:
        console.print("[red]Provide --spec or --spec-file[/red]")
        raise typer.Exit(1)

    state = SwarmState(
        task_id=str(uuid.uuid4())[:8],
        spec=spec_text,
        language=language,
    )

    swarm = get_swarm()
    console.print(Panel.fit(
        f"[bold cyan]CodeForge Swarm[/bold cyan]\n"
        f"Task: {state.task_id}\nLang: {language}\nSpec: {spec_text[:120]}...",
        title="Launching",
    ))

    final = asyncio.run(swarm.ainvoke({"state": state}))
    fs: SwarmState = final["state"]

    # ---- Report ----
    table = Table(title="Test Results")
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Error", style="red")
    for r in fs.test_results + fs.adversarial_results:
        table.add_row(
            r.name[:60],
            "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]",
            (r.error_type or "")[:30],
        )
    console.print(table)

    if fs.metric_results:
        mtable = Table(title="DeepEval Metrics")
        mtable.add_column("Metric", style="magenta")
        mtable.add_column("Score", justify="right")
        mtable.add_column("Verdict")
        for m in fs.metric_results:
            mtable.add_row(m.name, f"{m.score:.2f}", "[green]ok[/green]" if m.passed else "[red]flag[/red]")
        console.print(mtable)

    console.print(Panel.fit(
        f"Verdict: [bold {'green' if fs.verdict == 'pass' else 'red'}]{fs.verdict.upper()}[/bold {'green' if fs.verdict == 'pass' else 'red'}]\n"
        f"Healing loops: {fs.healing_loop}\n"
        f"{fs.escalate_reason}",
        title="Result",
    ))

    console.print(Panel(fs.source_code, title="Final Source", border_style="blue"))

    if save:
        save.write_text(fs.model_dump_json(indent=2))
        console.print(f"[dim]Saved state -> {save}[/dim]")


@app.command()
def memory_stats():
    """Show Qdrant memory collection size."""
    from .memory.qdrant_store import BugMemory
    m = BugMemory()
    info = m.client.get_collection(m.collection)
    console.print(f"[cyan]Collection:[/cyan] {m.collection}")
    console.print(f"[cyan]Points:[/cyan] {info.points_count}")


if __name__ == "__main__":
    app()