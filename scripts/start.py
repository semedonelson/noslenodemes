from scripts.helpful_scripts import (
    read_chainlink_data,
    get_dex_data,
    get_token,
    list_of_tokens,
    get_account,
    get_dex_info,
)
from scripts.classes import token, ObjectEncoder, dex_pair_info, cidade
import json
from json import JSONEncoder
from brownie import ChainWatcher
import sys

import time
from datetime import date
from datetime import datetime
from datetime import timedelta


def deploy_watcher():
    account = get_account()
    watcher = ChainWatcher.deploy(
        {"from": account},
    )
    print("Deployed Chain Watcher!")
    return watcher, account


def get_dex_pairs_list(dex_info):
    dx_processed = []
    final_dex_pairs_list = []
    for dx in dex_info:
        dx_processed.append(dx.name)
        for pair in dx.pairs:
            dx_pair_token0_id = pair["token0"]["id"]
            dx_pair_token1_id = pair["token1"]["id"]
            d_p = dex_pair_info(dx.name, pair["id"], pair["token0"], pair["token1"])
            tmp_dex_pairs_list = []
            tmp_dex_pairs_list.append(d_p)
            for dx_p in dex_info:
                if dx_p.name not in dx_processed:
                    for pair_m in dx_p.pairs:
                        dx_p_pair_m_token0_id = pair_m["token0"]["id"]
                        dx_p_pair_m_token1_id = pair_m["token1"]["id"]
                        if (
                            dx_pair_token0_id == dx_p_pair_m_token0_id
                            and dx_pair_token1_id == dx_p_pair_m_token1_id
                        ):
                            d_p = dex_pair_info(
                                dx_p.name,
                                pair_m["id"],
                                pair_m["token0"],
                                pair_m["token1"],
                            )
                            tmp_dex_pairs_list.append(d_p)
                            break
            if len(tmp_dex_pairs_list) > 1:
                final_dex_pairs_list.append(tmp_dex_pairs_list)
    return final_dex_pairs_list


def dex_info_processor(watcher, account, dex_info):
    print("Processing pairs ....")
    final_dex_pairs_list = get_dex_pairs_list(dex_info)
    for lst in final_dex_pairs_list:
        for index, dex_p in enumerate(lst):
            if index + 1 < len(lst) and index >= 0:
                curr_item = dex_p
                next_item = lst[index + 1]
                dex0_name = curr_item.dex_name
                dex1_name = next_item.dex_name
                dex0_factory, dex0_router = get_dex_info(dex_info, curr_item.dex_name)
                pair0_id = curr_item.pair_id
                dex1_factory, dex1_router = get_dex_info(dex_info, next_item.dex_name)
                pair1_id = next_item.pair_id
                token0 = curr_item.token0["id"]
                token1 = curr_item.token1["id"]
                token0_decimals = curr_item.token0["decimals"]
                token1_decimals = curr_item.token1["decimals"]
                amount0 = 10 ** int(token0_decimals)
                amount1 = 10 ** int(token1_decimals)
                tokens = []
                tokens.append(token0)
                tokens.append(token1)
                amounts = []
                amounts.append(amount0)
                amounts.append(amount1)
                routers = []
                routers.append(dex0_router)
                routers.append(dex1_router)
                # try:
                """
                print(
                    f"token0: {tokens[0]} token1: {tokens[1]} amount0: {amounts[0]} amount1: {amounts[1]} router0: {routers[0]} router1: {routers[1]}"
                )
                """
                profit, amountOut, result = watcher.validate(
                    tokens,
                    amounts,
                    routers,
                    {"from": account},
                )
                if profit > 0:
                    print(
                        f"profit: {profit} amountOut: {amountOut} token0: {result[0]} token1: {result[1]}"
                    )
                # except:
                #    print("Oops!", sys.exc_info()[0], "occurred.")
    print("Finished processing pairs!")


def main():
    cidades = []
    pt_cid = []
    c1 = cidade("lisboa", 1000)
    pt_cid.append(c1)
    c2 = cidade("porto", 500)
    pt_cid.append(c2)
    cidades.append(pt_cid)
    es_cid = []
    c3 = cidade("madrid", 2000)
    es_cid.append(c3)
    c4 = cidade("barcelona", 1500)
    es_cid.append(c4)
    cidades.append(es_cid)
    fr_cid = []
    c5 = cidade("paris", 2500)
    fr_cid.append(c5)
    c6 = cidade("lyon", 200)
    fr_cid.append(c6)
    cidades.append(fr_cid)
    cidades.sort(key=lambda x: sum(p.habitantes for p in x), reverse=True)
    for list in cidades:
        result = sum(p.habitantes for p in list)
        print(f"result: {result}")
        for c in list:
            print(f"nome: {c.nome} habitantes: {c.habitantes}")
    """
    tokens = []
    tokens.append("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2")
    tokens.append("0xdac17f958d2ee523a2206206994597c13d831ec7")
    amounts = []
    amounts.append(1000000000000000000)
    amounts.append(1000000)
    routers = []
    routers.append("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")
    routers.append("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")
    watcher, account = deploy_watcher()
    profit = 0
    amount = watcher.test(
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        1000000,
        "0xdac17f958d2ee523a2206206994597c13d831ec7",
        "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
        "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
        {"from": account},
    )
    print(f"profit: {profit} amount: {amount}")
    """


def main1():
    watcher, account = deploy_watcher()
    dex_info = get_dex_data()
    for d in dex_info:
        size = len(d.pairs)
        print(
            f"dex name: {d.name} factory: {d.factory} router: {d.router} default_token: {d.default_token} pairs: {size} graph: {d.use_graph}"
        )
    dex_info_processor(watcher, account, dex_info)
    # Multiprocessing a for loop
    # https://stackoverflow.com/a/20192251
    # https://docs.python.org/3/library/itertools.html
    # check


# erro: UniswapV2Library: INSUFFICIENT_INPUT_AMOUNT - https://github.com/Uniswap/v2-periphery/blob/master/contracts/libraries/UniswapV2Library.sol
# https://www.geeksforgeeks.org/python-remove-all-values-from-a-list-present-in-other-list/
# check pair for non graph dex


# https://github.com/Uniswap/v2-core/blob/master/contracts/UniswapV2Pair.sol
# reserve and balances
