from scripts.helpful_scripts import (
    read_chainlink_data,
    get_dex_data,
    get_token,
    list_of_tokens,
)
from scripts.classes import token, ObjectEncoder
import json
from json import JSONEncoder


def main():
    dex_info = get_dex_data()
    dex_master = None
    for d in dex_info:
        if d.is_master:
            dex_master = d
            break
    print(f"master: {dex_master.name}")
    for d in dex_info:
        size = len(d.pairs)
        print(
            f"dex name: {d.name} factory: {d.factory} router: {d.router} default_token: {d.default_token} pairs: {size} graph: {d.use_graph}"
        )
