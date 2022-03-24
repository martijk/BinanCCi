import math
import time

from binance_api import create_order, get_balances, get_exchange_stepsize, get_price, transfer_dust, get_flexible_position, redeem_flexible_position
from settings import BINANCE_ORDER_MIN, PAIRING, WAIT_SECONDS_BETWEEN_ORDERS


def redeem():
    for asset in get_flexible_position():
        if asset['canRedeem']:
            redeem_flexible_position(asset['productId'], asset['freeAmount'])
    time.sleep(WAIT_SECONDS_BETWEEN_ORDERS)

def rebalance(balances, required_weights):
    required_changes = _get_required_changes_in_portfolio(required_weights)
    dust_symbols = []

    for symbol, change_in_value, change, price in required_changes:
        pair = f'{symbol}{PAIRING}'

        if pair == f'{PAIRING}{PAIRING}':
            continue

        stepsize = get_exchange_stepsize(pair)
        # TODO: round up if selling?
        quantity = round(change, int(-math.log10(stepsize)))
        if quantity < 0 and -quantity > balances[symbol]:
            quantity += stepsize
        change_in_value = quantity * price

        # just let binance try if close to amount?
        if change_in_value < -BINANCE_ORDER_MIN:
            print(f'Selling {pair}. Change: {quantity}. Estimated change in value: {change_in_value}.')
            create_order(pair, 'sell', -quantity)
            time.sleep(WAIT_SECONDS_BETWEEN_ORDERS)
        # just let binance try if close to amount?
        elif change_in_value > BINANCE_ORDER_MIN:
            print(f'Buying {pair}. Change: {quantity}. Estimated change in value: {change_in_value}.')
            create_order(pair, 'buy', quantity)
            time.sleep(WAIT_SECONDS_BETWEEN_ORDERS)
        else:
            print(f'Could not create an order for {pair}: required change in value ({change_in_value}) is too small in magnitude.')

        # TODO: check if order succeeded (if applicable), or maybe check value first (.5 of min order size?)
        if symbol not in required_weights:
            dust_symbols.append(symbol)

    if dust_symbols:
        import sys
        if input(f'Dust: {dust_symbols}. Continue y/[n]? ') not in ['y', 'yes']:
            return
        print(transfer_dust(dust_symbols))
        time.sleep(WAIT_SECONDS_BETWEEN_ORDERS)


def _get_required_changes_in_portfolio(required_weights):
    portfolio = {s: {'balance': b} for (s, b) in get_balances().items()}

    for symbol in required_weights:
        if symbol not in portfolio:
            portfolio[symbol] = {'balance': 0}

    for symbol in portfolio:
        if symbol == PAIRING:
            price = 1
        else:
            price = get_price(symbol)

        portfolio[symbol]['price'] = price
        portfolio[symbol]['value'] = portfolio[symbol]['balance'] * price if price is not None else None

    total_value = sum([portfolio[s]['value'] for s in portfolio if portfolio[s]['value'] is not None])
    print(f'Total value: {total_value}')

    for symbol in portfolio:
        if symbol not in required_weights:
            portfolio[symbol]['required_change'] = -portfolio[symbol]['balance'] if portfolio[symbol]['price'] is not None else 0
            portfolio[symbol]['required_change_in_value'] = portfolio[symbol]['required_change'] * portfolio[symbol]['price'] if portfolio[symbol]['price'] is not None else 0
        else:
            portfolio[symbol]['required_change_in_value'] = required_weights[symbol] * total_value - portfolio[symbol]['value']
            portfolio[symbol]['required_change'] = portfolio[symbol]['required_change_in_value'] / portfolio[symbol]['price']

    required_changes = [(s, portfolio[s]['required_change_in_value'], portfolio[s]['required_change'], portfolio[s]['price'])
                        for s in portfolio if portfolio[s]['required_change'] != 0]

    def f(x):
        if x < 0:
            return -x  # First sell assets by descending order of action value.
        if x > 0:
            return -1/x  # Then buy assets by descending order of action value.

    required_changes.sort(key=lambda x: f(x[1]), reverse=True)

    return required_changes
