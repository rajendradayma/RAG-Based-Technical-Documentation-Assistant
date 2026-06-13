# FastAPI Basics

FastAPI is a modern, fast (high-performance) web framework for building APIs with Python based on standard Python type hints.

## Creating a Simple Application

To create a FastAPI application, instantiate the FastAPI class:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

## Path Parameters

You can declare path parameters with the same syntax used by Python format strings:

```python
@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}
```

FastAPI will automatically validate that `item_id` is an integer, and return a clear error if it is not.

## Query Parameters

When you declare other function parameters that are not part of the path parameters, they are automatically interpreted as query parameters.

```python
@app.get("/items/")
def read_item(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```

## Request Body with Pydantic

Use Pydantic models to declare a request body:

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool | None = None

@app.post("/items/")
def create_item(item: Item):
    return item
```

FastAPI will read the body of the request as JSON, convert the corresponding types, validate the data, and provide automatic documentation.

## Running the Application

Run the server with Uvicorn:

```bash
uvicorn main:app --reload
```

The `--reload` flag makes the server restart after code changes, which is useful only during development.

## Automatic Documentation

FastAPI automatically generates interactive API documentation. Once your app is running, visit:
- `/docs` for the Swagger UI
- `/redoc` for the ReDoc UI

These are generated automatically based on your path operations, parameters, and Pydantic models.

## HTTP Status Codes

You can set custom status codes for responses:

```python
from fastapi import status

@app.post("/items/", status_code=status.HTTP_201_CREATED)
def create_item(item: Item):
    return item
```

## Error Handling

FastAPI provides the `HTTPException` class for returning HTTP error responses:

```python
from fastapi import HTTPException

@app.get("/items/{item_id}")
def read_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]
```
