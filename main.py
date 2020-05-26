import json
import requests
from typing import Union
from flask import jsonify

base = 'http://webservices.nextbus.com/service/publicJSONFeed?'
# debug = False

def process(request) -> dict:
    """Takes in an event from AWS API Gateway.
    The event is the payload of the POST request made from DialogFlow to the our fulfillment endpoint.
    Use the included sample_event.json, which should match this format:
    https://developers.google.com/actions/reference/v1/dialogflow-webhook#request

    The lambda function returns a dict that should match this format:
    https://developers.google.com/actions/build/json/dialogflow-webhook-json#dialogflow-response-body
    Source is always the "BART API"    """

    # if debug:
    #     print("Running in debug mode!")
    #     event = request
    #     jsonify = lambda x : x
    # else:
    event = request.get_json()

    params = event.get("queryResult").get("parameters")
    busLine, start, end = params.get("bus-line"), params.get("start"), params.get("end")

    # First, let's query for the stop ID.
    stopId, stopTitle = getStopInfo(busLine, start)
    print('Stop ID =', stopId)
    print('Stop Title =', stopTitle)

    # Now, let's find the minutes to the next arrival.
    nextBusTime = getNextBusTime(busLine, stopId)
    print('Next Bus Time =', nextBusTime)

    # Now, let's build a string response.
    responseStr = buildResponse(stopTitle, nextBusTime)
    print('Response =', responseStr)

    # Let's convert the string response to a JSON response.
    responseJson = buildJSONResponse(responseStr)

    return jsonify(responseJson)

def getStopInfo(routeTag, station) -> Union[str, str]:
    """Returns the list of stops given a route

    Args:
        routeTag (str): The route tag i.e. peri
        station (str): The unprocessed station name i.e. sproul hall

    Returns:
        str: the stopId i.e. "14"
        str: the stopTitle i.e. "Sproul Hall @ Bancroft Way"

    """
    url = base + 'command=routeConfig&a=ucb&r=' + routeTag
    print('Query for List of Stops: ' + url)
    stopsQuery = requests.get(url)
    stops = stopsQuery.json().get("route").get("stop")
    stopId, stopTitle = None, None
    for stop in stops:
        title = stop.get("title").lower()
        title = title.split(" ")[0]
        search = station.split(" ")[0]
        if title.__contains__(search):
            stopTitle = stop.get("shortTitle")
            stopId = stop.get("stopId")

    return stopId, stopTitle


def getNextBusTime(routeTag, stopId) -> int:
    """Returns the minutes to the next bus arrival.

    Args:
        routeTag (str): The route tag i.e. peri
        stopId (str): The stop id used to query for a stop

    Returns:
        int: the minutes to the next bus arrival (None if no buses found)

    """
    url = base + 'command=predictions&a=ucb&stopId={0}&routeTag={1}'.format(stopId, routeTag)
    print('Query for Bus Predictions: ' + url)
    predictionsQuery = requests.get(url)
    direction = predictionsQuery.json().get("predictions").get("direction", None)
    if direction != None:
        predictions = direction.get("prediction")
        if len(predictions) > 0:
            return int(predictions[0].get("minutes"))

    return None


def buildResponse(stopTitle, nextBusTime) -> str:
    """Builds & returns a string response to be returned to the user.

    Args:
        stopTitle (str): The route tag i.e. Sproul Hall @ Bancroft Way
        nextBusTime (int): The time to the next bus arrival (i.e. 5)

    Returns:
        str: the string response to be displayed to the user

    """
    if nextBusTime == None:
        return "There are no scheduled stops for this bus at this time."
    elif nextBusTime <= 1:
        return "The next bus departs shortly."
    else:
        return "The next bus departs in " + str(nextBusTime) + " minutes."


def buildJSONResponse(responseStr) -> dict:
    """Builds & returns a JSON response formatted according to DialogFlow docs.

    Args:
        responseStr (str): The string response

    Returns:
        dict: the json response including the string response passed in

    """
    path = 'response_format.json'

    with open(path) as f:
        response = json.load(f)
        items = [
            {"simpleResponse":
                {
                    "textToSpeech": responseStr,
                    "displayText": responseStr
                }
            }]

        response["payload"]["google"]["richResponse"]["items"] = items
        return response


def test_lambda_handler():
    """This may be helpful when testing your function"""
    path = 'sample_event.json'
    # global debug
    # debug = True
    with open(file=path, mode='r') as f:
        sample_event = json.load(f)

    response = process(sample_event)
    print(json.dumps(response, indent=4))

if __name__ == '__main__':
    test_lambda_handler()
