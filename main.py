from binance_api import get_balances
from constituents import calculate_weights
from portfolio_rebalancing import rebalance, redeem
import sys

redeem()
balances = get_balances()
print(f'Portfolio before rebalance: {balances}')
weights = calculate_weights()
print(f'Updated weights: {weights}')
if input('Continue y/[n]? ') not in ['y', 'yes']:
    sys.exit()
rebalance(balances, weights)
print(f'Portfolio after rebalance: {get_balances()}')
