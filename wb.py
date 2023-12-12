import logger
import requests
import myClass

logger = logger.init_logger(__name__)

BASE_URL = "https://suppliers-api.wildberries.ru"


def update_price(headers, body):
    requests.post(f"{BASE_URL}/public/api/v1/prices", headers=headers, json=body)


def update_stock(headers, products, warehouse):
    body = {
        "stocks": products
    }
    requests.put(f"{BASE_URL}/api/v3/stocks/{warehouse}", headers=headers, json=body)


def get_new_orders(headers):
    orders = []
    response = requests.put(f"{BASE_URL}/api/v3/orders/new", headers=headers)
    for item in response["orders"]:
        orders.append(item)
    return orders


def get_products(headers):
    products = []
    body = {
        "sort": {
            "cursor": {
                "limit": 1000
            },
            "filter": {
                "withPhoto": -1
            }
        }
    }
    r = requests.post(f"{BASE_URL}/content/v1/cards/cursor/list", headers=headers, json=body).json()
    for item in r["data"]["cards"]:
        product = myClass.Product()
        product.sku = item["vendorCode"]
        product.id = item["nmID"]
        product.barcode = item["sizes"][0]["skus"]
        products.append(product)
    return products


def get_product(headers, sku):
    body = {
        "vendorCodes": [
            sku
        ],
        "allowedCategoriesOnly": True
    }
    return requests.post(f"{BASE_URL}/content/v1/cards/filter", headers=headers, json=body).json()


def get_warehouse(headers):
    warehouse = []
    response = requests.post(f"{BASE_URL}/api/v3/warehouses", headers=headers).json()
    for item in response:
        warehouse.append(item["id"])
    return warehouse
