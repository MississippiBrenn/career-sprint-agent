"""Command-line interface for Career Sprint Agent."""

import asyncio
import webbrowser
from datetime import datetime, timedelta

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from .config import LIBRARY_STATE_FILE, LIBRARIES
from .core import LibraryMonitor, Storage
from .core.models import ActionType, ChangeType, StudySession

app = typer.Typer(
    name="career-agent",
    help="Career Sprint Agent - Personal career management system",
)
console = Console()


def get_monitor() -> LibraryMonitor:
    """Initialize the library monitor with storage."""
    storage = Storage(LIBRARY_STATE_FILE)
    return LibraryMonitor(storage)


def change_type_style(change_type: ChangeType) -> str:
    """Get Rich style for change type."""
    styles = {
        ChangeType.MAJOR: "bold red",
        ChangeType.MINOR: "bold yellow",
        ChangeType.PATCH: "dim",
        ChangeType.NEW: "bold green",
        ChangeType.UNKNOWN: "dim",
    }
    return styles.get(change_type, "")


def action_style(action: ActionType) -> str:
    """Get Rich style for action type."""
    styles = {
        ActionType.URGENT: "bold red",
        ActionType.DEEP_DIVE: "bold cyan",
        ActionType.SKIM: "yellow",
        ActionType.BOOKMARK: "dim",
    }
    return styles.get(action, "")


@app.command()
def status():
    """Show current status of all monitored libraries."""
    monitor = get_monitor()
    state = monitor.get_status()

    if not state.libraries:
        console.print(
            "[yellow]No libraries tracked yet. Run 'check-updates' first.[/yellow]"
        )
        return

    table = Table(title="Library Status", show_header=True)
    table.add_column("Library", style="cyan")
    table.add_column("Current", style="dim")
    table.add_column("Latest", style="green")
    table.add_column("Status")
    table.add_column("Last Checked", style="dim")

    for lib in state.libraries.values():
        status_text = (
            Text("UPDATE AVAILABLE", style="bold yellow")
            if lib.is_outdated
            else Text("current", style="green")
        )
        last_checked = lib.last_checked.strftime("%Y-%m-%d %H:%M")
        table.add_row(
            lib.display_name,
            lib.current_version,
            lib.latest_version,
            status_text,
            last_checked,
        )

    console.print(table)

    if state.last_full_check:
        console.print(
            f"\n[dim]Last full check: {state.last_full_check.strftime('%Y-%m-%d %H:%M')}[/dim]"
        )


@app.command("check-updates")
def check_updates():
    """Check all monitored libraries for updates."""
    console.print("[bold]Checking libraries for updates...[/bold]\n")

    monitor = get_monitor()
    changes = asyncio.run(monitor.check_all_libraries())

    if not changes:
        console.print("[green]All libraries are up to date![/green]")
        return

    console.print(f"[bold]Found {len(changes)} update(s):[/bold]\n")

    for change in changes:
        # Change header
        change_style = change_type_style(change.change_type)
        header = f"{change.display_name}: {change.previous_version or 'NEW'} → {change.new_version}"
        console.print(f"[{change_style}]● {header}[/{change_style}]")

        # Action recommendation
        action_text = change.action.value.replace("_", " ").upper()
        console.print(f"  [{action_style(change.action)}]Action: {action_text}[/{action_style(change.action)}]")

        # Learning prompt
        if change.learning_prompt:
            console.print(f"  [dim]{change.learning_prompt}[/dim]")

        # Relevance tags
        if change.relevance:
            tags = " ".join(f"[{r}]" for r in change.relevance)
            console.print(f"  Tags: {tags}")

        # Changelog link
        if change.changelog_url:
            console.print(f"  [blue underline]{change.changelog_url}[/blue underline]")

        console.print()


@app.command()
def changes(days: int = 7):
    """Show recent changes detected in the last N days."""
    monitor = get_monitor()
    state = monitor.get_status()

    since = datetime.now() - timedelta(days=days)
    recent = state.get_changes_since(since)

    if not recent:
        console.print(f"[dim]No changes detected in the last {days} days.[/dim]")
        return

    console.print(f"[bold]Changes in the last {days} days:[/bold]\n")

    for change in recent:
        change_style = change_type_style(change.change_type)
        console.print(
            f"[{change_style}]● {change.display_name}[/{change_style}] "
            f"{change.previous_version or 'NEW'} → {change.new_version} "
            f"[dim]({change.detected_at.strftime('%Y-%m-%d')})[/dim]"
        )
        if change.learning_prompt:
            console.print(f"  [dim]{change.learning_prompt}[/dim]")


@app.command()
def outdated():
    """Show only libraries with available updates."""
    monitor = get_monitor()
    outdated_libs = monitor.get_outdated()

    if not outdated_libs:
        console.print("[green]All libraries are up to date![/green]")
        return

    table = Table(title="Libraries with Updates Available", show_header=True)
    table.add_column("Library", style="cyan")
    table.add_column("Current", style="red")
    table.add_column("Latest", style="green")
    table.add_column("Summary", style="dim", max_width=50)

    for lib in outdated_libs:
        table.add_row(
            lib.display_name,
            lib.current_version,
            lib.latest_version,
            lib.summary or "",
        )

    console.print(table)


@app.command("mark-updated")
def mark_updated(package: str):
    """Mark a library as updated after you've upgraded it locally."""
    monitor = get_monitor()
    if monitor.mark_updated(package):
        console.print(f"[green]Marked {package} as updated.[/green]")
    else:
        console.print(f"[red]Library '{package}' not found.[/red]")


@app.command()
def learn(package: str = typer.Argument(None)):
    """Show learning opportunities from recent changes."""
    monitor = get_monitor()
    state = monitor.get_status()

    # Get changes with learning content
    changes_to_show = state.recent_changes
    if package:
        changes_to_show = [c for c in changes_to_show if c.library == package]

    if not changes_to_show:
        console.print("[dim]No changes with learning opportunities found.[/dim]")
        return

    for change in changes_to_show[-5:]:  # Show last 5
        panel_content = []

        # Learning prompt
        if change.learning_prompt:
            panel_content.append(f"[bold]{change.learning_prompt}[/bold]\n")

        # Concepts by level
        if change.concepts.beginner:
            panel_content.append(f"[green]Beginner:[/green] {', '.join(change.concepts.beginner)}")
        if change.concepts.intermediate:
            panel_content.append(f"[yellow]Intermediate:[/yellow] {', '.join(change.concepts.intermediate)}")
        if change.concepts.advanced:
            panel_content.append(f"[red]Advanced:[/red] {', '.join(change.concepts.advanced)}")

        # Action
        action_text = change.action.value.replace("_", " ").upper()
        panel_content.append(f"\n[bold]Recommended:[/bold] {action_text}")

        # Changelog link
        if change.changelog_url:
            panel_content.append(f"\n[link={change.changelog_url}]{change.changelog_url}[/link]")

        console.print(Panel(
            "\n".join(panel_content),
            title=f"{change.display_name} {change.new_version}",
            border_style=action_style(change.action),
        ))
        console.print()


@app.command()
def dive(package: str):
    """Start a deep dive study session for a library."""
    monitor = get_monitor()
    state = monitor.get_status()

    # Check for active session
    active = state.get_active_session()
    if active:
        console.print(
            f"[yellow]Active session in progress: {active.display_name} "
            f"(started {active.started_at.strftime('%H:%M')})[/yellow]"
        )
        console.print("Run [bold]career-agent done[/bold] to complete it first.")
        return

    # Find the library change
    changes = [c for c in state.recent_changes if c.library == package]
    if not changes:
        # Check if it's a tracked library
        if package not in state.libraries:
            console.print(f"[red]Library '{package}' not found.[/red]")
            console.print("Run [bold]career-agent check-updates[/bold] first.")
            return
        # Use library info instead
        lib = state.libraries[package]
        display_name = lib.display_name
        version = lib.latest_version
        changelog_url = None
        concepts = None
    else:
        change = changes[-1]  # Most recent
        display_name = change.display_name
        version = change.new_version
        changelog_url = change.changelog_url
        concepts = change.concepts

    # Create study session
    session = StudySession(
        library=package,
        display_name=display_name,
        version=version,
        started_at=datetime.now(),
    )
    state.study_sessions.append(session)
    monitor.storage.save(state)

    # Display session start
    console.print(Panel(
        f"[bold green]Deep dive started![/bold green]\n\n"
        f"Library: [cyan]{display_name}[/cyan]\n"
        f"Version: [yellow]{version}[/yellow]\n"
        f"Started: {session.started_at.strftime('%Y-%m-%d %H:%M')}",
        title="Study Session",
        border_style="green",
    ))

    # Show concepts if available
    if concepts:
        console.print("\n[bold]Concepts to explore:[/bold]")
        if concepts.beginner:
            console.print(f"  [green]Beginner:[/green] {', '.join(concepts.beginner)}")
        if concepts.intermediate:
            console.print(f"  [yellow]Intermediate:[/yellow] {', '.join(concepts.intermediate)}")
        if concepts.advanced:
            console.print(f"  [red]Advanced:[/red] {', '.join(concepts.advanced)}")

    # Open changelog if available
    if changelog_url:
        console.print(f"\n[dim]Opening changelog...[/dim]")
        webbrowser.open(changelog_url)
    else:
        console.print(f"\n[dim]No changelog URL available. Check PyPI or GitHub.[/dim]")

    console.print("\n[bold]When finished, run:[/bold] career-agent done")


@app.command()
def done():
    """Complete the current study session."""
    monitor = get_monitor()
    state = monitor.get_status()

    # Find active session
    active = state.get_active_session()
    if not active:
        console.print("[yellow]No active study session.[/yellow]")
        console.print("Start one with: [bold]career-agent dive <library>[/bold]")
        return

    # Calculate duration
    ended_at = datetime.now()
    duration = int((ended_at - active.started_at).total_seconds() / 60)

    console.print(Panel(
        f"Completing session: [cyan]{active.display_name}[/cyan]\n"
        f"Duration: [yellow]{duration} minutes[/yellow]",
        title="Session Complete",
        border_style="cyan",
    ))

    # Prompt for details
    cards = IntPrompt.ask("AnkiDroid cards created", default=0)
    notes = Prompt.ask("Quick notes (optional)", default="")

    # Update session
    active.ended_at = ended_at
    active.duration_minutes = duration
    active.cards_created = cards
    active.notes = notes if notes else None
    active.completed = True

    monitor.storage.save(state)

    console.print(f"\n[green]Session logged![/green]")
    console.print(f"  Duration: {duration} min | Cards: {cards}")
    if notes:
        console.print(f"  Notes: {notes}")

    # Suggest marking as updated
    if Confirm.ask(f"\nMark [cyan]{active.library}[/cyan] as studied?", default=True):
        monitor.mark_updated(active.library)
        console.print(f"[green]Marked {active.library} as current.[/green]")


@app.command()
def sessions(days: int = 30):
    """Show recent study sessions."""
    monitor = get_monitor()
    state = monitor.get_status()

    if not state.study_sessions:
        console.print("[dim]No study sessions yet.[/dim]")
        console.print("Start one with: [bold]career-agent dive <library>[/bold]")
        return

    since = datetime.now() - timedelta(days=days)
    recent = [s for s in state.study_sessions if s.started_at > since]

    if not recent:
        console.print(f"[dim]No sessions in the last {days} days.[/dim]")
        return

    table = Table(title=f"Study Sessions (last {days} days)", show_header=True)
    table.add_column("Date", style="dim")
    table.add_column("Library", style="cyan")
    table.add_column("Duration", style="yellow")
    table.add_column("Cards", style="green")
    table.add_column("Status")

    total_minutes = 0
    total_cards = 0

    for session in recent:
        status = "[green]✓[/green]" if session.completed else "[yellow]in progress[/yellow]"
        duration = f"{session.duration_minutes} min" if session.duration_minutes is not None else "-"
        if session.duration_minutes is not None:
            total_minutes += session.duration_minutes
        total_cards += session.cards_created

        table.add_row(
            session.started_at.strftime("%Y-%m-%d"),
            session.display_name,
            duration,
            str(session.cards_created),
            status,
        )

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {total_minutes} min | {total_cards} cards")


@app.command()
def libraries():
    """List all monitored libraries."""
    table = Table(title="Monitored Libraries", show_header=True)
    table.add_column("#", style="dim")
    table.add_column("Package", style="cyan")
    table.add_column("Category", style="yellow")
    table.add_column("Relevance", style="dim")

    from .config import LIBRARY_CONTEXT

    for i, lib in enumerate(LIBRARIES, 1):
        context = LIBRARY_CONTEXT.get(lib, {})
        table.add_row(
            str(i),
            context.get("display_name", lib),
            context.get("category", ""),
            ", ".join(context.get("relevance", [])),
        )

    console.print(table)


@app.callback()
def main():
    """Career Sprint Agent - Personal career management system."""
    pass


if __name__ == "__main__":
    app()
