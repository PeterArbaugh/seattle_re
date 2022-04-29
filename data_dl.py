import requests
from datetime import date

download_url = 'https://www.redfin.com/stingray/api/gis-csv?al=1&include_pending_homes=false&isRentals=false&max_num_beds=4&max_price=1000000&num_baths=1.5&num_beds=2&num_homes=350&ord=redfin-recommended-asc&page_number=1&region_id=17887,16163&region_type=6,6&sf=1,2,5,6,7&status=1&uipt=1,2,3&v=8'

def download_file(url, filename=''):
    try:
        if filename:
            pass            
        else:
            filename = str(date.today()) + '_for_sale.csv'

        with requests.get(url) as req:
            with open(filename, 'wb') as f:
                for chunk in req.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return filename
    except Exception as e:
        print(e)
        return None

download_file(download_url)

 