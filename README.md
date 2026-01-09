# CleanSlate (Phobos)

A containerized privacy tool that strips metadata from files (images, docs, video) using `exiftool`, backs them up to cloud storage using `rclone`, and logs events to Firebase Firestore.

## Features

- **Metadata Removal**: Strip EXIF and other metadata from files using exiftool
- **Cloud Backup**: Automatically backup originals to Google Drive (or other rclone remotes)
- **Database Logging**: Track all file processing events in Firebase Firestore
- **File Watcher**: Daemon mode monitors directories and auto-processes new files
- **REST API**: FastAPI-based endpoints for programmatic access
- **CLI**: Rich command-line interface for manual operations

## Supported File Types

- Images: `.jpg`, `.jpeg`, `.png`
- Documents: `.pdf`, `.docx`
- Videos: `.mp4`, `.mov`

## Quick Start

### Local Development

1. **Clone and setup**:
```bash
git clone <repo-url>
cd phobos
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment** (copy `.env.example` to `.env`):
```bash
DAEMON_MODE=false
WATCH_DIR=/data/watch
OUTPUT_DIR=/data/clean
RCLONE_REMOTE_NAME=gdrive
RCLONE_DEST_PATH=backups
FIREBASE_CREDENTIALS=/path/to/firebase-credentials.json
```

3. **Run CLI commands**:
```bash
# Health check
python main.py health

# Sanitize a file
python main.py sanitize /path/to/photo.jpg

# Preview metadata only (no changes)
python main.py sanitize /path/to/photo.jpg --dry-run

# Skip confirmation after preview
python main.py sanitize /path/to/photo.jpg --confirm

# Show all metadata (not only removable)
python main.py sanitize /path/to/photo.jpg --dry-run --show-all-metadata

# Backup a file
python main.py backup /path/to/file.pdf --remote gdrive:backups

# Start API server
python main.py run-api

# Start daemon mode
python main.py run-daemon
```

### Docker Deployment

1. **Build the image**:
```bash
docker build -t cleanslate .
```

2. **Run in API-only mode**:
```bash
docker run -p 8000:8000 \
  -e DAEMON_MODE=false \
  -v $(pwd)/data:/data \
  -v $(pwd)/firebase-credentials.json:/app/firebase-service-account.json \
  cleanslate
```

3. **Run in daemon mode** (watcher + API):
```bash
docker run -p 8000:8000 \
  -e DAEMON_MODE=true \
  -v $(pwd)/data:/data \
  -v $(pwd)/rclone.conf:/root/.config/rclone/rclone.conf \
  -v $(pwd)/firebase-credentials.json:/app/firebase-service-account.json \
  cleanslate
```

## Architecture

### Services

- **`app/services/backup_service.py`**: Rclone wrapper for cloud uploads
- **`app/services/cleaner_service.py`**: Exiftool wrapper for metadata removal
- **`app/services/db_service.py`**: Firebase Firestore client for event logging

### Daemon Mode

The file watcher (`app/daemon/watcher.py`) monitors `WATCH_DIR` and:
1. Backs up original file to cloud storage
2. Sanitizes file by removing metadata
3. Moves processed file to `OUTPUT_DIR`
4. Logs transaction to Firestore

### API Endpoints

- `GET /health` - Health check
- `GET /status` - Service status
- `POST /sanitize` - Upload a file, returns full metadata, removed metadata, and a shareable link to the sanitized file on the configured rclone remote
- `POST /backup` - Backup a file to cloud

Example sanitize upload (multipart):

```bash
curl -X POST http://localhost:8000/sanitize \
  -F "file=@/path/to/photo.jpg" | jq
```

Example response (abridged):

```json
{
  "success": true,
  "message": "File sanitized successfully",
  "file_path": "/tmp/cleanslate_uploads/abc123.jpg",
  "file_size": 12345,
  "metadata_before": {"EXIF:Make": "Canon"},
  "metadata_after": {},
  "removed_metadata": {"EXIF:Make": {"before": "Canon", "after": null}},
  "remote_link": "https://drive.google.com/..."
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DAEMON_MODE` | `false` | Enable daemon mode (watcher + API) |
| `WATCH_DIR` | `/data/watch` | Directory to monitor for new files |
| `OUTPUT_DIR` | `/data/clean` | Directory for processed files |
| `RCLONE_REMOTE_NAME` | `gdrive` | Rclone remote name (from rclone.conf) |
| `RCLONE_DEST_PATH` | `backups` | Folder path on remote |
| `FIREBASE_ENABLED` | `true` | Toggle Firestore logging (set to `false` to disable Firebase completely) |
| `FIREBASE_CREDENTIALS` | - | Path to Firebase service account JSON (only required when `FIREBASE_ENABLED=true`) |

### Setup Firebase

1. Create a Firebase project at https://console.firebase.google.com
2. Enable Firestore Database
3. Generate a service account key (Project Settings → Service Accounts)
4. Download the JSON key and set `FIREBASE_CREDENTIALS` to its path

### Setup Rclone

1. Install rclone: https://rclone.org/install/
2. Configure remote:
```bash
rclone config
# Follow prompts to set up Google Drive or other remote
```
3. Mount config in Docker or set `RCLONE_REMOTE_NAME` to match your remote name

## Development

### Run Tests

```bash
pytest -v
```

### Project Layout
- [app/](app/) — application code
	- [app/services/](app/services/) — service modules (rclone, cleaner, db)
	- [app/daemon/](app/daemon/) — watcher/daemon logic
	- [app/api/](app/api/) — FastAPI app modules
	- [app/cli.py](app/cli.py) — CLI entrypoint
- [tests/](tests/) — test suite
- [.env.example](.env.example) — environment template
- [requirements.txt](requirements.txt) — dependencies
- [Dockerfile](Dockerfile) — container image

## License

MIT