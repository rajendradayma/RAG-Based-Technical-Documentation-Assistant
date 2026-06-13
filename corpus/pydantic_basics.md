Pydantic Complete Guide — From Basics to Advanced
Pydantic is the most widely used data validation library for Python. It uses Python type hints to validate, serialize, and document data. Pydantic v2 (released 2023) is written in Rust and is 5-50x faster than v1.
1. Defining a Model
Models are defined by inheriting from BaseModel:
Python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str
    age: int | None = None
Fields without a default value are required. Fields with a default value (like age above) are optional.
Default Values and Factories
Python
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class User(BaseModel):
    id: int
    name: str = "Anonymous"
    created_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)
Use Field(default_factory=...) for mutable defaults (lists, dicts) to avoid the common Python pitfall of shared references.
2. Validation
Pydantic automatically validates data when you create a model instance:
Python
user = User(id=1, name="Alice", email="alice@example.com")
If data doesn't match expected types, Pydantic raises a ValidationError with detailed information about what went wrong, including field name and error type.
Strict vs Lax Validation
Python
from pydantic import BaseModel

class Model(BaseModel):
    value: int

# Lax mode (default): coerces "123" -> 123
m = Model(value="123")

# Strict mode: raises error for "123"
from pydantic import Strict
class StrictModel(BaseModel):
    value: Strict[int]
Model Validation from Dictionaries
Python
data = {"id": 1, "name": "Alice", "email": "alice@example.com"}
user = User.model_validate(data)
Validation from JSON
Python
json_str = '{"id": 1, "name": "Alice", "email": "alice@example.com"}'
user = User.model_validate_json(json_str)
3. Type Coercion
Pydantic attempts to coerce values to the declared type where possible:
Python
from pydantic import BaseModel

class CoerceExample(BaseModel):
    int_field: int
    float_field: float
    bool_field: bool
    str_field: str

m = CoerceExample(
    int_field="42",      # str -> int: 42
    float_field="3.14",  # str -> float: 3.14
    bool_field=1,        # int -> bool: True
    str_field=123,       # int -> str: "123"
)
This behavior can be controlled using strict mode in Pydantic v2 or the Strict types.
4. Nested Models
Models can contain other models as fields:
Python
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
Deeply Nested Validation
Python
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
5. Field Validators (Pydantic v2)
Custom validation logic using the @field_validator decorator:
Python
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
Mode='before' and Mode='after'
Python
from pydantic import BaseModel, field_validator

class Model(BaseModel):
    value: int

    @field_validator("value", mode="before")
    @classmethod
    def coerce_string(cls, v):
        if isinstance(v, str) and v.startswith("0x"):
            return int(v, 16)
        return v

    @field_validator("value", mode="after")
    @classmethod
    def double_it(cls, v):
        return v * 2
Multiple Field Validation
Python
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
6. Model Validators
Validate the entire model after all fields are set:
Python
from pydantic import BaseModel, model_validator

class Rectangle(BaseModel):
    width: float
    height: float

    @model_validator(mode="after")
    def check_dimensions(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("dimensions must be positive")
        return self

    @model_validator(mode="before")
    @classmethod
    def set_square_if_single_value(cls, data):
        if isinstance(data, dict) and "size" in data and "width" not in data:
            data["width"] = data["height"] = data.pop("size")
        return data
7. Serialization
Convert models to dictionaries or JSON:
Python
user = User(id=1, name="Alice", email="alice@example.com", age=30)

user.model_dump()        # returns a dict
user.model_dump_json()   # returns a JSON string
Serialization Options
Python
# Exclude fields
user.model_dump(exclude={"age"})

# Include only specific fields
user.model_dump(include={"name", "email"})

# Exclude unset fields
user.model_dump(exclude_unset=True)

# Exclude None values
user.model_dump(exclude_none=True)

# Custom mode: json-compatible dict
user.model_dump(mode="json")
Custom JSON Encoders
Python
from datetime import datetime
from pydantic import BaseModel

class Event(BaseModel):
    name: str
    timestamp: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
8. Configuration with model_config
Model behavior is configured using model_config (Pydantic v2) or Config class (v1):
Python
from pydantic import BaseModel, ConfigDict

class User(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        str_to_lower=True,
        validate_assignment=True,
        extra="forbid",           # "ignore", "allow", "forbid"
        frozen=False,             # True makes model immutable
        populate_by_name=True,    # Allow field aliases
        use_enum_values=True,
    )

    name: str
    email: str
Common Config Options
Table
Option	Description
str_strip_whitespace	Strip leading/trailing whitespace from strings
str_to_lower / str_to_upper	Convert strings to lower/upper case
validate_assignment	Validate on field assignment
extra	Handle extra fields: ignore, allow, forbid
frozen	Make model immutable
populate_by_name	Allow using field names as well as aliases
use_enum_values	Use enum values instead of enum instances
json_schema_extra	Add extra JSON schema metadata
9. Aliases
Map field names to different external names:
Python
from pydantic import BaseModel, Field

class User(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(alias="userName")
    email: str = Field(alias="emailAddress")
    created_at: str = Field(alias="createdAt")

# Create with aliases
user = User(userName="Alice", emailAddress="alice@example.com")

# Or with field names
user = User(name="Alice", email="alice@example.com")

# Serialization uses aliases
user.model_dump(by_alias=True)
# {"userName": "Alice", "emailAddress": "alice@example.com", "createdAt": None}
10. Computed Fields
Fields that are computed from other fields (Pydantic v2.1+):
Python
from pydantic import BaseModel, computed_field
from typing import List

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
11. Discriminated Unions
Handle multiple model types with a discriminator field:
Python
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
12. Generic Models
Create reusable generic model structures:
Python
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

users_page = PaginatedResponse[User](
    total=100, page=1, page_size=10,
    items=[User(id=1, name="Alice"), User(id=2, name="Bob")]
)

products_page = PaginatedResponse[Product](
    total=50, page=1, page_size=10,
    items=[Product(id=1, price=9.99)]
)
13. Custom Data Types
Custom Types with __get_pydantic_core_schema__
Python
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
Constrained Types
Python
from pydantic import BaseModel, Field
from typing import Annotated

class User(BaseModel):
    # Constrained string
    username: Annotated[str, Field(min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")]

    # Constrained integer
    age: Annotated[int, Field(gt=0, lt=150)]

    # Constrained float
    score: Annotated[float, Field(ge=0.0, le=100.0)]

    # Constrained list
    tags: Annotated[list[str], Field(min_length=1, max_length=10)]
14. JSON Schema Generation
Pydantic automatically generates JSON Schema for your models:
Python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

print(User.model_json_schema())
Customizing JSON Schema
Python
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
15. Root Models
Validate the root type directly:
Python
from pydantic import RootModel

class StringList(RootModel[list[str]]):
    pass

class StringDict(RootModel[dict[str, str]]):
    pass

items = StringList.model_validate(["a", "b", "c"])
mapping = StringDict.model_validate({"key": "value"})
16. Secret Types
Hide sensitive data in serialization:
Python
from pydantic import BaseModel, SecretStr, SecretBytes

class User(BaseModel):
    username: str
    password: SecretStr
    api_key: SecretBytes

user = User(username="alice", password="secret123", api_key=b"mykey")
print(user.model_dump())
# {"username": "alice", "password": "**********", "api_key": "**********"}

# Access the real value
print(user.password.get_secret_value())  # "secret123"
17. Payment Card Numbers (Optional)
Python
from pydantic import BaseModel, PaymentCardNumber

class Payment(BaseModel):
    card_number: PaymentCardNumber
    expiry_month: int
    expiry_year: int
18. Performance and Benchmarking
Pydantic v2 is significantly faster than v1:
Python
from pydantic import BaseModel
import time

class User(BaseModel):
    id: int
    name: str
    email: str

# Benchmark
start = time.time()
for _ in range(100000):
    User(id=1, name="Alice", email="alice@example.com")
print(f"Time: {time.time() - start:.2f}s")
Tips for Better Performance
Use model_validate() instead of constructor for dict input
Use model_validate_json() for JSON strings
Use ser_json_timedelta="iso8601" for consistent JSON
Avoid unnecessary validators
Use frozen=True for immutable models (enables caching)
19. Migration from Pydantic v1 to v2
Key Changes
Table
v1	v2
.dict()	.model_dump()
.json()	.model_dump_json()
.parse_obj()	.model_validate()
.parse_raw()	.model_validate_json()
.schema()	.model_json_schema()
Config class	model_config = ConfigDict(...)
@validator	@field_validator
@root_validator	@model_validator
Field(...)	Field(...) mostly same
Optional[T]	`T	None` (Python 3.10+)
Example Migration
Python
# v1 style
from pydantic import BaseModel, validator

class UserV1(BaseModel):
    name: str
    age: int

    class Config:
        validate_assignment = True

    @validator("age")
    def check_age(cls, v):
        if v < 0:
            raise ValueError("age must be positive")
        return v

# v2 style
from pydantic import BaseModel, field_validator, ConfigDict

class UserV2(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    name: str
    age: int

    @field_validator("age")
    @classmethod
    def check_age(cls, v):
        if v < 0:
            raise ValueError("age must be positive")
        return v
20. Integration with FastAPI
Pydantic is the data layer of FastAPI:
Python
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

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
Request Body + Path + Query Parameters
Python
from fastapi import FastAPI, Path, Query
from pydantic import BaseModel
from typing import Annotated

app = FastAPI()

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

@app.put("/items/{item_id}")
async def update_item(
    item_id: Annotated[int, Path(title="The ID of the item to get", ge=0, le=1000)],
    q: str | None = None,
    item: Item | None = None,
):
    results = {"item_id": item_id}
    if q:
        results.update({"q": q})
    if item:
        results.update({"item": item})
    return results
21. Advanced Patterns
Partial Models (for PATCH requests)
Python
from pydantic import BaseModel
from typing import Optional
from functools import partial

class User(BaseModel):
    name: str
    email: str
    age: int

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None

# Or using create_model dynamically
from pydantic import create_model

UserPatch = create_model(
    "UserPatch",
    __base__=User,
    name=(Optional[str], None),
    email=(Optional[str], None),
    age=(Optional[int], None),
)
Immutable Models
Python
from pydantic import BaseModel, ConfigDict

class ImmutableUser(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str

user = ImmutableUser(id=1, name="Alice")
# user.name = "Bob"  # Raises: FrozenInstanceError
Model Inheritance
Python
from pydantic import BaseModel

class BaseItem(BaseModel):
    name: str
    price: float

class FoodItem(BaseItem):
    category: str = "food"
    expiration_date: str

class ElectronicItem(BaseItem):
    category: str = "electronics"
    warranty_months: int

food = FoodItem(name="Apple", price=0.5, expiration_date="2024-12-01")
electronic = ElectronicItem(name="Phone", price=999.99, warranty_months=24)
22. Error Handling and ValidationError
Python
from pydantic import BaseModel, ValidationError

class User(BaseModel):
    id: int
    name: str
    email: str

try:
    user = User(id="not_an_int", name="", email="invalid")
except ValidationError as e:
    print(e.errors())
    # List of error dicts with loc, msg, type, input

    # Pretty JSON output
    print(e.json())

    # Human-readable
    print(str(e))
Custom Error Messages
Python
from pydantic import BaseModel, field_validator

class User(BaseModel):
    name: str
    age: int

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if len(v) < 2:
            raise ValueError("name must be at least 2 characters long")
        return v
