"""Регистрация всех API-роутеров приложения.

Импортирует роутеры из модулей маршрутов и объединяет их
в список для удобного подключения к FastAPI-приложению.
"""

from app.api.routes.data import router as data_router
from app.api.routes.export import router as export_router
from app.api.routes.pipeline import router as pipeline_router
from app.api.routes.projects import router as projects_router
from app.api.routes.upload import router as upload_router

all_routers = [
    projects_router,
    upload_router,
    pipeline_router,
    data_router,
    export_router,
]
