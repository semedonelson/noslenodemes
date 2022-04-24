from brownie import config, network, accounts
from scripts.classes import oracle_data, ObjectEncoder, pair, dex, ethgasoracle
from scripts.getdata import run_query_post, get_prices_data, get_ethgasoracle
import csv
import json
from json import JSONEncoder
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal

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
    print("Starting get DEX data ...")
    dexs = []
    for dex_name in config["dex"]:
        print(f"Getting {dex_name} data ...")
        factory = config["dex"][dex_name]["factory"]
        router = config["dex"][dex_name]["router"]
        default_token = config["dex"][dex_name]["default_token"]
        use_graph = config["dex"][dex_name]["use_graph"]
        is_master = config["dex"][dex_name]["is_master"]
        return_records = REQUEST_SIZE
        # to remove
        total = 0
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
                    # to remove
                    total += return_records
                    print(f"Getting Pairs from {dex_name}. Total: {total}")
                    # add pair to the list
                    for pair in pairs:
                        pair["dailyVolumeUSD"] = 0
                        dex_pairs.append(pair)
                    id = pairs[-1]["id"]
                else:
                    print(
                        f"error request data to graph. dex: {dex_name} # url {url} # {query} # response: {my_dt}"
                    )
                    time.sleep(2)

            # get dailyVolumeUSD (last 24h)
            dex_pairs = pair_daily_Volume(dex_name, dex_pairs)
            # order pairs by dailyVolumeUSD
            dex_pairs.sort(key=lambda x: Decimal(x["dailyVolumeUSD"]), reverse=True)
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


def pair_daily_Volume(dex_name, pairs):
    print(f"Getting {dex_name} daily volume information ...")
    date_time = date.today() - timedelta(days=1)
    unix_time = int(time.mktime(date_time.timetuple()))
    url = config["dex"][dex_name]["graph_url"]
    return_records = REQUEST_SIZE
    skip = 0
    dailyVolumeInfo = []

    while return_records == REQUEST_SIZE:
        query = config["dex"][dex_name]["graph_daily_Volume_query"]
        query = query.replace("@size", str(REQUEST_SIZE))
        query = query.replace("@skip", str(skip))
        query = query.replace("@time", str(unix_time))
        my_dt = run_query_post(query, url)
        if "data" in my_dt:
            my_data = my_dt["data"]
            pairDayDatas = my_data["pairDayDatas"]
            return_records = len(pairDayDatas)
            skip = skip + return_records
            for p_d in pairDayDatas:
                dailyVolumeInfo.append(p_d)
            if skip > 5000:
                break

    total = len(dailyVolumeInfo)
    print(f"{dex_name} total pairs traded in last 24h: {total}")

    for pair in pairs:
        volume = get_volume_info_data(dailyVolumeInfo, pair["id"])
        if volume != None:
            pair["dailyVolumeUSD"] = Decimal(pair["dailyVolumeUSD"]) + Decimal(volume)

    return pairs


def get_volume_info_data(info_list, pair_address):
    try:
        info = next(x for x in info_list if x["pairAddress"] == pair_address)
        return info["dailyVolumeUSD"]
    except:
        pass


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


def get_liquidity_pairs_list_percentage():
    return int(config["liquidity_pairs_list_percentage"])


def get_prices():
    prices = {}
    response = get_prices_data()
    try:
        prices[config["token_weth"].lower()] = response["ethereum"]["usd"]
        prices[config["token_tether"].lower()] = response["tether"]["usd"]
        prices[config["token_usdc"].lower()] = response["usd-coin"]["usd"]
    except:
        pass
    return prices


def get_gas():
    gas = get_ethgasoracle()
    return gas
