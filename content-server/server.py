from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse


app = FastAPI(title="Content Server")
PAGES_DIR = Path(__file__).resolve().parent / "pages"


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    links = "\n".join(
        f'<li><a href="/pages/{page.name}">{page.name}</a></li>'
        for page in sorted(PAGES_DIR.glob("*.html"))
    )
    return f"""
    <html>
      <body style="font-family: sans-serif; padding: 2rem;">
        <h1>Content Server</h1>
        <p>Pages available for the demo:</p>
        <ul>{links}</ul>
      </body>
    </html>
    """


@app.get("/pages/{page_name}")
async def get_page(page_name: str) -> FileResponse:
    return FileResponse(PAGES_DIR / page_name)
