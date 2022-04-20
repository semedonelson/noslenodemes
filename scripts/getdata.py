import requests
from brownie import config
import json
from scripts.classes import ethgasoracle
from decimal import Decimal


def run_query_post(query, url):

    # endpoint where you are making the request
    response = requests.post(
        url,
        "",
        json={"query": query},
    )
    if response.status_code == 200:
        return response.json()
    else:
        return "Query failed. return code is {}. {}".format(response.status_code, query)


def get_prices_data():
    url = config["coingecko_prices_url"]
    response = requests.get(url, timeout=10)
    j = json.loads(response.content.decode("utf-8"))
    return j


def get_ethgasoracle():
    url = config["gasoracle_url"]
    response = requests.get(url, timeout=10)
    j = json.loads(response.content.decode("utf-8"))
    gas = ethgasoracle(
        int(j["result"]["FastGasPrice"]),
        int(j["result"]["ProposeGasPrice"]),
        int(j["result"]["SafeGasPrice"]),
        Decimal(j["result"]["suggestBaseFee"]),
    )

    return gas
