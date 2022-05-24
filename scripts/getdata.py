import requests
from brownie import config
import json
from scripts.classes import ethgasoracle
from decimal import Decimal
import time
from stem import Signal
from stem.control import Controller

HEADERS = {}


def get_headers():
    url = config["headers_url"]
    print("Getting new headers")
    headers_json = {}
    try:
        response = requests.get(url, timeout=10)
        j = json.loads(response.content.decode("utf-8"))
        headers_json = j["headers"]
        headers_json.pop("Accept-Encoding")
        headers_json.pop("Host")
    except:
        headers_json = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua": '" Not A;Brand";v="99", "Chromium";v="101", "Google Chrome";v="101"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36",
            "X-Amzn-Trace-Id": "Root=1-628cae00-2cf3ebb64e207b965e437458",
        }
    return headers_json


def get_tor_session():
    global HEADERS
    session = requests.session()
    if HEADERS == {}:
        HEADERS = get_headers()
    headers = HEADERS
    session.headers = headers
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
    global HEADERS
    session = get_tor_session()
    url = config["coingecko_prices_url"]
    url = url.replace("@coingecko_id", coingecko_id)

    response = session.get(url).text

    j = {coingecko_id: {"usd": 0}}
    if coingecko_id in response:
        j = json.loads(response)
    else:
        if "Cloudflare" in response:
            HEADERS = get_headers()
            print("Cloudflare error. Renew Tor IP address. Response: ", response)
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
