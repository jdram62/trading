import pandas as pd
import numpy as np
import config

from bokeh.io import curdoc, show
from bokeh.plotting import figure
from bokeh.models import Select, ColumnDataSource, CustomJS
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


def read_vol_candles(ticker_id):
    conn = pg2.connect(host="localhost", database="crypto", user="postgres", password=config.DB_PWD)
    conn.set_session(autocommit=True)
    with conn.cursor() as cursor:
        cursor.execute("""
                     SELECT dt, open, high, low, close, volume
                     FROM volumeBars
                     WHERE ticker_id= %s
                     ORDER BY dt ASC;
                 """, (ticker_id,))
        candles = cursor.fetchall()
    conn.close()
    df = pd.DataFrame(candles, columns=['dt', 'o', 'h', 'l', 'c', 'v'])
    df = df.set_index('dt')
    return df


def read_daily_candles(ticker_id):
    conn = pg2.connect(host="localhost", database="crypto", user="postgres", password=config.DB_PWD)
    conn.set_session(autocommit=True)
    with conn.cursor() as cursor:
        cursor.execute("""
                    SELECT dt, open, high, low, close, volume
                    FROM dailyBars
                    WHERE ticker_id= %s
                    ORDER BY dt ASC;
                """, (ticker_id,))
        candles = cursor.fetchall()
    conn.close()
    df = pd.DataFrame(candles, columns=['dt', 'o', 'h', 'l', 'c', 'v'])
    df = df.set_index('dt')
    condition = [df.c > df.o,
                 df.c < df.o]
    choices = ['green', 'red']
    df['color'] = np.select(condition, choices)
    return df


# vc_df = read_vol_candles(1)
# dc_df = read_daily_candles(1)


# set up plots
# vol_candle_src = ColumnDataSource(data=dict(dt=[], o=[], h=[], l=[], c=[], v=[]))
daily_candle_src = ColumnDataSource(data=dict(dt=[], o=[], h=[], l=[], c=[], v=[], color=[]))

# Daily Candles
p1 = figure(x_axis_type="datetime", y_axis_type="log", sizing_mode="stretch_both",
            tools=[WheelZoomTool(), PanTool(), ResetTool()])  # HoverTool for Date OHLCV to show on top/outside
p1.xaxis.major_label_orientation = 3 / 4
p1.grid.grid_line_alpha = 0.1
p1.xaxis.ticker.desired_num_ticks = 100  # 25 X axis tick every 4 hours

p1.segment(x0='dt', y0='l', x1='dt', y1='h', line_width=2, color='black', source=daily_candle_src)
p1.segment(x0='dt', y0='o', x1='dt', y1='c', line_width=8, color='color', source=daily_candle_src)

# widget set up
select_options = list(ticker for ticker in WATCHLIST)
ticker_select = Select(title='TICKER', value='BTC-USD', options=select_options, width=300)


def function_to_call(attr, old, new):
    update()


def update():
    # p1 = ticker_select.value
    ticker_id = [x + 1 for x, ticker in enumerate(WATCHLIST) if ticker == ticker_select.value]
    dc_df = read_daily_candles(ticker_id[0])
    daily_candle_src.data = dc_df
    p1.title.text = WATCHLIST[ticker_id[0]-1]


ticker_select.on_change('value', function_to_call)


widgets = column(ticker_select)
series = column(p1)
layout = column(widgets, series, sizing_mode='stretch_width')

update()

curdoc().add_root(layout)
curdoc().title = "Dash"
