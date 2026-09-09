from fastapi import FastAPI

app = FastAPI(title="Postgrad Teacher Platform")


@app.get("/health")
def health():
    return {"status": "ok"}
