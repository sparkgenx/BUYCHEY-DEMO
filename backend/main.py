from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl
from typing import Literal, Optional
import json
import os
from datetime import datetime

app = FastAPI(title="BuyChey API - by SparkGenX")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = os.path.join(os.path.dirname(__file__), "database.json")


def read_db():
    if not os.path.exists(DB_FILE):
        return {
            "vendors": [],
            "categories": [],
            "products": [],
            "orders": []
        }

    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def write_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class VendorLogin(BaseModel):
    username: str
    password: str


class Product(BaseModel):
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    price: float = Field(gt=0)
    description: str = Field(min_length=1)
    image_url: HttpUrl
    qr_code_url: HttpUrl
    vendor_id: int = Field(gt=0)


class ProductUpdate(BaseModel):
    product_id: int = Field(gt=0)
    name: Optional[str] = Field(default=None, min_length=1)
    category: Optional[str] = Field(default=None, min_length=1)
    price: Optional[float] = Field(default=None, gt=0)
    description: Optional[str] = Field(default=None, min_length=1)
    image_url: Optional[HttpUrl] = None
    qr_code_url: Optional[HttpUrl] = None


class Order(BaseModel):
    customer_name: str = Field(min_length=1)
    customer_email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    customer_phone: str = Field(min_length=7)
    customer_address: str = Field(min_length=1)
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    payment_method: Literal["qr_code", "cash_on_delivery"]


class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "confirmed", "rejected", "delivered"]


def find_vendor(db, vendor_id: int):
    return next((v for v in db["vendors"] if v["id"] == vendor_id), None)


def find_product(db, product_id: int):
    return next((p for p in db["products"] if p["id"] == product_id), None)


@app.get("/")
def root():
    return {"message": "Welcome to BuyChey API - by SparkGenX"}


@app.get("/products")
def get_products():
    db = read_db()
    return {"products": db["products"]}


@app.get("/products/category/{category}")
def get_products_by_category(category: str):
    db = read_db()

    products = [
        p for p in db["products"]
        if p["category"].lower() == category.lower()
    ]

    return {"products": products}


@app.get("/product/{product_id}")
def get_product(product_id: int):
    db = read_db()

    product = next(
        (p for p in db["products"] if p["id"] == product_id),
        None
    )

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"product": product}


@app.get("/categories")
def get_categories():
    db = read_db()
    return {"categories": db["categories"]}


@app.post("/vendor/login")
def vendor_login(credentials: VendorLogin):
    db = read_db()

    vendor = next(
        (
            v for v in db["vendors"]
            if v["username"] == credentials.username
            and v["password"] == credentials.password
        ),
        None
    )

    if not vendor:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "success": True,
        "vendor": {
            "id": vendor["id"],
            "name": vendor["name"],
            "username": vendor["username"]
        }
    }


@app.post("/product/add")
def add_product(product: Product):
    db = read_db()
    vendor = find_vendor(db, product.vendor_id)

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    new_id = max([p["id"] for p in db["products"]], default=0) + 1

    new_product = {
        "id": new_id,
        "vendor_id": product.vendor_id,
        "name": product.name,
        "category": product.category,
        "price": product.price,
        "description": product.description,
        "image_url": product.image_url,
        "qr_code_url": product.qr_code_url
    }

    db["products"].append(new_product)
    write_db(db)

    return {"success": True, "product": new_product}


@app.put("/product/update")
def update_product(product_update: ProductUpdate):
    db = read_db()

    product = next(
        (p for p in db["products"] if p["id"] == product_update.product_id),
        None
    )

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product_update.name is not None:
        product["name"] = product_update.name

    if product_update.category is not None:
        product["category"] = product_update.category

    if product_update.price is not None:
        product["price"] = product_update.price

    if product_update.description is not None:
        product["description"] = product_update.description

    if product_update.image_url is not None:
        product["image_url"] = product_update.image_url

    if product_update.qr_code_url is not None:
        product["qr_code_url"] = product_update.qr_code_url

    write_db(db)

    return {"success": True, "product": product}


@app.delete("/product/delete/{product_id}")
def delete_product(product_id: int):
    db = read_db()

    product = next(
        (p for p in db["products"] if p["id"] == product_id),
        None
    )

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db["products"] = [
        p for p in db["products"] if p["id"] != product_id
    ]

    write_db(db)

    return {"success": True, "message": "Product deleted"}


@app.post("/order/create")
def create_order(order: Order):
    db = read_db()
    product = find_product(db, order.product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    vendor = find_vendor(db, product["vendor_id"])

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    new_id = max([int(o["id"]) for o in db["orders"]], default=0) + 1

    new_order = {
        "id": str(new_id),
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "customer_phone": order.customer_phone,
        "customer_address": order.customer_address,
        "vendor_id": product["vendor_id"],
        "vendor_name": vendor["name"],
        "product_id": product["id"],
        "product_name": product["name"],
        "product_price": product["price"],
        "quantity": order.quantity,
        "total_amount": product["price"] * order.quantity,
        "payment_method": order.payment_method,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    db["orders"].append(new_order)
    write_db(db)

    return new_order


@app.get("/vendor/orders/{vendor_id}")
def get_vendor_orders(vendor_id: int):
    db = read_db()

    orders = [
        o for o in db["orders"]
        if o["vendor_id"] == vendor_id
    ]

    orders.sort(
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )

    return orders


@app.put("/order/status/{order_id}")
def update_order_status(order_id: str, status_update: OrderStatusUpdate):
    db = read_db()

    order = next(
        (o for o in db["orders"] if str(o["id"]) == str(order_id)),
        None
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order["status"] = status_update.status
    order["updated_at"] = datetime.now().isoformat()

    write_db(db)

    return order


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
