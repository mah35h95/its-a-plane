import requests

# BOUNDS_BOX = "51.6,51.4,-0.3,-0.1"
BOUNDS_BOX = "13.3,12.6,77.3,78.0"
# area to search for flights: top latitude, bottom latitude, left longitude, right longitude (so this example is central London)

# URLs
FLIGHT_SEARCH_HEAD = "https://data-live.flightradar24.com/zones/fcgi/feed.js?bounds="
FLIGHT_SEARCH_TAIL = "&faa=1&satellite=1&mlat=1&flarm=1&adsb=1&gnd=0&air=1&vehicles=0&estimated=0&maxage=14400&gliders=0&stats=0&ems=1&limit=1"
FLIGHT_SEARCH_URL = FLIGHT_SEARCH_HEAD + BOUNDS_BOX + FLIGHT_SEARCH_TAIL
# Used to get more flight details with a fr24 flight ID from the initial search
FLIGHT_LONG_DETAILS_HEAD = (
    "https://data-live.flightradar24.com/clickhandler/?version=1.5&notrail=true&flight="
    # "https://data-live.flightradar24.com/clickhandler/?version=1.5&flight="
)

# Request headers
request_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0",
    "cache-control": "no-store, no-cache, must-revalidate, post-check=0, pre-check=0",
    "accept": "application/json",
}


# Look for flights overhead
def get_flights():
    try:
        response = requests.get(url=FLIGHT_SEARCH_URL, headers=request_headers).json()
        print(response)
    except:
        print("Error during fetch")
        return False
    if len(response) == 3:
        # print ("Flight found.")
        for flight_id, flight_info in response.items():
            # the JSON has three main fields, we want the one that's a flight ID
            if not (flight_id == "version" or flight_id == "full_count"):
                if len(flight_info) > 13:
                    return flight_id
    else:
        return False


# Take the flight ID we found with a search, and load details about it
def get_flight_details(fn):
    response = requests.get(url=FLIGHT_LONG_DETAILS_HEAD + fn, headers=request_headers)
    print(response.text)


last_flight = ""
flight_id = get_flights()

if flight_id:
    if flight_id == last_flight:
        print("Same flight found, so keep showing it")
    else:
        print("New flight " + flight_id + " found")
        get_flight_details(flight_id)
        last_flight = flight_id
