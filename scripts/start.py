from scripts.helpful_scripts import (
    read_chainlink_data,
    get_dex_data,
    get_token,
    list_of_tokens,
    get_account,
)
from scripts.classes import token, ObjectEncoder, dex_pair
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


def main1():
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


def main():
    deploy_watcher()
    dex_info = get_dex_data()
    for d in dex_info:
        size = len(d.pairs)
        print(
            f"dex name: {d.name} factory: {d.factory} router: {d.router} default_token: {d.default_token} pairs: {size} graph: {d.use_graph}"
        )
    dx_processed = []
    final_dex_pairs_list = []
    for dx in dex_info:
        dx_processed.append(dx.name)
        for pair in dx.pairs:
            dx_pair_token0_id = pair["token0"]["id"]
            dx_pair_token1_id = pair["token1"]["id"]
            d_p = dex_pair(dx.name, pair["id"], pair["token0"], pair["token1"])
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
                            d_p = dex_pair(
                                dx_p.name,
                                pair_m["id"],
                                pair_m["token0"],
                                pair_m["token1"],
                            )
                            tmp_dex_pairs_list.append(d_p)
                            break
            if len(tmp_dex_pairs_list) > 1:
                final_dex_pairs_list.append(tmp_dex_pairs_list)
    for lst in final_dex_pairs_list:
        for pair in lst:
            dx_name = pair.dex_name
            pair_id = pair.pair_id
            token0_id = pair.token0["id"]
            token1_id = pair.token1["id"]
            print(
                f"dx: {dx_name} pair: {pair_id} token0: {token0_id} token1: {token1_id}"
            )
        print("################################################")
    # https://www.geeksforgeeks.org/python-remove-all-values-from-a-list-present-in-other-list/
    # check pair for non graph dex


# https://github.com/Uniswap/v2-core/blob/master/contracts/UniswapV2Pair.sol
# reserve and balances
