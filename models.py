from sqlalchemy import Integer, String, Column, DateTime,Text, Numeric, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum 

class OrderStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    cancelled = "cancelled"

class Users(Base):
    __tablename__="users"
    id = Column(Integer, primary_key = True, index = True)
    email = Column(String, nullable = False,unique= True, index=True)
    hashed_password = Column(String, nullable = False)
    role = Column(String, nullable = False , default = "user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    orders = relationship("Order", back_populates = "user")


class Products(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key = True, index = True)
    name = Column(String, nullable = False, index = True)
    description = Column(Text, nullable = True)
    price = Column(Numeric(10,2),nullable= False)
    stock = Column(Integer, nullable=False, default = 0)
    created_at = Column(DateTime(timezone=True),server_default=func.now())

class Order(Base):
    __tablename__="orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable = False)
    status = Column(SAEnum(OrderStatus), nullable= False,  default = OrderStatus.pending)
    total_amount = Column(Numeric(10,2), nullable = False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("Users", back_populates = "orders")
    items = relationship("OrderItem", back_populates = "order", cascade = "all, delete-orphan")

class OrderItem(Base):
    __tablename__="orderitems"
    id = Column(Integer, primary_key = True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable = False)
    quantity = Column(Integer, nullable = False)
    price_at_purchase = Column(Numeric(10,2), nullable = False)

    order = relationship("Order", back_populates = "items")
    product = relationship("Products")
    


