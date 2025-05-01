import uvicorn
from app import create_app
from app.database import init_db

app, templates = create_app()

@app.on_event("startup")
async def on_startup():
    init_db()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)