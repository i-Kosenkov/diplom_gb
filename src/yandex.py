from datetime import datetime, timedelta
import requests
import logger
import myClass
import mc
import os
import time

logger = logger.init_logger(__name__)

BASE_URL = "https://api.partner.market.yandex.ru"


def get_orders(headers, days, substatus="", status="PROCESSING", products=False):
    params = {
        "fromDate": f"{datetime.today() - timedelta(days=days, hours=0, minutes=0):%d-%m-%Y}",
        "toDate": f"{datetime.today():%d-%m-%Y}",
        "status": status,
        "substatus": substatus
    }
    response = requests.get(f"{BASE_URL}/campaigns/{headers[1]['id']}/orders", headers=headers[1], params=params).json()
    orders = []
    for item in response["orders"]:
        order = myClass.Order()
        order.get_ya_order(item)
        order.shop = headers[0]
        if headers[0] == "Bromptonbike":
            order.counterparty = mc.counterparty[6]
        if products:
            order.get_ya_products(item)
        orders.append(order)
    return orders


def get_order(headers, order_number, products=False):
    response = requests.get(f"{BASE_URL}/campaigns/{headers[1]['id']}/orders/{order_number}", headers=headers[1]).json()
    order = myClass.Order()
    if response["order"]:
        order.get_ya_order(response["order"])
        order.shop = headers[0]
        if products:
            order.get_ya_products(response["order"])
    return order


# Обновить цены
def update_price(headers, data):
    body = {
        "offers": data
    }
    requests.post(f"{BASE_URL}/businesses/{headers[1]['businessId']}/offer-prices/updates", headers=headers[1],
                  json=body)


# Обновить остатки
def update_stock(headers, data):
    body = {
        "skus": data
    }
    requests.put(f"{BASE_URL}/campaigns/{headers[1]['id']}/offers/stocks", headers=headers[1], json=body)


# Получить возвраты за последние 30 дней.
def get_returns(headers, days, status):
    params = {
        "fromDate": f"{datetime.today() - timedelta(days=days, hours=0, minutes=0):%d-%m-%Y}"
    }
    r = requests.get(f"{BASE_URL}/campaigns/{headers[1]['id']}/returns", headers=headers[1], params=params).json()
    orders = [item["orderId"] for item in r["result"]["returns"] if item["shipmentStatus"] == status]
    return orders


def get_id_warehouse(headers):
    r = requests.get(f"{BASE_URL}/businesses/{headers[1]['businessId']}/warehouses", headers=headers[1]).json()
    return r["result"]["warehouses"][0]["id"]


def collect_order(headers, order):
    print(order.number)
    body = {
        "order": {
            "status": "PROCESSING",
            "substatus": "READY_TO_SHIP"
        }}
    requests.put(f"{BASE_URL}/campaigns/{headers[1]['id']}/orders/{order.number}/status", headers=headers[1], json=body)


def get_label(headers, order):
    r = requests.get(f"{BASE_URL}/campaigns/{headers[1]['id']}/orders/{order.number}/delivery/labels",
                     headers=headers[1])
    file = open(f"/print/{order.number}.pdf", "wb")
    file.write(r.content)
    file.close()
    logger.info("YANDEX: print label order " + str(order.number))
    os.system(f"lp -d TSC -o landscape -o media=Custom.100x80mm -o fit-to-page /print/{order.number}.pdf")
    # time.sleep(20)
    os.remove(f"/print/{order.number}.pdf")


def get_products(headers):
    products = []
    link = f"{BASE_URL}/businesses/{headers[1]['businessId']}/offer-mappings?page_token="
    resp = requests.post(link, headers=headers[1]).json()
    while True:
        for item in resp["result"]["offerMappings"]:
            product = myClass.Product()
            product.sku = item["offer"]["offerId"]
            product.name = item["offer"]["name"]
            try:
                product.barcode = item["offer"]["barcodes"]
            except Exception as err:
                logger.exception(err)
            # try:
            #     product.price = item["offer"]["basicPrice"]["value"]
            # except Exception as err:
            #     logger.exception(err)
            products.append(product)
        if resp["result"]["paging"]:
            resp = requests.post(link + resp["result"]["paging"]["nextPageToken"], headers=headers[1]).json()
            continue
        break
    return products


def get_act(headers):
    act = requests.get(f"{BASE_URL}/campaigns/{headers[1]['id']}/shipments/reception-transfer-act", headers=headers[1])
    if act.status_code == 200:
        file = open(f"/print/act_{headers[0]}.pdf", "wb")
        file.write(act.content)
        file.close()
        os.system(f"lp -d HP /print/act_{headers[0]}.pdf")
        os.remove(f"/print/act_{headers[0]}.pdf")
        logger.info("YANDEX: print act " + headers[0])
