import config
import time
import logging

import asyncio
import aiohttp
import asyncpg

from datetime import datetime as dt
from datetime import timezone as tz
from datetime import timedelta as td
from dateutil.parser import parse

import numpy as np


sem = asyncio.BoundedSemaphore(10)

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
    """ Combat coinbase pro 10 request per second rate limit
    :param ticker:
    :return:
    """
    for x, sym in enumerate(WATCHLIST):
        if sym == ticker:
            await asyncio.sleep(0.1+(x/10))


async def clear_table(pool):
    """ Raw clear table
    :param pool: Database pool
    :return:
    """
    async with pool.acquire()as conn:
        await conn.execute("""
            DELETE FROM volumeBars;
        """)


async def update_watchlist(pool) -> None:
    """ Responsible for ensuring database watchlist is same as python's
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
    """
    :param conn: Pool connection already established
    :param candles: Volume list ready to write
    :return:
    """
    for candle in candles:
        await conn.execute("""
            INSERT INTO volumeBars(ticker_id, dt, open, high, low, close, volume)
            VALUES ($1, $2, $3, $4, $5, $6, $7);
        """, candle[0], candle[1], candle[2], candle[3], candle[4], candle[5], candle[6])
    print('db write done')


async def build_vol_candles(trades, base_info, partial_candle):
    """ Logic for building volume candles
        Later when building other size volume candles, use same function of create new?
    :param trades: 2D numpy array of trades containing [time, price, quantity]
    :param base_info: Dict of Tuples containing necessary info per ticker
    :param partial_candle: Incomplete volume candle that is passed
    :return: datetime of where to continue build
    """
    vol = 0
    vol_candles = []
    prev_index = 0
    if partial_candle != 0:
        vol = partial_candle[6]

    for n, trade in enumerate(trades):
        vol += trade[2]
        if vol >= base_info[3]:
            if partial_candle != 0:
                data = (base_info[0],
                        trades[prev_index, 0],  # Date
                        trades[prev_index, 1],  # Open
                        np.max(trades[prev_index:, 1]),  # High
                        np.min(trades[prev_index:, 1]),  # Low
                        trades[-1, 1],  # Close
                        vol)
                vol_candles.append(data)  # Volume
                partial_candle = 0
            else:
                data = (base_info[0],
                        trades[prev_index, 0],  # Date
                        trades[prev_index, 1],  # Open
                        np.max(trades[prev_index:n + 1, 1]),  # High
                        np.min(trades[prev_index:n + 1, 1]),  # Low
                        trades[n, 1],  # Close
                        vol)
                vol_candles.append(data)  # Volume
            vol = 0
            prev_index = n + 1

    if vol != 0:
        data = (base_info[0],
                trades[prev_index, 0],  # Date
                trades[prev_index, 1],  # Open
                np.max(trades[prev_index:, 1]),  # High
                np.min(trades[prev_index:, 1]),  # Low
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
    found = False
    updated = False
    partial_vol_candle = 0
    headers = []
    base_url = base_info[2] + f'products/{base_info[1]}/trades'
    await rate_limiter(base_info[1])
    print('active task', len(asyncio.all_tasks()))
    async with aiohttp.ClientSession() as session:
        async with sem:
            while not updated:
                print('active task', len(asyncio.all_tasks()))

                # async with pool.acquire() as conn:
                await rate_limiter(base_info[1])
                if sem.locked():
                    print('\t\t\t sem lock')
                    await asyncio.sleep(2)
                async with session.get(url=base_url, params=params) as resp:
                    print('\t', resp.real_url, base_info[1])
                    print('\t', resp.status, base_info[1])
                    trades_resp = await resp.json(encoding='utf-8')
                    trades = []
                    parse_time = parse(trades_resp[0]['time'])
                    parse_time = parse_time.replace(microsecond=0, tzinfo=None)
                    params = {'limit': '1000', 'after': resp.headers['Cb-After']}
                    if parse_time < base_info[4]:
                        if 'Cb-Before' in resp.headers:
                            headers.append(resp.headers['Cb-Before'])
                        found = True
                        params = {'limit': '1000', 'after': headers.pop(-1)}
                        async with pool.acquire() as conn:
                            print('found page resp')
                            print('\nfound\n', base_info[1])
                            for trade in trades_resp:
                                trade['time'] = parse(trade['time'])
                                trade['time'] = trade['time'].replace(microsecond=0, tzinfo=None)
                                if trade['time'] > base_info[5]:
                                    updated = True
                                data = (trade['time'], float(trade['price']), float(trade['size']))
                                trades.append(data)
                            trades = np.array(trades)
                            trades = np.flipud(trades)
                        continue
                    if found:
                        if sem.locked():
                            print('\t\t\t sem lock')
                            await asyncio.sleep(2)
                        params = {'limit': '1000', 'after': headers.pop(-1)}
                        print('active task', len(asyncio.all_tasks()))
                        async with pool.acquire() as conn:
                            for trade in trades_resp:
                                trade['time'] = parse(trade['time'])
                                trade['time'] = trade['time'].replace(microsecond=0, tzinfo=None)
                                if trade['time'] > base_info[5]:
                                    print(trade['time'], base_info[5], 'updated true')
                                    updated = True
                                data = (trade['time'], float(trade['price']), float(trade['size']))
                                trades.append(data)
                            trades = np.array(trades)
                            trades = np.flipud(trades)

                            #vol_candles = await build_vol_candles(trades, base_info, partial_vol_candle)

                            #if vol_candles[-1][6] >= base_info[3]:
                             #   print('vol candles', vol_candles)
                                #await write_db(conn, vol_candles)
                            #    partial_vol_candle = 0
                            #else:
                            #    print('partial vol candle', vol_candles)
                            #    partial_vol_candle = vol_candles[-1]
                            #    if len(vol_candles) > 1:
                            #        del vol_candles[-1]
                            #        print('write to db', vol_candles)
                                    #await write_vol_bars(conn, vol_candles)


async def get_6hour_candles(base_info, pool):
    """ Get 350 days or till inception of 6 hour candles from Coinbase Pro &
        Write candles to database
    :param base_info: Dict of Tuples containing necessary info per ticker
    :param pool: database pool
    :return:
    """
    _6hour_td = td(days=50)
    base_url = base_info[2] + f'products/{base_info[1]}/candles'
    params = {'granularity': 21600}
    async with aiohttp.ClientSession() as session:
        for i in range(7):
            async with session.get(url=base_url, params=params) as resp:
                print(len(asyncio.all_tasks()))
                print(resp.status)
                print(resp.real_url)
                candles_resp = await resp.json()
                if len(candles_resp) == 0:
                    print('found')
                    return 0
                end_date = dt.fromtimestamp(candles_resp[-1][0]).replace(tzinfo=None)
                start_date = end_date - _6hour_td
                await rate_limiter(base_info[1])
                params = {'granularity': 21600, 'start': start_date.isoformat(), 'end': end_date.isoformat()}
    print('done')


async def main():
    async with asyncpg.create_pool(database="crypto",
                                   host="localhost",
                                   user="postgres",
                                   password=config.DB_PWD) as pool:
        # CENTRAL STANDARD IS UTC - 7 HOURS
        now = dt.now(tz.utc).replace(microsecond=0, tzinfo=None)
        _td = td(days=0, hours=12)
        start = (now - _td).replace(minute=0, second=0, tzinfo=None)

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
                                 start,  # Start time of db writes
                                 now)  # End time of db writes

        #candles = await asyncio.gather(* [get_6hour_candles(base_info[ticker], pool) for ticker in base_info])
        await clear_table(pool)
        # await update_watchlist(pool)
        #done = await asyncio.gather(*[get_trades(base_info[ticker], pool) for ticker in base_info])


if __name__ == "__main__":
    start_time = time.time()

    asyncio.run(main())

    print(str(time.time() - start_time).format('%.2f'), '\t seconds elapsed')

