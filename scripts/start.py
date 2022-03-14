from scripts.helpful_scripts import (
    read_chainlink_data,
    get_dex_data,
    get_token,
    list_of_tokens,
    get_account,
    get_dex_info,
    get_liquidity_pairs_list_percentage,
)
from scripts.classes import token, ObjectEncoder, dex_pair_info, dex_pair_final
import json
from json import JSONEncoder
from brownie import ChainWatcher
import sys

import time
from datetime import date
from datetime import datetime
from datetime import timedelta

MOST_TRADED_PAIRS_LIST = []
LESS_TRADED_PAIRS_LIST = []


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
            d_p = dex_pair_info(
                dx.name,
                pair["id"],
                pair["dailyVolumeUSD"],
                pair["token0"],
                pair["token1"],
            )
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
                                pair_m["dailyVolumeUSD"],
                                pair_m["token0"],
                                pair_m["token1"],
                            )
                            tmp_dex_pairs_list.append(d_p)
                            break
            if len(tmp_dex_pairs_list) > 1:
                final_dex_pairs_list.append(tmp_dex_pairs_list)
    final_dex_pairs_list.sort(
        key=lambda x: sum(p.dailyVolumeUSD for p in x), reverse=True
    )
    return final_dex_pairs_list


def dex_info_processor(watcher, account, dex_info):
    print("Processing pairs ....")
    final_dex_pairs_list = get_dex_pairs_list(dex_info)
    sz = len(final_dex_pairs_list)
    most_traded_dex_pairs_list, less_traded_dex_pairs_list = list_divide(
        final_dex_pairs_list
    )
    MOST_TRADED_PAIRS_LIST = list_prepare(most_traded_dex_pairs_list, dex_info)
    LESS_TRADED_PAIRS_LIST = list_prepare(less_traded_dex_pairs_list, dex_info)
    sz1 = len(MOST_TRADED_PAIRS_LIST)
    sz2 = len(LESS_TRADED_PAIRS_LIST)
    print("Finished processing pairs!")


def list_prepare(final_dex_pairs_list, dex_info):
    final_list = []
    for lst in final_dex_pairs_list:
        tmp_list = []
        for index_current, item_current in enumerate(lst):
            if index_current + 1 < len(lst) and index_current >= 0:
                for index_next, item_next in enumerate(lst):
                    if index_next > index_current:
                        curr_item = item_current
                        next_item = item_next
                        dex0_name = curr_item.dex_name
                        dex1_name = next_item.dex_name
                        dex_name = []
                        dex_name.append(dex0_name)
                        dex_name.append(dex1_name)
                        dex0_factory, dex0_router = get_dex_info(
                            dex_info, curr_item.dex_name
                        )
                        dex1_factory, dex1_router = get_dex_info(
                            dex_info, next_item.dex_name
                        )
                        factories = []
                        factories.append(dex0_factory)
                        factories.append(dex1_factory)
                        routers = []
                        routers.append(dex0_router)
                        routers.append(dex1_router)
                        pair0_id = curr_item.pair_id
                        pair1_id = next_item.pair_id
                        pairs = []
                        pairs.append(pair0_id)
                        pairs.append(pair1_id)
                        token0 = curr_item.token0["id"]
                        token1 = curr_item.token1["id"]
                        tokens = []
                        tokens.append(token0)
                        tokens.append(token1)
                        token0_decimals = curr_item.token0["decimals"]
                        token1_decimals = curr_item.token1["decimals"]
                        decimals = []
                        decimals.append(token0_decimals)
                        decimals.append(token1_decimals)
                        amount0 = 10 ** int(token0_decimals)
                        amount1 = 10 ** int(token1_decimals)
                        amounts = []
                        amounts.append(amount0)
                        amounts.append(amount1)
                        # create object
                        dpf = dex_pair_final(
                            dex_name,
                            factories,
                            routers,
                            pairs,
                            tokens,
                            decimals,
                            amounts,
                        )
                        tmp_list.append(dpf)
        final_list.append(tmp_list)
    return final_list


def check_profitability():
    # try:
    profit, amountOut, result, balance0, balance1 = watcher.validate(
        tokens,
        amounts,
        routers,
        pairs,
        {"from": account},
    )
    if profit > 0:
        print(
            f"profit: {profit} amountOut: {amountOut} token0: {result[0]} token1: {result[1]} balance0 0: {balance0[0]} balance0 1: {balance0[1]} balance1 0: {balance1[0]} balance1 1: {balance1[1]}"
        )
    # except:
    #    print("Oops!", sys.exc_info()[0], "occurred.")


def list_divide(final_dex_pairs_list):
    LUIQ_PAIR_PERC = get_liquidity_pairs_list_percentage()
    if LUIQ_PAIR_PERC < 10:
        LUIQ_PAIR_PERC = 10
    elif LUIQ_PAIR_PERC > 50:
        LUIQ_PAIR_PERC = 50
    size = len(final_dex_pairs_list)
    value = int(size * (LUIQ_PAIR_PERC / 100))
    first_part = final_dex_pairs_list[:value]
    second_part = final_dex_pairs_list[value:]
    return first_part, second_part


def main1():
    # test

    lst = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

    print("first_half")
    for v in first_half:
        print(f"value: {v}")
    print("second_half")
    for v in second_half:
        print(f"value: {v}")

    """
    https://stackoverflow.com/a/12032202
    import itertools

    for a,b,c in itertools.product(cc1, cc2, cc3):
        print a,b,c
    """
    """
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


def main():
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
