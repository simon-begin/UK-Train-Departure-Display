from fixture import destinations_for_station_fixture, destinations_for_departure_fixture


def abbr_station(journey_config, input_str):
    dict = journey_config['stationAbbr']
    for key in dict.keys():
        input_str = input_str.replace(key, dict[key])
    return input_str


def load_departures_for_station(journey_config, app_id, api_key):
    if journey_config["departureStation"] == "":
        raise ValueError(
            "Please set the journey.departure_station property in config.json")

    if app_id == "" or api_key == "":
        raise ValueError(
            "Please complete the transport_api section of your config.json file")

    departure_station = journey_config["departureStation"]

    data = destinations_for_station_fixture
    # apply abbreviations / replacements to station names (long stations names dont look great on layout)
    # see config file for replacement list
    for item in data["departures"]["all"]:
        item['origin_name'] = abbr_station(journey_config, item['origin_name'])
        item['destination_name'] = abbr_station(journey_config, item['destination_name'])

    if "error" in data:
        raise ValueError(data["error"])

    return data["departures"]["all"], data["station_name"]


def load_destinations_for_departure(journey_config, timetable_url):
    data = destinations_for_departure_fixture

    # apply abbreviations / replacements to station names (long stations names dont look great on layout)
    # see config file for replacement list
    found_departure_station = False

    for item in list(data["stops"]):
        if item['station_code'] == journey_config['departureStation']:
            found_departure_station = True

        if not found_departure_station:
            data["stops"].remove(item)
            continue

        item['station_name'] = abbr_station(journey_config, item['station_name'])

    if "error" in data:
        raise ValueError(data["error"])

    departure_destination_list = list(map(lambda x: x["station_name"], data["stops"]))[1:]

    if len(departure_destination_list) == 1:
        departure_destination_list[0] = departure_destination_list[0] + ' only.'

    return departure_destination_list
