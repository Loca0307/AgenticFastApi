from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import database_models
from database import get_db
from models import Item

router = APIRouter(prefix="/items", tags=["items"])


@router.get("")
def get_all(db: Session = Depends(get_db)):
    return db.query(database_models.Item).all()


@router.post("")
def create_item(item: Item, db: Session = Depends(get_db)):
    db.add(database_models.Item(**item.model_dump()))
    db.commit()
    return item


@router.get("/{item_id}")
def get_one(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(database_models.Item).filter(database_models.Item.id == item_id).first()
    if db_item:
        return db_item
    return {"message": f"Item with id {item_id} not found."}


@router.put("/{item_id}")
def update_item(item_id: int, updated_item: Item, db: Session = Depends(get_db)):
    db_item = db.query(database_models.Item).filter(database_models.Item.id == item_id).first()
    if db_item:
        db_item.name = updated_item.name
        db_item.description = updated_item.description
        db.commit()
        return db_item


@router.delete("/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(database_models.Item).filter(database_models.Item.id == item_id).first()
    if db_item:
        db.delete(db_item)
        db.commit()
        return {"message": f"Item with id {item_id} deleted."}
    return {"message": f"Item with id {item_id} not found."}