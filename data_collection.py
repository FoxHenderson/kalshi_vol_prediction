import requests
import json
from datetime import datetime
import time

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
ENDPOINT = "/markets"
URL = BASE_URL + ENDPOINT
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

params = {
    "status": "settled",
    "limit": 100
}

"""ticker, title, CATEGORY, TIME TO EXPIRATION, CLOSE EARLY?, FINAL_VOLUME"""



class Market:

    def __init__(self, market):

        ticker_str = market.get("ticker")
        self.close_time = market.get("close_time").split(".")[0]
        self.open_time = market.get("open_time").split(".")[0]
        self.settlement_price = market.get("settlement_value")
        self.title = market.get("title", "N/A")
        self.volume = market.get("volume")
        self.can_close_early = market.get("can_close_early")

        #print ("close", close_time_str.rstrip('Z'))
        #print("open", open_time_str.rstrip('Z'))



        close_time_dt = datetime.strptime(close_time_str.rstrip('Z'), DATE_FORMAT)
        self.close_time = close_time_dt.timestamp()
        open_time_dt = datetime.strptime(open_time_str.rstrip('Z'), DATE_FORMAT)
        self.open_time = open_time_dt.timestamp()
        

        self.duration = self.close_time-self.open_time


        self.settlement_price = market.get("settlement_price", None)
        
        self.title = market.get("title", "N/A")
        
        parts = ticker_str.split('-', 2)



        self.series_ticker = parts[0]
        self.event_ticker = parts[1]
        self.outcome = parts[2]
        self.full_ticker = ticker_str



try:
    print(f"Attemping to fetch data from {URL}")
    response = requests.get(URL, params=params)
    response.raise_for_status()
    data = response.json()

    market_list = []
    skipped = 0
    for market in data.get("markets", []):
        m = Market(market)
        market_list.append(m)
        

    print(f"\n Successfully retrieved {len(market_list)} settled market tickers.")
    print("skipped:", skipped)
    if market_list:
        for i in range(0, 10):
            print(f"{i+1}.  {(market_list[i]).full_ticker}")
    

    print(market_list[0].open_time)
    print(market_list[0].close_time)
except requests.exceptions.RequestException as e:
    print(e)
