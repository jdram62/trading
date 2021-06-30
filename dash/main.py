import pandas as pd
import config

from bokeh.plotting import figure, show, output_file

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
        w = 43200000 # 12Hours in milliseconds

        p1 = figure(x_axis_type="datetime", tools=TOOLS, plot_width=1500,plot_height=600, title=sym)
        p1.xaxis.major_label_orientation = 3 / 4
        p1.grid.grid_line_alpha = 0.1

        p1.segment(df.date, df.high, df.date, df.low, color="black")
        p1.vbar(df.date[inc], w, df.open[inc], df.close[inc], fill_color="green", line_color="black")
        p1.vbar(df.date[dec], w, df.open[dec], df.close[dec], fill_color="red", line_color="black")

        output_file("candlestick.html", title=sym)

        show(p1)





