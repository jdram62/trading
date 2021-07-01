import pandas as pd
import config

from bokeh.plotting import figure, show, output_file
from bokeh.models import DaysTicker

import asyncio
import asyncpg

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


async def read_vol_candles():
    """
    :return:
    """
    async with asyncpg.create_pool(database="crypto", host="localhost",
                                   user="postgres", password=config.DB_PWD) as pool:
        async with pool.acquire() as conn:
            candles = await conn.fetch("""
                SELECT * FROM volumeBars  
            """)
    return candles


async def read_daily_candles():
    async with asyncpg.create_pool(database="crypto", host="localhost",
                                   user="postgres", password=config.DB_PWD) as pool:
        async with pool.acquire() as conn:
            candles = await conn.fetch("""
                SELECT * FROM dailyBars  
            """)
    return candles


async def main():
    vol_candles = await read_vol_candles()
    daily_candles = await read_daily_candles()
    df_dict = {}
    for x, ticker in enumerate(WATCHLIST):
        vol_list = []
        daily_list = []
        for row in vol_candles:
            if x + 1 == row[0]:
                vol_list.append([row[1], row[2], row[3], row[4], row[5], row[6]])
        for row in daily_candles:
            if x + 1 == row[0]:
                daily_list.append([row[1], row[2], row[3], row[4], row[5], row[6]])
        df_vol = pd.DataFrame(vol_list, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df_daily = pd.DataFrame(daily_list, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df_dict[ticker] = [df_vol, df_daily]
    return df_dict


if __name__ == '__main__':

    dfs = asyncio.run(main())
    TOOLS = "pan,wheel_zoom,box_zoom,reset,save"

    for k, sym in enumerate(WATCHLIST):
        df_vol_candles = dfs[sym][0]
        df_daily_candles = dfs[sym][1]
        inc = df_vol_candles.close > df_vol_candles.open
        dec = df_vol_candles.open > df_vol_candles.close
        w = 43200000  # 12Hours in milliseconds

        p1 = figure(x_axis_type="datetime",
                    tools=TOOLS, sizing_mode="stretch_both", title=sym)
        p1.xaxis.major_label_orientation = 3 / 4
        p1.grid.grid_line_alpha = 0.1
        p1.xaxis.ticker.desired_num_ticks = 50

        p1.segment(df_vol_candles.date, df_vol_candles.high, df_vol_candles.date, df_vol_candles.low, color="black")
        p1.vbar(df_vol_candles.date[inc], w, df_vol_candles.open[inc],
                df_vol_candles.close[inc], fill_color="green", line_color="black")
        p1.vbar(df_vol_candles.date[dec], w, df_vol_candles.open[dec],
                df_vol_candles.close[dec], fill_color="red", line_color="black")

        output_file("candlestick.html", title=sym)

        show(p1)
