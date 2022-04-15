import requests
from brownie import config
import json
from scripts.classes import ethgasstation


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


def get_ethgasstation():
    url = config["ethgasstation_url"]
    response = requests.get(url, timeout=10)
    j = json.loads(response.content.decode("utf-8"))
    gas = ethgasstation(
        int(j["fast"]),
        int(j["fastest"]),
        int(j["safeLow"]),
        int(j["average"]),
    )

    return gas
