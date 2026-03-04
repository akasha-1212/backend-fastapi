from sqlalchemy import Column, Integer, String, Boolean,Date, DateTime, ForeignKey
from database import Base
from sqlalchemy.sql import func

class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(100), unique=True)
    password = Column(String(255))
    qr_token = Column(String(100), unique=True)
    subscription_end_date = Column(Date)
    is_active = Column(Boolean, default=True)

class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)

    customer_name = Column(String(100), nullable=False)   # ✅ NEW
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now()) 
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True)
    shop_id = Column(Integer, ForeignKey("shops.id"))
    file_name = Column(String(255))
    file_path = Column(String(255))