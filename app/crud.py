from sqlalchemy.orm import Session

from . import models, schemas


def get_user(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.User):
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_predictions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Prediction).offset(skip).limit(limit).all()


def create_prediction(db: Session, prediction: schemas.PredictionCreate, username: str):
    db_prediction = models.Prediction(**prediction.dict(), requester_username=username)
    db.add(db_prediction)
    db.commit()
    db.refresh(db_prediction)
    return db_prediction


def get_user_credits(db: Session, username: str):
    return db.query(models.Credits).filter(models.Credits.owner_username == username).first()


def change_user_credits(db: Session, credits: schemas.Credits, username: str):
    db_credits = db.query(models.Credits).filter(models.Credits.owner_username == username).first()
    db_credits.amount = credits.amount
    db.commit()
    db.refresh(db_credits)
    return db_credits
