import json
import os
import time
from datetime import datetime

from PIL import ImageFont
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.core.sprite_system import framerate_regulator
from luma.core.virtual import viewport, snapshot
from luma.oled.device import ssd1322

from open import is_run
from trains import load_departures_for_station, load_destinations_for_departure


def load_config():
    with open('config.json', 'r') as json_config:
        data = json.load(json_config)
        return data


def make_font(name, size):
    font_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            'fonts',
            name
        )
    )
    return ImageFont.truetype(font_path, size)


def render_destination(departure, font):
    departure_time = departure["aimed_departure_time"]
    destination_name = departure["destination_name"]

    def draw_text(draw, width, height):
        train = f"{departure_time}  {destination_name}"
        draw.text((0, 0), text=train, font=font, fill="yellow")

    return draw_text


def render_service_status(departure):
    def draw_text(draw, width, height):
        train = ""

        if isinstance(departure["expected_departure_time"], str):
            train = 'Exp ' + departure["expected_departure_time"]

        if departure["aimed_departure_time"] == departure["expected_departure_time"]:
            train = "On time"

        w, h = draw.textsize(train, font)
        draw.text((width - w, 0), text=train, font=font, fill="yellow")

    return draw_text


def render_platform(departure):
    def draw_text(draw, width, height):
        if isinstance(departure["platform"], str):
            draw.text((0, 0), text="Plat " + departure["platform"], font=font, fill="yellow")

    return draw_text


def render_calling_at(draw, width, height):
    stations = "Calling at:"
    draw.text((0, 0), text=stations, font=font, fill="yellow")


def render_stations(stations):
    def draw_text(draw, width, height):
        global station_render_count, pause_count

        if len(stations) == station_render_count - 5:
            station_render_count = 0

        draw.text(
            (0, 0), text=stations[station_render_count:], width=width, font=font, fill="yellow")

        if station_render_count == 0 and pause_count < 8:
            pause_count += 1
            station_render_count = 0
        else:
            pause_count = 0
            station_render_count += 1

    return draw_text


def render_time(draw, width, height):
    raw_time = datetime.now().time()
    hour, minute, second = str(raw_time).split('.')[0].split(':')

    w1, h1 = draw.textsize("{}:{}".format(hour, minute), font_bold_large)
    w2, h2 = draw.textsize(":00", font_bold_tall)

    draw.text(((width - w1 - w2) / 2, 0), text="{}:{}".format(hour, minute),
              font=font_bold_large, fill="yellow")
    draw.text((((width - w1 - w2) / 2) + w1, 5), text=":{}".format(second),
              font=font_bold_tall, fill="yellow")


def render_welcome_to(x_offset):
    def draw_text(draw, width, height):
        text = "Welcome to"
        draw.text((int(x_offset), 0), text=text, font=font_bold, fill="yellow")

    return draw_text


def render_departure_station(departure_station, x_offset):
    def draw(draw, width, height):
        text = departure_station
        draw.text((int(x_offset), 0), text=text, font=font_bold, fill="yellow")

    return draw


def render_dots(draw, width, height):
    text = ".  .  ."
    draw.text((0, 0), text=text, font=font_bold, fill="yellow")


def load_data(api_config, journey_config):
    run_hours = [int(x) for x in api_config['operatingHours'].split('-')]
    if not is_run(run_hours[0], run_hours[1]):
        return False, False, journey_config['outOfHoursName']

    departures, station_name = load_departures_for_station(
        journey_config, api_config["appId"], api_config["apiKey"])

    if len(departures) == 0:
        return False, False, station_name

    first_departure_destinations = load_destinations_for_departure(
        journey_config, departures[0]["service_timetable"]["id"])

    return departures, first_departure_destinations, station_name


def draw_blank_signage(device, width, height, departure_station):
    global station_render_count, pause_count

    with canvas(device) as draw:
        welcome_size = draw.textsize("Welcome to", font_bold)

    with canvas(device) as draw:
        station_size = draw.textsize(departure_station, font_bold)

    device.clear()

    virtual_viewport = viewport(device, width=width, height=height)

    row_one = snapshot(width, 10, render_welcome_to(
        (width - welcome_size[0]) / 2), interval=10)
    row_two = snapshot(width, 10, render_departure_station(
        departure_station, (width - station_size[0]) / 2), interval=10)
    row_three = snapshot(width, 10, render_dots, interval=10)
    row_time = snapshot(width, 14, render_time, interval=1)

    if len(virtual_viewport._hotspots) > 0:
        for hotspot, xy in virtual_viewport._hotspots:
            virtual_viewport.remove_hotspot(hotspot, xy)

    virtual_viewport.add_hotspot(row_one, (0, 0))
    virtual_viewport.add_hotspot(row_two, (0, 12))
    virtual_viewport.add_hotspot(row_three, (0, 24))
    virtual_viewport.add_hotspot(row_time, (0, 50))

    return virtual_viewport


def draw_signage(device, width, height, data):
    global station_render_count, pause_count

    device.clear()

    virtual_viewport = viewport(device, width=width, height=height)

    status = "Exp 00:00"
    calling_at = "Calling at:"

    departures, first_departure_destinations, departure_station = data

    with canvas(device) as draw:
        w, h = draw.textsize(calling_at, font)

    calling_width = w
    width = virtual_viewport.width

    # _first measure the text size
    with canvas(device) as draw:
        w, h = draw.textsize(status, font)
        pw, ph = draw.textsize("Plat 88", font)

    row_one_a = snapshot(
        width - w - pw - 5, 10, render_destination(departures[0], font_bold), interval=10)
    row_one_b = snapshot(w, 10, render_service_status(
        departures[0]), interval=1)
    row_one_c = snapshot(pw, 10, render_platform(departures[0]), interval=10)
    row_two_a = snapshot(calling_width, 10, render_calling_at, interval=100)
    row_two_b = snapshot(width - calling_width, 10,
                         render_stations(", ".join(first_departure_destinations)), interval=0.1)

    if len(departures) > 1:
        row_three_a = snapshot(width - w - pw, 10, render_destination(
            departures[1], font), interval=10)
        row_three_b = snapshot(w, 10, render_service_status(
            departures[1]), interval=1)
        row_three_c = snapshot(pw, 10, render_platform(departures[1]), interval=10)

    if len(departures) > 2:
        row_four_a = snapshot(width - w - pw, 10, render_destination(
            departures[2], font), interval=10)
        row_four_b = snapshot(w, 10, render_service_status(
            departures[2]), interval=1)
        row_four_c = snapshot(pw, 10, render_platform(departures[2]), interval=10)

    row_time = snapshot(width, 14, render_time, interval=0.1)

    if len(virtual_viewport._hotspots) > 0:
        for hotspot, xy in virtual_viewport._hotspots:
            virtual_viewport.remove_hotspot(hotspot, xy)

    station_render_count = 0
    pause_count = 0

    virtual_viewport.add_hotspot(row_one_a, (0, 0))
    virtual_viewport.add_hotspot(row_one_b, (width - w, 0))
    virtual_viewport.add_hotspot(row_one_c, (width - w - pw, 0))
    virtual_viewport.add_hotspot(row_two_a, (0, 12))
    virtual_viewport.add_hotspot(row_two_b, (calling_width, 12))

    if len(departures) > 1:
        virtual_viewport.add_hotspot(row_three_a, (0, 24))
        virtual_viewport.add_hotspot(row_three_b, (width - w, 24))
        virtual_viewport.add_hotspot(row_three_c, (width - w - pw, 24))

    if len(departures) > 2:
        virtual_viewport.add_hotspot(row_four_a, (0, 36))
        virtual_viewport.add_hotspot(row_four_b, (width - w, 36))
        virtual_viewport.add_hotspot(row_four_c, (width - w - pw, 36))

    virtual_viewport.add_hotspot(row_time, (0, 50))

    return virtual_viewport


try:
    config = load_config()

    serial = spi()
    device = ssd1322(serial, mode="1", rotate=2)
    font = make_font("Dot Matrix Regular.ttf", 10)
    font_bold = make_font("Dot Matrix Bold.ttf", 10)
    font_bold_tall = make_font("Dot Matrix Bold Tall.ttf", 10)
    font_bold_large = make_font("Dot Matrix Bold.ttf", 20)

    widget_width = 256
    widget_height = 64

    station_render_count = 0
    pause_count = 0
    loop_count = 0

    regulator = framerate_regulator(fps=10)

    data = load_data(config["transportApi"], config["journey"])

    if not data[0]:
        virtual = draw_blank_signage(
            device, width=widget_width, height=widget_height, departure_station=data[2])
    else:
        virtual = draw_signage(device, width=widget_width,
                               height=widget_height, data=data)

    time_at_start = time.time()
    time_now = time.time()

    while True:
        with regulator:
            if time_now - time_at_start >= config["refreshTime"]:
                data = load_data(config["transportApi"], config["journey"])
                if not data[0]:
                    virtual = draw_blank_signage(
                        device, width=widget_width, height=widget_height, departure_station=data[2])
                else:
                    virtual = draw_signage(device, width=widget_width,
                                           height=widget_height, data=data)

                time_at_start = time.time()

            time_now = time.time()
            print('display refreshed')
            virtual.refresh()

except KeyboardInterrupt:
    pass
except ValueError as err:
    print(f"Error: {err}")
except KeyError as err:
    print(f"Error: Please ensure the {err} environment variable is set")
