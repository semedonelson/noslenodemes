from brownie import config, network, accounts
from scripts.classes import oracle_data, ObjectEncoder, pair, dex
from scripts.getdata import run_query_post
import csv
import json
from json import JSONEncoder
import time

REQUEST_SIZE = 1000
FORKED_LOCAL_ENVIRONMENTS = ["mainnet-fork", "mainnet-fork-dev"]
LOCAL_BLOCKCHAIN_ENVIRONMENTS = ["development", "ganache-local"]


def read_chainlink_data():
    file = open("chainlink_price_feed.csv")
    csvreader = csv.reader(file)
    header = next(csvreader)
    oracles_info = []
    for row in csvreader:
        if "/" in row[0].split(";")[0]:
            pair0 = (row[0].split(";")[0]).split("/")[0]
            pair1 = (row[0].split(";")[0]).split("/")[1]
            decimal = row[0].split(";")[1]
            proxy = row[0].split(";")[2]
            o = oracle_data(pair0, pair1, decimal, proxy)
            oracles_info.append(o)
    file.close()
    json_string = json.dumps(oracles_info, indent=4, sort_keys=True, cls=ObjectEncoder)
    oracle_dict = json.loads(json_string)
    return oracle_dict


def get_dex_data():
    print("Starting get DEX data ....")
    dexs = []
    for dex_name in config["dex"]:
        print(f"Getting {dex_name} data ...")
        factory = config["dex"][dex_name]["factory"]
        router = config["dex"][dex_name]["router"]
        default_token = config["dex"][dex_name]["default_token"]
        use_graph = config["dex"][dex_name]["use_graph"]
        is_master = config["dex"][dex_name]["is_master"]
        return_records = REQUEST_SIZE
        dex_pairs = []
        id = ""
        # pairs
        if use_graph:
            print(f"Getting {dex_name} data from theGraph ...")
            while return_records == REQUEST_SIZE:
                url = config["dex"][dex_name]["graph_url"]
                query = config["dex"][dex_name]["graph_query"]
                query = query.replace("@id", id)
                query = query.replace("@size", str(REQUEST_SIZE))
                my_dt = run_query_post(query, url)
                if "data" in my_dt:
                    my_data = my_dt["data"]
                    pairs = my_data["pairs"]
                    return_records = len(pairs)
                    for pair in pairs:
                        dex_pairs.append(pair)
                    id = pairs[-1]["id"]
                else:
                    print(
                        f"error request data to graph. dex: {dex_name} # url {url} # {query} # response: {my_dt}"
                    )
                    time.sleep(2)
            json_string = json.dumps(
                dex_pairs, indent=4, sort_keys=True, cls=ObjectEncoder
            )
            pairs_dict = json.loads(json_string)
            # dex
            d = dex(
                dex_name,
                factory,
                router,
                default_token,
                pairs=pairs_dict,
                use_graph=use_graph,
                is_master=is_master,
            )
            dexs.append(d)
        else:
            # dex
            d = dex(
                dex_name,
                factory,
                router,
                default_token,
                pairs=[],
                use_graph=use_graph,
                is_master=is_master,
            )
            dexs.append(d)
    return dexs


def get_dex_info(dex_list, dex_name):
    for dex in dex_list:
        if dex.name == dex_name:
            return dex.factory, dex.router


def get_token(pairs, symbol):
    token = None
    for pair in pairs:
        if pair["token0"]["symbol"] == symbol:
            token = pair["token0"]["id"]
            break
        elif pair["token1"]["symbol"] == symbol:
            token = pair["token1"]["id"]
            break
    return token


def list_of_tokens(oracle_info):
    tokens = []
    for oracle in oracle_info:
        if oracle["pair0"] not in tokens:
            tokens.append(oracle["pair0"])
        if oracle["pair1"] not in tokens:
            tokens.append(oracle["pair1"])
    return tokens


def get_account(index=None, id=None):
    # accounts[0]
    # accounts.add("env")
    # accounts.load("id")
    if index:
        return accounts[index]
    if id:
        return accounts.load(id)
    if (
        network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS
        or network.show_active() in FORKED_LOCAL_ENVIRONMENTS
    ):
        return accounts[0]
    return accounts.add(config["wallets"]["from_key"])
