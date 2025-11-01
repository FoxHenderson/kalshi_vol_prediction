import requests
import json
from datetime import datetime
import time

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
ENDPOINT = "/markets"
URL = BASE_URL + ENDPOINT
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

global SERIES_IDs
SERIES_IDs = {}

params = {
    "status": "settled",
    "limit": 1000,
    "cursor": None
}

"""ticker, title, CATEGORY, TIME TO EXPIRATION, CLOSE EARLY?, FINAL_VOLUME"""



class Market:




    
    def __init__(self, market):

        ticker_str = market.get("ticker")
        close_time_str = market.get("close_time").split(".")[0]
        open_time_str = market.get("open_time").split(".")[0]
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


        self.settlement_price = market.get("settlement_price")
        
        self.title = market.get("title", "N/A")
        
        parts = ticker_str.split('-', 2)



        self.series_ticker = parts[0]


        if self.series_ticker not in SERIES_IDs:
            response = requests.get(f"https://api.elections.kalshi.com/trade-api/v2/series/{self.series_ticker}")
            response.raise_for_status()
            data = response.json()
            series = data.get("series", [])
            SERIES_IDs[self.series_ticker] = series.get("category")

        self.category = SERIES_IDs[self.series_ticker]



        self.event_ticker = parts[1]
        self.outcome = parts[2]
        self.full_ticker = ticker_str


    def to_dict(self):
        return{
            "full_ticker": self.full_ticker,
            "series_ticker": self.series_ticker,
            "event_ticker": self.event_ticker,
            "outcome": self.outcome,
            "title": self.title,
            "duration": self.duration,
            "can_close_early": self.can_close_early,
            "final_volume": self.volume,
            "settlement_price": self.settlement_price,
            "category": self.category
        }

print(f"Attemping to fetch data from {URL}")

market_list = []
skipped = 0
counter = 0
page_counter = 0
while True:
    page_counter += 1
    print(f"\n--- Requesting Page {page_counter}. Markets fetched so far: {len(market_list)} ---")
    
    # 1. MAKE THE REQUEST using the current fetch_params (with the correct cursor)
    try:
        response = requests.get(URL, params=params)
        response.raise_for_status() # Check for HTTP errors (4xx or 5xx)
        data = response.json()
    except requests.RequestException as e:
        print(f"An error occurred during API request: {e}")
        break

    # 2. PROCESS THE MARKETS
    markets_on_this_page = data.get("markets", [])
    if not markets_on_this_page:
        print("No markets found on this page.")
        break # Exit if no markets are returned
        
    for market in markets_on_this_page:
        m = Market(market)
        market_list.append(m)

    # 3. HANDLE PAGINATION (The crucial part!)
    next_cursor = data.get("cursor")
    print(f"Received {len(markets_on_this_page)} markets. Next cursor: {next_cursor}")
    
    # Check if this is the final page
    if page_counter == 25:
        break

    if not next_cursor:
        print("\nPagination complete. No further cursor returned.")
        break
    
    # Update the cursor for the next request
    params["cursor"] = next_cursor
    
    # 4. RATE LIMIT DELAY (Necessary pause)
    time.sleep(1)
        

    print(f"\n Successfully retrieved {len(market_list)} settled market tickers.")
    print("skipped:", skipped)


if market_list:
    for i in range(0, 10):
        print(f"{i+1}.  {(market_list[i]).full_ticker}")






json_data_list = [m.to_dict() for m in market_list]
next_cursor
output_filename = "data2.json"

with open(output_filename, "w") as f:
    json.dump(json_data_list, f, indent=4)

