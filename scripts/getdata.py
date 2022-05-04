import requests
from brownie import config
import json
from scripts.classes import ethgasoracle
from decimal import Decimal
import time


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


def get_prices_data(coingecko_id, retry):
    url = config["coingecko_prices_url"]
    url = url.replace("@coingecko_id", coingecko_id)
    response = requests.get(url, timeout=10)
    retry_total = int(config["max_retry_in_price_retrieve_error"])
    j = {coingecko_id: {"usd": 0}}
    if response.status_code == 200:
        j = json.loads(response.content.decode("utf-8"))
    elif response.status_code == 429:
        if retry > 0:
            retry = retry - 1
            time.sleep(retry_total - retry)
            get_prices_data(coingecko_id, retry)
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


def get_weth_abi():
    url = config["etherscan_weth_abi"]
    response = requests.get(url, timeout=10)
    j = json.loads(response.content.decode("utf-8"))
    abi_json = json.loads(j["result"])
    return abi_json


def get_coingecko_token_list():
    url = config["coingecko_tokens_list_url"]
    response = requests.get(url, timeout=10)
    token_list_json = json.loads(response.content.decode("utf-8"))
    return token_list_json


def get_coingecko_token_det(url):
    response = requests.get(url, timeout=10)
    j = json.loads(response.content.decode("utf-8"))
    token_id = j["platforms"]["ethereum"]
    return token_id
