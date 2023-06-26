from machine import Pin, SPI
from ssd1306 import SSD1306_SPI
import framebuf
from time import sleep
from utime import sleep_ms
import network  # handles connecting to WiFi
import urequests  # handles making and servicing network requests

try:
    from code_secrets import secrets
except ImportError:
    print("Secrets including geo are kept in code_secrets.py, please add them there!")
    raise

# Time in seconds to wait between scrolling one line and the next
PAUSE_BETWEEN_LINE_SCROLLING = 3

# How often to query fr24 - quick enough to catch a plane flying over, not so often as to cause any issues, hopefully
QUERY_DELAY = 25

# Area to search for flights, see secrets file
# BOUNDS_BOX = "51.6,51.4,-0.3,-0.1"
BOUNDS_BOX = secrets["bounds_box"]
# area to search for flights: top latitude, bottom latitude, left longitude, right longitude (so this example is central London)

# URLs
FLIGHT_SEARCH_HEAD = "https://data-live.flightradar24.com/zones/fcgi/feed.js?bounds="
FLIGHT_SEARCH_TAIL = "&faa=1&satellite=1&mlat=1&flarm=1&adsb=1&gnd=0&air=1&vehicles=0&estimated=0&maxage=14400&gliders=0&stats=0&ems=1&limit=1"
FLIGHT_SEARCH_URL = FLIGHT_SEARCH_HEAD + BOUNDS_BOX + FLIGHT_SEARCH_TAIL
# Used to get more flight details with a fr24 flight ID from the initial search
FLIGHT_LONG_DETAILS_HEAD = (
    # "https://data-live.flightradar24.com/clickhandler/?flight="
    "https://data-live.flightradar24.com/clickhandler/?version=1.5&notrail=true&flight="
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
        response = urequests.get(url=FLIGHT_SEARCH_URL, headers=request_headers).json()
    except Exception as e:
        print("Error getting a flight")
        print(e.__class__.__name__ + "----------------ERROR---------------")
        print(e)
        checkConnection()
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
    # Get the URL response one chunk at a time
    try:
        response = urequests.get(
            url=FLIGHT_LONG_DETAILS_HEAD + fn, headers=request_headers
        ).json()
    # Handle occasional URL fetching errors
    except Exception as e:
        print("Error getting a flight details")
        print(e.__class__.__name__ + "----------------ERROR---------------")
        print(e)
        checkConnection()
        return False
    return parse_details_json(response)


# Look at the byte array that fetch_details saved into and extract any fields we want
def parse_details_json(long_json):
    try:
        # Some available values from the JSON. Put the details URL and a flight ID in your browser and have a look for more.
        flight_number = long_json["identification"]["number"]["default"]
        # print(flight_number)
        flight_callsign = long_json["identification"]["callsign"]
        aircraft_code = long_json["aircraft"]["model"]["code"]
        aircraft_model = long_json["aircraft"]["model"]["text"]
        # aircraft_registration=long_json["aircraft"]["registration"]
        airline_name = long_json["airline"]["name"]
        # airline_short=long_json["airline"]["short"]
        airport_origin_name = long_json["airport"]["origin"]["name"]
        airport_origin_name = airport_origin_name.replace(" Airport", "")
        airport_origin_code = long_json["airport"]["origin"]["code"]["iata"]
        # airport_origin_country=long_json["airport"]["origin"]["position"]["country"]["name"]
        # airport_origin_country_code=long_json["airport"]["origin"]["position"]["country"]["code"]
        # airport_origin_city=long_json["airport"]["origin"]["position"]["region"]["city"]
        # airport_origin_terminal=long_json["airport"]["origin"]["info"]["terminal"]
        airport_destination_name = long_json["airport"]["destination"]["name"]
        airport_destination_name = airport_destination_name.replace(" Airport", "")
        airport_destination_code = long_json["airport"]["destination"]["code"]["iata"]
        # airport_destination_country=long_json["airport"]["destination"]["position"]["country"]["name"]
        # airport_destination_country_code=long_json["airport"]["destination"]["position"]["country"]["code"]
        # airport_destination_city=long_json["airport"]["destination"]["position"]["region"]["city"]
        # airport_destination_terminal=long_json["airport"]["destination"]["info"]["terminal"]
        # time_scheduled_departure=long_json["time"]["scheduled"]["departure"]
        # time_real_departure=long_json["time"]["real"]["departure"]
        # time_scheduled_arrival=long_json["time"]["scheduled"]["arrival"]
        # time_estimated_arrival=long_json["time"]["estimated"]["arrival"]
        # latitude=long_json["trail"][0]["lat"]
        # longitude=long_json["trail"][0]["lng"]
        # altitude=long_json["trail"][0]["alt"]
        # speed=long_json["trail"][0]["spd"]
        # heading=long_json["trail"][0]["hd"]

        if flight_number or flight_callsign:
            print(
                "Flight is called by Number: "
                + flight_number
                + ", or Call Sign: "
                + flight_callsign
            )
        else:
            print("No number or callsign for this flight.")

        # Set up to 6 of the values above as text for display_flights to put on the screen
        # Short strings get placed on screen, then longer ones scroll over each in sequence

        global line1_short, line1_long, line2_short, line2_long, line3_short, line3_long

        if flight_number:
            line1_short = flight_number
        else:
            line1_short = flight_callsign
        line1_long = airline_name + " - " + flight_callsign
        line2_short = airport_origin_code + " - " + airport_destination_code
        line2_long = airport_origin_name + " - " + airport_destination_name
        line3_short = aircraft_code
        line3_long = aircraft_model

        if not line1_short:
            line1_short = ""
        if not line1_long:
            line1_long = ""
        if not line2_short:
            line2_short = ""
        if not line2_long:
            line2_long = ""
        if not line3_short:
            line3_short = ""
        if not line3_long:
            line3_long = ""

        # optional filter example - check things and return false if you want

        # if altitude > 10000:
        #    print("Altitude Filter matched so don't display anything")
        #    return False

    except (KeyError, ValueError, TypeError) as e:
        print("Error parsing JSON, skip displaying this flight")
        print("JSON error")
        print(e)
        return False

    return True


# Populate the lines, then scroll longer versions of the text
def display_flight(oled):
    global flight_id, line1_short, line1_long, line2_short, line2_long, line3_short, line3_long, line1, line2, line3

    line1 = line1_short
    line2 = line2_short
    line3 = line3_short
    display_details(oled, flight_id, line1, line2, line3)
    sleep(PAUSE_BETWEEN_LINE_SCROLLING)

    line1 = line1_long
    display_details(oled, flight_id, line1, line2, line3)
    sleep(PAUSE_BETWEEN_LINE_SCROLLING)
    line1 = line1_short

    line2 = line2_long
    display_details(oled, flight_id, line1, line2, line3)
    sleep(PAUSE_BETWEEN_LINE_SCROLLING)
    line2 = line2_short

    line3 = line3_long
    display_details(oled, flight_id, line1, line2, line3)
    sleep(PAUSE_BETWEEN_LINE_SCROLLING)
    line3 = line3_short

    display_details(oled, flight_id, line1, line2, line3)
    sleep(PAUSE_BETWEEN_LINE_SCROLLING)


def display_details(oled, flight_id, line1, line2, line3):
    oled.fill(0)
    oled.text("ID: " + flight_id, 0, 0)
    oled.text(line1, 0, 16)
    oled.text(line2, 0, 16 * 2)
    oled.text(line3, 0, 16 * 3)
    oled.show()
    if len(line1) > 16:
        scroll(oled, line1, 0, 16)
    if len(line2) > 16:
        scroll(oled, line2, 0, 16 * 2)
    if len(line3) > 16:
        scroll(oled, line3, 0, 16 * 3)


def scroll(oled, line, x, y):
    for i in range(160 + len(line) * 8):
        oled.fill_rect(x, y, 128, 16, 0)
        oled.text(line, 128 - x - i, y)
        oled.show()
        sleep_ms(10)
    oled.fill_rect(x, y, 128, 16, 0)
    oled.text(line, x, y)
    oled.show()


def display_logo(oled):
    oled.text("Booting up ^", 0, 16 * 2)
    oled.show()
    # Display the Raspberry Pi logo on the OLED
    buffer = bytearray(
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00|?\x00\x01\x86@\x80\x01\x01\x80\x80\x01\x11\x88\x80\x01\x05\xa0\x80\x00\x83\xc1\x00\x00C\xe3\x00\x00~\xfc\x00\x00L'\x00\x00\x9c\x11\x00\x00\xbf\xfd\x00\x00\xe1\x87\x00\x01\xc1\x83\x80\x02A\x82@\x02A\x82@\x02\xc1\xc2@\x02\xf6>\xc0\x01\xfc=\x80\x01\x18\x18\x80\x01\x88\x10\x80\x00\x8c!\x00\x00\x87\xf1\x00\x00\x7f\xf6\x00\x008\x1c\x00\x00\x0c \x00\x00\x03\xc0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    )
    fb = framebuf.FrameBuffer(buffer, 32, 32, framebuf.MONO_HLSB)

    oled.blit(fb, 96, 15)
    oled.show()


def display_pikachu(oled):
    # Display the Raspberry Pi logo on the OLED
    buffer = bytearray(
        b"\x00\x00\x01\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xe0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xf0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\xfc\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xfe\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf8\x80\x00\x00\x00\x00\x00\x00\x00\x01\xe0\x00\x00\x00\x00\x00x@\x00\x00\x00\x00\x00\x00\x00\x1f\xe0\x00\x00\x00\x00\x008\x10\x00\x00\x00\x00\x00\x00\x00\xff\xc0\x00\x00\x00\x00\x008\x0c\x00\x00\x00\x00\x00\x00\x03\xff\x80\x00\x00\x00\x00\x00\x18\x02\x00\x00\x00\x00\x00\x00\x1c\x7f\x80\x00\x00\x00\x00\x00\x0c\x01\x80\x00\x00\x00\x00\x00`\x7f\x00\x00\x00\x00\x00\x00\x0c\x00\xc0\x00\x00\x00\x00\x01\x80~\x00\x00\x00\x00\x00\x00\x04\x000\x00\x00\x00\x00\x0e\x00|\x00\x00\x00\x00\x00\x00\x06\x00\x18\x00\x00\x00\x008\x00\xfc\x00\x00\x00\x00\x00\x00\x03\x00\x06\x00\x00\x00\x00\xe0\x00\xf8\x00\x00\x00\x00\x00\x00\x01\x00\x03\x00\x00\x00\x03\x80\x00\xf0\x00\x00\x00\x00\x00\x00\x01\x80\x00\x80\x00\x00\x0c\x00\x00\xe0\x00\x00\x00\x00\x00\x00\x00\xc0\x00`\x00\x000\x00\x01\xc0\x00\x00\x00\x00\x00\x00\x00\xc0\x00?\xff\xff\xe0\x00\x01\x80\x00\x00\x00\x00\x00\x00\x00`\x00\x10\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x000\x00\x00\x00\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x18\x00\x00\x00\x00\x00\x00\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x0c\x00\x00\x00\x00\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x0c\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x00\x00\x00\x00\x00\x03 \x00\x00\x00\x00\x01\x80\x00\x00\x00\x00\x00\x00\x00\x00\x01\xc0\x00\x00\x00\x00C\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x00\x00\x00\x00&\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x00\x00\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x80\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xe0\x00\x05\xc0\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x04p\x00\x08\xe0\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x04p\x00\x08\xe0\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x06\xf0\x00\r\xe0\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xf0\x00\x07\xe0\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x03\xf0\x00\x07\xe0\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x01\xe0\x00\x01\xc0\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0c\x00\x00\xf0\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00\xf0\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\xc0\x000\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1f\xe0\x00\x00\x00\x0f\x81\x80\x00\x00\x00\x00\x00\x00\x00\x00\x1f\xf0\x00\x00\x00\x1f\xc0\x80\x00\x00\x00\x00\x00\x00\x00\x00\x1f\xf0\x00\x00\x00\x1f\xe0\x80\x00\x00\x00\x00\x00\x00\x00\x00\x1f\xf0\x00\x00\x00\x1f\xe0\x80\x00\x00\x00\x00\x00\x00\x00\x00?\xf0\x01\xfe\x00\x1f\xe0\xc0\x00\x00\x00\x00\x00\x00\x00\x007\xe0\x03\xf3\x80\x1f\xe0\xc0\x00\x00\x00\x00\x00\x00\x00\x00#\xc0\x03\xc1\x80\x1f\xc0@\x00\x00\x00\x00\x00\x00\x00\x000\x00\x03\x80\x80\x0f\xc0@\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x03\x00\xc0\x07\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x03\x00\x80\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x01\x81\x80\x00\x00`\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x01\xc7\x80\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x7f\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x000\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x18\x00\x00\x00\x00"
    )
    fb = framebuf.FrameBuffer(buffer, 128, 64, framebuf.MONO_HLSB)

    oled.invert(0)
    oled.blit(fb, 0, 0)
    oled.show()


def display_plane(oled):
    # open image, put your image here
    with open("plane-icon.pbm", "rb") as f:
        f.readline()  # number
        f.readline()  # Creator
        f.readline()  # Dimensions
        data = bytearray(f.read())

    fb = framebuf.FrameBuffer(data, 128, 64, framebuf.MONO_HLSB)

    oled.fill(0)
    for i in range(0, 112 * 2):
        # oled.invert(0)
        oled.blit(fb, 128 - i, 0)
        oled.show()
        sleep_ms(6)


def checkConnection():
    global wlan, oled
    display_pikachu(oled)
    # Fill in your network name (ssid) and password here:
    print("Check and reconnect WiFi")
    attempts = 10
    attempt = 1
    while (wlan.isconnected() == False) and attempt < attempts:
        print("Connect attempt " + str(attempt) + " of " + str(attempts))
        try:
            print("Attempt WiFi connect...")
            wlan.connect(secrets["ssid"], secrets["password"])
        except Exception as e:
            print(e.__class__.__name__ + "----------------ERROR---------------")
            print(e)
        attempt += 1
    if wlan.isconnected() == True:
        print(f"Successfully connected. Status: {wlan.status()}")
    else:
        print(f"Failed to connect. Status: {wlan.status()}")


# Blank the display when a flight is no longer found
def clear_flight():
    global line1, line2, line3
    line1 = line2 = line3 = ""


# Connect to network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# text strings to go in the lines
line1_short = ""
line1_long = ""
line2_short = ""
line2_long = ""
line3_short = ""
line3_long = ""

line1 = ""
line2 = ""
line3 = ""

spi = SPI(0, 100000, mosi=Pin(19), sck=Pin(18))
# oled = SSD1306_SPI(WIDTH, HEIGHT, spi, dc,rst, cs) use GPIO PIN NUMBERS
oled = SSD1306_SPI(128, 64, spi, Pin(17), Pin(20), Pin(16))

oled.fill(0)
display_logo(oled)
sleep(2)

checkConnection()
last_flight = ""

while True:
    try:
        flight_id = get_flights()

        if flight_id:
            if flight_id == last_flight:
                print("Same flight found, so keep showing it")
            else:
                print("New flight " + flight_id + " found, clear display")
                clear_flight()
                if get_flight_details(flight_id):
                    display_plane(oled)
                    display_flight(oled)
                else:
                    print("error loading details, skip displaying this flight")

                last_flight = flight_id
        else:
            print("No flights found, clear display")
            clear_flight()

        oled.fill(0)
        oled.show()

        print("Going to sleep for a while...")
        sleep(5)
        for i in range(0, QUERY_DELAY, +5):
            sleep(5)
    except KeyboardInterrupt as ke:
        print(ke.__class__.__name__ + "-------------FORCE-TERMINATING-------------")
        oled.fill(0)
        oled.show()
        break
