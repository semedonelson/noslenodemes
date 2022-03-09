import json
from json import JSONEncoder


class oracle_data:
    def __init__(self, pair0, pair1, decimal, proxy):
        self.pair0 = pair0
        self.pair1 = pair1
        self.decimal = decimal
        self.proxy = proxy


class dex:
    def __init__(
        self, name, factory, router, default_token, pairs, use_graph, is_master
    ):
        self.name = name
        self.factory = factory
        self.router = router
        self.default_token = default_token
        self.pairs = pairs
        self.use_graph = use_graph
        self.is_master = is_master


class token:
    def __init__(self, code, id):
        self.code = code
        self.id = id


class token0:
    def __init__(self, id, name, symbol, decimals):
        self.id = id
        self.name = name
        self.symbol = symbol
        self.decimals = decimals


class token1:
    def __init__(self, id, name, symbol, decimals):
        self.id = id
        self.name = name
        self.symbol = symbol
        self.decimals = decimals


class pair:
    def __init__(
        self,
        id,
        token0,
        token1,
    ):
        self.id = id
        self.token0 = token0
        self.token1 = token1


class dex_pair_info:
    def __init__(self, dex_name, pair_id, token0, token1):
        self.dex_name = dex_name
        self.pair_id = pair_id
        self.token0 = token0
        self.token1 = token1


class ObjectEncoder(JSONEncoder):
    def default(self, obj):
        return obj.__dict__
