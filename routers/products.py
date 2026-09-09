from fastapi import APIRouter, HTTPException, status, Depends
import schemas
from sqlalchemy.orm import Session
from database import get_db
import models
from security import require_admin

router = APIRouter(prefix="/products",tags=["products"])

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
    return new_product

@router.get("/",response_model = list[schemas.ProductResponse])
def get_products(db: Session = Depends(get_db)):
    return db.query(models.Products).all()

@router.get("/{product_id}", response_model = schemas.ProductResponse)
def get_product(product_id : int , db: Session = Depends(get_db)):
    product = db.query(models.Products).filter(models.Products.id==product_id).first()
    if product is None:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Product not found")
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
    return product

@router.delete("/{product_id}",status_code = status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int , db: Session = Depends(get_db), current_user: models.Users = Depends(require_admin)):
    product = db.query(models.Products).filter(models.Products.id==product_id).first()
    if product is None:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Product not found")
    db.delete(product)
    db.commit()
    
