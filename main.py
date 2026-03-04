from ast import List

from fastapi import FastAPI, Depends, Form, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import engine, SessionLocal
import models
from models import Shop, Upload
from schemas import RegisterRequest, LoginRequest
from auth import hash_password, verify_password, create_access_token, oauth2_scheme
from jose import JWTError, jwt
import uuid
from fastapi.responses import RedirectResponse
from datetime import date
import os
from fastapi.middleware.cors import CORSMiddleware
import qrcode
from fastapi.responses import FileResponse

from pydantic import BaseModel, EmailStr, Field


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

from fastapi.staticfiles import StaticFiles

# Create folder first
if not os.path.exists("qrcodes"):
    os.makedirs("qrcodes")

QR_FOLDER = "qrcodes"
os.makedirs(QR_FOLDER, exist_ok=True)

app.mount("/qrcodes", StaticFiles(directory=QR_FOLDER), name="qrcodes")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")
# ======================
# DB Dependency
# ======================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ShopCreate(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)

# ======================
# REGISTER SHOP (JSON BODY)
# ======================

from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import IntegrityError
import uuid
from datetime import date
import qrcode

def generate_qr_image(token: str) -> str:
    # The QR should open your Angular upload page:
    url = f"http://10.149.71.26:8000/upload?token={token}"

    img = qrcode.make(url)
    file_name = f"{token}.png"
    file_path = os.path.join(QR_FOLDER, file_name)
    img.save(file_path)

    return file_name
@app.post("/register")
def register(data: ShopCreate, db: Session = Depends(get_db)):
    # check duplicate email
    existing = db.query(Shop).filter(Shop.email == data.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    qr_token = str(uuid.uuid4())

    shop = Shop(
        name=data.name.strip(),
        email=data.email.strip().lower(),
        password=hash_password(data.password),
        qr_token=qr_token,
        subscription_end_date=date(2099, 1, 1),
        is_active=True
    )

    try:
        db.add(shop)
        db.commit()
        db.refresh(shop)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")

    # return qr image filename if you generate it
    qr_file_name = generate_qr_image(qr_token)
    return {
        "message": "Registered Successfully",
        "qr_token": qr_token,
        "qr_code": qr_file_name
    }

    
    



    # duplicate email check
    existing = db.query(Shop).filter(Shop.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    qr_token = str(uuid.uuid4())

    shop = Shop(
        name=data.name.strip(),
        email=data.email.strip().lower(),
        password=hash_password(data.password),
        qr_token=qr_token,
        subscription_end_date=date(2099,1,1),
        is_active=True
    )

    try:
        db.add(shop)
        db.commit()
        db.refresh(shop)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")

    # ✅ generate QR code image in backend and return filename
    qr_file_name = f"{qr_token}.png"
    # (your QR generate code should create /qrcodes/{qr_file_name})

    return {"message": "Registered Successfully", "qr_token": qr_token, "qr_code": qr_file_name}

    qr_token = str(uuid.uuid4())

    shop = Shop(
        name=data.name,
        email=data.email,
        password=hash_password(data.password),
        qr_token=qr_token,
    is_active=True
    )


    db.add(shop)
    db.commit()

    # Generate QR code
    qr_data = f"http://10.149.71.26:8000/upload?token={qr_token}"
    qr = qrcode.make(qr_data)

    qr_folder = "qrcodes"
    if not os.path.exists(qr_folder):
        os.makedirs(qr_folder)

    qr_path = f"{qr_folder}/{qr_token}.png"
    qr.save(qr_path)

    return {
        "message": "Registered Successfully",
        "qr_image_url": f"http://10.149.71.26:8000/{qr_path}"
    }
# ======================
# LOGIN (JSON BODY)
# ======================


@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    shop = db.query(Shop).filter(Shop.email == data.email).first()

    if not shop or not verify_password(data.password, shop.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(shop.id)})

    return {
        "access_token": token,
        "shop_name": shop.name   # ✅ MUST EXIST
    }

# ======================
# GET CURRENT SHOP
# ======================

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

def get_current_shop(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        shop_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=401, detail="Shop not found")

    return shop


# ======================
# UPLOAD FILE (QR BASED)
# ======================

# DELETE file
@app.delete("/delete-file/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_shop: Shop = Depends(get_current_shop)
):
    file = db.query(Upload).filter(
        Upload.id == file_id,
        Upload.shop_id == current_shop.id
    ).first()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # delete from disk
    import os
    if os.path.exists(file.file_path):
        os.remove(file.file_path)

    db.delete(file)
    db.commit()

    return {"message": "File deleted successfully"}

from fastapi.responses import HTMLResponse

from fastapi.responses import HTMLResponse
from fastapi import Query

@app.get("/upload", response_class=HTMLResponse)
def upload_page(token: str, ok: int = Query(0)):
    success_alert = ""

    if ok == 1:
        success_alert = """
        <div class="alert alert-success alert-dismissible fade show" role="alert">
          ✅ Files uploaded successfully!
          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """

    return f"""
    <!doctype html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
      <title>Upload Files</title>
    </head>
    <body class="bg-light">

      <div class="container py-4">
        <div class="card shadow rounded-4 p-4">
          <h3 class="fw-bold mb-3">📤 Upload Documents</h3>

          {success_alert}

          <form action="/upload-multiple?token={token}" method="post" enctype="multipart/form-data">
            
            <div class="mb-3">
              <label class="form-label fw-semibold">Customer Name</label>
              <input type="text" name="customer_name" class="form-control" required
                     placeholder="Enter customer name" />
            </div>

            <div class="mb-3">
              <label class="form-label fw-semibold">Select Files</label>
              <input type="file" name="files" class="form-control" multiple required />
              <div class="form-text">You can upload multiple files.</div>
            </div>

            <button class="btn btn-success w-100 fw-semibold" type="submit">
              🚀 Upload Files
            </button>

          </form>

        </div>
      </div>

      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
from fastapi import Form, File, UploadFile

from typing import List
from fastapi import UploadFile, File, Form

@app.post("/upload-multiple")
async def upload_multiple(
    token: str,
    customer_name: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    shop = db.query(Shop).filter(Shop.qr_token == token).first()
    if not shop:
        return {"detail": "Invalid QR"}

    import os, uuid
    os.makedirs("uploads", exist_ok=True)

    for file in files:
        unique_name = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join("uploads", unique_name)

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        upload = Upload(
            file_name=file.filename,
            file_path=file_path,
            shop_id=shop.id,
            customer_name=customer_name
        )
        db.add(upload)

    db.commit()

    # ✅ redirect back to upload page with success flag
    return RedirectResponse(
        url=f"/upload?token={token}&ok=1",
        status_code=303
    )
from typing import List
from schemas import UploadOut

@app.get("/my-files", response_model=list[UploadOut])
def my_files(current_shop: Shop = Depends(get_current_shop), db: Session = Depends(get_db)):
    return db.query(Upload).filter(Upload.shop_id == current_shop.id).order_by(Upload.id.desc()).all()

import qrcode

def generate_qr_image(token: str) -> str:
    # The QR should open your Angular upload page:
    url = f"http://10.149.71.26:8000/upload?token={token}"

    img = qrcode.make(url)
    file_name = f"{token}.png"
    file_path = os.path.join(QR_FOLDER, file_name)
    img.save(file_path)

    return file_name