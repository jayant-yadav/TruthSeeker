# Backend Setup

This directory contains the backend server code for the project.

## Prerequisites

- Python 3.12 or higher
- `uv` package installer (recommended over pip)

## Environment Setup

```bash
uv sync
source .venv/bin/activate
uv pip install -r requirements.txt --no-binary=whispercpp --no-cache
```

Create a `.env` file in the root directory with the following variables:

```bash
OPENAI_API_KEY=your_openai_api_key
```

### Google Cloud Speech-to-Text
1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Name your service account (e.g., "speech-to-text-service")
4. Assign the "Cloud Speech-to-Text Service Agent" role
5. Create and download the JSON key file
6. Store this key securely - it gives access to your Google Cloud resources

Add the following line to your `.env` file:
```bash
GOOGLE_APPLICATION_CREDENTIALS="FULL_PATH_TO_THE_JSON_KEY_FILE"
```

## Running the Server

```bash
uvicorn app.main:app --reload
```

## Development

- The main application code is in the `app` directory
- API endpoints are defined in `app/main.py`
- Transcription logic is in `app/transcription/*.py`

## Managing Dependencies

- Add a new dependency:
```bash
uv add <package-name>
```

- Remove a dependency:
```bash
uv remove <package-name>
```

# Commands to run backend on windows 
