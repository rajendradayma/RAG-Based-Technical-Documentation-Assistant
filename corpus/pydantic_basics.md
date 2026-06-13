
pydantic_docs = '''# Pydantic Documentation

Pydantic is the most widely used data validation library for Python. It uses Python type hints to validate, serialize, and document data. Pydantic v2 (released in 2023) is written in Rust and is 5-50x faster than v1.

Key features include:
- **Type enforcement**: Ensures data conforms to declared types.
- **Automatic validation**: Validates data on model creation and assignment.
- **JSON serialization**: Converts models to and from JSON effortlessly.
- **Self-documenting**: Generates JSON Schema for your models.
- **IDE integration**: Full support for autocompletion and type checking.
- **Performance**: Rust-powered core for maximum speed.

---

## Installation

Install Pydantic using pip:

```bash
pip install pydantic
```

For email validation support, install with the email extra:

```bash
pip install pydantic[email]
```

For settings management (integration with environment variables):

```bash
pip install pydantic-settings
```

---

## Defining Models

Models are the core of Pydantic. They are defined by inheriting from `BaseModel` and declaring fields with type annotations.

### Basic Model Definition

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str
    age: int | None = None
```

**Field requirements:**
- Fields without a default value are **required**. The client must provide them, or Pydantic raises a `ValidationError`.
- Fields with a default value (like `age: int | None = None` above) are **optional**. If not provided, they use the default.
- Type annotations tell Pydantic what type to expect and how to validate/coerce the data.

### Default Values and Factories

For simple default values, assign them directly:

```python
class User(BaseModel):
    name: str = "Anonymous"
    is_active: bool = True
```

For mutable defaults (lists, dicts, sets), always use `Field(default_factory=...)` to avoid the common Python pitfall where all instances share the same mutable object:

```python
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class User(BaseModel):
    id: int
    name: str = "Anonymous"
    created_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)
```

**Why `default_factory` matters:**

```python
# WRONG - All users share the same list!
class BadUser(BaseModel):
    tags: list[str] = []

# CORRECT - Each user gets their own list
class GoodUser(BaseModel):
    tags: list[str] = Field(default_factory=list)
```

---

## Validation

Pydantic's primary purpose is to validate data. Validation occurs automatically when you create a model instance.

### Basic Validation

```python
user = User(id=1, name="Alice", email="alice@example.com")
```

If the data doesn't match the expected types, Pydantic raises a `ValidationError` with detailed information about what went wrong, including the field name, the expected type, the provided value, and a human-readable error message.

### ValidationError Details

```python
from pydantic import BaseModel, ValidationError

class User(BaseModel):
    id: int
    name: str
    email: str

try:
    user = User(id="not_an_int", name="", email="invalid")
except ValidationError as e:
    # List of error dictionaries
    print(e.errors())
    
    # Pretty JSON output
    print(e.json())
    
    # Human-readable string
    print(str(e))
```

Each error dictionary contains:
- `loc`: Location of the error (field name path).
- `msg`: Human-readable error message.
- `type`: Error type code.
- `input`: The actual input value that caused the error.

### Strict vs Lax Validation

By default, Pydantic uses **lax validation**, which attempts to coerce values to the declared type:

```python
from pydantic import BaseModel

class Model(BaseModel):
    value: int

# Lax mode (default): coerces "123" -> 123
m = Model(value="123")
```

For **strict validation** where types must match exactly, use `Strict` types:

```python
from pydantic import BaseModel, Strict

class StrictModel(BaseModel):
    value: Strict[int]

# This will raise a ValidationError
m = StrictModel(value="123")
```

### Validating from Dictionaries

When you already have a dictionary (e.g., from parsing JSON), use `model_validate`:

```python
data = {"id": 1, "name": "Alice", "email": "alice@example.com"}
user = User.model_validate(data)
```

### Validating from JSON Strings

For JSON strings, use `model_validate_json`:

```python
json_str = '{"id": 1, "name": "Alice", "email": "alice@example.com"}'
user = User.model_validate_json(json_str)
```

This is more efficient than parsing JSON to a dict first, then validating.

---

## Type Coercion

Pydantic attempts to coerce values to the declared type where possible. This is a powerful feature that makes APIs flexible while maintaining type safety.

### Coercion Examples

```python
from pydantic import BaseModel

class CoerceExample(BaseModel):
    int_field: int
    float_field: float
    bool_field: bool
    str_field: str

m = CoerceExample(
    int_field="42",      # str "42" -> int 42
    float_field="3.14",  # str "3.14" -> float 3.14
    bool_field=1,        # int 1 -> bool True
    str_field=123,       # int 123 -> str "123"
)
```

### Common Coercion Rules

| Source Type | Target Type | Result |
|-------------|-------------|--------|
| `str` | `int` | Parsed if valid integer string |
| `str` | `float` | Parsed if valid float string |
| `int` | `float` | Converted to float (42 -> 42.0) |
| `int` | `bool` | 0 -> False, non-zero -> True |
| `bool` | `int` | True -> 1, False -> 0 |
| `int` | `str` | Converted to string (123 -> "123") |
| `float` | `int` | Truncated (3.9 -> 3) |
| `list` | `set` | Converted to set |
| `str` | `datetime` | Parsed from ISO format |

**Important**: Coercion is convenient but can sometimes hide bugs. Use strict mode when exact types are critical.

---

## Nested Models

Real-world data is often hierarchical. Pydantic models can contain other models as fields, enabling deep validation of complex structures.

### Basic Nested Models

```python
from pydantic import BaseModel

class Address(BaseModel):
    street: str
    city: str
    zip_code: str

class User(BaseModel):
    id: int
    name: str
    address: Address

user = User(
    id=1,
    name="Alice",
    address={"street": "123 Main St", "city": "NYC", "zip_code": "10001"}
)
```

When creating a `User`, Pydantic automatically:
1. Validates that `address` is a dictionary or `Address` instance.
2. Creates an `Address` model from the dictionary.
3. Validates all `Address` fields.
4. If any `Address` field is invalid, includes the path (`address.street`, etc.) in the error.

### Deeply Nested Structures

```python
from pydantic import BaseModel
from typing import List

class Product(BaseModel):
    name: str
    price: float

class OrderItem(BaseModel):
    product: Product
    quantity: int

class Order(BaseModel):
    id: int
    items: List[OrderItem]

order = Order(
    id=1,
    items=[
        {"product": {"name": "Widget", "price": 9.99}, "quantity": 2},
        {"product": {"name": "Gadget", "price": 19.99}, "quantity": 1},
    ]
)
```

Pydantic validates the entire hierarchy, providing detailed error paths like `items[0].product.price` if a product price is invalid.

---

## Field Validators

While type annotations handle basic validation, you often need custom business logic. Pydantic v2 provides the `@field_validator` decorator for this purpose.

### Basic Field Validator

```python
from pydantic import BaseModel, field_validator

class User(BaseModel):
    name: str
    email: str
    age: int

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()

    @field_validator("age")
    @classmethod
    def age_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("age must be positive")
        return v

    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v):
        if "@" not in v:
            raise ValueError("invalid email format")
        return v.lower()
```

**Key points about `@field_validator`:**
- Must be a `@classmethod` in Pydantic v2.
- Receives the field value as the argument.
- Should return the validated (and possibly transformed) value.
- Raises `ValueError` with a descriptive message for invalid data.

### Validation Modes: `before` and `after`

Pydantic v2 allows validators to run before or after the default type coercion:

```python
from pydantic import BaseModel, field_validator

class Model(BaseModel):
    value: int

    @field_validator("value", mode="before")
    @classmethod
    def coerce_string(cls, v):
        # Runs BEFORE type coercion
        if isinstance(v, str) and v.startswith("0x"):
            return int(v, 16)  # Convert hex string to int
        return v

    @field_validator("value", mode="after")
    @classmethod
    def double_it(cls, v):
        # Runs AFTER type coercion (v is guaranteed to be int)
        return v * 2
```

- **`mode="before"`**: Receives the raw input value. Useful for custom parsing or preprocessing.
- **`mode="after"`**: Receives the value after Pydantic's type coercion. Useful for additional constraints.

### Cross-Field Validation

Access other fields during validation using the `info` parameter:

```python
from pydantic import BaseModel, field_validator

class User(BaseModel):
    password: str
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("passwords do not match")
        return v
```

`info.data` contains the values of previously validated fields. Note that the order of field definitions matters — you can only access fields that appear before the current field in the model definition.

---

## Model Validators

Sometimes you need to validate the entire model, not just individual fields. Use `@model_validator` for cross-field or whole-model validation.

### After Validation

Runs after all fields have been validated and the model instance is created:

```python
from pydantic import BaseModel, model_validator

class Rectangle(BaseModel):
    width: float
    height: float

    @model_validator(mode="after")
    def check_dimensions(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("dimensions must be positive")
        return self
```

### Before Validation

Runs on the raw input data before any field validation:

```python
from pydantic import BaseModel, model_validator

class Rectangle(BaseModel):
    width: float
    height: float

    @model_validator(mode="before")
    @classmethod
    def set_square_if_single_value(cls, data):
        if isinstance(data, dict) and "size" in data and "width" not in data:
            data["width"] = data["height"] = data.pop("size")
        return data
```

**Use cases for model validators:**
- Ensuring combinations of fields are valid (e.g., start date before end date).
- Computing derived fields from multiple inputs.
- Transforming input data structures before field validation.

---

## Serialization

Pydantic models can be converted to Python dictionaries or JSON strings, making them ideal for APIs, databases, and caching.

### Basic Serialization

```python
user = User(id=1, name="Alice", email="alice@example.com", age=30)

user.model_dump()        # Returns a Python dict
user.model_dump_json()   # Returns a JSON string
```

### Serialization Options

```python
# Exclude specific fields
user.model_dump(exclude={"age"})

# Include only specific fields
user.model_dump(include={"name", "email"})

# Exclude fields that were not explicitly set
user.model_dump(exclude_unset=True)

# Exclude fields with None values
user.model_dump(exclude_none=True)

# JSON-compatible mode (converts datetime to ISO strings, etc.)
user.model_dump(mode="json")
```

### Custom JSON Encoders

For types that aren't JSON-serializable by default (like `datetime`), provide custom encoders:

```python
from datetime import datetime
from pydantic import BaseModel

class Event(BaseModel):
    name: str
    timestamp: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

---

## Configuration with `model_config`

Model behavior is controlled through the `model_config` attribute using `ConfigDict`.

### Common Configuration Options

```python
from pydantic import BaseModel, ConfigDict

class User(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,   # Strip whitespace from strings
        str_to_lower=True,           # Convert strings to lowercase
        validate_assignment=True,    # Validate when fields are modified
        extra="forbid",              # Reject extra fields: "ignore", "allow", "forbid"
        frozen=False,                # Make model immutable if True
        populate_by_name=True,       # Allow using field names as well as aliases
        use_enum_values=True,        # Use enum values instead of enum instances
    )

    name: str
    email: str
```

### Configuration Options Reference

| Option | Values | Description |
|--------|--------|-------------|
| `str_strip_whitespace` | `bool` | Strip leading/trailing whitespace from strings |
| `str_to_lower` | `bool` | Convert strings to lowercase |
| `str_to_upper` | `bool` | Convert strings to uppercase |
| `validate_assignment` | `bool` | Validate when fields are assigned after creation |
| `extra` | `"ignore"`, `"allow"`, `"forbid"` | How to handle fields not in the model |
| `frozen` | `bool` | Prevent modification after creation |
| `populate_by_name` | `bool` | Allow using field names alongside aliases |
| `use_enum_values` | `bool` | Serialize enums as their values |
| `json_schema_extra` | `dict` | Add extra metadata to JSON Schema |

---

## Aliases

Aliases allow you to use different names for fields in serialization/deserialization versus your Python code. This is essential when working with external APIs that use different naming conventions.

### Declaring Aliases

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(alias="userName")
    email: str = Field(alias="emailAddress")
    created_at: str = Field(alias="createdAt")
```

### Using Aliases

```python
# Create using aliases (e.g., from external API data)
user = User(userName="Alice", emailAddress="alice@example.com")

# Create using field names (e.g., in your own code)
user = User(name="Alice", email="alice@example.com")

# Serialize with aliases (for external APIs)
user.model_dump(by_alias=True)
# {"userName": "Alice", "emailAddress": "alice@example.com", "createdAt": None}
```

**Best practices:**
- Use `populate_by_name=True` to allow both aliases and field names.
- Use aliases when integrating with camelCase APIs (JavaScript conventions) while keeping snake_case in Python.
- Always document aliases clearly for API consumers.

---

## Computed Fields

Computed fields are properties that are calculated from other fields and included in serialization. They are available in Pydantic v2.1+.

```python
from pydantic import BaseModel, computed_field

class Rectangle(BaseModel):
    width: float
    height: float

    @computed_field
    @property
    def area(self) -> float:
        return self.width * self.height

    @computed_field
    @property
    def is_square(self) -> bool:
        return self.width == self.height

rect = Rectangle(width=4, height=4)
print(rect.model_dump())
# {"width": 4, "height": 4, "area": 16, "is_square": True}
```

**Important:**
- `@computed_field` must be used with `@property`.
- The return type annotation is required and appears in the JSON Schema.
- Computed fields are read-only and cannot be set during model creation.

---

## Discriminated Unions

When a field can be one of several different models, use discriminated unions to tell Pydantic which model to use based on a discriminator field.

```python
from pydantic import BaseModel, Field
from typing import Literal, Union

class Cat(BaseModel):
    pet_type: Literal["cat"]
    name: str
    meows: int

class Dog(BaseModel):
    pet_type: Literal["dog"]
    name: str
    barks: int

class Lizard(BaseModel):
    pet_type: Literal["lizard"]
    name: str
    scales: bool

Pet = Union[Cat, Dog, Lizard]

class Person(BaseModel):
    name: str
    pet: Pet = Field(discriminator="pet_type")

person = Person(name="Alice", pet={"pet_type": "cat", "name": "Whiskers", "meows": 5})
```

**How it works:**
- The `discriminator` field (`pet_type`) tells Pydantic which model to instantiate.
- `Literal` types ensure only specific values are accepted.
- Validation errors indicate which union member failed and why.
- JSON Schema includes all possible variants for documentation.

---

## Generic Models

Generic models allow you to create reusable model templates parameterized by type.

```python
from pydantic import BaseModel
from typing import TypeVar, Generic

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    items: list[T]

class User(BaseModel):
    id: int
    name: str

class Product(BaseModel):
    id: int
    price: float

# Create paginated responses for different types
users_page = PaginatedResponse[User](
    total=100, page=1, page_size=10,
    items=[User(id=1, name="Alice"), User(id=2, name="Bob")]
)

products_page = PaginatedResponse[Product](
    total=50, page=1, page_size=10,
    items=[Product(id=1, price=9.99)]
)
```

**Benefits:**
- Type safety: Your IDE knows the exact type of `items`.
- Code reuse: One paginated response model works for any content type.
- JSON Schema: Generated schemas correctly reflect the concrete types used.

---

## Custom Data Types

Pydantic supports custom types for domain-specific validation.

### Custom Types with Schema Customization

```python
from pydantic_core import CoreSchema, core_schema
from pydantic import BaseModel, GetCoreSchemaHandler
from typing import Any

class PhoneNumber(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )

    @classmethod
    def _validate(cls, v: str) -> str:
        if not v.startswith("+"):
            raise ValueError("phone number must start with +")
        if len(v) < 10:
            raise ValueError("phone number too short")
        return v

class User(BaseModel):
    name: str
    phone: PhoneNumber

user = User(name="Alice", phone="+1234567890")
```

### Constrained Types with Annotated

Python 3.9+ `Annotated` allows attaching constraints directly to type hints:

```python
from pydantic import BaseModel, Field
from typing import Annotated

class User(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")]
    age: Annotated[int, Field(gt=0, lt=150)]
    score: Annotated[float, Field(ge=0.0, le=100.0)]
    tags: Annotated[list[str], Field(min_length=1, max_length=10)]
```

---

## JSON Schema Generation

Pydantic automatically generates JSON Schema for your models, which powers FastAPI's interactive documentation and enables API contract validation.

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

schema = User.model_json_schema()
```

### Customizing JSON Schema

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {"id": 1, "name": "Alice", "email": "alice@example.com"}
        ]
    })

    id: int = Field(description="Unique identifier")
    name: str = Field(description="Full name of the user")
    email: str = Field(description="Email address", format="email")
```

---

## Root Models

Root models validate the root type directly, useful for lists or dictionaries that need validation at the top level.

```python
from pydantic import RootModel

class StringList(RootModel[list[str]]):
    pass

class StringDict(RootModel[dict[str, str]]):
    pass

items = StringList.model_validate(["a", "b", "c"])
mapping = StringDict.model_validate({"key": "value"})
```

---

## Secret Types

For sensitive data like passwords and API keys, use `SecretStr` and `SecretBytes` to prevent accidental exposure in logs or serialization.

```python
from pydantic import BaseModel, SecretStr, SecretBytes

class User(BaseModel):
    username: str
    password: SecretStr
    api_key: SecretBytes

user = User(username="alice", password="secret123", api_key=b"mykey")
print(user.model_dump())
# {"username": "alice", "password": "**********", "api_key": "**********"}

# Access the real value when needed
print(user.password.get_secret_value())  # "secret123"
```

**Security best practices:**
- Always use `SecretStr` for passwords and tokens.
- Never log model dumps containing secret fields.
- Use `get_secret_value()` only when necessary (e.g., passing to hashing functions).

---

## Performance and Best Practices

### Performance Tips

Pydantic v2 is significantly faster than v1 due to its Rust core:

1. **Use `model_validate()` for dicts**: More efficient than the constructor for dictionary input.
2. **Use `model_validate_json()` for JSON**: Avoids intermediate dict creation.
3. **Use `frozen=True` for immutable data**: Enables internal caching optimizations.
4. **Minimize validators**: Each validator adds overhead; use type annotations where possible.
5. **Use `slots=True` in ConfigDict**: Reduces memory usage for models with many instances.

### Migration from v1 to v2

| Pydantic v1 | Pydantic v2 |
|-------------|-------------|
| `.dict()` | `.model_dump()` |
| `.json()` | `.model_dump_json()` |
| `.parse_obj()` | `.model_validate()` |
| `.parse_raw()` | `.model_validate_json()` |
| `.schema()` | `.model_json_schema()` |
| `Config` class | `model_config = ConfigDict(...)` |
| `@validator` | `@field_validator` |
| `@root_validator` | `@model_validator` |
| `Optional[T]` | `T \| None` (Python 3.10+) |

---

## Integration with FastAPI

Pydantic is the foundation of FastAPI's request/response handling.

### Request and Response Models

```python
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Annotated

app = FastAPI()

class Item(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: str | None = None
    price: Annotated[float, Field(gt=0)]
    tax: float | None = None

@app.post("/items/")
async def create_item(item: Item):
    return item
```

**What happens automatically:**
- Request body is validated against `Item` model.
- Invalid requests return `422 Unprocessable Entity` with detailed errors.
- Response is serialized to JSON using the model.
- Interactive docs show the model schema.

### Partial Updates with Optional Fields

For `PATCH` operations where only some fields may be updated:

```python
from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    name: str
    email: str
    age: int

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None
```
