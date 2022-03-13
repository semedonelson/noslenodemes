import json
from json import JSONEncoder
import decimal


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
        dailyVolumeUSD,
        token0,
        token1,
    ):
        self.id = id
        self.dailyVolumeUSD = dailyVolumeUSD
        self.token0 = token0
        self.token1 = token1


class cidade:
    def __init__(self, nome, habitantes):
        self.nome = nome
        self.habitantes = habitantes


class dex_pair_info:
    def __init__(self, dex_name, pair_id, dailyVolumeUSD, token0, token1):
        self.dex_name = dex_name
        self.pair_id = pair_id
        self.dailyVolumeUSD = dailyVolumeUSD
        self.token0 = token0
        self.token1 = token1


class fakefloat(float):
    def __init__(self, value):
        self._value = value

    def __repr__(self):
        return str(self._value)


class ObjectEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return fakefloat(obj)
        return obj.__dict__
