from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings
from app.core.security import require_admin

UI_DIR = "app/ui"


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="AI customer support assistant API.",
    )
    app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def support_workspace() -> FileResponse:
        return FileResponse(f"{UI_DIR}/index.html")

    @app.get("/admin", include_in_schema=False, dependencies=[Depends(require_admin)])
    async def admin_workspace() -> FileResponse:
        return FileResponse(f"{UI_DIR}/admin.html")

    app.include_router(router)
    return app


app = create_app()
