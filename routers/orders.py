from fastapi import APIRouter,Depends,HTTPException, status
from sqlalchemy.orm import Session
import schemas
from database import get_db
import models 
from security import get_current_user
from decimal import Decimal
from cache import redis_client
import stripe
from config import settings

stripe.api_key = settings.stripe_secret_key

router = APIRouter(prefix = "/orders", tags=["orders"])

@router.post("/", response_model = schemas.OrderResponse, status_code = status.HTTP_201_CREATED)
def create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(get_current_user)
):
    total = Decimal("0")
    order_items=[]
    for item in order.items:
        product = db.query(models.Products).filter(models.Products.id == item.product_id).with_for_update().first()
        if not product:
            raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = f"Product {item.product_id} not found")
        if product.stock<item.quantity:
            raise HTTPException(status_code = status.HTTP_409_CONFLICT, detail = f"Insufficient stock for {product.name}. Available {product.stock}")
        product.stock-=item.quantity
        total+= product.price * item.quantity
        order_items.append(models.OrderItem(
            product_id = item.product_id,
            quantity = item.quantity,
            price_at_purchase = product.price
        ))
    new_order = models.Order(
        user_id = current_user.id,
        total_amount = total,
        items = order_items
    )
    try:
        db.add(new_order)
        db.commit()
    except Exception: 
        db.rollback()
        raise HTTPException(status_code = 500, detail = "Order could not be processed")
    db.refresh(new_order)
    try:
        keys = [f"products:{item.product_id}" for item in order.items]
        keys.append("products:all")
        redis_client.delete(*keys)
    except Exception:
        pass # stale stock self-heals at TTL if Redis is down
    return new_order

@router.get("/", response_model = list[schemas.OrderResponse])
def list_my_orders(db: Session = Depends(get_db), current_user: models.Users = Depends(get_current_user)):
    return db.query(models.Order).filter(models.Order.user_id == current_user.id).all()

@router.get("/{order_id}", response_model = schemas.OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: models.Users = Depends(get_current_user)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail= f"Order not found")

    if order.user_id != current_user.id and current_user.role!="admin":
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN, detail = f"You are not authorized to view this order")

    return order

@router.post("/{order_id}/pay",response_model=schemas.PaymentIntentResponse)
def pay_order(order_id: int, db: Session = Depends(get_db), current_user: models.Users = Depends(get_current_user)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = f"Order not found")

    if order.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN, detail = f"You are not authorized to pay for this order")

    if order.status != models.OrderStatus.pending:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT, detail = f"Order cannot be paid as it is not pending")

    amount = int(order.total_amount * 100)

    try:
        intent = stripe.PaymentIntent.create(amount=amount, currency = "usd", automatic_payment_methods={
        "enabled": True,
        "allow_redirects": "never"
    }, metadata={"order_id": order.id})
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code = status.HTTP_502_BAD_GATEWAY, detail = f"Payment gateway error")

    order.payment_intent_id = intent.id
    db.commit()
    return {"client_secret": intent.client_secret}
    
    
    