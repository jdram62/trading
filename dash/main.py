import pandas as pd
import config

from bokeh.io import curdoc, show
from bokeh.plotting import figure
from bokeh.models import Select, ColumnDataSource
from bokeh.layouts import row, column
from bokeh.models.tools import WheelZoomTool, PanTool, ResetTool, HoverTool

import psycopg2 as pg2

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


def nix(val, ticker_list):
    return [i for i in ticker_list if i != val]


def read_vol_candles(ticker_id, connection):
    with connection.cursor() as cursor:
        cursor.execute("""
                     SELECT dt, open, high, low, close, volume
                     FROM volumeBars
                     WHERE ticker_id= %s
                     ORDER BY dt ASC;
                 """, (ticker_id,))
        candles = cursor.fetchall()
    df = pd.DataFrame(candles, columns=['dt', 'o', 'h', 'l', 'c', 'v'])
    df = df.set_index('dt')
    return df


def read_daily_candles(ticker_id, connection):
    with connection.cursor() as cursor:
        cursor.execute("""
                    SELECT dt, open, high, low, close, volume
                    FROM dailyBars
                    WHERE ticker_id= %s
                    ORDER BY dt ASC;
                """, (ticker_id,))
        candles = cursor.fetchall()
    df = pd.DataFrame(candles, columns=['dt', 'o', 'h', 'l', 'c', 'v'])
    df = df.set_index('dt')
    return df


if __name__ == '__main__':
    # for n in WATCHLIST:
    #    print(nix(n, WATCHLIST))
    conn = pg2.connect(host="localhost", database="crypto", user="postgres", password=config.DB_PWD)
    conn.set_session(autocommit=True)

    vc_df = read_vol_candles(1, conn)
    print('start read')
    dc_df = read_daily_candles(1, conn)
    print('end read')
    conn.close()

    vol_candle_src = ColumnDataSource(data=dict(dt=[], o=[], h=[], l=[], c=[], v=[]))
    daily_candle_src = ColumnDataSource(data=dict(dt=[], o=[], h=[], l=[], c=[], v=[]))

    daily_candle_src.data = dc_df

    dc_inc = dc_df.c > dc_df.o
    dc_dec = dc_df.o > dc_df.c

    vc_inc = vc_df.c > vc_df.o
    vc_dec = vc_df.o > vc_df.c

    w1 = 43200000 * 2 - 25
    w2 = 3600000  # 1 Hour in milliseconds

    # Daily Candles
    p1 = figure(title='BTC-USD', x_axis_type="datetime", y_axis_type="log", height=700,
                sizing_mode="stretch_width", width=1500,
                tools=[WheelZoomTool(), PanTool(), ResetTool()])  # HoverTool for Date OHLCV to show on top/outside
    # formatters= {'x': 'datetime'}
    p1.xaxis.major_label_orientation = 3 / 4
    p1.grid.grid_line_alpha = 0.1
    p1.xaxis.ticker.desired_num_ticks = 25  # X axis tick every 4 hours

    p1.segment(x0='dt', y0='l', x1='dt', y1='h', line_width=1, color='black', source=daily_candle_src)
    # p1.vbar(x='dt', width=w1, top=, bottom=)

    main_col = column(p1)
    show(main_col)
    # curdoc().add_root(main_col)
    # curdoc().title = "crypto"
    # gridplot([[p1], [p2]], sizing_mode='stretch_both')
