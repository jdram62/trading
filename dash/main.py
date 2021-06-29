import pandas as pd
import config

from math import pi
from bokeh.driving import count
from bokeh.layouts import column, gridplot, row
from bokeh.models import ColumnDataSource, Select, Slider
from bokeh.plotting import curdoc, figure, show, output_file

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


async def read_db():
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


async def main():
    candles = await read_db()
    return candles


if __name__ == '__main__':

    candles_ret = asyncio.run(main())
    df_list = []
    for x, ticker in enumerate(WATCHLIST):
        temp_list = []
        for row in candles_ret:
            if x+1 == row[0]:
                temp_list.append([row[1], row[2], row[3], row[4], row[5]])
        df = pd.DataFrame(temp_list, columns=['date', 'open', 'high', 'low', 'close'])
        # df = df.set_index('date')
        df_list.append(df)

    for k, sym in enumerate(WATCHLIST):
        df = df_list[k]
        inc = df.close > df.open
        dec = df.open > df.close
        TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
        w = 12 * 60 * 60 * 1000  # half day in ms

        p1 = figure(x_axis_type="datetime", tools=TOOLS, plot_width=1750,plot_height=400, title=sym)
        p1.xaxis.major_label_orientation = pi / 4
        p1.grid.grid_line_alpha = 0.3

        p1.segment(df.date, df.high, df.date, df.low, color="black")
        p1.vbar(df.date[inc], w, df.open[inc], df.close[inc], fill_color="#D5E1DD", line_color="black")
        p1.vbar(df.date[dec], w, df.open[dec], df.close[dec], fill_color="#F2583E", line_color="black")

        output_file("candlestick.html", title=sym)

        show(p1)

    #curdoc().add_root(, toolbar_location="left", width=1000)
    #curdoc().title = "OHLC"




