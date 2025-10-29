# Assets Folder

This folder contains static assets for the Lemi application.

## Contents

- **Logo**: Main application logo (various formats)
- **Icon**: App icon/favicon
- **Images**: Other static images used in the app

## Usage

These assets can be served by the FastAPI backend and accessed by the frontend.

To serve static files, add this to your `main.py`:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")
```

Then access files at: `http://localhost:8000/static/assets/logo.png`
