import config
import time

import asyncio
import aiohttp
import asyncpg

from datetime import datetime as dt
from datetime import timezone as tz
from datetime import timedelta as td
from dateutil.parser import parse

import numpy as np

WATCHLIST = (
    'BTC-USD',
    'ETH-USD',
    'AAVE-USD',
    'MATIC-USD',
    'REN-USD',
    'LINK-USD',
    'CRV-USD',
    'SUSHI-USD',
    'UNI-USD',
    'SNX-USD',
)


async def rate_limiter(ticker):
    """ Coinbase pro limits 10 request per second
    :param ticker:
    :return:
    """
    for x, sym in enumerate(WATCHLIST):
        if sym == ticker:
            await asyncio.sleep(0.11 + (x / 10))


async def clear_table(pool):
    """
    :param pool: Database pool
    :return:
    """
    async with pool.acquire()as conn:
        await conn.execute("""
            DELETE FROM volumeBars;
        """)


async def update_watchlist(pool) -> None:
    """ Responsible for ensuring database watchlist is same as scripts
        Same order, and key constraints needed
        Should be able to always run, first function to run as well
    :param pool: database pool
    :return:
    """
    async with pool.acquire() as conn:
        for j, ticker in enumerate(WATCHLIST):
            await conn.execute("""
                                INSERT INTO watchlist(id, ticker)
                                VALUES ($1, $2)
                                ON CONFLICT (id) DO NOTHING;
                        """, j + 1, ticker)


async def write_vol_bars(conn, candles):
    """ DB write
    :param conn: Pool connection already established
    :param candles: Volume list ready to write
    :return:
    """
    for candle in candles:
        print(candle)
        await conn.execute("""
            INSERT INTO volumeBars(ticker_id, dt, open, high, low, close, volume)
            VALUES ($1, $2, $3, $4, $5, $6, $7);
        """, candle[0], candle[1], candle[2], candle[3], candle[4], candle[5], candle[6])
    print('db write done')


async def write_6h_candles(conn, candles):
    """
    :param conn:
    :param candles:
    :return:
    """
    for candle in candles:
        print(candle)
        await conn.execute("""
            INSERT INTO timeBars(ticker_id, dt, open, high, low, close, volume)
            VALUES ($1, $2, $3, $4, $5, $6, $7);
        """, candle[0], candle[1], candle[2], candle[3], candle[4], candle[5], candle[6])
    print('db write done')


async def build_vol_candles(trades, base_info):
    """ builds vol_candle
    :param trades:  numpy array of trades containing [time, price, quantity]
    :param base_info: Dict of Tuples containing necessary info per ticker
    :return: datetime of where to continue build
    """
    vol = 0
    vol_candles = []
    open_index = 0
    for n, trade in enumerate(trades):
        vol += trade[2]
        if vol >= base_info[3]:
            data = (base_info[0],
                    trades[open_index, 0],  # Date
                    trades[open_index, 1],  # Open
                    np.max(trades[open_index:n + 1, 1]),  # High
                    np.min(trades[open_index:n + 1, 1]),  # Low
                    trades[n, 1],  # Close
                    vol)
            vol_candles.append(data)  # Volume
            vol = 0
            open_index = n + 1
    if vol != 0:
        data = (base_info[0],
                trades[open_index, 0],  # Date
                trades[open_index, 1],  # Open
                np.max(trades[open_index:, 1]),  # High
                np.min(trades[open_index:, 1]),  # Low
                trades[-1, 1],  # Close
                vol)
        vol_candles.append(data)  # Volume
    return vol_candles


async def get_trades(base_info, pool):
    """ Parse Trade History, build trade indicators and write to database
    :param base_info: Dict of Tuples containing necessary info per ticker
    :param pool: database pool
    :return:
    """
    params = {'limit': '1000'}
    updated = False
    base_url = base_info[2] + f'products/{base_info[1]}/trades'
    trades = []
    responses = 0
    reference_times = [base_info[4].replace(hour=12, minute=0, second=0, microsecond=0),
                       base_info[4].replace(hour=0, minute=0, second=0, microsecond=0)]
    if reference_times[0] < base_info[4]:
        reference_times[1] = reference_times[1] - (base_info[6] * 2)
    else:
        reference_times[0] = reference_times[0] - (base_info[6] * 2)
    async with aiohttp.ClientSession() as session:
        while not updated:
            async with pool.acquire() as conn:
                async with session.get(url=base_url, params=params) as resp:
                    print('\t', resp.status, base_info[1])
                    responses += 1
                    for trade in await resp.json():
                        trade_time = parse(trade['time'])
                        trade_time = trade_time.replace(microsecond=0, tzinfo=None)
                        trades.append((trade_time, float(trade['price']), float(trade['size'])))
                        if trade_time < base_info[5]:
                            trades = np.array(trades)
                            trades = np.flipud(trades)
                            vol_candles = await build_vol_candles(trades, base_info)
                            await write_vol_bars(conn, vol_candles)
                            return 0
                        elif responses == 50000:
                            trades = np.array(trades)
                            trades = np.flipud(trades)
                            vol_candles = await build_vol_candles(trades, base_info)
                            await write_vol_bars(conn, vol_candles)
                            responses = 0
                            trades = []
                        elif trade_time < reference_times[0]:
                            trades = np.array(trades)
                            trades = np.flipud(trades)
                            vol_candles = await build_vol_candles(trades, base_info)
                            await write_vol_bars(conn, vol_candles)
                            reference_times[0] = reference_times[0] - (base_info[6] * 2)
                            responses = 0
                            trades = []
                        elif trade_time < reference_times[1]:
                            trades = np.array(trades)
                            trades = np.flipud(trades)
                            vol_candles = await build_vol_candles(trades, base_info)
                            await write_vol_bars(conn, vol_candles)
                            reference_times[1] = reference_times[1] - (base_info[6] * 2)
                            responses = 0
                            trades = []
                    params = {'limit': '1000', 'after': resp.headers['Cb-After']}
                    await asyncio.sleep(.1)


async def get_6hour_candles(base_info, pool):
    """ Get 350 days or till inception of 6 hour candles from Coinbase Pro &
        add database write
    :param base_info: Dict of Tuples containing necessary info per ticker
    :param pool: database pool
    :return:
    """
    _6hour_td = td(days=50)
    base_url = base_info[2] + f'products/{base_info[1]}/candles'
    params = {'granularity': 21600}
    await rate_limiter(base_info[1])
    async with aiohttp.ClientSession() as session:
        for i in range(7):
            async with session.get(url=base_url, params=params) as resp:
                print(resp.status)
                candles_resp = await resp.json()
                if len(candles_resp) == 0:
                    return 0
                end_date = dt.fromtimestamp(candles_resp[-1][0]).replace(tzinfo=None)
                start_date = end_date - _6hour_td
                await asyncio.sleep(.11)
                params = {'granularity': 21600, 'start': start_date.isoformat(), 'end': end_date.isoformat()}


async def main():
    async with asyncpg.create_pool(database="crypto",
                                   host="localhost",
                                   user="postgres",
                                   password=config.DB_PWD) as pool:
        now = dt.now(tz.utc).replace(microsecond=0, tzinfo=None)
        _td = td(days=7)
        end = (now - _td).replace(hour=0, minute=0, second=0, tzinfo=None)
        candle_buffer = td(hours=12)
        base_info = {}
        temp_freq = (
            1000, 14000, 2600, 3300000, 350000, 147000, 133000, 56000, 29000, 29000
        )
        for i, ticker in enumerate(WATCHLIST):
            url = f"https://api.pro.coinbase.com/"
            base_info[ticker] = (i + 1,  # trade id in db
                                 ticker,  # symbol
                                 url,  # base url endpoint
                                 temp_freq[i],  # Amount of vol needed for 1 vol candle close per ticker
                                 now,
                                 end,  # desired historical time to parse
                                 candle_buffer)  # delta of candle buffer

        # candles = await (asyncio.gather(* [get_6hour_candles(base_info[ticker], pool) for ticker in base_info]))
        #await clear_table(pool)
        #await update_watchlist(pool)
        done = await asyncio.gather(*[get_trades(base_info[ticker], pool) for ticker in base_info])
        # await get_trades(base_info['CRV-USD'], pool)
        print('done')
        # await get_trades(base_info['ETH-USD'], pool)


if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())
    print(str(time.time() - start_time).format('%.2f'), '\t seconds elapsed')
