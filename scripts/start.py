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
import sys, signal
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
import concurrent.futures
import random
from queue import Queue

MOST_TRADED_PAIRS_LIST = []
LESS_TRADED_PAIRS_LIST = []
TEST_LIST = []
list_filled = False


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


def do_test_list(q):
    TEST_LIST = []
    for _ in range(0, 10):
        TEST_LIST.append(random.randint(0, 100))
    list_filled = True
    q.put(TEST_LIST)
    time.sleep(10)


def do_something01(secs, q):
    print("do_something01")
    while True:
        try:
            date_time_current = datetime.now()
            date_time_next = date_time_current + timedelta(minutes=1)
            unix_date_time_current = int(time.mktime(date_time_current.timetuple()))
            unix_date_time_next = int(time.mktime(date_time_next.timetuple()))
            print("execute do_test_list")
            do_test_list(q)
            while unix_date_time_next > unix_date_time_current:
                try:
                    date_time_current = datetime.now()
                    unix_date_time_current = int(
                        time.mktime(date_time_current.timetuple())
                    )
                    time.sleep(secs)
                except KeyboardInterrupt:
                    print("shutdown initialized")
                    break
                except:
                    continue
        except KeyboardInterrupt:
            print("shutdown initialized")
            break
        except:
            continue
    print("Done do_something01! ")


def do_something02(secs, q):
    print("do_something02")
    my_test_list = []
    while True:
        my_test_list = q.get().copy()
        print("New List")
        for value in my_test_list:
            print(f"value: {value}")
        time.sleep(1)
        print(f"do_something02: list_filled: {list_filled}")

    print("Done do_something02! ")


def do_something03(secs):
    print("do_something03")
    time.sleep(secs)
    print("Done do_something03! ")


def do_something04(secs):
    print("do_something04")
    time.sleep(secs)
    print("Done do_something04! ")


def main():
    start = time.perf_counter()
    queue = Queue()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        f1 = executor.submit(do_something01, 1, queue)
        f2 = executor.submit(do_something02, 10, queue)
        f3 = executor.submit(do_something03, 1)
        f4 = executor.submit(do_something04, 1)

    print(f1.result(), f2.result(), f3.result(), f4.result())

    end = time.perf_counter()
    total = round(end - start, 2)
    print(f"Finished in {total} seconds")


def main1():
    watcher, account = deploy_watcher()
    dex_info = (
        get_dex_data()
    )  # um thread aqui(esta thread para procurar alterações de x em x tempo)
    for d in dex_info:
        size = len(d.pairs)
        print(
            f"dex name: {d.name} factory: {d.factory} router: {d.router} default_token: {d.default_token} pairs: {size} graph: {d.use_graph}"
        )
    # sempre que há o resultado do thread anterior
    dex_info_processor(watcher, account, dex_info)

    # havera um thread para processar o MOST_TRADED_PAIRS_LIST e
    # um outro thread para o LESS_TRADED_PAIRS_LIST
    # Um ultimo thread é para executar o resultado das duas threads anteriores
