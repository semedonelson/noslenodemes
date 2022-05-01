from scripts.helpful_scripts import (
    read_chainlink_data,
    get_dex_data,
    get_token,
    list_of_tokens,
    get_account,
    get_dex_info,
    get_liquidity_pairs_list_percentage,
    get_prices,
    get_gas,
    get_weth,
    get_etherscan_weth_abi,
)
from scripts.classes import (
    token,
    ObjectEncoder,
    dex_pair_info,
    dex_pair_final,
    ethgasoracle,
    tokens_in_wallet,
    dex,
)
import json
from json import JSONEncoder
from brownie import config, ChainWatcher, FlashSwap, web3, network
import sys, signal
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
import concurrent.futures
import random
from queue import Queue
from decimal import Decimal
import traceback
from eth_abi import decode_single
from solcx import compile_standard, install_solc

# Global variables
MOST_TRADED_PAIRS_LIST = []
LESS_TRADED_PAIRS_LIST = []
PAIRS_LIST_TO_REMOVE = []
DEX_INFO_LIST = []
PRICES = {}
GAS = 0.0
SUGGEST_BASE_FEE = 0.0
WETH_BALANCE = 0
WETH_ABI = ""
TOKENS_IN_WALLET_LIST = []
# Queues
queue_dex_info = Queue()
queue_most_traded_pairs = Queue()
queue_less_traded_pairs = Queue()
queue_dex_pair_final_list = Queue()


def deploy_watcher():
    account = get_account()
    if len(ChainWatcher) == 0:
        watcher = ChainWatcher.deploy(
            {"from": account},
        )
        print("Deployed Chain Watcher Contract!")
    else:
        watcher = ChainWatcher[-1]
        print(f"Chain Watcher Contract already Deployed. Address: {watcher.address}")
    return watcher, account


def deploy_flash_swap():
    account = get_account()
    if len(FlashSwap) == 0:
        flash = FlashSwap.deploy(
            {"from": account},
        )
        print("Deployed Flash Swap Contract!")
    else:
        flash = FlashSwap[-1]
        print(f"Flash Swap Contract already Deployed. Address: {flash.address}")
    return flash, account


def get_dex_pairs_list(dex_info):
    dx_processed = []
    watcher = ChainWatcher[-1]
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
    watcher = ChainWatcher[-1]
    while True:
        dex_info = queue_dex_info.get()
        for d in dex_info:
            size = len(d.pairs)
            print("--------------------------------------------------")
            print(
                f"Dex Name: {d.name} \nFactory: {d.factory} \nRouter: {d.router} \nDefault Token: {d.default_token} \nPairs: {size} \nGraph: {d.use_graph}"
            )
        print("--------------------------------------------------")
        print("Processing pairs ....")
        final_dex_pairs_list = get_dex_pairs_list(dex_info)
        if bool(config["remove_min_threshould_pairs"]):
            lst_total = len(final_dex_pairs_list)
            print(
                f"Start preparing to remove list from 'less then thresould' pairs. Total: {lst_total}"
            )
            try:
                dex_pairs_list_itens_to_remove = []
                for itens_list in final_dex_pairs_list:
                    less_them_thresould = False
                    for item in itens_list:
                        reserve0 = 0
                        reserve1 = 0
                        try:
                            reserve0, reserve1 = watcher.getReservers(item.pair_id)
                        except:
                            continue
                        token0_value_usd = get_amount_usd_value(
                            item.token0["id"].lower(),
                            Decimal(reserve0)
                            / Decimal(10 ** int(item.token0["decimals"])),
                            Decimal(reserve0)
                            / Decimal(10 ** int(item.token0["decimals"])),
                            Decimal(reserve1)
                            / Decimal(10 ** int(item.token1["decimals"])),
                            item.token0["id"].lower(),
                            item.token1["id"].lower(),
                        )
                        if token0_value_usd < Decimal(
                            config["token_value_min_threshould"]
                        ):
                            less_them_thresould = True
                        token1_value_usd = get_amount_usd_value(
                            item.token1["id"].lower(),
                            Decimal(reserve1)
                            / Decimal(10 ** int(item.token1["decimals"])),
                            Decimal(reserve0)
                            / Decimal(10 ** int(item.token0["decimals"])),
                            Decimal(reserve1)
                            / Decimal(10 ** int(item.token1["decimals"])),
                            item.token0["id"].lower(),
                            item.token1["id"].lower(),
                        )
                        if token1_value_usd < Decimal(
                            config["token_value_min_threshould"]
                        ):
                            less_them_thresould = True
                        if less_them_thresould == True:
                            dex_pairs_list_itens_to_remove.append(item)
            except:
                pass
            # remove less then thresould pair in the final list
            for itens_list_to_rm in dex_pairs_list_itens_to_remove:
                for itens_list in final_dex_pairs_list:
                    if (
                        itens_list_to_rm.pair_id == itens_list[0].pair_id
                        or itens_list_to_rm.pair_id == itens_list[1].pair_id
                    ):
                        final_dex_pairs_list.remove(itens_list)
                        break
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
    global DEX_INFO_LIST
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
                time.sleep(60)
                try:
                    date_time_current = datetime.now()
                    unix_date_time_current = int(
                        time.mktime(date_time_current.timetuple())
                    )
                except KeyboardInterrupt:
                    print("shutdown initialized")
                    break
                except:
                    pass
                    continue
        except KeyboardInterrupt:
            print("shutdown initialized")
            break
        except:
            pass
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
        if len(list_most_traded_pairs) > 0:
            print(f" Most traded pairs Finished in {total} seconds cycle: {count}")


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
        if len(list_less_traded_pairs) > 0:
            print(f" Less traded pairs Finished in {total} seconds cycle: {count}")


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
        """
        reserve0_top = int(
            (int(config["top_percentage_amount_to_request"]) / 100)
            * min(dex0_reserve0, dex1_reserve0)
        )
        """
        reserve1 = int(
            (int(config["percentage_amount_to_use"]) / 100)
            * min(dex0_reserve1, dex1_reserve1)
        )
        """
        reserve1_top = int(
            (int(config["top_percentage_amount_to_request"]) / 100)
            * min(dex0_reserve1, dex1_reserve1)
        )
        """
        amounts.append(reserve0)
        amounts.append(reserve1)

        if reserve0 == 0 or reserve1 == 0:
            continue

        try:
            profit, amountOut, result = watcher.validate(
                _dex_pair_final.tokens,
                amounts,
                _dex_pair_final.routers,
                {"from": account},
            )
            if profit > 0:
                if result[0] == _dex_pair_final.tokens[0]:
                    _pairAddress = _dex_pair_final.pairs_id[0]
                    _tokenBorrow = _dex_pair_final.tokens[0]
                    """
                    if amountOut > reserve0_top:
                        reserve_percentage = Decimal((reserve0_top * 100) / amountOut)
                        amountOut = reserve0_top
                        profit = int(profit * (reserve_percentage / 100))
                    """
                    _amountTokenPay = amountOut
                    _sourceRouter = _dex_pair_final.routers[0]
                    _targetRouter = _dex_pair_final.routers[1]
                    _amountProfit_d = Decimal(profit) / Decimal(
                        10 ** int(_dex_pair_final.decimals[1])
                    )
                    reserve0_d = Decimal(dex0_reserve0) / Decimal(
                        10 ** int(_dex_pair_final.decimals[0])
                    )
                    reserve1_d = Decimal(dex0_reserve1) / Decimal(
                        10 ** int(_dex_pair_final.decimals[1])
                    )
                    gross_profit_usd = round(
                        get_amount_usd_value(
                            _tokenBorrow.lower(),
                            _amountProfit_d,
                            reserve0_d,
                            reserve1_d,
                            _dex_pair_final.tokens[0].lower(),
                            _dex_pair_final.tokens[1].lower(),
                        ),
                        2,
                    )
                    (
                        max_base_fee_per_gas,
                        max_priority_fee,
                        exec_cost_usd,
                        gas_limit,
                    ) = execution_cost(gross_profit_usd)
                    net_profit_usd = round(
                        Decimal(gross_profit_usd) - Decimal(exec_cost_usd), 2
                    )
                    if net_profit_usd > 0:
                        print(
                            f"Profit found: pair: {_pairAddress} token to borrow: {_tokenBorrow} amount: {_amountTokenPay} net profit USD: {net_profit_usd}"
                        )
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            start_s = executor.submit(
                                start_swap,
                                dex_pair_final_list,
                                _pairAddress,
                                _tokenBorrow,
                                _dex_pair_final.tokens[1],
                                _amountTokenPay,
                                _sourceRouter,
                                _targetRouter,
                                gas_limit,
                                max_base_fee_per_gas,
                                max_priority_fee,
                            )
                elif result[0] == _dex_pair_final.tokens[1]:
                    _pairAddress = _dex_pair_final.pairs_id[1]
                    _tokenBorrow = _dex_pair_final.tokens[1]
                    """
                    if amountOut > reserve1_top:
                        reserve_percentage = Decimal((reserve1_top * 100) / amountOut)
                        amountOut = reserve1_top
                        profit = int(profit * (reserve_percentage / 100))
                    """
                    _amountTokenPay = amountOut
                    _sourceRouter = _dex_pair_final.routers[1]
                    _targetRouter = _dex_pair_final.routers[0]
                    _amountProfit_d = Decimal(profit) / Decimal(
                        10 ** int(_dex_pair_final.decimals[0])
                    )
                    reserve0_d = Decimal(dex1_reserve0) / Decimal(
                        10 ** int(_dex_pair_final.decimals[0])
                    )
                    reserve1_d = Decimal(dex1_reserve1) / Decimal(
                        10 ** int(_dex_pair_final.decimals[1])
                    )
                    gross_profit_usd = round(
                        get_amount_usd_value(
                            _tokenBorrow.lower(),
                            _amountProfit_d,
                            reserve0_d,
                            reserve1_d,
                            _dex_pair_final.tokens[0].lower(),
                            _dex_pair_final.tokens[1].lower(),
                        ),
                        2,
                    )
                    (
                        max_base_fee_per_gas,
                        max_priority_fee,
                        exec_cost_usd,
                        gas_limit,
                    ) = execution_cost(gross_profit_usd)
                    net_profit_usd = round(
                        Decimal(gross_profit_usd) - Decimal(exec_cost_usd), 2
                    )
                    if net_profit_usd > 0:
                        print(
                            f"Profit found: pair: {_pairAddress} token to borrow: {_tokenBorrow} amount: {_amountTokenPay} net profit USD: {net_profit_usd}"
                        )
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            start_s = executor.submit(
                                start_swap,
                                dex_pair_final_list,
                                _pairAddress,
                                _tokenBorrow,
                                _dex_pair_final.tokens[0],
                                _amountTokenPay,
                                _sourceRouter,
                                _targetRouter,
                                gas_limit,
                                max_base_fee_per_gas,
                                max_priority_fee,
                            )
        except:
            error = traceback.format_exc()
            print(
                "Oops!",
                error,
                "occurred. pair0: ",
                _dex_pair_final.pairs_id[0],
                " pair1: ",
                _dex_pair_final.pairs_id[1],
                " amount0: ",
                amounts[0],
                " amount1: ",
                amounts[1],
            )


def fill_prices_info():
    global PRICES
    global GAS
    global SUGGEST_BASE_FEE
    WETH_ABI = get_etherscan_weth_abi()
    account = get_account()
    while True:
        try:
            # Prices
            pr = get_prices()
            if len(pr) > 0:
                PRICES = pr
            # Gas
            gas_oracle = get_gas()
            if config["gas_type"] == "fast":
                GAS = gas_oracle.fastGasPrice
            elif config["gas_type"] == "propose":
                GAS = gas_oracle.proposeGasPrice
            elif config["gas_type"] == "safe":
                GAS = gas_oracle.safeGasPrice
            else:
                GAS = gas_oracle.fastGasPrice

            SUGGEST_BASE_FEE = gas_oracle.suggestBaseFee
            check_balance(WETH_ABI)
            # sleep
            time.sleep(int(config["coingecko_prices_refresh_seconds"]))
        except:
            error = traceback.format_exc()
            print(f"fill_prices_info error: {error}")


def swap_tokens_estimate_gas(
    _tokenIn,
    _tokenOut,
    _amountIn,
    _amountOutMin,
    _router,
):
    flas_swap = FlashSwap[-1]
    account = get_account()

    web3_flas_swap = web3.eth.contract(address=flas_swap.address, abi=flas_swap.abi)
    estimated_gas = web3_flas_swap.functions.swap_tokens(
        web3.toChecksumAddress(_tokenIn.lower()),
        web3.toChecksumAddress(_tokenOut.lower()),
        _amountIn,
        _amountOutMin,
        web3.toChecksumAddress(_router.lower()),
    ).estimateGas({"from": web3.toChecksumAddress(account.address.lower())})
    print(f"Est. Gas:  {estimated_gas}")


def get_amount_usd_value(token_borrow, amount, reserve0, reserve1, token0, token1):
    global PRICES
    token0_price = 0.0
    token1_price = 0.0
    pos = -1
    usd_price = 0.0
    try:
        token0_price = Decimal(PRICES[token0])
        pos = 0
    except:
        pass
    try:
        token1_price = Decimal(PRICES[token1])
        pos = 1
    except:
        pass
    if pos > -1:
        if token_borrow == token0 and pos == 0:
            usd_price = Decimal(amount * token0_price)
        elif token_borrow == token1 and pos == 1:
            usd_price = Decimal(amount * token1_price)
        else:
            if token_borrow == token0:
                usd_price = Decimal(((reserve1 / reserve0) * token1_price) * amount)
            elif token_borrow == token1:
                usd_price = Decimal(((reserve0 / reserve1) * token0_price) * amount)
    return usd_price


def execution_cost(profit):
    global GAS
    global SUGGEST_BASE_FEE
    global PRICES
    max_priority_fee = Decimal(GAS) - Decimal(SUGGEST_BASE_FEE)
    base_fee_per_gas = Decimal(GAS) * Decimal(config["base_fee_multiplier"])

    if profit < Decimal(config["profit_level1"]):
        max_priority_fee = max_priority_fee * max(
            Decimal(1.0), Decimal(config["profit_level1_priority_feed_multiplier"])
        )
    elif profit < Decimal(config["profit_level2"]):
        max_priority_fee = max_priority_fee * max(
            Decimal(1.0), Decimal(config["profit_level2_priority_feed_multiplier"])
        )
    elif profit < Decimal(config["profit_level3"]):
        max_priority_fee = max_priority_fee * max(
            Decimal(1.0), Decimal(config["profit_level3_priority_feed_multiplier"])
        )
    elif profit < Decimal(config["profit_level4"]):
        max_priority_fee = max_priority_fee * max(
            Decimal(1.0), Decimal(config["profit_level4_priority_feed_multiplier"])
        )
    else:
        max_priority_fee = max_priority_fee * max(
            Decimal(1.0), Decimal(config["profit_level_other_priority_feed_multiplier"])
        )
    max_base_fee_per_gas = base_fee_per_gas + max_priority_fee
    max_base_fee_per_gas_wei = int(Decimal(max_base_fee_per_gas) * (Decimal(10) ** 9))
    max_base_fee_per_gas_ether = web3.fromWei(max_base_fee_per_gas_wei, "ether")
    eth_price = Decimal(PRICES[config["token_weth"].lower()])
    gas_limit = int(config["gas_limit_start_swap"])
    cost = (eth_price * max_base_fee_per_gas_ether) * gas_limit
    latest_block = web3.eth.getBlock("latest")

    return (
        int(max_base_fee_per_gas),
        int(max_priority_fee),
        round(cost, 2),
        gas_limit,
    )


def tst_fill_prices_info():
    global PRICES
    global GAS
    global SUGGEST_BASE_FEE
    # Prices
    pr = get_prices()
    if len(pr) > 0:
        PRICES = pr
    # Gas
    gas_oracle = get_gas()
    if config["gas_type"] == "fast":
        GAS = gas_oracle.fastGasPrice
    elif config["gas_type"] == "propose":
        GAS = gas_oracle.proposeGasPrice
    elif config["gas_type"] == "safe":
        GAS = gas_oracle.safeGasPrice
    else:
        GAS = gas_oracle.fastGasPrice

    SUGGEST_BASE_FEE = gas_oracle.suggestBaseFee


def swap_tokens(tokenIn, tokenOut, amountIn, account, json_abi):
    global TOKENS_IN_WALLET_LIST
    watcher = ChainWatcher[-1]
    flash = FlashSwap[-1]
    tokens = []
    tokens.append(tokenIn)
    tokens.append(tokenOut)
    dx1 = dex(
        "uniswap",
        "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
        "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
        "WETH",
        1000,
        True,
        True,
    )
    dx2 = dex(
        "sushiswap",
        "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac",
        "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
        "WETH",
        1000,
        True,
        True,
    )
    DEX_INFO_LIST.append(dx1)
    DEX_INFO_LIST.append(dx2)
    maxAmountOut = 0
    router = ""
    for dx in DEX_INFO_LIST:
        amountOut = 0
        try:
            amountOut = watcher.getAmountsOut(dx.router, amountIn, tokens)
            if amountOut > maxAmountOut:
                maxAmountOut = amountOut
                router = dx.router
        except Exception as e:
            continue
    if maxAmountOut > 0:
        min_depre = Decimal(config["min_depre_percentage_token_swap"])
        maxAmountOut = int(maxAmountOut - (maxAmountOut * (min_depre / 100)))
        print(f"router: {router} maxAmountOut: {maxAmountOut}")
        try:
            token_contract = web3.eth.contract(
                address=web3.toChecksumAddress(tokenIn.lower()),
                abi=json_abi,
            )
            print(f"Start approve Flash contract to spend {amountIn} of {tokenIn}")
            tx_hash = token_contract.functions.approve(
                flash.address, amountIn
            ).transact({"from": account.address})
            x_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            print(
                f"Start swap {amountIn} of {tokenIn} to at least {maxAmountOut} of {tokenOut}."
            )
            swap = flash.swap_tokens(
                tokenIn, tokenOut, amountIn, maxAmountOut, router, {"from": account}
            )
            swap.wait(1)
            if network.show_active() != "mainnet":
                if tokenOut not in TOKENS_IN_WALLET_LIST:
                    t_in_w = tokens_in_wallet(tokenOut, 0)
                    TOKENS_IN_WALLET_LIST.append(t_in_w)
        except Exception as e:
            print("Error: ", e)


def check_convertions(json_abi):
    account = get_account()
    global TOKENS_IN_WALLET_LIST
    global DEX_INFO_LIST
    minimum_weth_target_wei = web3.toWei(
        Decimal(config["minimum_weth_target"]), "ether"
    )

    weth_contract = web3.eth.contract(
        address=web3.toChecksumAddress(config["token_weth"].lower()), abi=json_abi
    )
    weth_amount_wei = weth_contract.functions.balanceOf(account.address).call()
    ether_amount_wei = web3.eth.getBalance(account.address)
    if weth_amount_wei < minimum_weth_target_wei:
        if ether_amount_wei > 0:
            if minimum_weth_target_wei - weth_amount_wei > ether_amount_wei:
                get_weth(ether_amount_wei)
            else:
                get_weth(minimum_weth_target_wei - weth_amount_wei)

    swap_tokens(
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "0xdac17f958d2ee523a2206206994597c13d831ec7",
        web3.toWei(1.0, "ether"),
        account,
        json_abi,
    )


def check_balance(json_abi):
    global WETH_BALANCE
    global PRICES
    global TOKENS_IN_WALLET_LIST
    account = get_account()

    if len(TOKENS_IN_WALLET_LIST) == 0:
        t_in_w = tokens_in_wallet(config["token_weth"], 0)
        TOKENS_IN_WALLET_LIST.append(t_in_w)

    check_convertions(json_abi)
    TOKENS_IN_WALLET_LIST = get_tokens_in_wallet(json_abi, account)
    if len(PRICES) > 0:
        ether_amount = web3.fromWei(web3.eth.getBalance(account.address), "ether")
        ether_amount_usd = round(
            ether_amount * Decimal(PRICES[config["token_weth"]]), 2
        )
        print(f"Ether amount: {ether_amount} Ether USD: {ether_amount_usd}")

        print("Tokens in wallet:")
        count = 0
        weth_current_amount = 0
        for tk in TOKENS_IN_WALLET_LIST:
            if tk.amount > 0:
                count += 1
                if tk.token == config["token_weth"]:
                    amount_usd = round(
                        web3.fromWei(tk.amount, "ether")
                        * Decimal(PRICES[config["token_weth"]]),
                        2,
                    )
                    amount_ether = web3.fromWei(tk.amount, "ether")
                    print(
                        f"{count} - token: {tk.token} amount: {amount_ether} USD: {amount_usd}"
                    )
                else:
                    print(f"{count} - token: {tk.token} amount: {tk.amount}")


def start_swap(
    dex_pair_final_list,
    pairAddress,
    tokenBorrow,
    tokenOther,
    amountTokenPay,
    sourceRouter,
    targetRouter,
    gasLimit,
    maxFeePerGas,
    maxPriorityFeePerGas,
):
    flash_swap = FlashSwap[-1]
    account = get_account()
    total_block_number = web3.eth.block_number + 2
    try:
        swap_trx = flash_swap.start(
            total_block_number,
            pairAddress,
            tokenBorrow,
            amountTokenPay,
            sourceRouter,
            targetRouter,
            {
                "from": account,
                "gasLimit": gasLimit,
                "maxFeePerGas": maxFeePerGas,
                "maxPriorityFeePerGas": maxPriorityFeePerGas,
            },
        )
        swap_trx.wait(1)
        check_profitability(dex_pair_final_list)
        print(f"Profit for pair {pairAddress} executed.")
        if network.show_active() != "mainnet":
            if tokenOther not in TOKENS_IN_WALLET_LIST:
                t_in_w = tokens_in_wallet(tokenOther, 0)
                TOKENS_IN_WALLET_LIST.append(t_in_w)

    except Exception as e:
        error = traceback.format_exc()
        print("Error executing swap. Error: ", error)
        # remove from list
        errors = config["list_errors_to_remove_pairs"].split(";")
        if error.find("eth_abi.exceptions.NonEmptyPaddingBytes") != -1:
            PAIRS_LIST_TO_REMOVE.append(dex_pair_final_list)
            print(f"pair {pairAddress} added on the lis to be removed.")
        else:
            for er in errors:
                if error.find(er) != -1 or (
                    e.__str__().find("revert") != -1
                    and e.__str__().find("revert:") == -1
                ):
                    try:
                        PAIRS_LIST_TO_REMOVE.append(dex_pair_final_list)
                        print(f"pair {pairAddress} added on the lis to be removed.")
                        break
                    except:
                        pass
                    break


def get_tokens_in_wallet(json_abi, account):
    global TOKENS_IN_WALLET_LIST
    if network.show_active() == "mainnet":
        pass  # go get from bsscan
    else:
        for tk in TOKENS_IN_WALLET_LIST:
            contract = web3.eth.contract(
                address=web3.toChecksumAddress(tk.token.lower()), abi=json_abi
            )
            qty = contract.functions.balanceOf(account.address).call()
            tk.amount = qty
    return TOKENS_IN_WALLET_LIST


def remove_pairs_with_errors(global_list, list_to_remove):
    list_removed = []
    try:
        for itens_list_to_rm in list_to_remove:
            for item_list in global_list:
                if (
                    itens_list_to_rm[0].pairs_id[0] == item_list[0].pairs_id[0]
                    and itens_list_to_rm[0].pairs_id[1] == item_list[0].pairs_id[1]
                ):
                    global_list.remove(item_list)
                    list_removed.append(itens_list_to_rm)
                    print("item removed from the list")
                    break

        for itn in list_removed:
            for itens_list_to_rm in list_to_remove:
                if (
                    itn[0].pairs_id[0] == itens_list_to_rm[0].pairs_id[0]
                    and itn[0].pairs_id[1] == itens_list_to_rm[0].pairs_id[1]
                ):
                    list_to_remove.remove(itens_list_to_rm)
                    break
    except:
        error = traceback.format_exc()
        print("remove_pairs_with_errors error ", error)

    return global_list, list_to_remove


def no_multithreads_sending_swaps():
    list_most_traded_pairs = []
    list_less_traded_pairs = []
    global PAIRS_LIST_TO_REMOVE
    while True:
        try:
            try:
                list_most_traded_pairs = queue_most_traded_pairs.get_nowait()
            except:
                pass

            if len(PAIRS_LIST_TO_REMOVE) > 0:
                (
                    list_most_traded_pairs,
                    PAIRS_LIST_TO_REMOVE,
                ) = remove_pairs_with_errors(
                    list_most_traded_pairs, PAIRS_LIST_TO_REMOVE
                )

            if len(list_most_traded_pairs) > 0:
                print("Start Executing Most Traded Pairs")
            for dex_pair_final_list in list_most_traded_pairs:
                check_profitability(dex_pair_final_list)
            if len(list_most_traded_pairs) > 0:
                print("End Executing Most Traded Pairs")
            # ---------------------------------
            if len(PAIRS_LIST_TO_REMOVE) > 0:
                (
                    list_less_traded_pairs,
                    PAIRS_LIST_TO_REMOVE,
                ) = remove_pairs_with_errors(
                    list_less_traded_pairs, PAIRS_LIST_TO_REMOVE
                )

            try:
                list_less_traded_pairs = queue_less_traded_pairs.get_nowait()
            except:
                pass
            if len(list_less_traded_pairs) > 0:
                print("Start Executing Less Traded Pairs")
            for dex_pair_final_list in list_less_traded_pairs:
                check_profitability(dex_pair_final_list)
            if len(list_less_traded_pairs) > 0:
                print("End Executing Less Traded Pairs")
        except:
            error = traceback.format_exc()
            print("Error: ", error)


def test():
    global GAS
    global SUGGEST_BASE_FEE
    fill_prices_info()
    (
        max_base_fee_per_gas,
        max_priority_fee,
        cost,
        gas_limit,
    ) = execution_cost(100000)
    print(f"GAS: {GAS} SUGGEST_BASE_FEE: {SUGGEST_BASE_FEE}")
    print(
        f"max_base_fee: {max_base_fee_per_gas} max_priority_fee: {max_priority_fee} cost: {cost} gas_limit: {gas_limit}"
    )


def main():
    global WETH_ABI
    deploy_flash_swap()
    deploy_watcher()
    WETH_ABI = get_etherscan_weth_abi()
    tst_fill_prices_info()
    check_balance(WETH_ABI)
    # fill_prices_info()


def main1():
    print("Starting main!")
    pair0 = "0x6b0b819494a3b789439f32fb0097a625b16b5225"
    pair1 = "0x89fa2fd7dd529d70912b434269843389c5575822"
    token0 = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    token1 = "0xc7924bf912ebc9b92e3627aed01f816629c7e400"
    watcher, account = deploy_watcher()
    dex0_reserve0, dex0_reserve1 = watcher.getReservers(pair0)
    dex1_reserve0, dex1_reserve1 = watcher.getReservers(pair1)
    print(
        f"dex0_reserve0: {dex0_reserve0} dex0_reserve1: {dex0_reserve1} dex1_reserve0: {dex1_reserve0} dex1_reserve1: {dex1_reserve1}"
    )
    reserve0 = int(
        (int(config["percentage_amount_to_use"]) / 100)
        * min(dex0_reserve0, dex1_reserve0)
    )
    reserve1 = int(
        (int(config["percentage_amount_to_use"]) / 100)
        * min(dex0_reserve1, dex1_reserve1)
    )
    print(f"reserve0: {reserve0} reserve1: {reserve1}")
    """
    tokens = []
    tokens.append("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2")
    tokens.append("0xc7924bf912ebc9b92e3627aed01f816629c7e400")
    amounts = []
    amounts.append(reserve0)
    amounts.append(reserve1)
    routers = []
    routers.append("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")
    routers.append("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")
    pairs = []
    pairs.append("0x6b0b819494a3b789439f32fb0097a625b16b5225")
    pairs.append("0x89fa2fd7dd529d70912b434269843389c5575822")
    profit, amountOut, result = watcher.validate(
        tokens,
        amounts,
        routers,
        {"from": account},
    )
    print(
        f"profit: {profit} amountOut: {amountOut} result0: {result[0]} result1: {result[1]}"
    )
    """
    """
    deploy_flash_swap()
    _pairAddress = "0x6b0b819494a3b789439f32fb0097a625b16b5225"
    _tokenBorrow = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    _amountTokenPay = 10000000
    _sourceRouter = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    _targetRouter = "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"
    gas_limit = 330000
    max_base_fee_per_gas = 150
    max_priority_fee = 10
    dex_pair_final_list = []
    start_swap(
        dex_pair_final_list,
        _pairAddress,
        _tokenBorrow,
        _amountTokenPay,
        _sourceRouter,
        _targetRouter,
        gas_limit,
        max_base_fee_per_gas,
        max_priority_fee,
    )
    """
    watcher, account = deploy_watcher()
    flash, acc = deploy_flash_swap()
    tst_fill_prices_info()
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
    pairs.append(pair0)
    pairs.append(pair1)
    tokens = []
    tokens.append(token0)
    tokens.append(token1)
    decimals = []
    decimals.append(18)
    decimals.append(18)
    amount0 = reserve0
    amount1 = reserve1
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
    # profit, amountOut, result = watcher.validate(tokens, amounts, routers, {"from": account},)
    # print(f"profit: {profit} amountOut: {amountOut}")
    check_profitability(list_final)


def main0():
    global WETH_ABI
    WETH_ABI = get_etherscan_weth_abi()
    check_balance(WETH_ABI)
    deploy_watcher()
    deploy_flash_swap()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        prices = executor.submit(fill_prices_info)
        dx_list = executor.submit(fill_dex_info)
        dx_proc = executor.submit(dex_info_processor)
        if bool(config["use_multithreads_for_sending_swaps"]):
            lst_most_traded = executor.submit(execute_most_traded_pairs)
            lst_less_traded = executor.submit(execute_less_traded_pairs)
        else:
            exec_swaps = executor.submit(no_multithreads_sending_swaps)
        print(
            dx_list.result(),
            dx_proc.result(),
            lst_most_traded.result(),
            lst_less_traded.result(),
            prices.result(),
        )


if __name__ == "__main__":
    main()
# https://docs.uniswap.org/protocol/V2/reference/smart-contracts/common-errors
# web3_flas_swap.functions.start estimated_gas: 298750
# get weth - https://github.com/PatrickAlphaC/aave_brownie_py_freecode
# https://docs.uniswap.org/protocol/V2/reference/smart-contracts/router-02
