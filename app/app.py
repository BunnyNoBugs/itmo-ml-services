from datetime import datetime, timedelta, timezone
from typing import Union, List

from fastapi import Depends, FastAPI, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing_extensions import Annotated
from dotenv import load_dotenv
import os
from sqlalchemy.orm import Session
import yaml

from . import crud, models, schemas
from .database import SessionLocal, engine

from io import StringIO
import pandas as pd

from ml.model import load_model

load_dotenv()

models.Base.metadata.create_all(bind=engine)

# load config file
with open('config.yaml') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

SECRET_KEY = os.environ.get('SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# create a route
@app.get("/")
def index():
    return {"text": "Software classification"}


@app.on_event("startup")
def startup_event():
    global model, model_type
    model_type = 'lr'
    model = load_model(model_type)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str, db: Session = Depends(get_db)):
    user = crud.get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = crud.get_user(db, token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
        current_user: Annotated[schemas.User, Depends(get_current_user)]
):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# todo: response models

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    user = models.User(username=user.username, email=user.email, hashed_password=hashed_password)
    crud.create_user(db=db, user=user)
    crud.create_user_credits(db=db, credits=schemas.Credits(amount=config['starting_credits']), username=user.username)
    return user


@app.post("/token")
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)
) -> schemas.Token:
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return schemas.Token(access_token=access_token, token_type="bearer")


@app.post("/predict")
async def predict(current_user: Annotated[schemas.User, Depends(get_current_active_user)],
                  file: UploadFile = File(...), requested_model_type: str = 'lr', db: Session = Depends(get_db)):
    contents = await file.read()
    input_df = pd.read_csv(StringIO(contents.decode()))

    global model, model_type
    if requested_model_type != model_type:
        model_type = requested_model_type
        model = load_model(model_type)

    model_price = config['models_pricing'][model_type]
    user_credits = crud.get_user_credits(db=db, username=current_user.username)
    if user_credits.amount < model_price:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Not enough credits. {model_price} credits are required, you have {user_credits.amount}."
        )
    else:
        pred_result = model.predict(input_df)
        prediction = schemas.PredictionCreate(model_type=model_type, datetime=datetime.now(timezone.utc))
        crud.create_prediction(db=db, prediction=prediction, username=current_user.username)
        crud.change_user_credits(db=db, credits=schemas.Credits(amount=user_credits.amount - model_price),
                                 username=current_user.username)
        return {'pred_result': pred_result.tolist()}
