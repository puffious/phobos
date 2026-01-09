"""CLI for CleanSlate using Typer.

Provides commands for interacting with the CleanSlate service:
- health: sanity check
- sanitize: remove metadata from a file
- backup: backup a file to cloud storage
- run-daemon: start the file watcher daemon
- run-api: start the API server
"""

import os
import sys
from pathlib import Path

import typer

from app.services.backup_service import backup_file, BackupError
from app.services.cleaner_service import sanitize_file, CleanerError

app = typer.Typer(help="CleanSlate CLI")

VERSION = "0.0.1"


@app.command()
def health():
    """Sanity check; prints OK."""
    typer.echo("OK")


@app.command()
def sanitize(filepath: str = typer.Argument(..., help="Path to file to sanitize")):
    """Remove metadata from a file."""
    file_path = Path(filepath)
    
    if not file_path.exists():
        typer.secho(f"Error: File not found: {filepath}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    
    try:
        typer.echo(f"Sanitizing: {filepath}")
        result = sanitize_file(str(file_path))
        
        if result.get("success"):
            typer.secho(f"✓ Sanitized successfully", fg=typer.colors.GREEN)
            typer.echo(f"  File: {result.get('file')}")
            typer.echo(f"  Size: {result.get('file_size')} bytes")
        else:
            typer.secho(f"✗ Sanitization failed", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
            
    except CleanerError as e:
        typer.secho(f"✗ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command()
def backup(
    filepath: str = typer.Argument(..., help="Path to file to backup"),
    remote: str = typer.Option("gdrive:backups", help="Remote destination"),
):
    """Backup a file to cloud storage."""
    file_path = Path(filepath)
    
    if not file_path.exists():
        typer.secho(f"Error: File not found: {filepath}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    
    try:
        typer.echo(f"Backing up: {filepath} → {remote}")
        result = backup_file(str(file_path), remote)
        
        if result.get("success"):
            typer.secho(f"✓ Backup successful", fg=typer.colors.GREEN)
            typer.echo(f"  File: {result.get('file')}")
            typer.echo(f"  Remote: {result.get('remote')}")
        else:
            typer.secho(f"✗ Backup failed", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
            
    except BackupError as e:
        typer.secho(f"✗ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command()
def run_daemon(
    watch_dir: str = typer.Option(None, help="Directory to watch"),
    output_dir: str = typer.Option(None, help="Output directory"),
    remote: str = typer.Option(None, help="Rclone remote destination"),
):
    """Start the file watcher daemon."""
    from app.config import load_config
    from app.daemon.watcher import start_watcher
    
    try:
        config = load_config()
        watch = watch_dir or str(config.watch_dir)
        output = output_dir or str(config.output_dir)
        rclone_dest = remote or f"{config.rclone_remote_name}:{config.rclone_dest_path}"
        
        typer.echo(f"Starting daemon...")
        typer.echo(f"  Watch: {watch}")
        typer.echo(f"  Output: {output}")
        typer.echo(f"  Remote: {rclone_dest}")
        
        observer = start_watcher(watch, output, rclone_dest)
        
        typer.secho("✓ Daemon started. Press Ctrl+C to stop.", fg=typer.colors.GREEN)
        
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            typer.echo("\nStopping daemon...")
            from app.daemon.watcher import stop_watcher
            stop_watcher(observer)
            typer.secho("✓ Daemon stopped", fg=typer.colors.GREEN)
            
    except Exception as e:
        typer.secho(f"✗ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command()
def run_api(
    host: str = typer.Option("0.0.0.0", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
):
    """Start the API server."""
    try:
        import uvicorn
        typer.echo(f"Starting API server on {host}:{port}")
        uvicorn.run("app.api:app", host=host, port=port, log_level="info")
    except Exception as e:
        typer.secho(f"✗ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    sys.exit(main())
