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


class dex_pair_info:
    def __init__(self, dex_name, pair_id, dailyVolumeUSD, token0, token1):
        self.dex_name = dex_name
        self.pair_id = pair_id
        self.dailyVolumeUSD = dailyVolumeUSD
        self.token0 = token0
        self.token1 = token1


class dex_pair_final:
    def __init__(
        self, dex_names, factories, routers, pairs_id, tokens, decimals, amounts
    ):
        self.dex_names = dex_names
        self.factories = factories
        self.routers = routers
        self.pairs_id = pairs_id
        self.tokens = tokens
        self.decimals = decimals
        self.amounts = amounts


class tokens_in_wallet:
    def __init__(self, token, amount):
        self.token = token
        self.amount = amount


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


class final_profitable_pairs:
    def __init__(
        self, tokenBorrow, tokenPay, amountTokenPay, sourceRouter, targetRouter
    ):
        self.tokenBorrow = tokenBorrow
        self.tokenPay = tokenPay
        self.amountTokenPay = amountTokenPay
        self.sourceRouter = sourceRouter
        self.targetRouter = targetRouter


class tokens_coingecko_price:
    def __init__(self, token, coingecko_id, symbol, decimal, usdPrice, lastUpdateTime):
        self.token = token
        self.coingecko_id = coingecko_id
        self.symbol = symbol
        self.decimal = decimal
        self.usdPrice = usdPrice
        self.lastUpdateTime = lastUpdateTime


class ethgasoracle:
    def __init__(self, fastGasPrice, proposeGasPrice, safeGasPrice, suggestBaseFee):
        self.fastGasPrice = fastGasPrice
        self.proposeGasPrice = proposeGasPrice
        self.safeGasPrice = safeGasPrice
        self.suggestBaseFee = suggestBaseFee
