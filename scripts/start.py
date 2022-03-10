from scripts.helpful_scripts import (
    read_chainlink_data,
    get_dex_data,
    get_token,
    list_of_tokens,
    get_account,
    get_dex_info,
)
from scripts.classes import token, ObjectEncoder, dex_pair_info
import json
from json import JSONEncoder
from brownie import ChainWatcher


def deploy_watcher():
    account = get_account()
    watcher = ChainWatcher.deploy(
        {"from": account},
    )
    print("Deployed Chain Watcher!")
    return watcher


def check_pairs(_factory, _token0, _token1):
    account = get_account()
    watcher = ChainWatcher[-1]
    address = watcher.validate_pair(
        _factory,
        _token0,
        _token1,
        {"from": account},
    )
    return address


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


def main1():
    d_p = dex_pair("NAME", "2323", "ssdsd", "")
    print(d_p.dex_name)
    """
    account = get_account()
    watcher = deploy_watcher()
    address = watcher.validate_pair(
        "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac",
        "0x4d44d6c288b7f32ff676a4b2dafd625992f8ffbd",
        "0xdac17f958d2ee523a2206206994597c13d831ec7",
        {"from": account},
    )
    print(f"check_pairs {address}")
    address = watcher.validate_pair(
        "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "0x4d44d6c288b7f32ff676a4b2dafd625992f8ffbd",
        "0xdac17f958d2ee523a2206206994597c13d831ec7",
        {"from": account},
    )
    print(f"check_pairs {address}")
    """


def main():
    watcher = deploy_watcher()
    dex_info = get_dex_data()
    for d in dex_info:
        size = len(d.pairs)
        print(
            f"dex name: {d.name} factory: {d.factory} router: {d.router} default_token: {d.default_token} pairs: {size} graph: {d.use_graph}"
        )
    # Multiprocessing a for loop
    # https://stackoverflow.com/a/20192251
    # https://docs.python.org/3/library/itertools.html
    # check
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
                print(
                    f"dex0_name: {dex0_name} dex1_name: {dex1_name} dex0_factory: {dex0_factory} dex0_router: {dex0_router} dex1_factory: {dex1_factory} dex1_router: {dex1_router} pair0_id: {pair0_id} pair1_id: {pair1_id} token0: {token0} token1: {token0} token0_decimals: {token0_decimals} token1_decimals: {token1_decimals}"
                )


# https://www.geeksforgeeks.org/python-remove-all-values-from-a-list-present-in-other-list/
# check pair for non graph dex


# https://github.com/Uniswap/v2-core/blob/master/contracts/UniswapV2Pair.sol
# reserve and balances
