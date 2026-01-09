"""Main entry point for CleanSlate."""
import logging
import os
import signal
import sys
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_daemon_mode():
    """Run in daemon mode with watcher + API."""
    from app.config import load_config
    from app.daemon.watcher import start_watcher, stop_watcher
    import uvicorn
    
    config = load_config()
    
    # Start file watcher in background thread
    watch_dir = str(config.watch_dir)
    output_dir = str(config.output_dir)
    rclone_dest = f"{config.rclone_remote_name}:{config.rclone_dest_path}"
    
    logger.info("Starting daemon mode...")
    logger.info(f"Watch directory: {watch_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Rclone destination: {rclone_dest}")
    
    observer = start_watcher(watch_dir, output_dir, rclone_dest)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        stop_watcher(observer)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run FastAPI server (blocking)
    logger.info("Starting API server on 0.0.0.0:8000")
    try:
        uvicorn.run("app.api:app", host="0.0.0.0", port=8000, log_level="info")
    finally:
        stop_watcher(observer)


def run_api_only():
    """Run API server only."""
    import uvicorn
    
    logger.info("Starting API-only mode on 0.0.0.0:8000")
    uvicorn.run("app.api:app", host="0.0.0.0", port=8000, log_level="info")


def main():
    """Main entrypoint."""
    # Check if running in daemon mode via environment variable
    daemon_mode = os.getenv("DAEMON_MODE", "false").lower() in ("true", "1", "yes")
    
    # If CLI args provided, delegate to CLI
    if len(sys.argv) > 1:
        from app.cli import app as cli_app
        cli_app()
    elif daemon_mode:
        run_daemon_mode()
    else:
        run_api_only()


if __name__ == "__main__":
    main()
