"""
視聴記録 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import Record, Movie, ViewingMethod, Mood
from pydantic import BaseModel, root_validator, validator
from typing import List, Optional
from datetime import datetime

router = APIRouter()

class RecordCreate(BaseModel):
    movie_id: int
    viewed_date: datetime
    viewing_method: ViewingMethod
    rating: Optional[float] = None
    mood: Optional[Mood] = None
    comment: Optional[str] = None

    @validator("rating")
    def validate_rating(cls, value):
        if value is not None and not (0.0 <= value <= 5.0):
            raise ValueError("rating must be between 0.0 and 5.0")
        return value

class RecordUpdate(BaseModel):
    viewed_date: Optional[datetime] = None
    viewing_method: Optional[ViewingMethod] = None
    rating: Optional[float] = None
    mood: Optional[Mood] = None
    comment: Optional[str] = None

    @validator("rating")
    def validate_rating(cls, value):
        if value is not None and not (0.0 <= value <= 5.0):
            raise ValueError("rating must be between 0.0 and 5.0")
        return value

    @root_validator(pre=True)
    def validate_any_field_present(cls, values):
        if not values:
            raise ValueError("at least one field must be provided")
        return values

class RecordResponse(BaseModel):
    id: int
    movie_id: int
    viewed_date: datetime
    viewing_method: ViewingMethod
    rating: Optional[float]
    mood: Optional[Mood]
    comment: Optional[str]
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[RecordResponse])
async def list_records(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """全記録取得"""
    records = db.query(Record).offset(skip).limit(limit).all()
    return records

@router.post("/", response_model=RecordResponse)
async def create_record(record: RecordCreate, db: Session = Depends(get_db)):
    """記録作成"""
    # 映画の存在確認
    movie = db.query(Movie).filter(Movie.id == record.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="映画が見つかりません")
    
    db_record = Record(**record.dict())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

@router.get("/{record_id}", response_model=RecordResponse)
async def get_record(record_id: int, db: Session = Depends(get_db)):
    """記録詳細取得"""
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="記録が見つかりません")
    return record

@router.delete("/{record_id}")
async def delete_record(record_id: int, db: Session = Depends(get_db)):
    """記録削除"""
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="記録が見つかりません")
    db.delete(record)
    db.commit()
    return {"message": "削除しました"}

@router.patch("/{record_id}", response_model=RecordResponse)
async def update_record(record_id: int, payload: RecordUpdate, db: Session = Depends(get_db)):
    """記録更新"""
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="記録が見つかりません")

    updates = payload.dict(exclude_unset=True)
    for key, value in updates.items():
        setattr(record, key, value)

    db.commit()
    db.refresh(record)
    return record
