from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import auth, models, schemas
from .consul_registration import deregister as consul_deregister
from .consul_registration import register as consul_register
from .database import Base, engine, get_db
from .observability import CorrelationIdMiddleware, logger

Base.metadata.create_all(bind=engine)

app = FastAPI(title="users-svc")
app.add_middleware(CorrelationIdMiddleware)


@app.on_event("startup")
def on_startup():
    consul_register()


@app.on_event("shutdown")
def on_shutdown():
    consul_deregister()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="database not ready")


@app.post("/register", response_model=schemas.UserOut, status_code=201)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="email already registered")

    user = models.User(
        email=payload.email,
        name=payload.name,
        hashed_password=auth.hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("user_registered", user_id=user.id)
    return user


@app.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not auth.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="invalid credentials")

    token = auth.create_access_token(user.id, user.email)
    logger.info("user_logged_in", user_id=user.id)
    return schemas.TokenOut(access_token=token)


@app.get("/users/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return user
