from fastapi import FastAPI

from app.api.admin_master_data import router as admin_master_data_router
from app.api.master_data import router as master_data_router

app = FastAPI(title="Postgrad Teacher Platform")
app.include_router(master_data_router)
app.include_router(admin_master_data_router)


@app.get("/health")
def health():
    return {"status": "ok"}
