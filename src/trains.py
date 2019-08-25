import os
import requests
import json

from fixture import destinations_for_station_fixture, destinations_for_departure_fixture


def abbrStation(journeyConfig, inputStr):
    dict = journeyConfig['stationAbbr']
    for key in dict.keys():
        inputStr = inputStr.replace(key, dict[key])
    return inputStr

def loadDeparturesForStation(journeyConfig, appId, apiKey):
    if journeyConfig["departureStation"] == "":
        raise ValueError(
            "Please set the journey.departureStation property in config.json")

    if appId == "" or apiKey == "":
        raise ValueError(
            "Please complete the transportApi section of your config.json file")

    departureStation = journeyConfig["departureStation"]

    data = destinations_for_station_fixture
    #apply abbreviations / replacements to station names (long stations names dont look great on layout)
    #see config file for replacement list
    for item in data["departures"]["all"]:
         item['origin_name'] = abbrStation(journeyConfig, item['origin_name'])
         item['destination_name'] = abbrStation(journeyConfig, item['destination_name'])

    if "error" in data:
        raise ValueError(data["error"])

    return data["departures"]["all"], data["station_name"]


def loadDestinationsForDeparture(journeyConfig, timetableUrl):

    data = destinations_for_departure_fixture

    #apply abbreviations / replacements to station names (long stations names dont look great on layout)
    #see config file for replacement list
    foundDepartureStation = False

    for item in list(data["stops"]):
        if item['station_code'] == journeyConfig['departureStation']:
            foundDepartureStation = True

        if foundDepartureStation == False:
            data["stops"].remove(item)
            continue

        item['station_name'] = abbrStation(journeyConfig, item['station_name'])

    if "error" in data:
        raise ValueError(data["error"])

    departureDestinationList = list(map(lambda x: x["station_name"], data["stops"]))[1:]

    if len(departureDestinationList) == 1:
        departureDestinationList[0] = departureDestinationList[0] + ' only.'

    return departureDestinationList
