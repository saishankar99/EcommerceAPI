from fastapi import APIRouter, HTTPException, status, Depends
import schemas
from sqlalchemy.orm import Session
import models
from security import hash_password,verify_password,create_access_token,get_current_user,require_admin
from fastapi.security import OAuth2PasswordRequestForm 
from database import get_db

router=APIRouter(prefix="/users", tags= ["users"])

@router.post("/register", status_code=status.HTTP_201_CREATED,response_model = schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Users).filter(models.Users.email == user.email).first()

    if existing is not None:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT, detail = "Email already registered")

    new_user = models.Users(email = user.email, hashed_password = hash_password(user.password))

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model = schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Users).filter(models.Users.email==form_data.username).first()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail = "Invalid login credentials ")

    access_token = create_access_token(data={"sub": user.email})

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me",response_model = schemas.UserResponse)
def readme(user: models.Users = Depends(get_current_user)):
    return user

@router.get("/admin-check")
def admin_check(current_user: models.Users = Depends(require_admin)):
    return {"message": f"Welcome admin {current_user.email}"}
