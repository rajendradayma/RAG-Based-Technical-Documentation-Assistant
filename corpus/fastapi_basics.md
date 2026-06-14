# FastAPI
# FastAPI Documentation

FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.8+ based on standard Python type hints. It is built on top of **Starlette** for the web parts and **Pydantic** for the data parts.

Key features include:
- **Fast**: Very high performance, on par with NodeJS and Go thanks to Starlette and Pydantic.
- **Fast to code**: Increase the speed to develop features by about 200% to 300%.
- **Fewer bugs**: Reduce about 40% of human-induced errors.
- **Intuitive**: Great editor support. Completion everywhere. Less time debugging.
- **Easy**: Designed to be easy to use and learn. Less time reading docs.
- **Short**: Minimize code duplication. Multiple features from each parameter declaration. Fewer bugs.
- **Robust**: Get production-ready code. With automatic interactive documentation.
- **Standards-based**: Based on (and fully compatible with) the open standards for APIs: OpenAPI and JSON Schema.

---

## Installation

FastAPI requires Python 3.8 or higher. Install it using pip:

```bash
pip install fastapi
```

You will also need an ASGI server to run your application. The recommended server is **Uvicorn**:

```bash
pip install uvicorn[standard]
```

The `[standard]` extra includes recommended dependencies for performance, such as `uvloop` and `httptools`.

---

## Creating Your First Application

The simplest FastAPI application looks like this:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}
```

### How It Works

1. **Import FastAPI**: Import the `FastAPI` class from the `fastapi` module. This class provides all the functionality for your API.

2. **Create an app instance**: Create an instance of the `FastAPI` class. This `app` object is the main point of interaction for creating your API. All routes, middleware, and events are registered on this object.

3. **Define a path operation**: Use decorators like `@app.get("/")` to tell FastAPI that the function below should handle requests to the path `/` using the `GET` operation.

4. **Return a response**: The function returns a dictionary, which FastAPI automatically converts to JSON.

### Running the Application

Save the code to a file named `main.py` and run it with Uvicorn:

```bash
uvicorn main:app --reload
```

- `main`: The file name (without the `.py` extension).
- `app`: The name of the FastAPI instance inside `main.py`.
- `--reload`: Enables auto-reload for development. **Never use in production**.

Once running, visit:
- `http://127.0.0.1:8000/` — Your API endpoint
- `http://127.0.0.1:8000/docs` — Interactive Swagger UI documentation
- `http://127.0.0.1:8000/redoc` — Alternative ReDoc documentation

---

## Path Parameters

Path parameters are variable parts of a URL path. They are declared using Python format string syntax inside the path decorator.

### Basic Path Parameters

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}
```

When you declare a path parameter with a type hint (like `int` above), FastAPI automatically:
- **Validates** the parameter: If a client sends `/items/foo`, FastAPI returns a clear `422 Unprocessable Entity` error explaining that `item_id` must be an integer.
- **Converts** the parameter: The value is parsed from a string (since URLs are always strings) into the declared Python type.
- **Documents** the parameter: The type appears in the interactive API documentation.

### Path Parameters with Enums

For parameters that should only accept specific predefined values, use Python's `Enum`:

```python
from enum import Enum
from fastapi import FastAPI

class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"

app = FastAPI()

@app.get("/models/{model_name}")
def get_model(model_name: ModelName):
    if model_name == ModelName.alexnet:
        return {"model_name": model_name, "message": "Deep Learning FTW!"}
    if model_name.value == "lenet":
        return {"model_name": model_name, "message": "LeCNN all the images"}
    return {"model_name": model_name, "message": "Have some residuals"}
```

Using `Enum` provides:
- **Validation**: Only values defined in the enum are accepted.
- **Documentation**: The interactive docs show the available values as a dropdown.
- **Type safety**: Your editor provides autocompletion for enum members.

---

## Query Parameters

Query parameters are key-value pairs that appear after the `?` in a URL, such as `/items/?skip=0&limit=10`. In FastAPI, any function parameter that is not part of the path is automatically treated as a query parameter.

### Basic Query Parameters

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/")
def read_item(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```

In this example:
- `skip` and `limit` are query parameters because they are not in the path template.
- Default values (`0` and `10`) make them **optional**. If not provided, the defaults are used.
- Type hints enable automatic validation and conversion.

### Optional Query Parameters

To make a query parameter truly optional (accepting `None`), declare it with a `None` default:

```python
from typing import Union
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/{item_id}")
def read_item(item_id: str, q: Union[str, None] = None):
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}
```

Here, `q` is optional. If the client does not provide it, the function receives `None`.

### Query Parameter Validation

FastAPI allows you to add validation constraints to query parameters using `Query`:

```python
from fastapi import FastAPI, Query
from typing import Annotated

app = FastAPI()

@app.get("/items/")
async def read_items(
    q: Annotated[str | None, Query(min_length=3, max_length=50)] = None
):
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results
```

The `Query` class provides:
- `min_length` / `max_length`: String length constraints.
- `pattern`: Regular expression validation.
- `gt` / `ge` / `lt` / `le`: Numeric range constraints (greater than, greater or equal, etc.).
- `title` / `description`: Human-readable metadata for documentation.
- `deprecated`: Mark parameters as deprecated in the docs.
- `alias`: Alternative name for the parameter in the URL.

---

## Request Body

When you need to send data from a client to your API, you send it as a **request body**. FastAPI uses **Pydantic models** to declare request bodies, which gives you automatic validation, serialization, and documentation.

### Declaring a Request Body

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

@app.post("/items/")
def create_item(item: Item):
    item_dict = item.model_dump()
    if item.tax:
        price_with_tax = item.price + item.tax
        item_dict.update({"price_with_tax": price_with_tax})
    return item_dict
```

**How Pydantic models work in FastAPI:**

1. **Validation**: FastAPI reads the request body as JSON and validates it against the Pydantic model. If the JSON is missing a required field or has the wrong type, FastAPI returns a detailed `422` error.

2. **Conversion**: Data types are automatically converted. For example, a JSON number is converted to a Python `float` or `int`.

3. **Documentation**: The model schema appears in the interactive docs, showing all fields, types, and whether they are required.

4. **IDE support**: Your editor provides autocompletion and type checking for model attributes.

### Multiple Body Parameters

You can declare multiple Pydantic models in a single path operation:

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

class User(BaseModel):
    username: str
    full_name: str | None = None

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item, user: User):
    results = {"item_id": item_id, "item": item, "user": user}
    return results
```

FastAPI automatically expects both `Item` and `User` JSON bodies and embeds them in the request. The client sends a single JSON object containing both models.

### Field Validation with `Field`

For more granular control over individual fields, use Pydantic's `Field`:

```python
from fastapi import FastAPI, Body
from pydantic import BaseModel, Field
from typing import Annotated

app = FastAPI()

class Item(BaseModel):
    name: str
    description: str | None = Field(
        default=None, title="The description of the item", max_length=300
    )
    price: float = Field(gt=0, description="The price must be greater than zero")
    tax: float | None = None

@app.put("/items/{item_id}")
async def update_item(
    item_id: int,
    item: Annotated[Item, Body(embed=True)],
):
    results = {"item_id": item_id, "item": item}
    return results
```

`Field` provides:
- `default`: Default value if not provided.
- `title` / `description`: Documentation metadata.
- `gt`, `ge`, `lt`, `le`: Numeric constraints.
- `min_length`, `max_length`: String constraints.
- `pattern`: Regex validation.
- `examples`: Example values for the interactive docs.

---

## HTTP Status Codes

HTTP status codes indicate the result of a request. FastAPI lets you set custom status codes for each path operation.

### Setting Status Codes

```python
from fastapi import FastAPI, status

app = FastAPI()

@app.post("/items/", status_code=status.HTTP_201_CREATED)
def create_item(name: str):
    return {"name": name}

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int):
    return None

@app.get("/items/", status_code=status.HTTP_200_OK)
def read_items():
    return [{"item_id": "Foo"}]
```

Common status codes:

| Code | Constant | Meaning |
|------|----------|---------|
| 200 | `HTTP_200_OK` | Success (default for GET) |
| 201 | `HTTP_201_CREATED` | Resource created (default for POST) |
| 204 | `HTTP_204_NO_CONTENT` | Success, no body (common for DELETE) |
| 400 | `HTTP_400_BAD_REQUEST` | Client error |
| 401 | `HTTP_401_UNAUTHORIZED` | Authentication required |
| 403 | `HTTP_403_FORBIDDEN` | Permission denied |
| 404 | `HTTP_404_NOT_FOUND` | Resource not found |
| 422 | `HTTP_422_UNPROCESSABLE_ENTITY` | Validation error (FastAPI default) |
| 500 | `HTTP_500_INTERNAL_SERVER_ERROR` | Server error |

---

## Error Handling

FastAPI provides the `HTTPException` class for returning HTTP error responses with custom status codes and detail messages.

### Raising HTTP Exceptions

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()
items = {"foo": "The Foo Wrestlers"}

@app.get("/items/{item_id}")
async def read_item(item_id: str):
    if item_id not in items:
        raise HTTPException(
            status_code=404,
            detail="Item not found",
            headers={"X-Error": "There goes my error"},
        )
    return {"item": items[item_id]}
```

When you raise `HTTPException`:
- FastAPI stops executing the path operation function immediately.
- It returns an HTTP response with the specified status code.
- The `detail` is returned as the response body (JSON by default).
- Optional `headers` can be added to the response.

### Custom Exception Handlers

For application-specific errors, you can define custom exceptions and handlers:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

class CustomException(Exception):
    def __init__(self, name: str):
        self.name = name

app = FastAPI()

@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=418,
        content={"message": f"Oops! {exc.name} did something."},
    )

@app.get("/unicorns/{name}")
async def read_unicorn(name: str):
    if name == "yolo":
        raise CustomException(name=name)
    return {"unicorn_name": name}
```

Custom exception handlers allow you to:
- Centralize error response formatting.
- Log errors consistently.
- Return user-friendly error messages while hiding internal details.

### Overriding Default Handlers

You can also override FastAPI's built-in exception handlers:

```python
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=400)
```

**Best practice**: Override default handlers only when you need custom error response formats. For most applications, FastAPI's default JSON error responses are sufficient and well-documented.

---

## Dependencies

FastAPI includes a powerful **dependency injection** system. Dependencies are functions that run before your path operation, and their return values are "injected" as parameters.

### Why Use Dependencies?

- **Code reuse**: Share common logic across multiple endpoints.
- **Database connections**: Open and close database sessions automatically.
- **Authentication**: Verify tokens or credentials before handling requests.
- **Validation**: Run custom validation logic.

### Basic Dependencies

```python
from fastapi import FastAPI, Depends

app = FastAPI()

async def common_parameters(q: str | None = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
async def read_items(commons: dict = Depends(common_parameters)):
    return commons

@app.get("/users/")
async def read_users(commons: dict = Depends(common_parameters)):
    return commons
```

The `Depends` class tells FastAPI to:
1. Call `common_parameters` before `read_items` or `read_users`.
2. Pass the return value of `common_parameters` as the `commons` parameter.
3. Cache the result within the request so sub-dependencies don't re-run.

### Classes as Dependencies

For more complex dependencies, you can use classes:

```python
from fastapi import FastAPI, Depends

app = FastAPI()

class CommonQueryParams:
    def __init__(self, q: str | None = None, skip: int = 0, limit: int = 100):
        self.q = q
        self.skip = skip
        self.limit = limit

@app.get("/items/")
async def read_items(commons: CommonQueryParams = Depends(CommonQueryParams)):
    response = {}
    if commons.q:
        response.update({"q": commons.q})
    response.update({"skip": commons.skip, "limit": commons.limit})
    return response
```

Class dependencies are useful when you need to:
- Encapsulate multiple related parameters.
- Add methods to process or validate parameters.
- Share configuration across endpoints.

### Dependencies with `yield` (Database Sessions)

The `yield` syntax is the recommended pattern for resources that need cleanup, such as database connections:

```python
from fastapi import FastAPI, Depends, HTTPException

app = FastAPI()

async def get_db():
    db = DBSession()
    try:
        yield db
    finally:
        db.close()

@app.get("/items/")
async def read_items(db: DBSession = Depends(get_db)):
    items = db.query(Item).all()
    return items
```

**How `yield` works:**
1. Code before `yield` runs before the path operation (e.g., open a database connection).
2. The yielded value is passed to the path operation.
3. Code after `yield` runs after the response is sent (e.g., close the connection).

**Important**: If an exception occurs in the path operation, the code after `yield` still runs, but you should handle exceptions there if needed.

### Global Dependencies

Apply dependencies to all routes in the application:

```python
from fastapi import FastAPI, Depends

async def verify_token():
    pass

app = FastAPI(dependencies=[Depends(verify_token)])
```

---

## Security and Authentication

FastAPI provides built-in security utilities, including OAuth2 password flow with JWT tokens.

### OAuth2 with Password and JWT

This is the industry-standard pattern for token-based authentication:

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from typing import Annotated

app = FastAPI()

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
```

**Components explained:**

- **`OAuth2PasswordBearer`**: Tells FastAPI that the URL `/token` is where clients send username and password to get a token. It also declares that your API expects a token in the `Authorization` header with `Bearer` scheme.

- **`passlib`**: Handles password hashing using bcrypt. Never store plain-text passwords.

- **`python-jose`**: Generates and verifies JWT tokens. JWTs are signed tokens that contain claims (like username and expiration).

**Token creation and verification flow:**

1. User sends username/password to `/token`.
2. Server verifies credentials against hashed passwords in the database.
3. Server creates a JWT with the username and expiration time.
4. Client includes the JWT in the `Authorization: Bearer <token>` header for subsequent requests.
5. Server verifies the JWT signature and extracts the user identity.

---

## Middleware and CORS

Middleware are functions that process requests before they reach your path operations, or process responses before they are sent to clients.

### CORS (Cross-Origin Resource Sharing)

CORS is a security mechanism that controls how web pages can request resources from a different domain. FastAPI provides built-in CORS middleware:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8080",
    "https://myfrontend.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**CORS parameters:**
- `allow_origins`: List of domains allowed to make requests. Use `["*"]` to allow all (not recommended with credentials).
- `allow_credentials`: Allow cookies and authorization headers in cross-origin requests.
- `allow_methods`: HTTP methods allowed (e.g., `["GET", "POST"]` or `["*"]` for all).
- `allow_headers`: Headers allowed in requests.

### Custom Middleware

Create custom middleware to run code on every request:

```python
from fastapi import FastAPI, Request
import time

app = FastAPI()

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

Custom middleware is useful for:
- Logging requests and responses.
- Adding security headers.
- Measuring request processing time.
- Rate limiting.
- Request/response modification.

---

## Background Tasks

Background tasks run after the response has been sent to the client. This is useful for operations that don't need to complete before the client receives a response, such as:

- Sending emails.
- Processing data.
- Writing to logs or databases.
- Calling external APIs.

```python
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

def write_notification(email: str, message=""):
    with open("log.txt", mode="w") as email_file:
        content = f"notification for {email}: {message}"
        email_file.write(content)

@app.post("/send-notification/{email}")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(write_notification, email, message="some notification")
    return {"message": "Notification sent in the background"}
```

**Important considerations:**
- Background tasks run in the same process as the main application.
- If the server restarts, pending background tasks are lost.
- For critical or long-running tasks, use a dedicated task queue like Celery, RQ, or Dramatiq instead.

---

## WebSockets

WebSockets provide full-duplex communication channels over a single TCP connection. Unlike HTTP, which is request-response based, WebSockets allow the server to push data to the client without the client requesting it.

### WebSocket Example with Connection Manager

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")
```

**WebSocket lifecycle:**
1. Client sends a WebSocket handshake request.
2. Server accepts with `await websocket.accept()`.
3. Both sides can send and receive messages.
4. Connection closes when either side disconnects or an error occurs.

**Use cases:**
- Real-time chat applications.
- Live notifications.
- Collaborative editing.
- Real-time dashboards and monitoring.
- Multiplayer games.

---

## File Uploads

FastAPI supports file uploads via `File` and `UploadFile`.

### Single File Upload

```python
from fastapi import FastAPI, File, UploadFile
from typing import Annotated

app = FastAPI()

@app.post("/files/")
async def create_file(file: Annotated[bytes, File()]):
    return {"file_size": len(file)}

@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile):
    return {"filename": file.filename}
```

**`File()` vs `UploadFile`:**

| Feature | `File()` (bytes) | `UploadFile` |
|---------|------------------|--------------|
| Memory usage | Loads entire file into memory | Streams file, uses disk for large files |
| Metadata | None | Access `filename`, `content_type`, `headers` |
| Spooling | No | Automatic spooling to disk for large files |
| Async reading | No | Yes, with `await file.read()` |

**Recommendation**: Use `UploadFile` for production applications, especially when handling large files or multiple uploads.

### Multiple File Uploads

```python
from fastapi import FastAPI, File, UploadFile
from typing import Annotated, List

app = FastAPI()

@app.post("/uploadfiles/")
async def create_upload_files(files: List[UploadFile]):
    return {"filenames": [file.filename for file in files]}
```

---

## Testing

FastAPI provides `TestClient` based on HTTPX for testing your application without running a server.

### Using TestClient

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/")
async def read_main():
    return {"msg": "Hello World"}

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}
```

**Benefits of TestClient:**
- No need to run a server during tests.
- Fast execution.
- Can inspect response status, headers, and JSON body.
- Supports all HTTP methods.
- Can send files, form data, and JSON bodies.

### Async Testing

For testing async code, use `AsyncClient` from HTTPX:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_root():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Tomato"}
```

---

## Advanced Response Handling

### Custom Response Classes

FastAPI returns JSON by default, but you can return other response types:

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse, StreamingResponse

app = FastAPI()

@app.get("/html/", response_class=HTMLResponse)
async def read_html():
    return "<html><body><h1>Hello</h1></body></html>"

@app.get("/file/")
async def get_file():
    return FileResponse("path/to/file.pdf", filename="report.pdf")
```

### Streaming Responses

Streaming is useful for large data or real-time feeds:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/stream/")
async def stream_data():
    def generate():
        for i in range(100):
            yield f"data: {i}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## Event Handlers

Event handlers run code when the application starts up or shuts down. This is useful for:
- Initializing database connections.
- Loading machine learning models.
- Setting up caches.
- Cleaning up resources.

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    yield
    # Shutdown
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)
```

**Note**: The older `@app.on_event("startup")` and `@app.on_event("shutdown")` decorators are deprecated in favor of the `lifespan` context manager.

---

## Bigger Applications — Routers

For large applications, split your code into multiple files using `APIRouter`:

```python
from fastapi import APIRouter

router = APIRouter(
    prefix="/items",
    tags=["items"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def read_items():
    return [{"item_id": "Foo"}]
```

Then include the router in your main application:

```python
from fastapi import FastAPI
from app.routers import items, users

app = FastAPI()
app.include_router(items.router)
app.include_router(users.router)
```

**Benefits of routers:**
- Organize code by domain or feature.
- Reuse router prefixes and tags.
- Apply dependencies to entire groups of routes.
- Better collaboration in team environments.

---

## Deployment

### Production ASGI Server

For production, use Gunicorn with Uvicorn workers:

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

- `-w 4`: Number of worker processes. Typically `2 * CPU cores + 1`.
- `-k uvicorn.workers.UvicornWorker`: Use Uvicorn's Gunicorn worker class.

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Production checklist:**
- Disable `--reload`.
- Use HTTPS with TLS certificates.
- Set up logging and monitoring.
- Use environment variables for secrets.
- Configure CORS appropriately.
- Add rate limiting.
- Use a process manager (systemd, supervisord, or Docker).
'''
