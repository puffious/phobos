"""CLI for CleanSlate using Typer.

Provides commands for interacting with the CleanSlate service:
- health: sanity check
- sanitize: remove metadata from a file
- backup: backup a file to cloud storage
- run-daemon: start the file watcher daemon
- run-api: start the API server
"""

import typer

app = typer.Typer(help="CleanSlate CLI")

VERSION = "0.0.1"


@app.command()
def health():
    """Sanity check; prints OK."""
    typer.echo("OK")


@app.command()
def sanitize(filepath: str = typer.Argument(..., help="Path to file to sanitize")):
    """Remove metadata from a file."""
    typer.echo(f"Sanitizing: {filepath}")


@app.command()
def backup(
    filepath: str = typer.Argument(..., help="Path to file to backup"),
    remote: str = typer.Option("gdrive:backups", help="Remote destination"),
):
    """Backup a file to cloud storage."""
    typer.echo(f"Backing up: {filepath} to {remote}")


@app.command()
def run_daemon():
    """Start the file watcher daemon."""
    typer.echo("Starting daemon...")


@app.command()
def run_api():
    """Start the API server."""
    typer.echo("Starting API server...")


if __name__ == "__main__":
    sys.exit(main())
