"""Skywatcher command-line interface.

This is the 'Agents CLI' / agent skill surface: a single `skywatcher` command
that exposes both the deterministic tools (no API key needed) and the full
multi-agent chat (needs GEMINI_API_KEY).

Examples:
    skywatcher ask "When can I see the ISS from Boulder?"
    skywatcher list-sats --category visual
    skywatcher passes "ISS" --lat 40.015 --lon -105.271
    skywatcher overhead --lat 40.015 --lon -105.271
    skywatcher find "Hubble"
    skywatcher mcp serve        # run the MCP server
"""
from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from .config import settings
from .tools import celestrak, sky_math

console = Console()


@click.group()
@click.version_option(package_name="skywatcher")
def main() -> None:
    """Skywatcher — your AI companion for what's overhead."""


# --- Deterministic commands (no API key required) --------------------------


@main.command("list-sats")
@click.option(
    "--category",
    "-c",
    default="visual",
    help="CelesTrak category (visual, active, starlink, last-30-days, geo, ...)",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_sats(category: str, as_json: bool) -> None:
    """List satellites in a CelesTrak category."""
    try:
        sats = celestrak.get_satellites(category)
    except Exception as e:  # network errors, bad category, etc.
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if as_json:
        click.echo(json.dumps([{"name": s.name, "norad_id": s.norad_id} for s in sats[:100]]))
        return

    table = Table(title=f"Satellites in '{category}' ({len(sats)} total, showing first 50)")
    table.add_column("NORAD ID", style="cyan")
    table.add_column("Name", style="white")
    for s in sats[:50]:
        table.add_row(str(s.norad_id), s.name)
    console.print(table)


@main.command("find")
@click.argument("query")
def find(query: str) -> None:
    """Find a satellite by name or NORAD id."""
    sat = celestrak.find_satellite(query)
    if sat is None:
        console.print(f"[yellow]No satellite matched '{query}'.[/yellow]")
        sys.exit(1)
    console.print(f"[green]Found:[/green] {sat.name}  (NORAD {sat.norad_id})")


@main.command("passes")
@click.argument("satellite_query")
@click.option("--lat", type=float, default=None, help="Observer latitude")
@click.option("--lon", type=float, default=None, help="Observer longitude")
@click.option("--hours", type=int, default=24, help="Hours ahead to search")
def passes(satellite_query: str, lat: float | None, lon: float | None, hours: int) -> None:
    """Predict visible passes of a satellite over a location."""
    lat = settings.default_lat if lat is None else lat
    lon = settings.default_lon if lon is None else lon

    sat = celestrak.find_satellite(satellite_query)
    if sat is None:
        console.print(f"[red]Satellite '{satellite_query}' not found.[/red]")
        sys.exit(1)

    console.print(f"[cyan]Predicting passes for {sat.name} (NORAD {sat.norad_id})[/cyan]")
    console.print(f"[dim]Observer: {lat}, {lon}  |  Next {hours}h[/dim]\n")

    try:
        events = sky_math.predict_passes(sat, lat, lon, hours_ahead=hours)
    except Exception as e:
        console.print(f"[red]Error computing passes:[/red] {e}")
        sys.exit(1)

    if not events:
        console.print("[yellow]No visible passes found in the time window.[/yellow]")
        return

    table = Table(title="Upcoming passes (times in UTC)")
    table.add_column("Start", style="green")
    table.add_column("Max Elev", style="yellow")
    table.add_column("End", style="red")
    table.add_column("Max El (deg)", justify="right")
    table.add_column("Rise Az", justify="right")
    for p in events:
        table.add_row(
            p.start_time,
            p.max_elevation_time,
            p.end_time,
            f"{p.max_elevation_deg}",
            f"{p.start_azimuth_deg}",
        )
    console.print(table)


@main.command("overhead")
@click.option("--lat", type=float, default=None, help="Observer latitude")
@click.option("--lon", type=float, default=None, help="Observer longitude")
def overhead(lat: float | None, lon: float | None) -> None:
    """List bright satellites currently overhead (>10 deg elevation)."""
    lat = settings.default_lat if lat is None else lat
    lon = settings.default_lon if lon is None else lon

    sats = celestrak.get_satellites("visual")
    positions = sky_math.satellites_overhead(sats, lat, lon)

    if not positions:
        console.print("[yellow]No bright satellites currently overhead.[/yellow]")
        return

    table = Table(title=f"Overhead from {lat}, {lon} (UTC now)")
    table.add_column("Name", style="white")
    table.add_column("NORAD", style="cyan")
    table.add_column("Altitude (km)", justify="right")
    for p in positions:
        table.add_row(p.name, str(p.norad_id), f"{p.altitude_km:.1f}")
    console.print(table)


# --- Agent command (requires GEMINI_API_KEY) -------------------------------


@main.command("ask")
@click.argument("query", required=False)
@click.option("--interactive", "-i", is_flag=True, help="Start an interactive chat session")
def ask(query: str | None, interactive: bool) -> None:
    """Ask the Skywatcher agent a question in natural language.

    Examples:
        skywatcher ask "When can I see the ISS from New York?"
        skywatcher ask "What does the Hubble telescope do?"
        skywatcher ask --interactive
    """
    from .agents.runner import ask as agent_ask

    if interactive:
        console.print("[bold cyan]Skywatcher interactive mode[/bold cyan] (Ctrl-D to exit)\n")
        while True:
            try:
                q = click.prompt("You", type=str)
            except (EOFError, click.exceptions.Abort):
                console.print("\n[dim]Goodbye.[/dim]")
                break
            console.print("[bold green]Skywatcher[/bold green] ", end="")
            try:
                response = agent_ask(q)
                console.print(response)
            except Exception as e:
                console.print(f"[red]Agent error:[/red] {e}")
            console.print()
        return

    if not query:
        click.echo("Provide a query: skywatcher ask \"...\"  or use --interactive")
        sys.exit(1)

    try:
        response = agent_ask(query)
        console.print(response)
    except Exception as e:
        console.print(f"[red]Agent error:[/red] {e}")
        sys.exit(1)


# --- MCP server command ----------------------------------------------------


@main.command("mcp")
@click.argument("subcommand", type=click.Choice(["serve"]))
def mcp(subcommand: str) -> None:
    """Run the Skywatcher MCP server (subcommand: serve)."""
    if subcommand == "serve":
        from .mcp_server.server import main as run_server

        run_server()


if __name__ == "__main__":
    main()
