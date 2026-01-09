"""Tests for main entrypoint."""
import os
from unittest.mock import patch, MagicMock

import pytest


class TestMainEntrypoint:
    """Test main entrypoint logic."""

    def test_main_with_cli_args(self):
        """Test that CLI args trigger CLI mode."""
        with patch("sys.argv", ["main.py", "health"]):
            with patch("app.cli.app") as mock_cli:
                from main import main
                
                main()
                
                mock_cli.assert_called_once()

    def test_main_daemon_mode(self):
        """Test daemon mode via env variable."""
        with patch.dict(os.environ, {"DAEMON_MODE": "true"}):
            with patch("sys.argv", ["main.py"]):
                with patch("main.run_daemon_mode") as mock_daemon:
                    from main import main
                    
                    main()
                    
                    mock_daemon.assert_called_once()

    def test_main_api_only_mode(self):
        """Test API-only mode (default)."""
        with patch.dict(os.environ, {"DAEMON_MODE": "false"}):
            with patch("sys.argv", ["main.py"]):
                with patch("main.run_api_only") as mock_api:
                    from main import main
                    
                    main()
                    
                    mock_api.assert_called_once()

    def test_run_daemon_mode(self):
        """Test daemon mode starts watcher and API."""
        with patch("app.config.load_config") as mock_config:
            with patch("app.daemon.watcher.start_watcher") as mock_watcher:
                with patch("uvicorn.run") as mock_uvicorn:
                    mock_cfg = MagicMock()
                    mock_cfg.watch_dir = "/data/watch"
                    mock_cfg.output_dir = "/data/output"
                    mock_cfg.rclone_remote_name = "gdrive"
                    mock_cfg.rclone_dest_path = "backups"
                    mock_config.return_value = mock_cfg

                    mock_observer = MagicMock()
                    mock_watcher.return_value = mock_observer

                    from main import run_daemon_mode
                    
                    try:
                        # Simulate quick exit
                        mock_uvicorn.side_effect = KeyboardInterrupt()
                        run_daemon_mode()
                    except (KeyboardInterrupt, SystemExit):
                        pass
                    
                    mock_watcher.assert_called_once()

    def test_run_api_only(self):
        """Test API-only mode."""
        with patch("uvicorn.run") as mock_uvicorn:
            mock_uvicorn.side_effect = KeyboardInterrupt()
            
            from main import run_api_only
            
            try:
                run_api_only()
            except KeyboardInterrupt:
                pass
            
            mock_uvicorn.assert_called_once()
