from fastapi import APIRouter, HTTPException, Depends,Request, status, BackgroundTasks
from sqlalchemy.orm import Session
import stripe
from config import settings
import models 
from database import get_db
import schemas
from cache import redis_client
from notifications import send_order_confirmation

router = APIRouter(prefix = "/payments", tags = ["payments"])

@router.post("/webhook",status_code = status.HTTP_200_OK)
async def webhook(request: Request, background_tasks: BackgroundTasks ,db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail = f"Invalid payload: {e}")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail = f"Invalid signature: {e}")

    if event["type"]=="payment_intent.succeeded":
        intent = event["data"]["object"]
        order_id = intent["metadata"].get("order_id")
        if order_id:
            order = db.query(models.Order).filter(models.Order.id == order_id).first()
            if order and order.status == models.OrderStatus.pending:
                order.status = models.OrderStatus.paid
                db.commit()
                email = order.user.email
                background_tasks.add_task(send_order_confirmation, email, order.id)
    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        order_id = intent['metadata'].get("order_id")
        if order_id:
            order = db.query(models.Order).filter(models.Order.id == order_id).first()
            if order and order.status == models.OrderStatus.pending:
                for item in order.items:
                    item.product.stock += item.quantity
                order.status = models.OrderStatus.cancelled
                db.commit()
                try:
                    for item in order.items:
                        redis_client.delete(f"products:{item.product_id}")
                    redis_client.delete(f"products:all")
                except Exception:
                    print("Failed to clear cache for order items")
    return {"status": "success"}