from fastapi import FastAPI
from routers import users,products,orders
import models
from database import engine


# models.Base.metadata.create_all(bind=engine)

app = FastAPI(title = "Ecommerce API")

app.include_router(users.router)
app.include_router(products.router)
app.include_router(orders.router)

@app.get("/health")
def health():
    return {"status":"ok"}