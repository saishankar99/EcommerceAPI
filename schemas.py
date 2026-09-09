from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from decimal import Decimal

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    role: str
    class Config:
        from_attributes = True


class Token(BaseModel):

    access_token: str
    token_type: str

class ProductCreate(BaseModel):
    name: str = Field(min_length=1,max_length=255)
    description: str | None  = None
    price: Decimal = Field(gt=0, max_digits=10,decimal_places =2)
    stock: int = Field(ge=0)

class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length =1 , max_length = 255)
    description: str | None = None
    price: Decimal | None = Field(default= None, gt=0, max_digits=10,decimal_places = 2)
    stock: int | None = Field(default=None, ge=0)

class ProductResponse(BaseModel):
    id: int
    name: str
    description: str | None 
    price: Decimal = Field(default= None, gt=0, max_digits=10,decimal_places = 2)
    stock: int
    created_at: datetime

    class Config:
        from_attributes = True

class OrderItemCreate(BaseModel):
    product_id : int 
    quantity: int = Field(gt=0)

class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length = 1)

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    price_at_purchase: Decimal
    class Config: 
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: str
    total_amount: Decimal
    created_at: datetime
    items: list[OrderItemResponse]
    class Config: 
        from_attributes = True
        


