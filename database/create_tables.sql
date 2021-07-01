CREATE TABLE watchlist (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL
);

CREATE TABLE volumeBars(
    ticker_id INTEGER NOT NULL,
    dt TIMESTAMP NOT NULL,
    open DECIMAL NOT NULL,
    high DECIMAL NOT NULL,
    low DECIMAL NOT NULL,
    close DECIMAL NOT NULL,
    volume DECIMAL NOT NULL,
    PRIMARY KEY (ticker_id, dt),
    CONSTRAINT fk_watchlist FOREIGN KEY (ticker_id) REFERENCES watchlist (id)
);

CREATE INDEX ON volumeBars (ticker_id, dt DESC);

CREATE TABLE dailyBars(
    ticker_id INTEGER NOT NULL,
    dt TIMESTAMP NOT NULL,
    open DECIMAL NOT NULL,
    high DECIMAL NOT NULL,
    low DECIMAL NOT NULL,
    close DECIMAL NOT NULL,
    volume DECIMAL NOT NULL,
    PRIMARY KEY (ticker_id, dt),
    CONSTRAINT fk_watchlist FOREIGN KEY (ticker_id) REFERENCES watchlist (id)
);

CREATE INDEX ON dailyBars (ticker_id, dt DESC);

CREATE TABLE hourBars(
    ticker_id INTEGER NOT NULL,
    dt TIMESTAMP NOT NULL,
    open DECIMAL NOT NULL,
    high DECIMAL NOT NULL,
    low DECIMAL NOT NULL,
    close DECIMAL NOT NULL,
    volume DECIMAL NOT NULL,
    PRIMARY KEY (ticker_id, dt),
    CONSTRAINT fk_watchlist FOREIGN KEY (ticker_id) REFERENCES watchlist (id)
);

CREATE INDEX ON hourBars (ticker_id, dt DESC);


CREATE TABLE dollarBars(
    ticker_id INTEGER NOT NULL,
    dt TIMESTAMP NOT NULL,
    open DECIMAL NOT NULL,
    high DECIMAL NOT NULL,
    low DECIMAL NOT NULL,
    close DECIMAL NOT NULL,
    volume DECIMAL NOT NULL,
    PRIMARY KEY (ticker_id, dt),
    CONSTRAINT fk_watchlist FOREIGN KEY (ticker_id) REFERENCES watchlist (id)
);

CREATE INDEX ON dollarBars (ticker_id, dt DESC);
