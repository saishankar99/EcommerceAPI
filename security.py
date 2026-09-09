from datetime import datetime, timezone, timedelta
from config import settings
from jose import jwt,JWTError
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends,HTTPException, status
from database import get_db
from sqlalchemy.orm import Session
import models 

def create_access_token(data: dict) -> str: 
    to_encode = data.copy()
    expiry = datetime.now(timezone.utc)+timedelta(minutes=settings.access_token_expiry_minutes)
    to_encode.update({"exp":expiry})
    return jwt.encode(to_encode,key=settings.secret_key,algorithm=settings.algorithm)

pwd_context = CryptContext(schemes = ["bcrypt"], deprecated = "auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain,hashed)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = 'users/login')

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.Users:
    credential_exception = HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail = "Could not validate credentials", headers = {"WWW-Authenticate":"Bearer"})

    try: 
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email = payload.get("sub")
        if email is None:
            raise credential_exception
    except JWTError:
        raise credential_exception

    User = db.query(models.Users).filter(models.Users.email == email).first()
    if User is None:
        raise credential_exception
    return User

def require_admin(current_user: models.Users = Depends(get_current_user)) -> models.Users:
    if current_user.role!="admin":
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN, detail = "Admin access required")
    return current_user
    
    
    