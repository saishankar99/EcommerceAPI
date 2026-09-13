from fastapi import FastAPI
from routers import users,products,orders,reviews
import models
from database import engine


# models.Base.metadata.create_all(bind=engine)

app = FastAPI(title = "Ecommerce API")

app.include_router(users.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(reviews.router)


@app.get("/health")
def health():
    return {"status":"ok"}