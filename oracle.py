from pycoingecko import CoinGeckoAPI
cg = CoinGeckoAPI()


def get_price(token):
    response = cg.get_price(ids=token, vs_currencies='usd')
    return response[token]['usd']
