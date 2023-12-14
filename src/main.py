import model


def check_new_orders():
    model.get_new_oz_orders()
    model.get_new_ya_orders()
    model.get_new_ae_orders()


def update_products():
    model.update_products()


def update_mc_orders():
    model.update_mc_orders()


def get_acts():
    model.get_acts()


def main():
    check_new_orders()
    # update_products()
    # update_mc_orders()
    # get_acts()


if __name__ == "__main__":
    main()
