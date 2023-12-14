import json
from flask import Flask, request
import model
import time
import cdek
import logger
import mc
import myClass
import requests
import login
import edo
import time

logger = logger.init_logger(__name__)

app = Flask(__name__)


@app.route("/check", methods=["GET", "POST"])
def check_server():
    return "Server is running", 200


# Методы для МС iGlonas
@app.route("/webhook/mc/demand_update", methods=["POST"])
def mc_demand_update():
    response = request.json
    # print(json.dumps(response,indent=4))
    # for item in response["events"]:
    #     edo.get_demand(item["meta"]["href"])
    return "success", 200


# Методы для МС М-Пласт
@app.route("/webhook/mc/customerorder_update", methods=["POST"])
def mc_order_update():
    response = request.json
    for item in response["events"]:
        order = myClass.Order()
        order_data = mc.get_request(item["meta"]["href"])
        order.get_mc_order(order_data)
        model.check_mc_order(order)

    # order_data = mc.get_request(response["events"][0]["meta"]["href"])
    # order.get_mc_order(order_data)
    # model.check_mc_order(order)
    return "success", 200


@app.route("/webhook/mc/demand_create", methods=["POST"])
def mc_demand_created():
    response = request.json
    demand_link = response["events"][0]["meta"]["href"]
    model.get_upd_from_mc(demand_link)
    model.update_stock_after_shipment(demand_link)
    time.sleep(20)
    model.get_cdek_label_from_mc_demand(demand_link)
    return "success", 200


@app.route("/webhook/tilda/new_order", methods=["POST"])
def tilda_new_order():
    response = request.json
    if response != {"test": "test"}:
        order = myClass.Order()
        order.get_tilda_order(response)
        model.create_mc(order)
    return "success", 200


@app.route("/webhook/cdek/status_update", methods=["POST"])
def cdek_status_update():
    response = request.json
    time.sleep(20)
    if response["attributes"]["code"] != "REMOVED":
        number = response["attributes"]["cdek_number"]
        order = myClass.Order()
        order_data = requests.get(f"{cdek.BASE_URL}/orders?cdek_number={number}", headers=login.cdek()).json()
        order.get_cdek_order(order_data)
        model.bot_message("СДЭК: " + order.track_number + " (" + order.number + ")\n" + order.status_delivery)
        model.check_order(order)
    return "success", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
