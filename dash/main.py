import pandas as pd
import config

from bokeh.layouts import gridplot, row, column
from bokeh.plotting import figure, output_file, show
from bokeh.models import Div
from bokeh.models.tools import WheelZoomTool, PanTool, ResetTool, HoverTool

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

        dc_inc = df_daily_candles.close > df_daily_candles.open
        dc_dec = df_daily_candles.open > df_daily_candles.close

        vc_inc = df_vol_candles.close > df_vol_candles.open
        vc_dec = df_vol_candles.open > df_vol_candles.close

        w1 = 43200000 * 2 - 25
        w2 = 3600000  # 1 Hour in milliseconds

        # Daily Candles
        p1 = figure(title=sym, x_axis_type="datetime", y_axis_type="log", height=400,
                    sizing_mode="stretch_width", width=1500,
                    tools=[WheelZoomTool(), PanTool(), ResetTool()])  # HoverTool for Date OHLCV to show on top/outside
        # formatters= {'x': 'datetime'}
        p1.xaxis.major_label_orientation = 3 / 4
        p1.grid.grid_line_alpha = 0.1
        p1.xaxis.ticker.desired_num_ticks = 25  # X axis tick every 4 hours

        p1.segment(df_daily_candles.date, df_daily_candles.high,
                   df_daily_candles.date, df_daily_candles.low, color="black")
        p1.vbar(df_daily_candles.date[dc_inc], w1, df_daily_candles.open[dc_inc], df_daily_candles.close[dc_inc],
                fill_color="green", line_color="black")
        p1.vbar(df_daily_candles.date[dc_dec], w1, df_daily_candles.open[dc_dec], df_daily_candles.close[dc_dec],
                fill_color="red", line_color="black")

        # Volume Bars
        p2 = figure(title=sym, x_axis_type="datetime", y_axis_type="log",
                    height=400, sizing_mode="stretch_both",
                    tools=[WheelZoomTool(), PanTool(), ResetTool()])
        # formatters= {'x': 'datetime'}
        p2.xaxis.major_label_orientation = 3 / 4
        p2.grid.grid_line_alpha = 0.1
        p2.xaxis.ticker.desired_num_ticks = 50  # X axis tick every 4 hours

        p2.segment(df_vol_candles.date, df_vol_candles.high, df_vol_candles.date, df_vol_candles.low, color="black")
        p2.vbar(df_vol_candles.date[vc_inc], w2, df_vol_candles.open[vc_inc], df_vol_candles.close[vc_inc],
                fill_color="green", line_color="black")
        p2.vbar(df_vol_candles.date[vc_dec], w2, df_vol_candles.open[vc_dec], df_vol_candles.close[vc_dec],
                fill_color="red", line_color="black")

        output_file("candlestick.html", title=sym)

        main_col = column(p1, p2)
        show(main_col, sizing_mode="stretch_both")

        #gridplot([[p1], [p2]], sizing_mode='stretch_both')
