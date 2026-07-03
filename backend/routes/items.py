from fastapi import APIRouter

import dynamodb_items
from models import Item

router = APIRouter(prefix="/items", tags=["items"])


@router.get("")
def get_all():
    return dynamodb_items.list_items()


@router.post("")
def create_item(item: Item):
    return dynamodb_items.create_item(name=item.name, description=item.description)


@router.get("/{item_id}")
def get_one(item_id: str):
    item = dynamodb_items.get_item(item_id)
    if item:
        return item
    return {"message": f"Item with name {item_id} not found."}


@router.put("/{item_id}")
def update_item(item_id: str, updated_item: Item):
    return dynamodb_items.update_item(name=item_id, description=updated_item.description)


@router.delete("/{item_id}")
def delete_item(item_id: str):
    deleted_item = dynamodb_items.delete_item(item_id)
    return {"message": f"Item with name {deleted_item['name']} deleted."}
