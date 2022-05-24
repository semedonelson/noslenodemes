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
    get_coingecko_token,
    get_coingecko_token_details,
    get_deploy_cost,
)
from scripts.classes import (
    token,
    ObjectEncoder,
    dex_pair_info,
    dex_pair_final,
    ethgasoracle,
    tokens_in_wallet,
    dex,
    tokens_coingecko_price,
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
import logging

# Global variables
MOST_TRADED_PAIRS_LIST = []
LESS_TRADED_PAIRS_LIST = []
PAIRS_LIST_TO_REMOVE = []
DEX_INFO_LIST = []
GAS = 0.0
SUGGEST_BASE_FEE = 0.0
WETH_BALANCE = 0
WETH_ABI = ""
ACCOUNT = None
TOKENS_IN_WALLET_LIST = []
COINGECKO_TOKEN_LIST = []
TOKENS_PRICES_LIST = []
DEFAULT_TOKENS_LIST = []
DEFAULT_TOKENS_PRICES_LIST = []
# Queues
queue_dex_info = Queue()
queue_most_traded_pairs = Queue()
queue_less_traded_pairs = Queue()
queue_dex_pair_final_list = Queue()

# Create Logger
logger = logging.getLogger("start")
logger.setLevel(logging.DEBUG)
# Create console handler and set level to debug
fh = logging.FileHandler("flashswap.log")
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
fh.setLevel(logging.INFO)
# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# add formatter to ch
ch.setFormatter(formatter)
fh.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch)
logger.addHandler(fh)


def coingecko_list_tokens():
    global COINGECKO_TOKEN_LIST
    logger.info("Get coingecko tokens list ...")
    COINGECKO_TOKEN_LIST = get_coingecko_token()
    total = len(COINGECKO_TOKEN_LIST)
    logger.info(f"Total of coingecko tokens: {total}")


def deploy_watcher(gasLimit, maxFeePerGas, maxPriorityFeePerGas):
    global ACCOUNT
    account = ACCOUNT
    if len(ChainWatcher) == 0:
        watcher = ChainWatcher.deploy(
            {
                "from": account,
                "gasLimit": gasLimit,
                "maxFeePerGas": maxFeePerGas,
                "maxPriorityFeePerGas": maxPriorityFeePerGas,
            },
        )
        logger.info("Deployed Chain Watcher Contract!")
    else:
        watcher = ChainWatcher[-1]
        logger.info(
            f"Chain Watcher Contract already Deployed. Address: {watcher.address}"
        )
    return watcher, account


def deploy_flash_swap(gasLimit, maxFeePerGas, maxPriorityFeePerGas):
    global ACCOUNT
    account = ACCOUNT
    if len(FlashSwap) == 0:
        flash = FlashSwap.deploy(
            {
                "from": account,
                "gasLimit": gasLimit,
                "maxFeePerGas": maxFeePerGas,
                "maxPriorityFeePerGas": maxPriorityFeePerGas,
            },
        )
        logger.info("Deployed Flash Swap Contract!")
    else:
        flash = FlashSwap[-1]
        logger.info(f"Flash Swap Contract already Deployed. Address: {flash.address}")
    return flash, account


def process_dex_pairs_list_tokens(final_dex_pairs_list):
    global TOKENS_PRICES_LIST
    global DEFAULT_TOKENS_PRICES_LIST
    tokens_list = []
    pairs_to_remove = []
    tokens_added = []
    tokens_not_found = []
    logger.info("Starting setup tokens price list ...")
    try:
        for pairs_list in final_dex_pairs_list:
            token0_found = False
            token1_found = False
            for pair in pairs_list:
                token0 = pair.token0["id"]
                token1 = pair.token1["id"]
                symbol0 = pair.token0["symbol"]
                symbol1 = pair.token1["symbol"]
                decimal0 = pair.token0["decimals"]
                decimal1 = pair.token1["decimals"]

                if token0 in DEFAULT_TOKENS_LIST:
                    if len(DEFAULT_TOKENS_PRICES_LIST) < len(DEFAULT_TOKENS_LIST):
                        if (
                            next(
                                (
                                    x.token
                                    for x in DEFAULT_TOKENS_PRICES_LIST
                                    if x.token == token0
                                ),
                                None,
                            )
                            == None
                        ):
                            coingecko_id0 = get_coingecko_id_by_symbol(symbol0, token0)
                            if len(coingecko_id0) == 1:
                                token0_found = True
                                t_c_p = tokens_coingecko_price(
                                    token0, coingecko_id0[0], symbol0, decimal0, 0, 0
                                )
                                DEFAULT_TOKENS_PRICES_LIST.append(t_c_p)
                                tokens_added.append(token0)
                    else:
                        continue
                else:
                    if token0 not in tokens_not_found:
                        if token0 not in tokens_added:
                            coingecko_id0 = get_coingecko_id_by_symbol(symbol0, token0)
                            if len(coingecko_id0) == 1:
                                token0_found = True
                                t_c_p = tokens_coingecko_price(
                                    token0, coingecko_id0[0], symbol0, decimal0, 0, 0
                                )
                                tokens_list.append(t_c_p)
                                tokens_added.append(token0)
                            else:
                                tokens_not_found.append(token0)
                        else:
                            token0_found = True

                if token1 in DEFAULT_TOKENS_LIST:
                    if len(DEFAULT_TOKENS_PRICES_LIST) < len(DEFAULT_TOKENS_LIST):
                        if (
                            next(
                                (
                                    x.token
                                    for x in DEFAULT_TOKENS_PRICES_LIST
                                    if x.token == token1
                                ),
                                None,
                            )
                            == None
                        ):
                            coingecko_id1 = get_coingecko_id_by_symbol(symbol1, token1)
                            if len(coingecko_id1) == 1:
                                token1_found = True
                                t_c_p = tokens_coingecko_price(
                                    token1, coingecko_id1[0], symbol1, decimal1, 0, 0
                                )
                                DEFAULT_TOKENS_PRICES_LIST.append(t_c_p)
                                tokens_added.append(token1)
                    else:
                        continue
                else:
                    if token1 not in tokens_not_found:
                        if token1 not in tokens_added:
                            coingecko_id1 = get_coingecko_id_by_symbol(symbol1, token1)
                            if len(coingecko_id1) == 1:
                                token1_found = True
                                t_c_p = tokens_coingecko_price(
                                    token1, coingecko_id1[0], symbol1, decimal1, 0, 0
                                )
                                tokens_list.append(t_c_p)
                                tokens_added.append(token1)
                            else:
                                tokens_not_found.append(token1)
                        else:
                            token1_found = True

                if token0_found == False and token1_found == False:
                    pairs_to_remove.append(pair.pair_id)

        for p in pairs_to_remove:
            for pairs_list in final_dex_pairs_list:
                found = False
                for pair in pairs_list:
                    if pair.pair_id.lower() == p.lower():
                        final_dex_pairs_list.remove(pairs_list)
                        found = True
                        break
                if found == True:
                    break
        TOKENS_PRICES_LIST = tokens_list
    except Exception as e:
        logger.exception("process_dex_pairs_list_tokens error: ")

    return final_dex_pairs_list


def get_coingecko_id_by_symbol(symbol, token):
    global COINGECKO_TOKEN_LIST
    ids = []
    token_details_url = config["coingecko_tokens_details_url"]
    for item in COINGECKO_TOKEN_LIST:
        if item["symbol"].lower() == symbol.lower():
            ids.append(item["id"])
    if len(ids) > 1:
        correct_id = ""
        found = False
        for id in ids:
            id_retrived = ""
            try:
                id_retrived = get_coingecko_token_details(
                    token_details_url.replace("@token_id", id)
                )
            except:
                continue
            if id_retrived.lower() == token.lower():
                correct_id = id
                found = True
                break
        if found == True:
            ids = []
            ids.append(correct_id)
        else:
            ids = []

    return ids


def get_dex_pairs_list(dex_info):
    dx_processed = []
    watcher = ChainWatcher[-1]
    final_dex_pairs_list = []
    tokens_to_excluse = config["tokens_to_exclude"].split(";")
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
                            dx_p_pair_m_token0_id in tokens_to_excluse
                            or dx_pair_token1_id in tokens_to_excluse
                        ):
                            continue

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
            logger.info("--------------------------------------------------")
            logger.info(
                f"Dex Name: {d.name} \nFactory: {d.factory} \nRouter: {d.router} \nDefault Token: {d.default_token} \nPairs: {size} \nGraph: {d.use_graph}"
            )
        logger.info("--------------------------------------------------")
        logger.info("Processing pairs ....")
        final_dex_pairs_list = get_dex_pairs_list(dex_info)
        logger.debug("Setup the pairs list based on Coingecko Tokens price list")
        final_dex_pairs_list = process_dex_pairs_list_tokens(final_dex_pairs_list)
        if bool(config["remove_min_threshould_pairs"]):
            lst_total = len(final_dex_pairs_list)
            logger.debug(
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
                        )
                        if token0_value_usd < Decimal(
                            config["token_value_min_threshould"]
                        ):
                            less_them_thresould = True
                        token1_value_usd = get_amount_usd_value(
                            item.token1["id"].lower(),
                            Decimal(reserve1)
                            / Decimal(10 ** int(item.token1["decimals"])),
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
        logger.info("Finished processing pairs! ")
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
            coingecko_list_tokens()
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
                    logger.debug("shutdown initialized")
                    break
                except:
                    pass
                    continue
        except KeyboardInterrupt:
            logger.debug("shutdown initialized")
            break
        except:
            pass
            continue


def execute_most_traded_pairs():
    global PAIRS_LIST_TO_REMOVE
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

        try:
            if len(PAIRS_LIST_TO_REMOVE) > 0:
                (
                    list_most_traded_pairs,
                    PAIRS_LIST_TO_REMOVE,
                ) = remove_pairs_with_errors(
                    list_most_traded_pairs, PAIRS_LIST_TO_REMOVE
                )

            if bool(config["use_multithreads_for_sending_swaps"]):
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    executor.map(check_profitability, list_most_traded_pairs)
            else:
                for dex_pair_final_list in list_most_traded_pairs:
                    check_profitability(dex_pair_final_list)

            end = time.perf_counter()
            total = round(end - start, 2)
            if len(list_most_traded_pairs) > 0:
                end_time = datetime.now()
                logger.debug(
                    f"{end_time} - Most traded pairs Finished in {total} seconds cycle: {count}"
                )
        except Exception as e:
            logger.exception("execute_most_traded_pairs error: ")


def execute_less_traded_pairs():
    global PAIRS_LIST_TO_REMOVE
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

        try:
            if len(PAIRS_LIST_TO_REMOVE) > 0:
                (
                    list_less_traded_pairs,
                    PAIRS_LIST_TO_REMOVE,
                ) = remove_pairs_with_errors(
                    list_less_traded_pairs, PAIRS_LIST_TO_REMOVE
                )

            if bool(config["use_multithreads_for_sending_swaps"]):
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    executor.map(check_profitability, list_less_traded_pairs)
            else:
                for dex_pair_final_list in list_less_traded_pairs:
                    check_profitability(dex_pair_final_list)

            end = time.perf_counter()
            total = round(end - start, 2)
            if len(list_less_traded_pairs) > 0:
                end_time = datetime.now()
                logger.debug(
                    f"{end_time} - Less traded pairs Finished in {total} seconds cycle: {count}"
                )
        except Exception as e:
            logger.exception("execute_less_traded_pairs error: ")


def check_profitability(dex_pair_final_list):
    global ACCOUNT
    account = ACCOUNT
    watcher = ChainWatcher[-1]
    for _dex_pair_final in dex_pair_final_list:
        amounts = []
        dex0_reserve0 = 0
        dex0_reserve1 = 0
        dex1_reserve0 = 0
        dex1_reserve1 = 0
        try:
            dex0_reserve0, dex0_reserve1 = watcher.getReservers(
                _dex_pair_final.pairs_id[0]
            )
            dex1_reserve0, dex1_reserve1 = watcher.getReservers(
                _dex_pair_final.pairs_id[1]
            )
        except:
            continue

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
                    """
                    reserve0_d = Decimal(dex0_reserve0) / Decimal(
                        10 ** int(_dex_pair_final.decimals[0])
                    )
                    reserve1_d = Decimal(dex0_reserve1) / Decimal(
                        10 ** int(_dex_pair_final.decimals[1])
                    )
                    """
                    gross_profit_usd = round(
                        get_amount_usd_value(
                            _dex_pair_final.tokens[1].lower(),
                            _amountProfit_d,
                        ),
                        2,
                    )
                    (
                        max_base_fee_per_gas,
                        max_priority_fee,
                        exec_cost_usd,
                        gas_limit,
                        meet_effort_criteria,
                    ) = execution_cost(gross_profit_usd)
                    net_profit_usd = round(
                        Decimal(gross_profit_usd) - Decimal(exec_cost_usd), 2
                    )
                    if (
                        net_profit_usd > 0
                        and exec_cost_usd > 0
                        and meet_effort_criteria == True
                    ):
                        logger.info(
                            f"Profit found: pair: {_pairAddress} Token Out: {_dex_pair_final.tokens[1]} Amount: {_amountTokenPay} Gross USD: {gross_profit_usd} Net USD: {net_profit_usd}"
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
                    """
                    reserve0_d = Decimal(dex1_reserve0) / Decimal(
                        10 ** int(_dex_pair_final.decimals[0])
                    )
                    reserve1_d = Decimal(dex1_reserve1) / Decimal(
                        10 ** int(_dex_pair_final.decimals[1])
                    )
                    """
                    gross_profit_usd = round(
                        get_amount_usd_value(
                            _dex_pair_final.tokens[0].lower(),
                            _amountProfit_d,
                        ),
                        2,
                    )
                    (
                        max_base_fee_per_gas,
                        max_priority_fee,
                        exec_cost_usd,
                        gas_limit,
                        meet_effort_criteria,
                    ) = execution_cost(gross_profit_usd)
                    net_profit_usd = round(
                        Decimal(gross_profit_usd) - Decimal(exec_cost_usd), 2
                    )
                    if (
                        net_profit_usd > 0
                        and exec_cost_usd > 0
                        and meet_effort_criteria == True
                    ):
                        logger.info(
                            f"Profit found: pair: {_pairAddress} Token Out: {_dex_pair_final.tokens[1]} Amount: {_amountTokenPay} Gross USD: {gross_profit_usd} Net USD: {net_profit_usd}"
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
        except Exception as e:
            logger.exception(
                f"Error swaping pair0: {_dex_pair_final.pairs_id[0]} pair1: {_dex_pair_final.pairs_id[1]}"
            )


def update_tokens_price():
    global TOKENS_PRICES_LIST
    global DEFAULT_TOKENS_PRICES_LIST
    next_default_tokens_update_unix = 0
    while True:
        if len(TOKENS_PRICES_LIST) > 0:
            for c_t in TOKENS_PRICES_LIST:
                try:
                    price = get_prices(c_t.coingecko_id)
                    if price > 0:
                        date_time_current = datetime.now()
                        c_t.usdPrice = price
                        c_t.lastUpdateTime = int(
                            time.mktime(date_time_current.timetuple())
                        )
                    date_time_current = datetime.now()
                    if (
                        int(time.mktime(date_time_current.timetuple()))
                        > next_default_tokens_update_unix
                    ):
                        for c_t in DEFAULT_TOKENS_PRICES_LIST:
                            try:
                                price = get_prices(c_t.coingecko_id)
                                if price > 0:
                                    date_time_current = datetime.now()
                                    c_t.usdPrice = price
                                    c_t.lastUpdateTime = int(
                                        time.mktime(date_time_current.timetuple())
                                    )
                            except:
                                continue
                        date_time_current = datetime.now()
                        next_default_tokens_update = date_time_current + timedelta(
                            minutes=int(config["default_tokens_update_minute"])
                        )
                        next_default_tokens_update_unix = int(
                            time.mktime(next_default_tokens_update.timetuple())
                        )
                except:
                    pass
        time.sleep(int(config["coingecko_prices_refresh_seconds"]))


def fill_metrics_info():
    global GAS
    global SUGGEST_BASE_FEE
    global ACCOUNT
    WETH_ABI = get_etherscan_weth_abi()
    account = ACCOUNT
    while True:
        try:
            # Gas
            gas_oracle = get_gas()
            if gas_oracle.fastGasPrice > 0:
                if config["gas_type"] == "fast":
                    GAS = gas_oracle.fastGasPrice
                elif config["gas_type"] == "propose":
                    GAS = gas_oracle.proposeGasPrice
                elif config["gas_type"] == "safe":
                    GAS = gas_oracle.safeGasPrice
                else:
                    GAS = gas_oracle.fastGasPrice

                SUGGEST_BASE_FEE = gas_oracle.suggestBaseFee

            check_balance()
            # sleep
            time.sleep(int(config["metrics_refresh_seconds"]))
        except Exception as e:
            logger.exception(f"fill_metrics_info error: ")
            pass


def swap_tokens_estimate_gas(
    _tokenIn,
    _tokenOut,
    _amountIn,
    _amountOutMin,
    _router,
):
    global ACCOUNT
    flas_swap = FlashSwap[-1]
    account = ACCOUNT

    web3_flas_swap = web3.eth.contract(address=flas_swap.address, abi=flas_swap.abi)
    estimated_gas = web3_flas_swap.functions.swap_tokens(
        web3.toChecksumAddress(_tokenIn.lower()),
        web3.toChecksumAddress(_tokenOut.lower()),
        _amountIn,
        _amountOutMin,
        web3.toChecksumAddress(_router.lower()),
    ).estimateGas({"from": web3.toChecksumAddress(account.address.lower())})
    logger.debug(f"Est. Gas:  {estimated_gas}")


def get_amount_usd_value(token, amount):
    usd_price = 0.00
    token_price = 0.00
    try:
        token_price = get_token_price(token)
    except:
        pass

    usd_price = Decimal(amount) * Decimal(token_price)
    return usd_price


def execution_cost(profit):
    global GAS
    global SUGGEST_BASE_FEE
    global WETH_ABI
    global ACCOUNT
    account = ACCOUNT
    json_abi = WETH_ABI
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
    eth_price = Decimal(get_token_price(config["token_weth"].lower()))
    gas_limit = int(config["gas_limit_start_swap"])
    cost_usd = (eth_price * max_base_fee_per_gas_ether) * gas_limit

    # transfer to WETH cost
    minimum_weth_target_wei = web3.toWei(
        Decimal(config["minimum_weth_target"]), "ether"
    )
    weth_contract = web3.eth.contract(
        address=web3.toChecksumAddress(config["token_weth"].lower()), abi=json_abi
    )
    weth_amount_wei = weth_contract.functions.balanceOf(account.address).call()
    convert_cost_usd = 0
    if weth_amount_wei < minimum_weth_target_wei:
        estimate_g = int(config["gas_limit_start_swap_tokens"])
        (
            _,
            _,
            convert_cost_usd,
            _,
        ) = swap_cost_to_another_token(estimate_g, profit)
    total_cost_usd = Decimal(cost_usd) + Decimal(convert_cost_usd)
    weth_amount_ether = web3.fromWei(weth_amount_wei, "ether")
    weth_amount_usd = weth_amount_ether * eth_price
    meet_effort_criteria = False

    if Decimal(total_cost_usd) < (
        (
            Decimal(weth_amount_usd)
            * max(Decimal(50.0), Decimal(config["entry_max_weth_value_percentage"]))
        )
        / 100
    ):
        meet_effort_criteria = True

    return (
        int(max_base_fee_per_gas),
        int(max_priority_fee),
        round(total_cost_usd, 2),
        gas_limit,
        meet_effort_criteria,
    )


def swap_cost_to_another_token(gas_limit, amount_profit):
    global GAS
    global SUGGEST_BASE_FEE
    max_priority_fee = Decimal(GAS) - Decimal(SUGGEST_BASE_FEE)
    base_fee_per_gas = Decimal(GAS) * Decimal(config["token_swap_base_fee_multiplier"])

    max_base_fee_per_gas = base_fee_per_gas + max_priority_fee
    max_base_fee_per_gas_wei = int(Decimal(max_base_fee_per_gas) * (Decimal(10) ** 9))
    max_base_fee_per_gas_ether = web3.fromWei(max_base_fee_per_gas_wei, "ether")
    eth_price = Decimal(get_token_price(config["token_weth"].lower()))
    cost = (eth_price * max_base_fee_per_gas_ether) * gas_limit
    profit_usd = Decimal(amount_profit / 10**18) * Decimal(eth_price)

    return (
        int(max_base_fee_per_gas),
        int(max_priority_fee),
        round(cost, 2),
        round(profit_usd, 2),
    )


def get_token_price(token):
    global TOKENS_PRICES_LIST
    price = 0.00
    try:
        price = 0
        lastTime = 0

        if token in DEFAULT_TOKENS_LIST:
            if len(DEFAULT_TOKENS_PRICES_LIST) > 0:
                token = token.lower()
                price, lastTime = next(
                    (
                        (x.usdPrice, x.lastUpdateTime)
                        for x in DEFAULT_TOKENS_PRICES_LIST
                        if x.token == token
                    ),
                    (0, 0),
                )

                date_time_current = datetime.now()
                unix_date_time_current = int(time.mktime(date_time_current.timetuple()))
                if (
                    lastTime
                    + max(int(config["valid_price_time_windows_minutes"]), 1) * 60
                    < unix_date_time_current
                ):
                    price = 0.00
        else:
            if len(TOKENS_PRICES_LIST) > 0:
                token = token.lower()
                price, lastTime = next(
                    (x.usdPrice, x.lastUpdateTime)
                    for x in TOKENS_PRICES_LIST
                    if x.token == token
                )

                date_time_current = datetime.now()
                unix_date_time_current = int(time.mktime(date_time_current.timetuple()))
                if (
                    lastTime
                    + max(int(config["valid_price_time_windows_minutes"]), 1) * 60
                    < unix_date_time_current
                ):
                    price = 0.00

    except:
        pass
    return price


def get_token_amount_price(token, amount):
    global TOKENS_PRICES_LIST
    global DEFAULT_TOKENS_PRICES_LIST
    global DEFAULT_TOKENS_LIST
    tokens_list = []
    price = 0.00
    value = 0.00
    try:
        if token in DEFAULT_TOKENS_LIST:
            tokens_list = DEFAULT_TOKENS_PRICES_LIST
        else:
            tokens_list = TOKENS_PRICES_LIST

        if len(tokens_list) > 0:
            token = token.lower()
            price, lastTime, decimal = next(
                (x.usdPrice, x.lastUpdateTime, x.decimal)
                for x in tokens_list
                if x.token == token
            )
            date_time_current = datetime.now()
            unix_date_time_current = int(time.mktime(date_time_current.timetuple()))

            if (
                lastTime + max(int(config["valid_price_time_windows_minutes"]), 1) * 60
                < unix_date_time_current
            ):
                value = 0.00
            else:
                value = Decimal(price) * Decimal(amount / Decimal(10 ** int(decimal)))

    except:
        pass
    return value


def tst_fill_prices_info():
    global GAS
    global SUGGEST_BASE_FEE
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


def swap_tokens_to_another(tokenIn, tokenOut, amountIn):
    global TOKENS_IN_WALLET_LIST
    global DEX_INFO_LIST
    global WETH_ABI
    global ACCOUNT
    json_abi = WETH_ABI
    account = ACCOUNT
    watcher = ChainWatcher[-1]
    flash = FlashSwap[-1]
    maxAmountOut = 0
    router = ""
    tokens = []
    tokens.append(tokenIn)
    tokens.append(tokenOut)
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
        estimate_g = int(config["gas_limit_start_swap_tokens"])

        (
            _,
            _,
            cost_usd,
            profit_usd,
        ) = swap_cost_to_another_token(estimate_g, maxAmountOut)
        logger.debug(
            f"Check convert {amountIn} of {tokenIn} to WETH. Cost USD: {cost_usd} Profit USD: {profit_usd}"
        )
        if profit_usd > cost_usd and cost_usd > 0:
            try:
                token_contract = web3.eth.contract(
                    address=web3.toChecksumAddress(tokenIn.lower()),
                    abi=json_abi,
                )
                allowance = token_contract.functions.allowance(
                    account.address, flash.address
                ).call()
                if allowance < amountIn:
                    logger.info(
                        f"Start approve Flash contract to spend {amountIn} of {tokenIn}"
                    )
                    tx_hash = token_contract.functions.approve(
                        flash.address, amountIn - allowance
                    ).transact({"from": account.address})
                    x_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

                estimate_gas = swap_tokens_estimate_gas(
                    tokenIn,
                    tokenOut,
                    amountIn,
                    maxAmountOut,
                    router,
                )
                (
                    max_base_fee_per_gas,
                    max_priority_fee,
                    cost_real_usd,
                    profit_usd,
                ) = swap_cost_to_another_token(estimate_gas, maxAmountOut)

                if profit_usd > cost_real_usd and cost_real_usd > 0:
                    logger.info(
                        f"Start swap {amountIn} of {tokenIn} to at least {maxAmountOut} of {tokenOut}."
                    )
                    swap = flash.swap_tokens(
                        tokenIn,
                        tokenOut,
                        amountIn,
                        maxAmountOut,
                        router,
                        {
                            "from": account,
                            "gasLimit": estimate_gas,
                            "maxFeePerGas": max_base_fee_per_gas,
                            "maxPriorityFeePerGas": max_priority_fee,
                        },
                    )
                    swap.wait(1)
                    if network.show_active() != "mainnet":
                        if tokenOut not in TOKENS_IN_WALLET_LIST:
                            t_in_w = tokens_in_wallet(tokenOut, 0)
                            TOKENS_IN_WALLET_LIST.append(t_in_w)
            except Exception as e:
                logger.exception("Error: ")


def check_convertions():
    global ACCOUNT
    account = ACCOUNT
    global TOKENS_IN_WALLET_LIST
    global DEX_INFO_LIST
    global WETH_ABI
    json_abi = WETH_ABI
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

    TOKENS_IN_WALLET_LIST = get_tokens_in_wallet()
    for t in TOKENS_IN_WALLET_LIST:
        if t.token.lower() != config["token_weth"].lower():
            swap_tokens_to_another(
                t.token.lower(), config["token_weth"].lower(), t.amount
            )


def check_balance():
    global WETH_BALANCE
    global TOKENS_IN_WALLET_LIST
    global TOKENS_PRICES_LIST
    global ACCOUNT
    account = ACCOUNT
    global WETH_ABI
    json_abi = WETH_ABI

    try:
        if len(TOKENS_IN_WALLET_LIST) == 0:
            t_in_w = tokens_in_wallet(config["token_weth"], 0)
            TOKENS_IN_WALLET_LIST.append(t_in_w)

        check_convertions()
        TOKENS_IN_WALLET_LIST = get_tokens_in_wallet()
        if len(TOKENS_PRICES_LIST) > 0:
            ether_amount = web3.fromWei(web3.eth.getBalance(account.address), "ether")
            if ether_amount > 0:
                ether_amount_usd = round(
                    ether_amount * Decimal(get_token_price(config["token_weth"])), 2
                )
                logger.debug(
                    f"Ether amount: {ether_amount} Ether USD: {ether_amount_usd}"
                )

            logger.debug("Tokens in wallet:")
            count = 0
            weth_current_amount = 0
            for tk in TOKENS_IN_WALLET_LIST:
                if tk.amount > 0:
                    count += 1
                    value = round(get_token_amount_price(tk.token, tk.amount), 2)
                    logger.debug(
                        f"{count} - Token: {tk.token} Amount: {tk.amount} USD: {value}"
                    )
    except Exception as e:
        logger.exception(f"check_balance error: {error}")


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
    global ACCOUNT
    account = ACCOUNT
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
        logger.info(f"Profit for pair {pairAddress} executed.")
        if network.show_active() != "mainnet":
            if tokenOther not in TOKENS_IN_WALLET_LIST:
                t_in_w = tokens_in_wallet(tokenOther, 0)
                TOKENS_IN_WALLET_LIST.append(t_in_w)

    except Exception as e:
        logger.exception("Error executing swap. Error: ")
        # remove from list
        errors = config["list_errors_to_remove_pairs"].split(";")
        if error.find("eth_abi.exceptions.NonEmptyPaddingBytes") != -1:
            PAIRS_LIST_TO_REMOVE.append(dex_pair_final_list)
            logger.debug(f"pair {pairAddress} added on the lis to be removed.")
        else:
            for er in errors:
                if error.find(er) != -1 or (
                    e.__str__().find("revert") != -1
                    and e.__str__().find("revert:") == -1
                ):
                    try:
                        PAIRS_LIST_TO_REMOVE.append(dex_pair_final_list)
                        logger.debug(
                            f"pair {pairAddress} added on the lis to be removed."
                        )
                        break
                    except:
                        pass
                    break


def get_tokens_in_wallet():
    global TOKENS_IN_WALLET_LIST
    global WETH_ABI
    global ACCOUNT
    json_abi = WETH_ABI
    account = ACCOUNT
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
                    logger.debug("item removed from the list")
                    break

        for itn in list_removed:
            for itens_list_to_rm in list_to_remove:
                if (
                    itn[0].pairs_id[0] == itens_list_to_rm[0].pairs_id[0]
                    and itn[0].pairs_id[1] == itens_list_to_rm[0].pairs_id[1]
                ):
                    list_to_remove.remove(itens_list_to_rm)
                    break
    except Exception as e:
        logger.exception("remove_pairs_with_errors error ")

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
                start_time = datetime.now()
                logger.debug(f"{start_time} - Start Executing Most Traded Pairs")
            for dex_pair_final_list in list_most_traded_pairs:
                check_profitability(dex_pair_final_list)
            if len(list_most_traded_pairs) > 0:
                end_time = datetime.now()
                logger.debug(f"{end_time} - End Executing Most Traded Pairs")
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
                start_time = datetime.now()
                print(f"{start_time} - Start Executing Less Traded Pairs")
            for dex_pair_final_list in list_less_traded_pairs:
                check_profitability(dex_pair_final_list)
            if len(list_less_traded_pairs) > 0:
                end_time = datetime.now()
                print(f"{end_time} - End Executing Less Traded Pairs")
        except Exception as e:
            print("Error: ")


def fill_default_tokens():
    global DEFAULT_TOKENS_LIST
    DEFAULT_TOKENS_LIST = config["default_tokens"].split(";")


def test():
    global TOKENS_PRICES_LIST
    global DEFAULT_TOKENS_PRICES_LIST
    myList = []
    myList_d = []
    date_time_current = datetime.now()
    t_p_weth = tokens_coingecko_price(
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "weth",
        "weth",
        18,
        2004.09,
        int(time.mktime(date_time_current.timetuple())),
    )
    t_p_usdt = tokens_coingecko_price(
        "0xdac17f958d2ee523a2206206994597c13d831ec7",
        "usd-coin",
        "usdc",
        18,
        100,
        int(time.mktime(date_time_current.timetuple())),
    )
    t_p_usdc = tokens_coingecko_price(
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "tether",
        "usdt",
        18,
        100,
        int(time.mktime(date_time_current.timetuple())),
    )

    t_p_degem = tokens_coingecko_price(
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb20",
        "degem",
        "degem",
        18,
        100,
        int(time.mktime(date_time_current.timetuple())),
    )
    t_p_defit = tokens_coingecko_price(
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb10",
        "defit",
        "defit",
        18,
        100,
        int(time.mktime(date_time_current.timetuple())),
    )

    fill_default_tokens()
    fill_global_variables()
    myList_d.append(t_p_usdt)
    myList_d.append(t_p_usdc)
    myList_d.append(t_p_weth)
    myList.append(t_p_degem)
    myList.append(t_p_defit)

    TOKENS_PRICES_LIST = myList
    DEFAULT_TOKENS_PRICES_LIST = myList_d
    check_balance()
    print("price: ", get_token_price("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"))
    update_tokens_price()


def main3():
    test()


def main2():
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


def main1():
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warn message")
    logger.error("error message")
    logger.critical("critical message")


def fill_global_variables():
    global WETH_ABI
    global ACCOUNT
    WETH_ABI = get_etherscan_weth_abi()
    ACCOUNT = get_account()


def main():
    fill_global_variables()
    check_balance()
    if len(ChainWatcher) == 0 or len(FlashSwap) == 0:
        (max_base_fee_per_gas, max_priority_fee, gas_limit) = get_deploy_cost()
        deploy_watcher(gas_limit, max_base_fee_per_gas, max_priority_fee)
        deploy_flash_swap(gas_limit, max_base_fee_per_gas, max_priority_fee)
    fill_default_tokens()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        metrics = executor.submit(fill_metrics_info)
        dx_list = executor.submit(fill_dex_info)
        dx_proc = executor.submit(dex_info_processor)
        prices = executor.submit(update_tokens_price)
        lst_most_traded = executor.submit(execute_most_traded_pairs)
        lst_less_traded = executor.submit(execute_less_traded_pairs)
        print(
            dx_list.result(),
            dx_proc.result(),
            lst_most_traded.result(),
            lst_less_traded.result(),
            metrics.result(),
            prices.result(),
        )


if __name__ == "__main__":
    main()
# https://docs.uniswap.org/protocol/V2/reference/smart-contracts/common-errors
# web3_flas_swap.functions.start estimated_gas: 298750
# get weth - https://github.com/PatrickAlphaC/aave_brownie_py_freecode
# https://docs.uniswap.org/protocol/V2/reference/smart-contracts/router-02
