import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError


TABLE_NAME = os.getenv("DYNAMODB_TABLE", "FastApiDb")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def get_items_table():
    """Create a DynamoDB table resource."""

    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(TABLE_NAME)


def list_items() -> list[dict]:
    """Read all items from DynamoDB."""

    response = get_items_table().scan()
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = get_items_table().scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    return [
        {
            "name": item["name"],
            "description": item.get("description", ""),
        }
        for item in items
    ]


def create_item(name: str, description: str = "") -> dict:
    """Create or replace one item in DynamoDB."""

    item = {
        "name": name,
        "description": description or "",
    }
    get_items_table().put_item(Item=item)
    return item


def get_item(name: str) -> Optional[dict]:
    """Read one item by name from DynamoDB."""

    response = get_items_table().get_item(Key={"name": name})
    item = response.get("Item")
    if not item:
        return None

    return {
        "name": item["name"],
        "description": item.get("description", ""),
    }


def update_item(name: str, description: str = "") -> dict:
    """Update one item's description in DynamoDB."""

    try:
        response = get_items_table().update_item(
            Key={"name": name},
            UpdateExpression="SET description = :description",
            ConditionExpression="attribute_exists(#name)",
            ExpressionAttributeNames={"#name": "name"},
            ExpressionAttributeValues={":description": description or ""},
            ReturnValues="ALL_NEW",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValueError(f"Item with name '{name}' not found in DynamoDB.") from error
        raise

    item = response["Attributes"]
    return {
        "name": item["name"],
        "description": item.get("description", ""),
    }


def delete_item(name: str) -> dict:
    """Delete one item from DynamoDB."""

    try:
        response = get_items_table().delete_item(
            Key={"name": name},
            ConditionExpression="attribute_exists(#name)",
            ExpressionAttributeNames={"#name": "name"},
            ReturnValues="ALL_OLD",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValueError(f"Item with name '{name}' not found in DynamoDB.") from error
        raise

    item = response["Attributes"]
    return {
        "name": item["name"],
        "description": item.get("description", ""),
    }
