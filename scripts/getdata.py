import requests
from brownie import config
import json
from scripts.classes import ethgasoracle
from decimal import Decimal
import time
from stem import Signal
from stem.control import Controller


def get_tor_session():
    session = requests.session()
    # Tor uses the 9050 port as the default socks port
    session.proxies = {
        "http": "socks5://127.0.0.1:9050",
        "https": "socks5://127.0.0.1:9050",
    }
    return session


# signal TOR for a new connection
def renew_connection():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate(password="47Fwch1wFkqEk3PzV2HiGA==")
        controller.signal(Signal.NEWNYM)


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


def get_prices_data(coingecko_id):
    session = get_tor_session()
    url = config["coingecko_prices_url"]
    url = url.replace("@coingecko_id", coingecko_id)
    response = session.get(url).text
    j = {coingecko_id: {"usd": 0}}
    if "error" not in response:
        j = json.loads(response)
    else:
        print("Error renew Tor IP address")
        renew_connection()

    return j


def get_ethgasoracle():
    url = config["gasoracle_url"]
    response = requests.get(url, timeout=10)
    j = json.loads(response.content.decode("utf-8"))
    if response.status_code == 200:
        gas = ethgasoracle(
            int(j["result"]["FastGasPrice"]),
            int(j["result"]["ProposeGasPrice"]),
            int(j["result"]["SafeGasPrice"]),
            Decimal(j["result"]["suggestBaseFee"]),
        )
    else:
        gas = ethgasoracle(
            int(-1),
            int(-1),
            int(-1),
            Decimal(-1.0),
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
