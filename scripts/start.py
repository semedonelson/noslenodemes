from scripts.helpful_scripts import (
    read_chainlink_data,
    get_dex_data,
    get_token,
    list_of_tokens,
    get_account,
    get_dex_info,
    get_liquidity_pairs_list_percentage,
    get_prices,
)
from scripts.classes import token, ObjectEncoder, dex_pair_info, dex_pair_final
import json
from json import JSONEncoder
from brownie import config, ChainWatcher, FlashSwap, web3
import sys, signal
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
import concurrent.futures
import random
from queue import Queue
from decimal import Decimal

# Global variables
MOST_TRADED_PAIRS_LIST = []
LESS_TRADED_PAIRS_LIST = []
DEX_INFO_LIST = []
PRICES = {}
# Queues
queue_dex_info = Queue()
queue_most_traded_pairs = Queue()
queue_less_traded_pairs = Queue()
queue_dex_pair_final_list = Queue()


def deploy_watcher():
    account = get_account()
    watcher = ChainWatcher.deploy(
        {"from": account},
    )
    print("Deployed Chain Watcher Contract!")
    return watcher, account


def deploy_flash_swap():
    account = get_account()
    flash = FlashSwap.deploy(
        {"from": account},
    )
    print("Deployed Flash Swap Contract!")
    return flash, account


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


def dex_info_processor():
    while True:
        dex_info = queue_dex_info.get()
        for d in dex_info:
            size = len(d.pairs)
            print(
                f"dex name: {d.name} factory: {d.factory} router: {d.router} default_token: {d.default_token} pairs: {size} graph: {d.use_graph}"
            )
        print("Processing pairs ....")
        final_dex_pairs_list = get_dex_pairs_list(dex_info)
        queue_dex_pair_final_list.put(final_dex_pairs_list)
        most_traded_dex_pairs_list, less_traded_dex_pairs_list = list_divide(
            final_dex_pairs_list
        )
        MOST_TRADED_PAIRS_LIST = list_prepare(most_traded_dex_pairs_list, dex_info)
        LESS_TRADED_PAIRS_LIST = list_prepare(less_traded_dex_pairs_list, dex_info)
        queue_most_traded_pairs.put(MOST_TRADED_PAIRS_LIST)
        queue_less_traded_pairs.put(LESS_TRADED_PAIRS_LIST)
        print("Finished processing pairs! ")
        ## to be removed
        # break


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


def get_reserves():
    watcher = ChainWatcher[-1]
    dex_pair_final_list_tmp = []
    DEX_PAIR_FINAL_LIST = []
    while True:
        try:
            dex_pair_final_list_tmp = queue_dex_pair_final_list.get_nowait()
            if len(dex_pair_final_list_tmp) > 0:
                DEX_PAIR_FINAL_LIST = dex_pair_final_list_tmp
        except:
            pass

        tokens_reserves_tmp = {}
        for _dex_pair_final in DEX_PAIR_FINAL_LIST:
            # pair 0
            reserve0, reserve1 = watcher.getReservers(_dex_pair_final[0].pair_id)
            tokens_reserves_tmp[
                _dex_pair_final[0].pair_id, _dex_pair_final[0].token0
            ] = reserve0

            tokens_reserves_tmp[
                _dex_pair_final[0].pair_id, _dex_pair_final[0].token1
            ] = reserve1
            # pair 1
            reserve0, reserve1 = watcher.getReservers(_dex_pair_final[1].pair_id)
            tokens_reserves_tmp[
                _dex_pair_final[1].pair_id, _dex_pair_final[1].token0
            ] = reserve0

            tokens_reserves_tmp[
                _dex_pair_final[1].pair_id, _dex_pair_final[1].token1
            ] = reserve1
        queue_tokens_reserves.put(tokens_reserves_tmp)


def fill_dex_info():
    while True:
        try:
            date_time_current = datetime.now()
            date_time_next = date_time_current + timedelta(
                minutes=int(config["dex_info_process_cicle_minutes"])
            )
            unix_date_time_current = int(time.mktime(date_time_current.timetuple()))
            unix_date_time_next = int(time.mktime(date_time_next.timetuple()))
            DEX_INFO_LIST = get_dex_data()
            queue_dex_info.put(DEX_INFO_LIST)
            ## to be removed
            # break
            while unix_date_time_next > unix_date_time_current:
                try:
                    date_time_current = datetime.now()
                    unix_date_time_current = int(
                        time.mktime(date_time_current.timetuple())
                    )
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


def execute_most_traded_pairs():
    list_most_traded_pairs = []
    count = 0
    while True:
        start = time.perf_counter()
        if len(list_most_traded_pairs) > 0:
            count += 1
        try:
            list_most_traded_pairs = queue_most_traded_pairs.get_nowait()
        except:
            pass
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(check_profitability, list_most_traded_pairs)
        end = time.perf_counter()
        total = round(end - start, 2)
        """
        if len(list_most_traded_pairs) > 0:
            print(f" Most traded pairs Finished in {total} seconds cycle: {count}")
        """


def execute_less_traded_pairs():
    list_less_traded_pairs = []
    count = 0
    while True:
        start = time.perf_counter()
        if len(list_less_traded_pairs) > 0:
            count += 1
        try:
            list_less_traded_pairs = queue_less_traded_pairs.get_nowait()
        except:
            pass
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(check_profitability, list_less_traded_pairs)
        end = time.perf_counter()
        total = round(end - start, 2)
        """
        if len(list_less_traded_pairs) > 0:
            print(f" Less traded pairs Finished in {total} seconds cycle: {count}")
        """


def check_profitability(dex_pair_final_list):
    account = get_account()
    watcher = ChainWatcher[-1]
    for _dex_pair_final in dex_pair_final_list:
        amounts = []
        dex0_reserve0, dex0_reserve1 = watcher.getReservers(_dex_pair_final.pairs_id[0])
        dex1_reserve0, dex1_reserve1 = watcher.getReservers(_dex_pair_final.pairs_id[1])
        reserve0 = int(
            (int(config["percentage_amount_to_use"]) / 100)
            * min(dex0_reserve0, dex1_reserve0)
        )
        reserve1 = int(
            (int(config["percentage_amount_to_use"]) / 100)
            * min(dex0_reserve1, dex1_reserve1)
        )
        amounts.append(reserve0)
        amounts.append(reserve1)
        # try
        profit, amountOut, result = watcher.validate(
            _dex_pair_final.tokens,
            amounts,
            _dex_pair_final.routers,
            _dex_pair_final.pairs_id,
            {"from": account},
        )
        if profit > 0:
            if result[0] == _dex_pair_final.tokens[0]:
                _pairAddress = _dex_pair_final.pairs_id[0]
                _tokenBorrow = _dex_pair_final.tokens[0]
                _amountTokenPay = amountOut
                _sourceRouter = _dex_pair_final.routers[0]
                _targetRouter = _dex_pair_final.routers[1]
                swap_gas_cost(
                    _pairAddress,
                    _tokenBorrow,
                    _amountTokenPay,
                    _sourceRouter,
                    _targetRouter,
                )
                """
                _amountTokenPay_d = Decimal(_amountTokenPay) / Decimal(
                    10 ** int(_dex_pair_final.decimals[0])
                )
                reserve0_d = Decimal(dex0_reserve0) / Decimal(
                    10 ** int(_dex_pair_final.decimals[0])
                )
                reserve1_d = Decimal(dex0_reserve1) / Decimal(
                    10 ** int(_dex_pair_final.decimals[1])
                )
                gross_profit_usd = get_amount_usd_value(
                    _tokenBorrow.lower(),
                    _amountTokenPay_d,
                    reserve0_d,
                    reserve1_d,
                    _dex_pair_final.tokens[0].lower(),
                    _dex_pair_final.tokens[1].lower(),
                )
                r = round(gross_profit_usd, 1)
                print(f"gross_profit_usd: {gross_profit_usd} r: {r}")
                """
            elif result[0] == _dex_pair_final.tokens[1]:
                _pairAddress = _dex_pair_final.pairs_id[1]
                _tokenBorrow = _dex_pair_final.tokens[1]
                _amountTokenPay = amountOut
                _sourceRouter = _dex_pair_final.routers[1]
                _targetRouter = _dex_pair_final.routers[0]
                swap_gas_cost(
                    _pairAddress,
                    _tokenBorrow,
                    _amountTokenPay,
                    _sourceRouter,
                    _targetRouter,
                )
                """
                _amountTokenPay_d = Decimal(_amountTokenPay) / Decimal(
                    10 ** int(_dex_pair_final.decimals[1])
                )
                reserve0_d = Decimal(dex1_reserve0) / Decimal(
                    10 ** int(_dex_pair_final.decimals[0])
                )
                reserve1_d = Decimal(dex1_reserve1) / Decimal(
                    10 ** int(_dex_pair_final.decimals[1])
                )
                gross_profit_usd = get_amount_usd_value(
                    _tokenBorrow.lower(),
                    _amountTokenPay_d,
                    reserve0_d,
                    reserve1_d,
                    _dex_pair_final.tokens[0].lower(),
                    _dex_pair_final.tokens[1].lower(),
                )
                r = round(gross_profit_usd, 1)
                print(f"gross_profit_usd: {gross_profit_usd} r: {r}")
                """
        # except:
        #    print("Oops!", sys.exc_info()[0], "occurred.")


def fill_prices_info():
    global PRICES
    while True:
        pr = get_prices()
        if len(pr) > 0:
            PRICES = pr
        time.sleep(int(config["coingecko_prices_refresh_seconds"]))


def swap_gas_cost(
    _pairAddress,
    _tokenBorrow,
    _amountTokenPay,
    _sourceRouter,
    _targetRouter,
):
    flas_swap = FlashSwap[-1]
    account = get_account()
    total_block_number = web3.eth.blockNumber + 2

    web3_flas_swap = web3.eth.contract(address=flas_swap.address, abi=flas_swap.abi)
    estimated_gas = web3_flas_swap.functions.start(
        total_block_number,
        web3.toChecksumAddress(_pairAddress.lower()),
        web3.toChecksumAddress(_tokenBorrow.lower()),
        _amountTokenPay,
        web3.toChecksumAddress(_sourceRouter.lower()),
        web3.toChecksumAddress(_targetRouter.lower()),
    ).estimateGas({"from": web3.toChecksumAddress(account.address.lower())})
    print(f"Est. Gas:  {estimated_gas}")
    """
    print(f"total_block_number: {total_block_number}")
    flas_swap.start(
        total_block_number,
        web3.toChecksumAddress(_tokenBorrow.lower()),
        _amountTokenPay,
        web3.toChecksumAddress(_tokenPay.lower()),
        web3.toChecksumAddress(_sourceRouter.lower()),
        web3.toChecksumAddress(_targetRouter.lower()),
        web3.toChecksumAddress(_sourceFactory.lower()),
        {"from": account},
    )
    """


def get_amount_usd_value(token_borrow, amount, reserve0, reserve1, token0, token1):
    global PRICES
    token0_price = 0
    token1_price = 0
    pos = -1
    usd_price = 0
    try:
        token0_price = PRICES[token0]
        pos = 0
    except:
        pass
    try:
        token1_price = PRICES[token1]
        pos = 1
    except:
        pass

    if token_borrow == token0 and pos == 0:
        usd_price = amount * token0_price
    elif token_borrow == token1 and pos == 1:
        usd_price = amount * token1_price
    else:
        if token_borrow == token0:
            usd_price = ((reserve1 / reserve0) * token1_price) * amount
        elif token_borrow == token1:
            usd_price = ((reserve10 / reserve1) * token0_price) * amount

    return usd_price


def tst_fill_prices_info():
    global PRICES
    pr = get_prices()
    if len(pr) > 0:
        PRICES = pr


def main1():
    print("Starting main!")
    watcher, account = deploy_watcher()
    deploy_flash_swap()
    dex_name = []
    dex_name.append("uniswap")
    dex_name.append("sushiswap")
    factories = []
    factories.append("0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f")
    factories.append("0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac")
    routers = []
    routers.append("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")
    routers.append("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")
    pairs = []
    pairs.append("0x08b57d4e6404da14d41290fd4e4cc281eff7c517")
    pairs.append("0xf86710f80bb24d31fb219f06fe2953b825ab2975")
    tokens = []
    tokens.append("0x8dd4228605e467671941ffb4cae15cf7959c8d9d")
    tokens.append("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2")
    decimals = []
    decimals.append(18)
    decimals.append(18)
    amount0 = 10 ** int(18)
    amount1 = 10 ** int(18)
    amounts = []
    amounts.append(amount0)
    amounts.append(amount1)
    dpf = dex_pair_final(
        dex_name,
        factories,
        routers,
        pairs,
        tokens,
        decimals,
        amounts,
    )
    list_final = []
    list_final.append(dpf)
    check_profitability(list_final)
    """
    reserve0, reserve1 = watcher.getReservers(
        "0x9c84f58bb51fabd18698efe95f5bab4f33e96e8f"
    )
    tokens_reserves[
        "0x9c84f58bb51fabd18698efe95f5bab4f33e96e8f",
        "0xb620be8a1949aa9532e6a3510132864ef9bc3f82",
    ] = reserve0
    tokens_reserves[
        "0x9c84f58bb51fabd18698efe95f5bab4f33e96e8f",
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
    ] = reserve1
    key0 = (
        "0x9c84f58bb51fabd18698efe95f5bab4f33e96e8f",
        "0xb620be8a1949aa9532e6a3510132864ef9bc3f82",
    )
    my_r0 = tokens_reserves[key0]
    key1 = (
        "0x9c84f58bb51fabd18698efe95f5bab4f33e96e8f",
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
    )
    my_r1 = tokens_reserves[key1]
    print(f"reserve0: {my_r0} reserve1: {my_r1}")
    """
    """
    swap_gas_cost(
        "0x00040a7ebfc9f6fbce4d23bd66b79a603ba1c323",
        "0x2432c78801380ba2538f9bddf65c81d525e64db4",
        1000000000000000000,
        "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
        "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
    )
    """


def main():
    watcher, account = deploy_watcher()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        dx_list = executor.submit(fill_dex_info)
        dx_proc = executor.submit(dex_info_processor)
        lst_most_traded = executor.submit(execute_most_traded_pairs)
        lst_less_traded = executor.submit(execute_less_traded_pairs)
        prices = executor.submit(fill_prices_info)
        print(
            dx_list.result(),
            dx_proc.result(),
            lst_most_traded.result(),
            lst_less_traded.result(),
            prices.result(),
        )


if __name__ == "__main__":
    main()
# https://rednafi.github.io/digressions/python/2020/04/21/python-concurrent-futures.html
# https://www.adamsmith.haus/python/answers/how-to-use-a-global-variable-with-multiple-threads-in-python
# https://www.adamsmith.haus/python/examples/4035/threading-share-a-global-variable-between-two-threads
# web3_flas_swap.functions.start estimated_gas: 298750
