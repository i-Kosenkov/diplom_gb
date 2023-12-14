import json

import requests
import login
import logger
from bs4 import BeautifulSoup
import myClass
import os
import time

logger = logger.init_logger(__name__)

BASE_URL = "https://api.moysklad.ru/api/remap/1.2/entity"

# 0 - М-Пласт, 1 - ИП Косенков ИА
organization = []
response = requests.get(f"{BASE_URL}/organization", headers=login.mc()).json()
for item in response["rows"]:
    organization.append(item)

# Счет: 0 - основной, 1 - эквайринг, 2 - тинькофф
organization_account = []
response = requests.get(organization[1]["accounts"]["meta"]["href"], headers=login.mc()).json()
for item in response["rows"]:
    organization_account.append(item)

# Контрагент: 0-Розничный, 1-ОЗОН, 2-Вайлдберис, 3-Яндекс, 4-АлиЭкспресс, 5-ОЗОН BRO, 6-Яндекс BRO, 7-Авито
counterparty = []
data = ['Розничный покупатель', 'ООО "ИНТЕРНЕТ РЕШЕНИЯ"', 'ООО "ВАЙЛДБЕРРИЗ"', 'ООО "ЯНДЕКС"', 'ООО "АЛИБАБА.КОМ (РУ)"',
        'ОЗОН BROMPTON', 'Яндекс BROMPTON', 'Авито']
for item in data:
    response = requests.get(f"{BASE_URL}/counterparty?filter=name={item}", headers=login.mc()).json()
    counterparty.append(response["rows"][0])

# Склад: 0 - Brompton, 1 - Основной
store = []
response = requests.get(f"{BASE_URL}/store", headers=login.mc()).json()
for item in response["rows"]:
    store.append(item)

# Статусы: 0-Новый, 1-Оплачен, 2-Готов к выдаче, 3-Отгружен, 4-В пути, 5-Закрыт
state = []
response = requests.get(f"{BASE_URL}/metadata", headers=login.mc()).json()
for item in response["customerorder"]["states"]:
    state.append({"meta": item["meta"]})

# Доп поля: 0-Заказ, 1-Магазин, 2-ФИО, 3-Телефон, 4-Почта, 5-Адрес
# 6-ПВЗ, 7-Трек, 8-Статус, 9-Компания, 10-С получателя, 11-Доставка
attr = []
response = requests.get(f"{BASE_URL}/customerorder/metadata/attributes", headers=login.mc()).json()
for item in response["rows"]:
    attr.append(item)

# Позиция доставка (арт. ТУ)
shipping = "ТУ"
response = requests.get(f"{BASE_URL}/assortment?offset=0&filter=code={shipping}", headers=login.mc()).json()
shipping = response["rows"][0]


# Получить заказ по номеру или по ID
def get_order(order_number):
    order = myClass.Order()
    # Ищем по номеру в доп поле
    mc_order = requests.get(f"{BASE_URL}/customerorder?filter={attr[0]['meta']['href']}={order_number}",
                            headers=login.mc()).json()
    if mc_order["rows"]:
        order.get_mc_order(mc_order["rows"][0])
        return order

    # Ищем по номеру заказа
    mc_order = requests.get(f"{BASE_URL}/customerorder?filter=name={order_number}", headers=login.mc()).json()
    if mc_order["rows"]:
        order.get_mc_order(mc_order["rows"][0])
        return order

    # Ищем по ID заказа
    mc_order = requests.get(f"{BASE_URL}/customerorder?filter=id={order_number}", headers=login.mc())
    if mc_order.status_code == 200:
        order.get_mc_order(mc_order.json()["rows"][0])

    return order


# Получить любой запрос
def get_request(request_link):
    return requests.get(request_link, headers=login.mc()).json()


def get_metadata():
    return requests.get(f"{BASE_URL}/metadata", headers=login.mc()).json()


def get_bundle_quantity(sku):
    # Получаем какие товары в комплекте (ссылка на комлпект)
    bundle = requests.get(f"{BASE_URL}/bundle?filter=code={sku}", headers=login.mc()).json()
    # Получаем товары из комплекта
    components = requests.get(bundle["rows"][0]["components"]["meta"]["href"], headers=login.mc()).json()
    min_quantity = []
    # Берем все товары комплекта и находим которого меньше всего, чтобы определить сток комплекта
    for product in components["rows"]:
        # Получаем id товара, чтобы потом запросить остаток на складе, вытаскиваем из ссылки на товар
        product_id = product["assortment"]["meta"]["href"].rsplit('/', 1)[1]
        # Получаем остаток товара на складе по id товара
        quantity = requests.get(f"{BASE_URL}/assortment?filter=id={product_id}", headers=login.mc()).json()
        # Добавляем остатки товаров в комплекте = сток / количество в комплекте
        min_quantity.append(quantity["rows"][0]["quantity"] / product["quantity"])
    # Из списка находим минимальный остаток, который и будет остатком комплекта
    return int(min(min_quantity))


# Получить товар по id или SKU(код товара)
def get_product(identity):
    # Ищем по SKU
    assortment = requests.get(f"{BASE_URL}/assortment?filter=code={identity}", headers=login.mc()).json()
    # Если не нашел по SKU ищем по ID
    if not assortment["rows"]:
        assortment = requests.get(f"{BASE_URL}/assortment?filter=id={identity}", headers=login.mc()).json()
    # Проверка на ошибку, так как по ID может возвращаться поле Error
    try:
        if assortment["rows"]:
            if not assortment["rows"][0]["meta"]["type"] == "service":
                product = myClass.Product()
                product.sku = assortment["rows"][0]["code"]
                product.price = assortment["rows"][0]["salePrices"][3]["value"]  # Цена: Маркет
                product.meta = assortment["rows"][0]["meta"]
                product.id = assortment["rows"][0]["id"]
                product.name = assortment["rows"][0]["name"]
                product.external_code = assortment["rows"][0]["externalCode"]
                if assortment["rows"][0]["meta"]["type"] == "bundle":
                    product.quantity = get_bundle_quantity(product.sku)
                    return product
                product.stock = assortment["rows"][0]["stock"]
                product.reserve = assortment["rows"][0]["reserve"]
                product.quantity = assortment["rows"][0]["quantity"]
                return product
    except Exception as err:
        logger.exception(err)
    logger.info("Product (" + identity + ") not found in MC")


# Получить JSON данные товара по id или SKU(код товара)
def get_product_data(identity):
    # Ищем по SKU
    product = requests.get(f"{BASE_URL}/assortment?filter=code={identity}", headers=login.mc()).json()
    if product["rows"]:
        return product["rows"][0]
    # Если не нашел по SKU ищем по ID
    product = requests.get(f"{BASE_URL}/assortment?filter=id={identity}", headers=login.mc()).json()
    if not product["errors"]:
        if product["rows"]:
            return product["rows"][0]


# Получить контрагента
def get_counterparty(inn):
    response = requests.get(f"{BASE_URL}/counterparty?filter=inn={inn}", headers=login.mc()).json()
    return response["rows"][0]


# Создать новый заказ
def create_order(order):
    body = {
        "organization": order.organization,
        "organizationAccount": order.organization_account,
        "agent": order.counterparty,
        "store": store[1],  # Склад основной
        "state": order.status_mc,
        "description": order.comment,
        "positions": order.products,
        "attributes": [
            # Номер заказа, доп поле
            {
                "meta": attr[0]["meta"],
                "value": order.number  # Значение должно быть STR
            },
            # Название магазина
            {
                "meta": attr[1]["meta"],
                "value": order.shop
            },
            # Имя получателя
            {
                "meta": attr[2]["meta"],
                "value": order.customer_name
            },
            # Телефон получателя
            {
                "meta": attr[3]["meta"],
                "value": order.customer_phone
            },
            # Email получателя
            {
                "meta": attr[4]["meta"],
                "value": order.customer_email
            },
            # Адрес доставки
            {
                "meta": attr[5]["meta"],
                "value": order.delivery_address
            },
            # Код ПВЗ
            {
                "meta": attr[6]["meta"],
                "value": order.delivery
            },
            # Трек номер
            {
                "meta": attr[7]["meta"],
                "value": order.track_number
            },
            # Статус
            {
                "meta": attr[8]["meta"],
                "value": order.status_delivery
            },
            # Название компании
            {
                "meta": attr[9]["meta"],
                "value": order.customer_inn + " " + order.customer_company
            },
            # Стоимость доставки
            {
                "meta": attr[11]["meta"],
                "value": str(order.delivery_price)
            }
        ]}
    response = requests.post(f"{BASE_URL}/customerorder", headers=login.mc(), json=body).json()
    order_mc = myClass.Order()
    order_mc.get_mc_order(response)
    return order_mc


# Создать отгрузку
def create_demand(order):
    body = {
        "organization": order.organization,
        "organizationAccount": order.organization_account,
        "agent": order.counterparty,
        "store": order.store,
        "customerOrder": {"meta": order.meta},
        "positions": order.products
    }
    return requests.post(f"{BASE_URL}/demand", headers=login.mc(), json=body).json()


# Создать входящий платеж
def create_payment(order):
    body = {
        "organization": order.organization,
        "agent": order.counterparty,
        "organizationAccount": order.organization_account,
        "operations": [{"meta": order.meta}],
        "sum": order.sum
    }
    requests.post(f"{BASE_URL}/paymentin", headers=login.mc(), json=body)


# Удалить заказ
def delete_order(id_order):
    requests.delete(f"{BASE_URL}/customerorder/{id_order}", headers=login.mc())


# Удалить отгрузку
def delete_demand(id_demand):
    requests.delete(f"{BASE_URL}/demand/{id_demand}", headers=login.mc())


# Удалить входящий платеж
def delete_payment(id_payment):
    requests.delete(f"{BASE_URL}/paymentin/{id_payment}", headers=login.mc())


# Обновить заказ МС
def update_order(order):
    body = {
        "state": order.status_mc,
        "attributes": [
            # Номер заказа СДЭК (трек номер)
            {
                "meta": attr[7]["meta"],
                "value": order.track_number
            },
            # Название компании отправителя (M-Plast, Brompton...)
            {
                "meta": attr[1]["meta"],
                "value": order.shop
            },
            # ФИО получателя
            {
                "meta": attr[2]["meta"],
                "value": order.customer_name
            },
            # Телефон получателя
            {
                "meta": attr[3]["meta"],
                "value": order.customer_phone
            },
            # Email получателя
            {
                "meta": attr[4]["meta"],
                "value": order.customer_email
            },
            # Адрес получателя
            {
                "meta": attr[5]["meta"],
                "value": order.delivery_address
            },
            # Код ПВЗ
            {
                "meta": attr[6]["meta"],
                "value": order.delivery_point
            },
            # Статус доставки
            {
                "meta": attr[8]["meta"],
                "value": order.status_delivery
            },
            # Стоимость доставки с получателя
            {
                "meta": attr[10]["meta"],
                "value": str(order.customer_log_cost)
            },
            # Стоимость доставки для отправителя
            {
                "meta": attr[11]["meta"],
                "value": str(order.sender_log_cost)
            }
        ]
    }
    requests.put(f"{BASE_URL}/customerorder/{order.id}", headers=login.mc(), json=body)


def update_order_status(order):
    body = {
        "state": order.status_mc,
        "attributes": [
            # Статус доставки
            {
                "meta": attr[8]["meta"],
                "value": order.status_delivery
            }]
    }
    requests.put(f"{BASE_URL}/customerorder/{order.id}", headers=login.mc(), json=body)


# Получить данные заказа по номеру Заказа
def get_order_data(order_number):
    order = requests.get(f"{BASE_URL}/customerorder?filter={attr[0]['meta']['href']}={order_number}",
                         headers=login.mc()).json()
    if order["rows"]:
        return order
    return requests.get(f"{BASE_URL}/customerorder?filter=name={order_number}", headers=login.mc()).json()


# Получить данные товаров в отгрузке из заказа
def get_demand_positions(order_data):
    try:
        return requests.get(order_data["rows"][0]["demands"][0]["meta"]["href"] + "/positions",
                            headers=login.mc()).json()
    except Exception as err:
        logger.exception(err)


# Получить данные товаров в заказе
def get_order_positions(order_data):
    try:
        return requests.get(order_data["rows"][0]["positions"]["meta"]["href"], headers=login.mc()).json()
    except Exception as err:
        logger.exception(err)


# Изменить цены в заказе
def put_new_orders_price(order_id, product_id, price):
    body = {
        "price": price
    }
    res = requests.put(f"{BASE_URL}/customerorder/{order_id}/positions/{product_id}", headers=login.mc(), json=body)


# Изменить цены в отгрузке
def put_new_demand_price(demand_id, product_id, price):
    body = {
        "price": price
    }
    requests.put(f"{BASE_URL}/demand/{demand_id}/positions/{product_id}", headers=login.mc(), json=body)


# Получить весь ассортимент
def get_all_assortment():
    offset = 0
    products_list = []
    assortment = requests.get(f"{BASE_URL}/assortment", headers=login.mc()).json()
    while assortment["rows"]:
        for item in assortment["rows"]:
            product = myClass.Product()
            if item["meta"]["type"] == "service":
                continue
            elif item["meta"]["type"] == "bundle":
                product.sku = item["code"]
                product.id = item["id"]
                product.quantity = -1
                # product.quantity = get_bundle_quantity(product.sku)

                product.price = item["salePrices"][3]["value"] / 100  # Цена Маркет
                products_list.append(product)
                continue
            else:
                product.sku = item["code"]
                product.id = item["id"]
                product.quantity = item["quantity"]
                product.price = item["salePrices"][3]["value"] / 100  # Цена Маркет
                products_list.append(product)
        offset += 1000
        assortment = requests.get(f"{BASE_URL}/assortment?offset={offset}", headers=login.mc()).json()
    for product in products_list:
        if product.quantity == -1:
            product.quantity = get_bundle(product.id, products_list)
            # print(product.sku, product.quantity)
    return products_list


def get_bundle(product_id, products_list):
    # Получаем товары из комплекта
    components = requests.get(f"{BASE_URL}/bundle/{product_id}/components", headers=login.mc()).json()
    min_quantity = []
    # Берем все товары комплекта и находим которого меньше всего, чтобы определить сток комплекта
    for component in components["rows"]:
        for product in products_list:
            if component["assortment"]["meta"]["href"].rsplit('/', 1)[1] == product.id:
                min_quantity.append(product.quantity / component["quantity"])
    return int(min(min_quantity))


# Сформировать ссылку и создать файл счета с печатью и подписью
def get_invoice(order_id):
    body = {
        "template": {
            "meta": {
                "href": f"{BASE_URL}/customerorder/metadata/customtemplate/2cc43b2e-f992-4ed3-bb9d-7f1559b4282f",
                "type": "customtemplate",
                "mediaType": "application/json"
            }
        }
    }
    resp = requests.post(f"{BASE_URL}/customerorder/{order_id}/publication", headers=login.mc(), json=body).json()
    resp = requests.get(resp["href"])
    soup = BeautifulSoup(resp.text, "html.parser")
    # Вытаскиваем ссылку на счет и сохраняем файл
    for link in soup.find_all("a"):
        if ".pdf" in link.get("href"):
            invoice = requests.get(link.get("href"))
            file_name = link.get("href").split('-')[-1]
            file = open(f"/email/{file_name}", 'wb')
            file.write(invoice.content)
            file.close()
            logger.info("Create invoice file " + link.get("href").split('-')[-1])
            return link.get("href")


def get_upd(demand_id):
    body = {
        "template": {
            "meta": {
                "href": f"{BASE_URL}/demand/metadata/customtemplate/fbcc2494-032d-4c2d-ae17-a6f0742b35a8",
                "type": "customtemplate",
                "mediaType": "application/json"
            }
        }
    }
    resp = requests.post(f"{BASE_URL}/demand/{demand_id}/publication", headers=login.mc(), json=body).json()
    resp = requests.get(resp["href"])
    soup = BeautifulSoup(resp.text, "html.parser")
    # Вытаскиваем ссылку на УПД и сохраняем файл
    for link in soup.find_all("a"):
        if ".pdf" in link.get("href"):
            upd = requests.get(link.get("href"))
            file_name = link.get("href").split('-')[-1]
            file = open(f"/print/{file_name}", 'wb')
            file.write(upd.content)
            file.close()
            logger.info("Print MC UPD " + file_name)
            os.system(f"lp -d HP -o landscape -n 2 /print/{file_name}")
            os.remove(f"/print/{file_name}")
