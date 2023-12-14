import requests
import json
from datetime import datetime, timedelta
import logger
import mc
import myClass
import os
import time

logger = logger.init_logger(__name__)

BASE_URL = "https://api-seller.ozon.ru"


# Получить товары из заказа ОЗОН
def get_products(order_data):
    products = []
    for i in range(len(order_data["products"])):
        product_mc = mc.get_product_data(order_data["products"][i]["offer_id"])
        products.append({
            "id_mc": product_mc["id"],
            "product_id": order_data["products"][i]["sku"],
            "sku": order_data["products"][i]["offer_id"],
            "name": order_data["products"][i]["name"],
            "quantity": order_data["products"][i]["quantity"],
            # "reserve": product["quantity"],
            "price": float(order_data["products"][i]["price"]) * 100,
            "payout": round(float(order_data["financial_data"]["products"][i]["payout"]) * 100, 2),
            "assortment": {"meta": product_mc["meta"]}
        })
        i += 1
    return products


def update_stock(headers, data):
    requests.post(f"{BASE_URL}/v2/products/stocks", headers=headers, data=data)


def update_price(headers, data):
    requests.post(f"{BASE_URL}/v1/product/import/prices", headers=headers, data=data)


# Получить все артикулы товаров в Озон
def get_products_sku(headers):
    data = json.dumps(
        {
            "filter": {
                "visibility": "ALL"
            },
            "last_id": "",
            "limit": 1000
        }
    )
    response = requests.post(f"{BASE_URL}/v3/product/info/stocks", headers=headers, data=data).json()
    sku_list = []
    for item in response["result"]["items"]:
        sku_list.append(item["offer_id"])
    return sku_list


# Получить id всех действующих складов FBS
def get_warehouse_id(headers):
    response = requests.post(f"{BASE_URL}/v1/warehouse/list", headers=headers).json()
    warehouse_id_list = []
    for item in response["result"]:
        if item["status"] == "disabled":
            continue
        else:
            warehouse_id_list.append(item["warehouse_id"])
    return warehouse_id_list


# Получить все заказы Озон (новые заказы статус awaiting_packaging)
def get_orders(headers, days, status, products=False):
    data = json.dumps(
        {
            "dir": "ASC",
            "filter": {
                "since": f"{datetime.today() - timedelta(days=days, hours=0, minutes=0):%Y-%m-%dT%H:%M:%SZ}",
                "to": f"{datetime.today():%Y-%m-%dT%H:%M:%SZ}",
                "status": status
            },
            "limit": 1000,
            "offset": 0,
            "translit": True,
            "with": {
                "analytics_data": True,
                "financial_data": True
            }
        }
    )
    response = requests.post(f"{BASE_URL}/v3/posting/fbs/list", headers=headers[1], data=data).json()
    orders = []
    for item in response["result"]["postings"]:
        order = myClass.Order()
        order.get_oz_order(item)
        order.shop = headers[0]
        if headers[0] == "Bromptonbike":
            order.counterparty = mc.counterparty[5]
        if products:
            order.get_oz_products(item)
        orders.append(order)
    return orders


# Получить заказ ОЗОН по номеру
def get_order(headers, order_number, products=False):
    data = json.dumps(
        {
            "posting_number": order_number,
            "with": {
                "analytics_data": True,
                "barcodes": False,
                "financial_data": True,
                "product_exemplars": False,
                "translit": True
            }
        }
    )
    response = requests.post(f"{BASE_URL}/v3/posting/fbs/get", headers=headers[1], data=data).json()
    order = myClass.Order()
    order.get_oz_order(response["result"])
    if products:
        order.get_oz_products(response["result"])
    order.shop = headers[0]
    return order


# Собрать заказ
def collect_order(headers, order):
    data = json.dumps(
        {
            "packages": [
                {
                    "products": order.products
                }
            ],
            "posting_number": order.number,
            "with": {
                "additional_data": True
            }
        }
    )
    requests.post(f"{BASE_URL}/v4/posting/fbs/ship", headers=headers[1], data=data)


# Скачать этикетку
def get_label(headers, order):
    data = json.dumps(
        {
            "posting_number": [order.number]
        }
    )
    response = requests.post(f"{BASE_URL}/v2/posting/fbs/package-label", headers=headers[1], data=data)
    file = open(f"/print/{order.number}.pdf", "wb")
    file.write(response.content)
    file.close()
    logger.info("OZON: print label order " + str(order.number))
    os.system(f"lp -d TSC -o landscape -o media=Custom.100x80mm -o fit-to-page /print/{order.number}.pdf")
    # time.sleep(20)
    os.remove(f"/print/{order.number}.pdf")


# Получить возвраты
def get_returns(headers, days, status):
    data = json.dumps(
        {
            "filter": {
                "accepted_from_customer_moment": {
                    "time_from": f"{datetime.today() - timedelta(days=days, hours=0, minutes=0):%Y-%m-%dT%H:%M:%SZ}",
                    "time_to": f"{datetime.today():%Y-%m-%dT%H:%M:%SZ}"
                },
                "status": status
            },
            "limit": 1000,
            "last_id": 0
        }
    )
    response = requests.post(f"{BASE_URL}/v3/returns/company/fbs", headers=headers[1], data=data).json()
    orders = []
    for item in response["returns"]:
        orders.append(item["posting_number"])
    return orders


# Получить финансовую инфу по доставленным заказам
def get_finance(headers):
    data = json.dumps(
        {
            "filter": {
                "date": {
                    "from": f"{datetime.today() - timedelta(days=17, hours=0, minutes=0):%Y-%m-%dT%H:%M:%SZ}",
                    "to": f"{datetime.today():%Y-%m-%dT%H:%M:%SZ}",
                },
                "operation_type": [],
                "posting_number": "",
                "transaction_type": "orders"
            },
            "page": 1,
            "page_size": 1000
        }
    )
    return requests.post(f"{BASE_URL}/v3/finance/transaction/list", headers=headers, data=data).json()


def get_act(headers):
    warehouse = get_warehouse_id(headers[1])
    data = {
        "filter": {
            "warehouse_id": warehouse[0]
        },
        "limit": 100
    }
    delivery_method = requests.post(f"{BASE_URL}/v1/delivery-method/list", headers=headers[1], json=data).json()
    data = {
        "delivery_method_id": delivery_method["result"][0]["id"],
        "departure_date": f"{datetime.today():%Y-%m-%dT%H:%M:%SZ}"
    }
    act_id = requests.post(f"{BASE_URL}/v2/posting/fbs/act/create", headers=headers[1], json=data)
    if act_id.status_code == 200:
        data = {
            "id": act_id.json()["result"]["id"],
            "doc_type": "act_of_acceptance"
        }
        time.sleep(60)
        act_file = requests.post(f"{BASE_URL}/v2/posting/fbs/digital/act/get-pdf", headers=headers[1], json=data)
        if act_file.status_code == 200:
            f = open(f"/print/act_{headers[0]}.pdf", "wb")
            f.write(act_file.content)
            f.close()
            os.system(f"lp -d HP /print/act_{headers[0]}.pdf")
            os.remove(f"/print/act_{headers[0]}.pdf")
            logger.info("OZON: print act " + headers[0])
