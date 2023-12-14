from datetime import datetime, timedelta
import requests
import logger
import myClass
import time
import os

logger = logger.init_logger(__name__)

BASE_URL = "https://openapi.aliexpress.ru"


def update_price(headers, data):
    data = {"products": data}
    requests.post(f"{BASE_URL}/api/v1/product/update-sku-price", headers=headers, json=data)


def update_stock(headers, data):
    data = {"products": data}
    requests.post(f"{BASE_URL}/api/v1/product/update-sku-stock", headers=headers, json=data)


def get_product(headers, sku):
    data = {
        "filter": {
            "search_content": {
                "content_values": [sku],
                "content_type": "SKU_SELLER_SKU"
            }
        },
        "limit": 50
    }
    response = requests.post(f"{BASE_URL}/api/v1/scroll-short-product-by-filter", headers=headers, json=data).json()
    product = myClass.Product()
    if response["data"]:
        product.id = response["data"][0]["id"]
        product.sku = sku
        for item in response["data"][0]["sku"]:
            if sku == item["code"]:
                product.quantity = item["ipm_sku_stock"]
                product.price = item["price"]
        product.name = response["data"][0]["Subject"]
    return product


def get_products(headers):
    products = []
    data = {
        "limit": 50
    }
    response = requests.post(f"{BASE_URL}/api/v1/scroll-short-product-by-filter", headers=headers, json=data).json()
    for item in response["data"]:
        for sku in item["sku"]:
            product = myClass.Product()
            product.id = sku["sku_id"]
            product.sku = sku["code"]
            product.barcode = item["id"]
            product.price = sku["discount_price"]
            product.quantity = sku["ipm_sku_stock"]
            products.append(product)

    while response["data"]:
        data = {
            "last_product_id": item["id"],
            "limit": 50
        }
        response = requests.post(f"{BASE_URL}/api/v1/scroll-short-product-by-filter", headers=headers, json=data).json()
        for item in response["data"]:
            for sku in item["sku"]:
                product = myClass.Product()
                product.id = sku["sku_id"]
                product.sku = sku["code"]
                product.barcode = item["id"]
                product.price = sku["discount_price"]
                product.quantity = sku["ipm_sku_stock"]
                products.append(product)
    return products


def get_order(headers, order_number, products=False):
    data = {
        "order_ids": [order_number],
        "trade_order_info": "LogisticInfo"
    }
    response = requests.post(f"{BASE_URL}/seller-api/v1/order/get-order-list", headers=headers, json=data).json()
    order = myClass.Order()
    order.get_ae_order(response["data"]["orders"][0])
    if products:
        order.get_ae_products(response["data"]["orders"])
    return order


# Получить заказы, status передавать в массиве []
def get_orders(headers, days, status, products=False):
    data = {
        "page_size": 100,
        "trade_order_info": "LogisticInfo",
        "order_statuses": status,
        "date_start": f"{datetime.today() - timedelta(days=days, hours=0, minutes=0):%Y-%m-%dT%H:%M:%SZ}"
    }
    response = requests.post(f"{BASE_URL}/seller-api/v1/order/get-order-list", headers=headers, json=data).json()
    orders = []
    for item in response["data"]["orders"]:
        order = myClass.Order()
        order.get_ae_order(item)
        if products:
            order.get_ae_products(item)
        orders.append(order)
    return orders


def collect_order(headers, order):
    products = []
    v = 0  # Объем
    total_weight = 0
    for product in order.products:
        products.append(
            {
                "quantity": product["quantity"],
                "sku_id": product["product_id"]
            }
        )
        v += product["length"] * product["height"] * product["width"] * product["quantity"]
        total_weight += product["weight"] * product["quantity"]
    average_size = int(round(pow(v, 1 / 3), 0))  # Находим длину ребра куба
    data = {"orders": [
        {
            "trade_order_id": order.number,
            "total_length": average_size,
            "total_width": average_size,
            "total_height": average_size,
            "total_weight": total_weight / 1000,  # Переводим в кг.
            "items": products
        }
    ]}
    response = requests.post(f"{BASE_URL}/seller-api/v1/logistic-order/create", headers=headers, json=data).json()
    #  Возвращаем log_id для печати этикетки
    return response["data"]["orders"][0]["logistic_orders"][0]["id"]


def get_label(headers, log_id):
    data = {
        "logistic_order_ids": [log_id]
    }
    response = requests.post(f"{BASE_URL}/seller-api/v1/labels/orders/get", headers=headers, json=data).json()
    file_link = requests.get(response["data"]["label_url"])
    file = open(f"/print/{log_id}.pdf", "wb")
    file.write(file_link.content)
    file.close()
    os.system(f"lp -d TSC -o landscape -o media=Custom.100x80mm -o fit-to-page /print/{log_id}.pdf")
    # time.sleep(20)
    os.remove(f"/print/{log_id}.pdf")


def get_act(headers):
    log_ids = []
    # Получаем список отправлений
    data = {
        "page_size": 100,
        "page": 1,
        "filter_status": "AWAITING_ADDING_TO_HANDOVER"
    }
    response = requests.post(f"{BASE_URL}/seller-api/v1/logistic-order/get", headers=headers, json=data).json()
    for item in response["data"]["logistic_orders"]:
        log_ids.append(item["logistic_order_id"])

    # Создаем лист передачи
    data = {
        "logistic_order_ids": log_ids,
        "arrival_date": f"{datetime.today():%Y-%m-%dT%H:%M:%SZ}"
    }
    response = requests.post(f"{BASE_URL}/seller-api/v1/handover-list/create", headers=headers, json=data)
    # if response.status_code == 200:
    #     time.sleep(20)
    #     data = {
    #         "handover_list_id": response.json()["data"]["handover_list_id"]
    #     }
    #     # Печатаем лист передачи
    #     url = requests.post(f"{BASE_URL}/seller-api/v1/labels/handover-lists/get", headers=headers, json=data).json()
    #     act = requests.get(url["data"]["label_url"])
    #     file = open("/print/act_aliexpress.pdf", "wb")
    #     file.write(act.content)
    #     file.close()
    #     os.system("lp -d HP /print/act_aliexpress.pdf")
    #     os.remove("/print/act_aliexpress.pdf")
