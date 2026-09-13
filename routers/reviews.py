from fastapi import APIRouter,Depends,HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models 
import schemas
from security import get_current_user

router = APIRouter(prefix="/products/{product_id}/reviews", tags = ["reviews"])

@router.post("/",response_model = schemas.ReviewResponse,status_code = status.HTTP_201_CREATED)
def create_review(product_id: int, 
        review: schemas.ReviewCreate, 
        db: Session = Depends(get_db),
        current_user : models.Users = Depends(get_current_user)
        ):  
    
    product = db.query(models.Products).filter(models.Products.id == product_id).first()

    if not product:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Product not found")

    orderItem = db.query(models.OrderItem).join(models.Order).filter(
        models.Order.user_id == current_user.id,
        models.Order.status == models.OrderStatus.paid,
        models.OrderItem.product_id == product_id
    ).first()

    if not orderItem:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN, detail = "You are only allowed to review products you have purchased")

    existing_review = db.query(models.Review).filter(
        models.Review.user_id == current_user.id,
        models.Review.product_id == product_id
    ).first()

    if existing_review:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT, detail = "You have already reviewed this product")

    new_review = models.Review(
        user_id = current_user.id,
        product_id = product_id,
        rating = review.rating,
        comment = review.comment
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return new_review

@router.get("/", response_model = list[schemas.ReviewResponse])
def get_reviews(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Products).filter(models.Products.id == product_id).first()
    if not product: 
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Product not found")

    return db.query(models.Review).filter(models.Review.product_id == product_id).all()

