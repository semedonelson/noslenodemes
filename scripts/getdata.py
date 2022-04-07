import requests
from brownie import config
import json


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


def list_coingecko_tokens():
    url = config["coingecko_tokens_list_url"]
    r = requests.get(url, timeout=30)
    j = json.loads(r.content.decode("utf-8"))
    return j
