import csv
import json
import os
import time
from datetime import datetime, timedelta

import requests

import aliexpress
import cdek
import logger
import login
import mailserver
import mc
import myClass
import ozon
import wb
import yandex

logger = logger.init_logger(__name__)


# Создать ярлык на папку print (Яндекс диск) в Linux и MacOS /Users/print
# Создать ярлык на папку orders в Linux /order=

# Обновляем товары в Озон (остатки + цена)
def update_oz_stock_price(headers):
    logger.info("OZON: update stock and price " + headers[0])
    products_list = []
    sku_list = ozon.get_products_sku(headers[1])
    warehouse_list_id = ozon.get_warehouse_id(headers[1])
    # Для каждого склада формируем список товаров и обновляем остатки
    for warehouse_id in warehouse_list_id:
        i = 0
        for sku in sku_list:
            product = mc.get_product(sku)
            products_list.append({
                "warehouse_id": warehouse_id,
                "offer_id": product.sku,
                "stock": product.quantity,
                "old_price": str(product.price * 1.2),
                "price": str(product.price)
            })
            i += 1
            # Лимит обновления остатков 100 шт.
            if i == 100 or sku == sku_list[-1]:
                data = json.dumps(
                    {
                        "stocks": products_list,
                        "prices": products_list
                    }
                )
                ozon.update_stock(headers[1], data)
                ozon.update_price(headers[1], data)
                products_list.clear()
                i = 0


# Обновляем сток и цены товаров ОЗОН
def update_oz_products(products):
    for headers in login.ozon().items():
        logger.info("OZON: update stock and price " + headers[0])
        products_list = []
        sku_list = ozon.get_products_sku(headers[1])
        warehouse_list_id = ozon.get_warehouse_id(headers[1])
        # Для каждого склада формируем список товаров и обновляем остатки
        for warehouse_id in warehouse_list_id:
            i = 0
            for sku in sku_list:
                for product in products:
                    if sku == product.sku:
                        products_list.append({
                            "warehouse_id": warehouse_id,
                            "offer_id": sku,
                            "stock": int(product.quantity),
                            "old_price": str(product.price * 1.2),
                            "price": str(product.price)
                        })
                        i += 1
                        # Лимит обновления остатков 100 шт.
                        if i == 100 or sku == sku_list[-1]:
                            data = json.dumps(
                                {
                                    "stocks": products_list,
                                    "prices": products_list
                                }
                            )
                            ozon.update_stock(headers[1], data)
                            ozon.update_price(headers[1], data)
                            products_list.clear()
                            i = 0
                        break


# Обновляем сток и цены товаров ЯНДЕКС
def update_ya_products(products):
    for headers in login.yandex().items():
        logger.info("YANDEX: update stock and price " + headers[0])
        data = []
        ya_products = yandex.get_products(headers)
        warehouse_id = yandex.get_id_warehouse(headers)
        for ya_product in ya_products:
            for product in products:
                if ya_product.sku == product.sku:
                    data.append(
                        {
                            "sku": ya_product.sku,
                            "warehouseId": warehouse_id,
                            "items": [
                                {
                                    "count": int(product.quantity),
                                    "type": "FIT",
                                    "updatedAt": f"{datetime.today() - timedelta(hours=3):%Y-%m-%dT%H:%M:%SZ}"
                                }
                            ],
                            "offerId": ya_product.sku,
                            "price": {
                                "value": product.price,
                                "currencyId": "RUR",
                                "discountBase": product.price * 1.2
                            }
                        }
                    )
                    break
        yandex.update_price(headers, data)
        yandex.update_stock(headers, data)


def update_wb_products(products):
    logger.info("WB: update stock and price")
    data = []
    wb_products = wb.get_products(login.wb())
    for product in wb_products:
        for item in products:
            if product.sku == item.sku:
                data.append({
                    "nmId": product.id,
                    "price": item.price,
                    "sku": product.barcode[0],
                    "amount": item.quantity
                })
                break
    wb.update_price(login.wb(), data)
    # wb.update_stock(login.wb(), data, warehouse)


def update_ae_products(products):
    logger.info("AE: update stock and price")
    data = []
    ae_products = aliexpress.get_products(login.aliexpress())
    for product in ae_products:
        for item in products:
            if product.sku == item.sku:
                data.append({
                    "product_id": product.barcode,
                    "skus": [
                        {
                            "sku_code": product.sku,
                            "price": str(item.price * 1.2),
                            "discount_price": str(item.price),
                            "inventory": int(item.quantity)
                        }]
                })
    aliexpress.update_stock(login.aliexpress(), data)
    aliexpress.update_price(login.aliexpress(), data)


def update_products():
    get_oz_returns()
    new_oz_order_state()
    get_ya_returns()
    new_ya_order_state()
    get_ae_returns()
    new_ae_order_state()
    logger.info("Updating stock and price in market places...")
    products = mc.get_all_assortment()
    update_oz_products(products)
    update_ya_products(products)
    update_wb_products(products)
    update_ae_products(products)


def update_stock_after_shipment(demand_link):
    logger.info("OZON: update stock after MC shipment")
    products = []
    positions = mc.get_request(demand_link + "/positions")
    for item in positions["rows"]:
        # Получаем товар из МС по ID товара
        product = mc.get_product(item["assortment"]["meta"]["href"].rsplit("/", 1)[1])
        if product:
            ae_product = aliexpress.get_product(login.aliexpress(), product.sku)
            # Добавляем в список товары из отгрузки
            products.append({
                # Для ОЗОН
                "offer_id": product.sku,
                "stock": product.quantity,
                # Для Яндекс
                "sku": product.sku,
                "items": [
                    {
                        "count": int(product.quantity),
                        "type": "FIT",
                        "updatedAt": f"{datetime.today() - timedelta(hours=3):%Y-%m-%dT%H:%M:%SZ}"
                    }],
                # Для АлиЭкспресс
                "product_id": ae_product.id,
                "skus": [
                    {
                        "sku_code": product.sku,
                        "inventory": int(product.quantity)
                    }]
            })

    # Обновляем остатки в ОЗОН
    for headers in login.ozon().items():
        logger.info("OZON: update stock " + headers[0])
        # Получаем все id складов в ОЗОН
        warehouse_list_id = ozon.get_warehouse_id(headers[1])
        for warehouse_id in warehouse_list_id:
            for item in products:
                item["warehouse_id"] = warehouse_id
            data = json.dumps(
                {
                    "stocks": products,
                }
            )
            ozon.update_stock(headers[1], data)

    # Обновляем остатки в Yandex
    for headers in login.yandex().items():
        logger.info("YANDEX: update stock " + headers[0])
        warehouse_id = yandex.get_id_warehouse(headers)
        for item in products:
            item["warehouseId"] = warehouse_id
        yandex.update_stock(headers, products)

    # Обновляем остатки в AliExpress
    logger.info("AliExpress: update stock")
    aliexpress.update_stock(login.aliexpress(), products)


# Получаем возвраты которые были получены из ОЗОН и удаляем отгрузку и заказ МС.
def get_oz_returns():
    for headers in login.ozon().items():
        logger.info("OZON: check returns " + headers[0])
        response = ozon.get_returns(headers, 30, "returned_to_seller")
        for order in response:
            logger.info("OZON: check returned order " + str(order))
            cancel_mc_order(order)


# Получаем возвраты (список номеров) которые были получены из ЯНДЕКС и удаляем отгрузку и заказ МС.
def get_ya_returns():
    for headers in login.yandex().items():
        logger.info("YANDEX: check returns and cancelled " + headers[0])
        response = yandex.get_returns(headers, 30, "PICKED")
        for order in response:
            logger.info("YANDEX: check returned order " + str(order))
            cancel_mc_order(order)
        response = yandex.get_orders(headers, 0, "", status="CANCELLED")
        for order in response:
            logger.info("YANDEX: check cancelled order " + order.number)
            cancel_mc_order(order.number)


def get_ae_returns():
    logger.info("ALIEXPRESS: check returns and cancelled")
    response = aliexpress.get_orders(login.aliexpress(), 30, ["Cancelled"])
    for order in response:
        logger.info("ALIEXPRESS: check cancelled order " + str(order.number))
        cancel_mc_order(order.number)


# Обработка отмененного заказа (удаление отгрузки и заказа)
def cancel_mc_order(order_number):
    data = mc.get_order_data(order_number)
    if data["rows"]:
        try:
            logger.info("MC: order " + str(order_number) + " found and deleting")
            mc.delete_demand(data["rows"][0]["demands"][0]["meta"]["href"].split("/")[-1])
            mc.delete_order(data["rows"][0]["meta"]["href"].split("/")[-1])
            file = open(f"/print/{order_number}.txt", "w")
            file.write(f"\n\n\n\n\n\n\n\n    Заказ {order_number} \n отменен ")
            file.close()
            os.system(f"lp -d TSC -o landscape -o media=Custom.100x80mm -o fit-to-page /print/{order_number}.txt")
            # time.sleep(20)
            os.remove(f"/print/{order_number}.txt")
            return
        except Exception as err:
            logger.exception(err)
    logger.info("MC: order not found " + str(order_number))


def get_new_oz_orders():
    for headers in login.ozon().items():
        orders = ozon.get_orders(headers, 1, "awaiting_packaging", True)
        for order in orders:
            logger.info("OZON: get new order " + order.shop + " " + str(order.number))
            create_mc(order)
            # Собираем заказ в ОЗОН
            ozon.collect_order(headers, order)
            time.sleep(20)
            oz_order = ozon.get_order(headers, order.number)
            if oz_order.status_delivery != "awaiting_packaging":
                # Печатаем этикетку Озон
                ozon.get_label(headers, order)


def get_new_ya_orders():
    for headers in login.yandex().items():
        orders = yandex.get_orders(headers, 0, "STARTED", products=True)
        for order in orders:
            create_mc(order)
            # Собираем заказ в Яндекс
            logger.info("YANDEX: get new order " + order.shop + " " + order.number)
            yandex.collect_order(headers, order)
            time.sleep(30)
            ya_order = yandex.get_order(headers, order.number)
            if ya_order.status_delivery != "STARTED":
                # Печатаем этикетку Яндекс
                time.sleep(30)
                yandex.get_label(headers, order)


def get_new_ae_orders():
    orders = aliexpress.get_orders(login.aliexpress(), 1, ["Created"], products=True)
    for order in orders:
        if not order.track_number:
            # Собираем заказ в AliExpress
            logger.info("ALIEXPRESS: get new order " + order.number)
            log_id = aliexpress.collect_order(login.aliexpress(), order)
            time.sleep(10)
            order.track_number = aliexpress.get_order(login.aliexpress(), order.number).track_number
            create_mc(order)
            time.sleep(10)
            # Печатаем этикетку AliExpress
            aliexpress.get_label(login.aliexpress(), log_id)


def update_oz_stock_after_mc_shipment(demand_link):
    logger.info("OZON: update stock after MC shipment")
    products_list = []
    positions = mc.get_request(demand_link + "/positions")
    for item in positions["rows"]:
        # Получаем товар из МС по ID товара
        product = mc.get_product(item["assortment"]["meta"]["href"].rsplit("/", 1)[1])
        if product:
            # Добавляем в список товары из отгрузки
            products_list.append({
                "offer_id": product.sku,
                "stock": product.quantity,
            })
    for company, headers in login.ozon().items():
        # Получаем все id складов в ОЗОН
        warehouse_list_id = ozon.get_warehouse_id(headers)
        for warehouse_id in warehouse_list_id:
            for item in products_list:
                item["warehouse_id"] = warehouse_id
            data = json.dumps(
                {
                    "stocks": products_list,
                }
            )
            # Обновляем остатки в ОЗОН
            ozon.update_stock(headers, data)


# Ловим смену статуса в Озон
def new_oz_order_state():
    for headers in login.ozon().items():
        logger.info("OZON: check new order status " + headers[0])
        orders = ozon.get_orders(headers, 30, "")
        try:
            with open("/orders/" + headers[1]["Client-Id"] + ".csv", mode="r") as file:
                reader = csv.reader(file)
                for order in orders:
                    for row in reader:
                        if row[0] == order.number:
                            if row[1] != order.status_delivery:
                                order.id = mc.get_order(order.number).id
                                # Проверяем заказ в МС если его нет выходим из цикла
                                if order.id:
                                    if order.status_delivery == "cancelled" and order.delivering_date is None:
                                        logger.info("MC: order canceled " + order.number)
                                        cancel_mc_order(order.number)
                                        break
                                    logger.info("MC: change order " + order.number + " status " + order.status_delivery)
                                    mc.update_order_status(order)
                                else:
                                    logger.info("MC: order not found " + order.number)
                                    break
                            else:
                                break
                    file.seek(0)
        except Exception as err:
            logger.exception(err)
        # Перезаписываем файл
        try:
            with open("/orders/" + headers[1]["Client-Id"] + ".csv", mode="w") as file:
                writer = csv.writer(file)
                for order in orders:
                    writer.writerow([order.number, order.status_delivery])
        except Exception as err:
            logger.exception(err)


# Ловим смену статуса в Yandex
def new_ya_order_state():
    for headers in login.yandex().items():
        logger.info("YANDEX: check new order status " + headers[0])
        orders = yandex.get_orders(headers, 30, "")
        try:
            with open("/orders/" + headers[1]["id"] + ".csv", mode="r") as file:
                reader = csv.reader(file)
                for order in orders:
                    for row in reader:
                        if row[0] == order.number:
                            if row[1] != order.status_delivery:
                                order.id = mc.get_order(order.number).id
                                # Проверяем заказ в МС если его нет выходим из цикла
                                if order.id:
                                    if order.status == "CANCELLED":
                                        logger.info("MC: order canceled " + order.number)
                                        cancel_mc_order(order.number)
                                        break
                                    logger.info("MC: change order " + order.number + " status " + order.status_delivery)
                                    mc.update_order_status(order)
                                else:
                                    logger.info("MC: order not found " + order.number)
                                    break
                            else:
                                break
                    file.seek(0)
        except Exception as err:
            logger.exception(err)
        # Перезаписываем файл
        try:
            with open("/orders/" + headers[1]["id"] + ".csv", mode="w") as file:
                writer = csv.writer(file)
                for order in orders:
                    writer.writerow([order.number, order.status_delivery])
        except Exception as err:
            logger.exception(err)


# Ловим смену статуса в AliExpress
def new_ae_order_state():
    logger.info("ALIEXPRESS: check new order status")
    orders = aliexpress.get_orders(login.aliexpress(), 30, [])
    try:
        with open("/orders/ae_orders.csv", mode="r") as file:
            reader = csv.reader(file)
            for order in orders:
                for row in reader:
                    if row[0] == order.number:
                        if row[1] != order.status_delivery:
                            order.id = mc.get_order(order.number).id
                            # Проверяем заказ в МС если его нет выходим из цикла
                            if order.id:
                                if order.status_delivery == "Cancelled":
                                    logger.info("MC: order canceled " + order.number)
                                    cancel_mc_order(order.number)
                                    break
                                logger.info("MC: change order " + order.number + " status " + order.status_delivery)
                                mc.update_order_status(order)
                            else:
                                logger.info("MC: order not found " + order.number)
                                break
                        else:
                            break
                file.seek(0)
    except Exception as err:
        logger.exception(err)
    # Перезаписываем файл
    try:
        with open("/orders/ae_orders.csv", mode="w") as file:
            writer = csv.writer(file)
            for order in orders:
                writer.writerow([order.number, order.status_delivery])
    except Exception as err:
        logger.exception(err)


# Проверяем заказ МС на обновления
def check_mc_order(order):
    # Если статус "Готов к отгрузке" отправляем email
    market = False
    if order.status_mc["meta"]["href"].split("/")[-1] == mc.state[2]["meta"]["href"].split("/")[-1]:
        for item in mc.counterparty[1:]:
            if order.counterparty["meta"] == item["meta"]:
                market = True
                break
        if not market:
            mailserver.done_letter(order)

    # Если поступила оплата меняем статус на Оплачен
    if order.payed > order.shipped:
        order.status_mc = mc.state[1]  # Статус Оплачен
        mc.update_order_status(order)
        return

        # Если отгрузка = поступлению меняем статус на Закрыт
    if order.payed == order.shipped and order.payed != 0:
        order.status_mc = mc.state[5]  # Статус Закрыт
        mc.update_order_status(order)
        return

        # Если была отгрузка но не было оплаты меняем статус на Отгружен
    # if order.payed < order.shipped:
    #     mc.change_status(order.id, mc.state[3])  # Статус Отгружен


# Печатаем наклейку СДЭК после отгрузки МС
def get_cdek_label_from_mc_demand(demand_link):
    # Получаем данные отгрузки которая была создана
    mc_demand = mc.get_request(demand_link)
    # Получаем данные заказа из отгрузки
    mc_order_data = mc.get_request(mc_demand["customerOrder"]["meta"]["href"])
    order = myClass.Order()
    order.get_mc_order(mc_order_data)
    # Если в заказе есть трек номер для отправки, получаем и печатаем этикетку СДЭК
    if order.track_number:
        logger.info("CDEK: print barcode " + order.track_number + " MC order " + order.number_mc)
        cdek.get_barcode(order.track_number)


def get_upd_from_mc(demand_link):
    demand_id = demand_link.rsplit("/", 1)[1]
    demand_mc = mc.get_request(demand_link)
    agent_id = demand_mc["agent"]["meta"]["href"].rsplit("/", 1)[1]
    # Проверяем чтобы контрагент не был маркет плейсом и розничным
    for counterparty in mc.counterparty:
        if agent_id == counterparty["meta"]["href"].rsplit("/", 1)[1]:
            return

    # Првоеряем чтобы компания не была М-Пласт
    organization_id = demand_mc["organization"]["meta"]["href"].rsplit("/", 1)[1]
    if organization_id != mc.organization[0]["id"]:
        mc.get_upd(demand_id)

    # Меняем статус заказа на Готов к выдаче
    order_mc = mc.get_order(demand_mc["customerOrder"]["meta"]["href"].rsplit("/", 1)[1])
    order_mc.status_mc = mc.state[2]  # Статус Готов к выдаче
    mc.update_order_status(order_mc)


def check_order(order):
    order_mc = mc.get_order(order.number)
    order.id = order_mc.id
    if order.id:
        # Оставлять статус Оплачен при создании оплаченного заказа в МС из Тильды
        if order_mc.status_mc == mc.state[1] and order.status_code == "CREATED":
            order.status_mc = mc.state[1]
        logger.info("MC: order " + order.number + " update from CDEK " + order.track_number)
        mc.update_order(order)


# Создаем в МС полученный заказ
def create_mc(order):
    order_mc = (mc.create_order(order))

    # Отправляем счет если определился контрагент
    if order.has_invoice:
        invoice_href = mc.get_invoice(order_mc.id)
        mailserver.invoice_letter(invoice_href, order)
        return

    # Создаем входящий платеж если была оплата картой
    if order.payment_system == "sberbank":
        mc.create_payment(order_mc)

    # Создаем отгрузку МС если была оплата или заказ с Маркета
    if order.payment_system == "sberbank" or order.payment_system == "market":
        order_mc.products = order.products
        mc.create_demand(order_mc)


# Обновляем стоимость товаров в МС после начислений в ОЗОН
def update_mc_orders():
    for headers in login.ozon().items():
        acquiring = 0.015  # 1,5%
        accruals = {}
        fin_result = ozon.get_finance(headers[1])
        # Собираем сумму комиссий по заказам
        for order in fin_result["result"]["operations"]:
            if order["posting"]["delivery_schema"] == "FBS":
                log_cost = 0
                for services in order["services"]:
                    log_cost += services["price"]
                # Записываем комиссию по логистике за 1 позицию продукции
                accruals[order["posting"]["posting_number"]] = -log_cost * 100

        logger.info("МС: update price in orders " + headers[0])
        for order_number, commission in accruals.items():
            order_oz = ozon.get_order(headers, order_number, True)
            order_mc = mc.get_order_data(order_oz.number)
            if order_mc["rows"]:
                logger.info("МС: order " + order_mc["rows"][0]["name"] + "(" + order_oz.number + ") updating prices")
                order_mc_id = order_mc["rows"][0]["id"]
                demand_mc_id = order_mc["rows"][0]["demands"][0]["meta"]["href"].split("/")[-1]
                order_positions = mc.get_order_positions(order_mc)
                demand_positions = mc.get_demand_positions(order_mc)
                commission = round(commission / order_oz.products_qlty, 2)
                i = 0
                for product in order_oz.products:
                    new_price = product["payout"] / product["quantity"] - (product["price"] * acquiring) - commission
                    mc.put_new_orders_price(order_mc_id, order_positions["rows"][i]["id"], int(new_price))
                    mc.put_new_demand_price(demand_mc_id, demand_positions["rows"][i]["id"], int(new_price))
                    logger.info(product["sku"] + " new price " + str(int(new_price) / 100))
                    i += 1
            else:
                logger.info("МС: order " + headers[0] + " " + order_oz.number + " not found")


def get_acts():
    for headers in login.yandex().items():
        logger.info("YANDEX: get act " + headers[0])
        yandex.get_act(headers)

    for headers in login.ozon().items():
        logger.info("OZON: get act " + headers[0])
        ozon.get_act(headers)

    logger.info("ALIEXPRESS: get act")
    aliexpress.get_act(login.aliexpress())


def bot_message(message):
    url = f"https://api.telegram.org/bot{login.telegram()}/sendMessage?chat_id=4631316&text={message}"
    requests.get(url)  # Эта строка отсылает сообщение
