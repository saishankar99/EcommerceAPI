import logging
import time
logger = logging.getLogger("uvicorn.error")
def send_order_confirmation(email: str, order_id: int):
    #No real email sending implemented, just simulating the delay
    print(f"Confirmation for order {order_id} sent to {email}")
    logger.info(f"Confirmation for order {order_id} sent to {email}")
    time.sleep(2)

