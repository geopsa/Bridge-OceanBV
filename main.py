
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from database import engine, SessionLocal, get_db, Base
from models import JobListing
import re
import time

from sqlalchemy.exc import IntegrityError

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)

SECRET_KEY = "f8d9a3b2c5e7d1f4a9b8c3e2d5f6a7b8"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 240

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def is_valid_email(email: str) -> bool:
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(email_pattern, email))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

from fastapi import Query






@app.get("/", response_class=HTMLResponse)
async def read_root(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50)
):
    token = request.cookies.get("access_token")
    username = None
    is_admin = False
    if token:
        try:
            username = verify_token(token)
            user = db.execute(
                text("SELECT admin FROM users WHERE username = :username"),
                {"username": username}
            ).fetchone()
            is_admin = user.admin == 1 if user else False
        except:
            pass
    offset = (page - 1) * per_page
    jobs = db.query(JobListing).offset(offset).limit(per_page).all()
    total_jobs = db.query(JobListing).count()
    for job in jobs:
        job.time_publication = datetime.fromtimestamp(job.time_publication).strftime('%d %b %Y')
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "username": username,
            "jobs": jobs,
            "is_admin": is_admin,
            "page": page,
            "per_page": per_page,
            "total_jobs": total_jobs
        }
    )





@app.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    hashed_password = pwd_context.hash(password)

    existing_user = db.execute(
        text("SELECT * FROM users WHERE username = :username OR email = :email"),
        {"username": username, "email": email}
    ).fetchone()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    try:
        db.execute(
            text("INSERT INTO users (username, password, email, admin) VALUES (:username, :password, :email, 0)"),
            {"username": username, "password": hashed_password, "email": email}
        )
        db.commit()
        return RedirectResponse(url="/login", status_code=303)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error: username or email already exists")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving user: {str(e)}")
    



@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.execute(
        text("SELECT * FROM users WHERE username = :username"),
        {"username": username}
    ).fetchone()
    if not user or not pwd_context.verify(password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": username})
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/logout", response_class=HTMLResponse)
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response

@app.get("/protected", response_class=HTMLResponse)
async def protected_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    username = verify_token(token)
    user = db.execute(
        text("SELECT admin FROM users WHERE username = :username"),
        {"username": username}
    ).fetchone()
    if not user or user.admin != 1:
        raise HTTPException(status_code=403, detail="Access denied: Admins only")
    return templates.TemplateResponse("index.html", {"request": request, "username": username})









@app.post("/favorite/{job_id}")
async def toggle_favorite(job_id: int, request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    username = verify_token(token)
    user = db.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username}
    ).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    favorite = db.execute(
        text("SELECT * FROM user_favorites WHERE user_id = :user_id AND job_id = :job_id"),
        {"user_id": user.id, "job_id": job_id}
    ).fetchone()
    
    if favorite:
        db.execute(
            text("DELETE FROM user_favorites WHERE user_id = :user_id AND job_id = :job_id"),
            {"user_id": user.id, "job_id": job_id}
        )
        db.commit()
        return {"message": "Removed from favorites"}
    else:
        db.execute(
            text("INSERT INTO user_favorites (user_id, job_id) VALUES (:user_id, :job_id)"),
            {"user_id": user.id, "job_id": job_id}
        )
        db.commit()
        return {"message": "Added to favorites"}







@app.get("/job/{job_id}", response_class=HTMLResponse)
async def job_detail(request: Request, job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return templates.TemplateResponse("job_detail.html", {"request": request, "job": job})







from fastapi import File, UploadFile

@app.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    # Пример: сохранить файл на сервере
    with open(f"uploads/{file.filename}", "wb") as f:
        f.write(file.file.read())
    return {"filename": file.filename}









# Страница добавления вакансии (только для админов)
@app.get("/add_job", response_class=HTMLResponse)
async def add_job_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    username = verify_token(token)
    user = db.execute(
        text("SELECT admin FROM users WHERE username = :username"),
        {"username": username}
    ).fetchone()
    if not user or user.admin != 1:
        raise HTTPException(status_code=403, detail="Access denied: Admins only")
    return templates.TemplateResponse("add_job.html", {"request": request})

# Обработка добавления вакансии
@app.post("/add_job", response_class=HTMLResponse)
async def add_job(
    request: Request,
    job_name: str = Form(...),
    description: str = Form(...),
    location: str = Form(...),
    busy: str = Form(...),
    how_many_people: int = Form(...),
    salary: str = Form(...),
    favorites: str = Form(...),
    question: str = Form(...),
    db: Session = Depends(get_db)
):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    username = verify_token(token)
    user = db.execute(
        text("SELECT admin FROM users WHERE username = :username"),
        {"username": username}
    ).fetchone()
    if not user or user.admin != 1:
        raise HTTPException(status_code=403, detail="Access denied: Admins only")

    # Автоматическая дата в формате Unix timestamp
    time_publication = int(time.time())

    try:
        db.execute(
            text("""
                INSERT INTO job_listing (job_name, description, location, busy, time_publication, how_many_people, salary, favorites, question)
                VALUES (:job_name, :description, :location, :busy, :time_publication, :how_many_people, :salary, :favorites, :question)
            """),
            {
                "job_name": job_name,
                "description": description,
                "location": location,
                "busy": busy,
                "time_publication": time_publication,
                "how_many_people": how_many_people,
                "salary": salary,
                "favorites": favorites,
                "question": question
            }
        )
        db.commit()
        return RedirectResponse(url="/", status_code=303)
    except:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error adding job")
    


    