import requests
from fake_useragent import UserAgent
from datetime import date

ua = UserAgent()
header = {'User-Agent':str(ua.random)}


download_url = 'https://www.redfin.com/stingray/api/gis-csv?al=1&include_pending_homes=true&isRentals=false&market=seattle&max_price=1500000&num_homes=350&ord=redfin-recommended-asc&page_number=1&region_id=16163,17887&region_type=6,6&sold_within_days=7&status=1&travel_with_traffic=false&travel_within_region=false&uipt=1,2,3,4,5,6,7,8&v=8'

def download_file(url, header, filename=''):
    try:
        if filename:
            pass            
        else:
            filename = str(date.today()) + '_sold.csv'

        with requests.get(url, headers=header) as req:
            with open(filename, 'wb') as f:
                for chunk in req.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return filename
    except Exception as e:
        print(e)
        return None

download_file(download_url, header)

 