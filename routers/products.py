from fastapi import APIRouter, HTTPException, status, Depends
import schemas
from sqlalchemy.orm import Session
from database import get_db
import models
from security import require_admin
from cache import redis_client
from pydantic import TypeAdapter

router = APIRouter(prefix="/products",tags=["products"])

PRODUCTS_ALL_KEY = "products:all"
CACHE_TTL = 300 #seconds; safety-net expiry even with invalidation

product_list_adapter = TypeAdapter(list[schemas.ProductResponse])

def product_key(product_id: int) -> str:
    return f"products:{product_id}"

def invalidate(*keys: str) -> None:
    try:
        redis_client.delete(*keys)
    except Exception:
        pass 

@router.post("/",status_code=status.HTTP_201_CREATED,response_model=schemas.ProductResponse)
def create_product(product: schemas.ProductCreate,db: Session = Depends(get_db),current_user: models.Users = Depends(require_admin)):
    new_product = models.Products(
        name = product.name,
        description = product.description,
        price = product.price,
        stock = product.stock
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    invalidate(PRODUCTS_ALL_KEY)
    return new_product

@router.get("/",response_model = list[schemas.ProductResponse])
def get_products(db: Session = Depends(get_db)):
    try:
        cached = redis_client.get(PRODUCTS_ALL_KEY)
    except Exception:
        cached = None
    if cached:
        return product_list_adapter.validate_json(cached)
    
    products = db.query(models.Products).all()
    validated = [schemas.ProductResponse.model_validate(p) for p in products]
    try:
        redis_client.setex(PRODUCTS_ALL_KEY, CACHE_TTL, product_list_adapter.dump_json(validated))
    except Exception:
        pass
    return validated
    # return db.query(models.Products).all()

@router.get("/{product_id}", response_model = schemas.ProductResponse)
def get_product(product_id : int , db: Session = Depends(get_db)):
    key = product_key(product_id)
    try: 
        cached = redis_client.get(key)
    except Exception:
        cached = None
    if cached:
        return schemas.ProductResponse.model_validate_json(cached)

    product = db.query(models.Products).filter(models.Products.id==product_id).first()
    if product is None:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Product not found")
    try: 
        redis_client.setex(key, CACHE_TTL, schemas.ProductResponse.model_validate(product).model_dump_json())
    except Exception:
        pass
    return product

@router.patch("/{product_id}", response_model = schemas.ProductResponse)
def update_product(product_id: int,product_update: schemas.ProductUpdate, db: Session = Depends(get_db), current_user: models.Users = Depends(require_admin)):
    product=db.query(models.Products).filter(models.Products.id==product_id).first()
    if product is None:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Product not found")
    update_data = product_update.model_dump(exclude_unset=True)
    for key,value in update_data.items():
        setattr(product,key,value)
    db.commit()
    db.refresh(product)
    invalidate(product_key(product_id), PRODUCTS_ALL_KEY)
    return product

@router.delete("/{product_id}",status_code = status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int , db: Session = Depends(get_db), current_user: models.Users = Depends(require_admin)):
    product = db.query(models.Products).filter(models.Products.id==product_id).first()
    if product is None:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Product not found")
    db.delete(product)
    db.commit()
    invalidate(product_key(product_id), PRODUCTS_ALL_KEY)
