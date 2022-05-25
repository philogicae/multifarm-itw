from web3 import Web3
from json import load
from oracle import get_price


# Constants
SECONDS_PER_WEEK = 60 * 60 * 24 * 7

# Parameters
CHAIN = 'Aurora'
RPC = 'https://mainnet.aurora.dev'

# Selected tokens (by Coingecko id)
TOKEN1 = 'near'
TOKEN2 = 'weth'


def fast_apr():
    # Prices from Coingecko oracle
    token1_price = get_price(TOKEN1)
    token2_price = get_price(TOKEN2)
    brl_price = get_price('borealis')

    # RPC Connection
    w3 = Web3(Web3.HTTPProvider(RPC))
    print('Connected to {}: {}'.format(
        CHAIN, 'OK' if w3.isConnected() else 'KO'))

    # Load factory & masterchef contracts
    contracts = load(open('contracts.json'))

    factory_address = contracts['address']['auroraswap_factory']
    masterchef_address = contracts['address']['auroraswap_masterchef']

    factory = w3.eth.contract(address=factory_address,
                              abi=contracts['abi']['factory'])
    masterchef = w3.eth.contract(
        address=masterchef_address, abi=contracts['abi']['masterchef'])

    # Load tokens
    token1_address = contracts['address'][TOKEN1]
    token2_address = contracts['address'][TOKEN2]
    brl_address = masterchef.functions.BRL().call()

    token1 = w3.eth.contract(address=token1_address,
                             abi=contracts['abi']['erc20'])
    token2 = w3.eth.contract(address=token2_address,
                             abi=contracts['abi']['erc20'])
    brl = w3.eth.contract(address=brl_address, abi=contracts['abi']['erc20'])

    brl_symbol = brl.functions.symbol().call()
    symbol1 = token1.functions.symbol().call()
    symbol2 = token2.functions.symbol().call()
    decimals1 = token1.functions.decimals().call()
    decimals2 = token2.functions.decimals().call()

    # Load pool
    pool_address = factory.functions.getPair(
        token1_address, token2_address).call()
    pool = w3.eth.contract(address=pool_address, abi=contracts['abi']['pair'])
    pool_decimals = pool.functions.decimals().call()
    pool_total_supply = pool.functions.totalSupply().call() / 10 ** pool_decimals
    pool_staked_supply = pool.functions.balanceOf(
        masterchef_address).call() / 10 ** pool_decimals

    pool_balance1 = token1.functions.balanceOf(
        pool_address).call() / 10 ** decimals1
    pool_balance2 = token2.functions.balanceOf(
        pool_address).call() / 10 ** decimals2
    pool_tvl_usd = pool_balance1 * token1_price + pool_balance2 * token2_price
    price_by_lp_token = pool_tvl_usd / pool_total_supply
    staked_tvl_usd = pool_staked_supply * price_by_lp_token

    # Find pool in masterchef
    pool_length = masterchef.functions.poolLength().call()
    pool_info = None
    index = 0
    while pool_info is None and index < pool_length:
        current_pool_info = masterchef.functions.poolInfo(index).call()
        if current_pool_info[0] == pool_address:
            pool_info = current_pool_info
        else:
            index += 1

    pool_alloc_pts = pool_info[1]
    total_alloc_pts = masterchef.functions.totalAllocPoint().call()

    # Calculate APR
    last_block = w3.eth.block_number
    args = [last_block, last_block+1]
    multiplier = masterchef.functions.getMultiplier(*args).call()

    rewards_per_block = masterchef.functions.BRLPerBlock().call() / 1e18
    rewards_per_week = rewards_per_block * multiplier * SECONDS_PER_WEEK / 1.1
    pool_rewards_per_week = pool_alloc_pts / total_alloc_pts * rewards_per_week
    usd_per_week = pool_rewards_per_week * brl_price

    weekly = usd_per_week / staked_tvl_usd * 100
    daily = weekly / 7
    apr = weekly * 52
    apy = (((1 + daily / 100) ** 365) - 1) * 100

    # Logs
    print(f'{index} - [{symbol1}]-[{symbol2}] Uni LP:')
    print(f'TVL Pool: {pool_total_supply:.4f} LP (${pool_tvl_usd:.2f})')
    print(f'TVL Staked: {pool_staked_supply:.4f} LP ($ {staked_tvl_usd:.2f})')
    print(f'LP Price: ${price_by_lp_token:.2f}')
    print(f'{symbol1} Price: ${token1_price:.2f}')
    print(f'{symbol2} Price: ${token2_price:.2f}')
    print(
        f'BRL per Week: {pool_rewards_per_week:.2f} (${usd_per_week:.2f})')
    print(f'APR: Day {daily:.2f}% Week {weekly:.2f}% Year {apr:.2f}%')
    print(f'APY: {apy:.2f}% (with daily compounding)')

    return dict(
        pool_index_in_masterchef=index,
        pool_name=f'{symbol1}-{symbol2} LP Uni V2',
        tvl_pool=pool_total_supply,
        tvl_pool_usd=pool_tvl_usd,
        tvl_staked=pool_staked_supply,
        tvl_staked_usd=staked_tvl_usd,
        lp_price_usd=price_by_lp_token,
        token_1=dict(address=token1_address,
                     symbol=symbol1, price=token1_price),
        token_2=dict(address=token2_address,
                     symbol=symbol2, price=token2_price),
        token_reward=dict(address=brl_address,
                          symbol=brl_symbol, price=brl_price),
        rewards_per_week=pool_rewards_per_week,
        rewards_per_week_used=usd_per_week,
        daily_apr=daily,
        weekly_apr=weekly,
        apr=apr,
        apy=apy
    )
