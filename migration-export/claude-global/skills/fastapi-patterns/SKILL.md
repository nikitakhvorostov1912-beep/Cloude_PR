---
description: Паттерны FastAPI: роутеры, Pydantic v2, зависимости, error handling, тестирование. Используй при работе с Python backend.
---

# FastAPI Patterns

## Структура проекта

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # create_app(), lifespan
│   ├── config.py             # Settings(BaseSettings)
│   ├── dependencies.py       # Dependency injection
│   ├── routers/
│   │   ├── __init__.py
│   │   └── {domain}.py       # APIRouter с prefix
│   ├── models/
│   │   ├── __init__.py
│   │   └── {domain}.py       # Pydantic v2 модели
│   ├── services/
│   │   └── {domain}.py       # Бизнес-логика
│   └── exceptions.py         # Кастомные исключения
├── tests/
│   ├── conftest.py           # fixtures, AsyncClient
│   └── test_{domain}.py
└── pyproject.toml
```

## Pydantic v2

```python
from pydantic import BaseModel, Field, ConfigDict

class ItemCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)

class ItemResponse(ItemCreate):
    id: int
    created_at: datetime
```

- `model_config = ConfigDict(...)` вместо `class Config`
- `model_validate()` вместо `parse_obj()`
- `model_dump()` вместо `.dict()`
- Field validators: `@field_validator`, `@model_validator`

## Роутеры

```python
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/items", tags=["items"])

@router.get("/", response_model=list[ItemResponse])
async def list_items(service: ItemService = Depends(get_item_service)):
    return await service.list_all()

@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(data: ItemCreate, service: ItemService = Depends(get_item_service)):
    return await service.create(data)
```

## Зависимости

```python
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()

async def get_item_service(settings: Settings = Depends(get_settings)) -> ItemService:
    return ItemService(settings)
```

## Error Handling

```python
from fastapi import Request
from fastapi.responses import JSONResponse

class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.message, "data": None}
    )
```

## Тестирование

```python
import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_item(client: AsyncClient):
    response = await client.post("/items/", json={"name": "Test", "price": 9.99})
    assert response.status_code == 201
    assert response.json()["name"] == "Test"
```

## Чеклист

- [ ] Все эндпоинты имеют `response_model`
- [ ] Все входные данные через Pydantic модели
- [ ] Бизнес-логика в services, не в роутерах
- [ ] Зависимости через `Depends()`
- [ ] Кастомные исключения с handler'ами
- [ ] Тесты через `httpx.AsyncClient`
