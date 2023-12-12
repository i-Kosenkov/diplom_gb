import logger
import mc
import requests
import login

logger = logger.init_logger(__name__)


class Order:
    def __init__(self):
        self.number = ""
        self.id = ""
        self.organization = mc.organization[1]  # Организация ИП
        self.organization_account = mc.organization_account[1]  # Счет эквайринг
        self.shop = ""
        self.counterparty = mc.counterparty[0]  # Розничный покупатель
        self.customer_name = ""
        self.customer_phone = ""
        self.customer_email = ""
        self.customer_company = ""
        self.customer_inn = ""
        self.comment = ""
        self.products = ""
        self.products_qlty = 0
        self.delivery = ""
        self.delivery_address = ""
        self.delivery_point = ""
        self.delivery_price = ""
        self.track_number = ""
        self.delivering_date = ""
        self.status = ""
        self.status_mc = ""
        self.status_code = ""
        self.status_delivery = ""
        self.payment_system = ""
        self.has_invoice = False
        self.meta = ""
        self.number_mc = ""
        self.store = mc.store[1]  # Склад - основной
        self.sum = ""
        self.customer_log_cost = ""
        self.sender_log_cost = ""
        self.payed = ""
        self.shipped = ""

    def get_oz_order(self, order_data):
        self.payment_system = "market"
        self.number = order_data["posting_number"]
        self.organization_account = mc.organization_account[0]
        self.counterparty = mc.counterparty[1]  # Интернет решения
        self.status_delivery = order_data["status"]
        self.delivery = order_data["analytics_data"]["delivery_type"]
        self.delivery_address = order_data["analytics_data"]["city"]
        self.delivering_date = order_data["delivering_date"]
        if self.status_delivery == "delivering":
            self.status_mc = mc.state[4]
        elif self.status_delivery == "delivered":
            self.status_mc = mc.state[3]
        else:
            self.status_mc = mc.state[2]

    def get_oz_products(self, order_data):
        products = []
        for i in range(len(order_data["products"])):
            product_mc = mc.get_product(order_data["products"][i]["offer_id"])
            if product_mc:
                products.append({
                    "id_mc": product_mc.id,
                    "product_id": order_data["products"][i]["sku"],
                    "sku": order_data["products"][i]["offer_id"],
                    "name": order_data["products"][i]["name"],
                    "quantity": order_data["products"][i]["quantity"],
                    # "reserve": product["quantity"],
                    "price": float(order_data["products"][i]["price"]) * 100,
                    "payout": round(float(order_data["financial_data"]["products"][i]["payout"]) * 100, 2),
                    "assortment": {"meta": product_mc.meta}
                })
            self.products_qlty += order_data["products"][i]["quantity"]
            i += 1
        self.products = products

    def get_ya_order(self, order_data):
        self.payment_system = "market"
        self.number = str(order_data["id"])
        self.organization_account = mc.organization_account[0]
        self.counterparty = mc.counterparty[3]  # Яндекс
        self.status_delivery = order_data["substatus"]
        self.status = order_data["status"]
        self.delivery = order_data["delivery"]["serviceName"]
        self.delivery_address = order_data["delivery"]["region"]["name"]
        # self.track_number = order_data["delivery"]["tracks"][0]["trackCode"]
        if self.status_delivery == "STARTED":
            self.status_mc = mc.state[2]  # Статус готов к выдаче
        elif self.status_delivery == "SHIPPED" or self.status == "PICKUP":
            self.status_mc = mc.state[4]  # Статус В пути
        elif self.status_delivery == "DELIVERY_SERVICE_DELIVERED":
            self.status_mc = mc.state[3]  # Статус Отгружен
        else:
            self.status_mc = mc.state[0]  # Статус Новый

    def get_ya_products(self, order_data):
        products = []
        for i in range(len(order_data["items"])):
            product_mc = mc.get_product(order_data["items"][i]["offerId"])
            if product_mc:
                products.append({
                    "id_mc": product_mc.id,
                    "product_id": order_data["items"][i]["id"],
                    "sku": order_data["items"][i]["offerId"],
                    "name": order_data["items"][i]["offerName"],
                    "quantity": order_data["items"][i]["count"],
                    # "reserve": product["quantity"],
                    "price": float(order_data["items"][i]["price"] * 0.75) * 100,
                    "assortment": {"meta": product_mc.meta}
                })
            i += 1
        self.products = products

    def get_ae_order(self, order_data):
        self.payment_system = "market"
        self.number = str(order_data["id"])
        self.shop = "M-Plast"
        self.organization_account = mc.organization_account[0]
        self.counterparty = mc.counterparty[4]  # АлиЭкспресс
        self.customer_name = order_data["buyer_name"]
        self.customer_phone = order_data["buyer_phone"]
        self.status_delivery = order_data["delivery_status"]
        self.delivery_address = order_data["delivery_info"]["street_house"]
        self.delivery = order_data["delivery_info"]["city"]
        try:
            self.delivery_price = order_data["pre_split_postings"][0]["delivery_fee"] / 100
        except Exception as err:
            logger.exception(err)
        try:
            self.track_number = order_data["logistic_orders"][0]["track_number"]
        except Exception as err:
            logger.exception(err)

        if self.status_delivery == "Shipped":
            self.status_mc = mc.state[4]
        elif self.status_delivery == "Delivered":
            self.status_mc = mc.state[3]
        else:
            self.status_mc = mc.state[2]

    def get_ae_products(self, order_data):
        products = []
        for i in range(len(order_data["order_lines"])):
            product_mc = mc.get_product(order_data["order_lines"][i]["sku_code"])
            if product_mc:
                products.append({
                    "id_mc": product_mc.id,
                    "product_id": order_data["order_lines"][i]["sku_id"],
                    "sku": order_data["order_lines"][i]["sku_code"],
                    "name": order_data["order_lines"][i]["name"],
                    "quantity": int(order_data["order_lines"][i]["quantity"]),
                    # "reserve": product["quantity"],
                    "price": float(order_data["order_lines"][i]["item_price"]),
                    "assortment": {"meta": product_mc.meta},
                    "height": order_data["order_lines"][i]["height"],
                    "width": order_data["order_lines"][i]["width"],
                    "length": order_data["order_lines"][i]["length"],
                    "weight": order_data["order_lines"][i]["weight"]
                })
            i += 1
        self.products = products

    def get_tilda_order(self, order_data):
        self.number = order_data["payment"]["orderid"]
        self.shop = order_data["store"]
        self.customer_name = order_data["name"]
        self.customer_phone = order_data["phone"]
        self.customer_email = order_data["email"]
        self.payment_system = order_data["paymentsystem"]
        self.status_mc = mc.state[1]

        if self.payment_system != "sberbank":
            self.organization_account = mc.organization_account[0]
            self.status_mc = mc.state[0]
            try:
                self.customer_inn = order_data["inn"]
                # Ищем контрагента в МС по ИНН
                counterparty = mc.get_counterparty(self.customer_inn)
                if counterparty:
                    self.counterparty = counterparty
                    self.has_invoice = True
            except Exception as err:
                logger.exception(err)

        try:
            self.customer_company = order_data["companyname"]
        except Exception as err:
            logger.exception(err)

        try:
            self.comment = order_data["comment"]
        except Exception as err:
            logger.exception(err)

        self.delivery = order_data["payment"]["delivery"]
        self.delivery_address = order_data["payment"]["delivery_address"]
        self.delivery_price = order_data["payment"]["delivery_price"]
        self.comment = self.delivery + "\n" + self.comment
        products = []
        discount = 0
        if order_data["paymentsystem"] == "sberbank":
            discount = 2
        for product in order_data["payment"]["products"]:
            product_mc = mc.get_product(product["sku"])
            if product_mc:
                products.append({
                    "id_mc": product_mc.id,
                    "sku": product["sku"],
                    "name": product["name"],
                    "quantity": product["quantity"],
                    # "reserve": product["quantity"],
                    "price": float(product["price"]) * 100,
                    "discount": discount,
                    "assortment": {"meta": product_mc.meta}
                })
        if order_data["payment"]["delivery_price"] != 0:
            products.append({
                "id_mc": mc.shipping["id"],
                "quantity": 1,
                "price": float(order_data["payment"]["delivery_price"]) * 100,
                "discount": discount,
                "assortment": {"meta": mc.shipping["meta"]}
            })
        self.products = products

    def get_mc_order(self, order_data):
        self.meta = order_data["meta"]
        self.id = order_data["id"]
        self.number_mc = order_data["name"]
        self.organization = order_data["organization"]
        self.organization_account = order_data["organizationAccount"]
        self.counterparty = order_data["agent"]
        self.store = order_data["store"]
        self.status_mc = order_data["state"]
        self.sum = order_data["sum"]
        self.payed = order_data["payedSum"]
        self.shipped = order_data["shippedSum"]
        try:
            for attribute in order_data["attributes"]:
                if attribute["id"] == mc.attr[0]["id"]:  # Заказ
                    self.number = attribute["value"]
                    continue
                if attribute["id"] == mc.attr[1]["id"]:  # Магазин
                    self.shop = attribute["value"]
                    continue
                if attribute["id"] == mc.attr[2]["id"]:  # ФИО
                    self.customer_name = attribute["value"]
                    continue
                if attribute["id"] == mc.attr[3]["id"]:  # Телефон
                    self.customer_phone = attribute["value"]
                    continue
                if attribute["id"] == mc.attr[4]["id"]:  # Почта
                    self.customer_email = attribute["value"]
                    continue
                if attribute["id"] == mc.attr[5]["id"]:  # Адрес
                    self.delivery_address = attribute["value"]
                    continue
                if attribute["id"] == mc.attr[6]["id"]:  # ПВЗ
                    self.delivery_point = attribute["value"]
                    continue
                if attribute["id"] == mc.attr[7]["id"]:  # Трек
                    self.track_number = attribute["value"]
                    continue
                if attribute["id"] == mc.attr[8]["id"]:  # Статус
                    self.status = attribute["value"]
                    continue
                if attribute["id"] == mc.attr[9]["id"]:  # Компания
                    self.customer_company = attribute["value"]
                    continue
                if attribute["id"] == mc.attr[10]["id"]:  # С получателя руб.
                    self.customer_log_cost = attribute["value"]
                    continue
                if attribute["id"] == mc.attr[11]["id"]:  # Доставка руб.
                    self.sender_log_cost = attribute["value"]
                    continue
        except Exception as err:
            logger.exception(err)

    def get_mc_products(self):
        products = []
        positions = requests.get(f"{mc.BASE_URL}/customerorder/{self.id}/positions", headers=login.mc()).json()
        for product in positions["rows"]:
            products.append(product)
        self.products = products

    def get_cdek_order(self, order_data):
        # self.id = response["entity"]["uuid"]
        self.number = order_data["entity"]["number"]
        self.track_number = order_data["entity"]["cdek_number"]
        self.status_delivery = order_data["entity"]["statuses"][0]["name"]
        self.status_code = order_data["entity"]["statuses"][0]["code"]
        if self.status_code == "CREATED":
            self.status_mc = mc.state[0]  # Новый
        elif self.status_code == "DELIVERED":
            self.status_mc = mc.state[5]  # Закрыт
        else:
            self.status_mc = mc.state[4]  # В пути

        self.shop = order_data["entity"]["sender"]["company"]
        self.customer_company = order_data["entity"]["recipient"]["company"]
        self.customer_name = order_data["entity"]["recipient"]["name"]
        self.customer_phone = order_data["entity"]["recipient"]["phones"][0]["number"]
        try:
            self.customer_email = order_data["entity"]["recipient"]["email"]
        except Exception as err:
            logger.exception(err)
        try:
            self.delivery_point = order_data["entity"]["delivery_point"]
        except Exception as err:
            logger.exception(err)
        self.delivery_address = order_data["entity"]["to_location"]["address"]
        self.customer_log_cost = order_data["entity"]["delivery_recipient_cost"]["value"]
        self.sender_log_cost = order_data["entity"]["delivery_detail"]["total_sum"]


class Product:
    def __init__(self):
        self.meta = ""
        self.sku = ""
        self.id = ""
        self.barcode = ""
        self.external_code = ""
        self.name = ""
        self.stock = ""
        self.reserve = ""
        self.quantity = ""
        self.price = ""
