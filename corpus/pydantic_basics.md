# Pydantic Basics

Pydantic is a data validation library for Python that uses Python type annotations to validate, serialize, and document data.

## Defining a Model

Models are defined by inheriting from `BaseModel`:

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str
    age: int | None = None
```

Fields without a default value are required. Fields with a default value (like `age` above) are optional.

## Validation

Pydantic automatically validates data when you create a model instance:

```python
user = User(id=1, name="Alice", email="alice@example.com")
```

If the data doesn't match the expected types, Pydantic raises a `ValidationError` with details about what went wrong, including the field name and the type of error.

## Type Coercion

Pydantic will attempt to coerce values to the declared type where possible. For example, the string `"123"` passed to an `int` field will be converted to the integer `123`. This behavior can be controlled using strict mode in Pydantic v2.

## Nested Models

Models can contain other models as fields:

```python
class Address(BaseModel):
    street: str
    city: str

class User(BaseModel):
    id: int
    name: str
    address: Address
```

## Field Validators

Custom validation logic can be added using the `field_validator` decorator (Pydantic v2):

```python
from pydantic import field_validator

class User(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("name must not be empty")
        return v
```

## Serialization

Models can be converted to dictionaries or JSON:

```python
user.model_dump()        # returns a dict
user.model_dump_json()   # returns a JSON string
```

## Default Factories

For mutable default values like lists or dicts, use `Field` with `default_factory`:

```python
from pydantic import Field

class User(BaseModel):
    tags: list[str] = Field(default_factory=list)
```

This avoids the common Python pitfall of sharing mutable default arguments across instances.

## Configuration

Model behavior can be configured using `model_config`:

```python
class User(BaseModel):
    model_config = {"str_strip_whitespace": True}
    name: str
```

This automatically strips leading and trailing whitespace from string fields.
