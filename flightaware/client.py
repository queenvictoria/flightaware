import os
import datetime
import logging

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("flightaware.client")

BASE_URL = "http://flightxml.flightaware.com/json/FlightXML2/"
MAX_RECORD_LENGTH = 15
EPOCH = datetime.datetime(1970, 1, 1)


def to_unix_timestamp(val):
    if val:
        if not isinstance(val, datetime.datetime):
            raise ValueError("input must be of type datetime")
        output = int((val - EPOCH).total_seconds())
    else:
        # Just bypass
        output = None
    return output


def from_unix_timestamp(val):
    return datetime.datetime.fromtimestamp(val)


class TrafficFilter(object):
    """
    "ga" to show only general aviation traffic
    "airline" to only show airline traffic
    null/empty to show all traffic.
    """
    GA = "ga"
    AIRLINE = "airline"
    ALL = None


class AirlineInsightReportType(object):
    ALTERNATE_ROUTE_POPULARITY = 1              # Alternate route popularity with fares
    PERCENTAGE_SCHEDULED_ACTUALLY_FLOWN = 2     # Percentage of scheduled flights that are actually flown
    PASSENGER_LOAD_FACTOR_ACTUALLY_FLOWN = 3    # Passenger load factor of flights that are actually flown
    CARRIERS_BY_CARGO_WEIGHT = 4                # Carriers by most cargo weight


class Client(object):
    def __init__(self, username, api_key):
        self.auth = HTTPBasicAuth(username, api_key)
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def _request(self, method, data=None):
        url = os.path.join(BASE_URL, method)
        logger.debug("POST\n%s\n%s\n", url, data)

        r = requests.post(url=url, data=data, auth=self.auth, headers=self.headers)
        result = r.json()
        final = result
        key = "{}Result".format(method)
        if key in result:
            final = result[key]
            # Test if final is a dict before iterating
            if type(final) is dict and "data" in final:
                final = final["data"]
        return final

    def aircraft_type(self, aircraft_type):
        """
        Given an aircraft type string such as GALX, AircraftType returns information about that type,  comprising the
        manufacturer  (for instance, "IAI"), type (for instance, "Gulfstream G200"), and description (like "twin-jet").

        type	string	aircraft type ID
        """
        data = {"type": aircraft_type}
        return self._request("AircraftType", data)

    def airline_flight_info(self, fa_flight_id):
        """
        AirlineFlightInfo returns additional information about a commercial airline flight, such as gate, baggage claim,
        and meal service information. This information is currently only available for some carriers and flights. To
        obtain the faFlightID, you can use a function such as GetFlightID, FlightInfoEx, or InFlightInfo.

        faFlightID	string	unique identifier assigned by FlightAware for this flight (or use "ident@departureTime")

        """
        data = {"faFlightID": fa_flight_id}
        return self._request("AirlineFlightInfo", data)

    def airline_flight_schedules(self, start_date, end_date, origin=None, destination=None, airline=None, flight_number=None, how_many=MAX_RECORD_LENGTH, offset=0):
        """
        AirlineFlightSchedules returns flight schedules that have been published by airlines. These schedules are available
        for the recent past as well as up to one year into the future.

        Flights performed by airline codeshares are also returned in these results.

        startDate	int	timestamp of earliest flight departure to return, specified in integer seconds since 1970 (UNIX epoch time)
        endDate	int	timestamp of latest flight departure to return, specified in integer seconds since 1970 (UNIX epoch time)
        origin	string	optional airport code of origin. If blank or unspecified, then flights with any origin will be returned.
        destination	string	optional airport code of destination. If blank or unspecified, then flights with any destination will be returned.
        airline	string	optional airline code of the carrier. If blank or unspecified, then flights on any airline will be returned.
        flightno	string	optional flight number. If blank or unspecified, then any flight number will be returned.
        howMany	int	maximum number of past records to obtain. Must be a positive integer value less than or equal to 15, unless SetMaximumResultSize has been called.
        offset	int	must be an integer value of the offset row count you want the search to start at. Most requests should be 0 (most recent report).
        """
        data = {
            "startDate": to_unix_timestamp(start_date),
            "endDate": to_unix_timestamp(end_date),
            "origin": origin,
            "destination": destination,
            "airline": airline,
            "flightno": flight_number,
            "howMany": how_many,
            "offset": offset,
        }
        results = self._request("AirlineFlightSchedules", data)
        for item in results:
            item["departure_time"] = from_unix_timestamp(item["departuretime"])
            item["arrival_time"] = from_unix_timestamp(item["arrivaltime"])
        return results

    def airline_info(self, airline):
        """
        AirlineInfo returns information about a commercial airline/carrier given an ICAO airline code.

        airlineCode	string	the ICAO airline ID (e.g., COA, ASA, UAL, etc.)
        """
        data = {"airlineCode": airline}
        return self._request("AirlineInfo", data)

    def airline_insight(self, origin, destination, report_type=AirlineInsightReportType.PERCENTAGE_SCHEDULED_ACTUALLY_FLOWN):
        """
        AirlineInsight returns historical booking and airfare information that has been published by airlines. Currently this
        information is only available for airports located within the United States and its territories. Information is
        historical and is aggregated from the 12 months prior to the most recently published (generally 4 to 6 months delayed).
        The returned data may involve estimated or extrapolated amounts.

        This function can return one of several types of reports, as specified by the reportType argument:

        1 = Alternate route popularity with fares
        2 = Percentage of scheduled flights that are actually flown
        3 = Passenger load factor of flights that are actually flown
        4 = Carriers by most cargo weight


        origin	string	airport code of origin
        destination	string	airport code of destination
        reportType	int	type of report to obtain (see list of values above)

        """
        data = {
            "origin": origin,
            "destination": destination,
            "reportType": report_type,
        }
        return self._request("AirlineInsight", data)

    def airport_info(self, airport):
        """
        AirportInfo returns information about an airport given an ICAO airport code such as KLAX, KSFO, KORD, KIAH, O07, etc.
        Data returned includes name (Houston Intercontinental Airport), location (typically city and state),
        latitude and longitude, and timezone (:America/Chicago).

        The returned timezone is specified in a format that is compatible with the official IANA zoneinfo database and
        can be used to convert the timestamps returned by all other functions into localtimes.
        Support for timestamp conversion using zoneinfo identifiers is available natively or through third-party libraries
        for most programming languages. In some cases, the leading colon (":") character may need to be removed
        from the timezone identifier in order for it to be recognized by some timezone libraries.

        airportCode	string	the ICAO airport ID (e.g., KLAX, KSFO, KIAH, KHOU, KJFK, KEWR, KORD, KATL, etc.)

        Sample results for BNA:
            {
                u'latitude': 36.1244722,
                u'timezone': u':America/Chicago',
                u'name': u'Nashville Intl',
                u'longitude': -86.6781944,
                u'location': u'Nashville, TN'
            }
        """
        data = {"airportCode": airport}
        return self._request("AirportInfo", data)

    def all_airlines(self):
        """
        AllAirlines returns the ICAO identifiers of all known commercial airlines/carriers.

        See AirlineInfo to retrieve additional information about any of the identifiers returned.
        """
        return self._request("AllAirlines")

    def all_airports(self):
        """
        AllAirports returns the ICAO identifiers of all known airports. For airports that do not have an ICAO identifier, the FAA LID identifier will be used.
        See AirportInfo to retrieve additional information about any of the identifiers returned.
        """
        return self._request("AllAirports")

    def block_indent_check(self, ident):
        """
        Given an aircraft identification, returns 1 if the aircraft is blocked from public tracking, 0 if it is not.
        ident	string	requested tail number
        """
        data = {"ident": ident}
        return self._request("BlockIdentCheck", data)

    def count_airport_operations(self, airport):
        """
        Given an airport, CountAirportOperations returns integer values on the number of aircraft scheduled or actually
        en route or departing from the airport. Scheduled arrival is a non-airborne flight that is scheduled to the airport in question.
        """
        data = {"airport": airport}
        return self._request("CountAirportOperations", data)

    def count_all_enroute_airline_operations(self):
        """
        CountAllEnrouteAirlineOperations returns an array of airlines and how many flights each currently has enroute.
        """
        return self._request("CountAllEnrouteAirlineOperations")

    def decode_flight_route(self, fa_flight_id):
        """
        Given a flight identifier (faFlightID) of a past, current, or future flight, DecodeFlightRoute returns a "cracked" list of noteworthy navigation points along the planned flight route. The list represents the originally planned route of travel, which may differ slightly from the actual flight path flown. The returned list will include the name, type, latitude, and longitude of each point. Additional reporting points along the route may be automatically included in the returned list. Not all flight routes can be successfully decoded by this function, particularly if the flight is not entirely within the continental U.S. airspace, since this function only has access to navaids within that area. To obtain the faFlightID, you can use a function such as GetFlightID, FlightInfoEx, or InFlightInfo.
        """
        data = {"faFlightID": fa_flight_id}
        return self._request("DecodeFlightRoute", data)

    def decode_route(self):
        raise NotImplementedError

    def arrived(self, airport, how_many=MAX_RECORD_LENGTH, filter=TrafficFilter.ALL, offset=0):
        """
        Arrived returns information about flights that have recently arrived for the specified airport and maximum number of
        flights to be returned. Flights are returned from most to least recent. Only flights that arrived within the last 24 hours are considered.

        Times returned are seconds since 1970 (UNIX epoch seconds).

        See also Departed, Enroute, and Scheduled for other airport tracking functionality.

        airport	string	the ICAO airport ID (e.g., KLAX, KSFO, KIAH, KHOU, KJFK, KEWR, KORD, KATL, etc.)
        howMany	int	determines the number of results. Must be a positive integer value less than or equal to 15, unless SetMaximumResultSize has been called.
        filter	string	can be "ga" to show only general aviation traffic, "airline" to only show airline traffic, or null/empty to show all traffic.
        offset	int	must be an integer value of the offset row count you want the search to start at. Most requests should be 0.
        """
        data = {"airport": airport, "howMany": how_many, "filter": filter, "offset": offset}
        return self._request("Arrived", data)

    def departed(self, airport, how_many=MAX_RECORD_LENGTH, filter=TrafficFilter.ALL, offset=0):
        """
        Departed returns information about already departed flights for a specified airport and maximum number of
        flights to be returned. Departed flights are returned in order from most recently to least recently departed.
        Only flights that have departed within the last 24 hours are considered.

        Times returned are seconds since 1970 (UNIX epoch seconds).

        See also Arrived, Enroute, and Scheduled for other airport tracking functionality.

        airport	string	the ICAO airport ID (e.g., KLAX, KSFO, KIAH, KHOU, KJFK, KEWR, KORD, KATL, etc.)
        howMany	int	determines the number of results. Must be a positive integer value less than or equal to 15, unless SetMaximumResultSize has been called.
        filter	string	can be "ga" to show only general aviation traffic, "airline" to only show airline traffic, or null/empty to show all traffic.
        offset	int	must be an integer value of the offset row count you want the search to start at. Most requests should be 0.
        """
        data = {"airport": airport, "howMany": how_many, "filter": filter, "offset": offset}
        return self._request("Departed", data)

    def enroute(self, airport, how_many=MAX_RECORD_LENGTH, filter=TrafficFilter.ALL, offset=0):
        """
        Enroute returns information about flights already in the air for the
        specified airport and maximum number of flights to be returned. Enroute
        flights are returned from soonest estimated arrival to least soon
        estimated arrival.

        See also Arrived, Departed, and Scheduled for other airport tracking
        functionality.


        airport string  the ICAO airport ID (e.g., KLAX, KSFO, KIAH, KHOU, KJFK, KEWR, KORD, KATL, etc.)

        howMany int determines the number of results. Must be a positive integer value less than or equal to 15, unless SetMaximumResultSize has been called.

        filter  string  can be "ga" to show only general aviation traffic, "airline" to only show airline traffic, or null/empty to show all traffic.

        offset  int must be an integer value of the offset row count you want the search to start at. Most requests should be 0.
        """
        data = {"airport": airport, "howMany": how_many, "filter": filter, "offset": offset}
        return self._request("Enroute", data)

    def fleet_arrived(self):
        raise NotImplementedError

    def fleet_scheduled(self):
        raise NotImplementedError

    def flight_info(self, ident, how_many=MAX_RECORD_LENGTH):
        """
        FlightInfo returns information about flights for a specific tail number (e.g., N12345), or ICAO airline code with flight number (e.g., SWA2558).

        The howMany argument specifies the maximum number of flights to be returned. Flight information will be returned from newest to oldest.
        The oldest flights searched by this function are about 2 weeks in the past.

        When specifying an airline with flight number, wither an ICAO or IATA code may be used to designate the airline, however andCodeshares and alternate idents are automatically searched.

        Times are in integer seconds since 1970 (UNIX epoch time), except for estimated time enroute, which is in hours and minutes.

        See FlightInfoEx for a more advanced interface.

        ident	string	requested tail number, or airline with flight number
        howMany	int	maximum number of past flights to obtain. Must be a positive integer value less than or equal to 15, unless SetMaximumResultSize has been called.
        """
        raise NotImplementedError

    def flight_info_ex(self):
        """
        FlightInfoEx returns information about flights for a specific tail number (e.g., N12345), or an ident (typically an ICAO airline with flight number, e.g., SWA2558),
        or a FlightAware-assigned unique flight identifier (e.g. faFlightID returned by another FlightXML function).

        The howMany argument specifies the maximum number of flights to be returned. When a tail number or ident is specified and multiple flights
        are available, the results will be returned from newest to oldest. The oldest flights searched by this function are about 2 weeks in the past.
        Codeshares and alternate idents are automatically searched. When a FlightAware-assigned unique flight identifier is supplied, at most a single result will be returned.

        Times are in integer seconds since 1970 (UNIX epoch time), except for estimated time enroute, which is in hours and minutes.

        See FlightInfo for a simpler interface.
        """
        raise NotImplementedError

    def get_flight_id(self, ident, departure_datetime):
        """
        GetFlightID looks up the "faFlightID" for a given ident and departure time. This value is a unique identifier assigned by
        FlightAware as a way to permanently identify a flight. The specified departure time must exactly match either the actual
        or scheduled departure time of the flight. The departureTime is specified as integer seconds since 1970 (UNIX epoch time).

        If more than one flight corresponds to the specified ident and departure time, then only the first matching faFlightID
        is returned. Codeshares and alternate idents are automatically searched.


        ident	string	requested tail number
        departureTime	int	time and date of the desired flight, UNIX epoch seconds since 1970
        """
        data = {
            "ident": ident,
            "departureTime": to_unix_timestamp(departure_datetime),
        }
        return self._request("GetFlightID", data)


    def get_historical_track(self):
        raise NotImplementedError

    def get_last_track(self, ident):
        """
        GetLastTrack looks up a flight's track log by specific tail number (e.g., N12345) or ICAO airline and flight number (e.g., SWA2558). It returns the track log from the current IFR flight or, if the aircraft is not airborne, the most recent IFR flight. It returns an array of positions, with each including the timestamp, longitude, latitude, groundspeed, altitude, altitudestatus, updatetype, and altitudechange. Altitude is in hundreds of feet or Flight Level where appropriate, see our FAQ about flight levels. Also included altitude status, update type, and altitude change.
        Altitude status is 'C' when the flight is more than 200 feet away from its ATC-assigned altitude. (For example, the aircraft is transitioning to its assigned altitude.) Altitude change is 'C' if the aircraft is climbing (compared to the previous position reported), 'D' for descending, and empty if it is level. This happens for VFR flights with flight following, among other things. Timestamp is integer seconds since 1970 (UNIX epoch time).
        This function only returns tracks for recent flights within approximately the last 24 hours. Use the GetHistoricalTrack function to look up a specific past flight rather than just the most recent one. Codeshares and alternate idents are automatically searched.
        """
        data = {"ident": ident}
        return self._request("GetLastTrack", data)

    def inbound_flight_info(self):
        raise NotImplementedError

    def in_flight_info(self, ident):
        """
        InFlightInfo looks up a specific tail number (e.g., N12345) or ICAO airline and flight number (e.g., SWA2558) and returns current position/direction/speed information. It is only useful for currently airborne flights within approximately the last 24 hours. Codeshares and alternate idents are automatically searched.
        """
        data = {"ident": ident}
        return self._request("InFlightInfo", data)

    def lat_lng_to_distance(self):
        raise NotImplementedError

    def lat_lng_to_heading(self):
        raise NotImplementedError

    def map_flight(self):
        raise NotImplementedError

    def map_flight_ex(self):
        raise NotImplementedError

    def metar(self, airport):
        """
        Given an airport, return the current raw METAR weather info. If no reports are available at the requested airport
        but are for a nearby airport, then the report from that airport may be returned instead.

        Use the MetarEx function for more functionality, including access to historical weather and parsed.
        airport	string	the ICAO airport ID (e.g., KLAX, KSFO, KIAH, KHOU, KJFK, KEWR, KORD, KATL, etc.)
        """
        data = {"airport": airport}
        return self._request("Metar", data)

    def metar_ex(self, airport):
        """
        Given an airport, return the METAR weather info as parsed, human-readable, and raw formats. If no reports are available
        at the requested airport but are for a nearby airport, then the reports from that airport may be returned instead.
        If a value greater than 1 is specified for howMany then multiple past reports will be returned, in order of increasing
        age. Historical data is generally only available for the last 7 days.

        Use the Metar function for a simpler interface to access just the most recent raw report.
        airport	string	the ICAO airport ID (e.g., KLAX, KSFO, KIAH, KHOU, KJFK, KEWR, KORD, KATL, etc.)
        """
        data = {"airport": airport}
        return self._request("MetarEx", data)

    def ntaf(self, airport):
        """
        Given an airport, return the terminal area forecast, if available.
        See Taf for a simpler interface.
        airport	string	the ICAO airport ID (e.g., KLAX, KSFO, KIAH, KHOU, KJFK, KEWR, KORD, KATL, etc.)
        """
        data = {"airport": airport}
        return self._request("NTaf", data)

    def taf(self, airport):
        """
        Given an airport, return the terminal area forecast, if available.
        See NTaf for a more advanced interface.
        airport	string	the ICAO airport ID (e.g., KLAX, KSFO, KIAH, KHOU, KJFK, KEWR, KORD, KATL, etc.)
        """
        data = {"airport": airport}
        return self._request("NTaf", data)

    def routes_between_airports(self, origin, destination):
        """
        RoutesBetweenAirports returns information about assigned IFR routings between two airports. For each known routing, the route, number of times that route has been assigned, and the filed altitude (measured in hundreds of feet or Flight Level) are returned. Only flights that departed within the last 6 hours and flight plans filed within the last 3 days are considered.
        """
        data = {"origin": origin, "destination": destination}
        return self._request("RoutesBetweenAirports", data)

    def routes_between_airports_ex(self):
        raise NotImplementedError

    def scheduled(self, airport, how_many=MAX_RECORD_LENGTH, filter=TrafficFilter.ALL, offset=0):
        """
        Scheduled returns information about scheduled flights (technically,
        filed IFR flights) for a specified airport and a maximum number of
        flights to be returned. Scheduled flights are returned from soonest to
        furthest in the future to depart. Only flights that have not actually
        departed, and have a scheduled departure time between 2 hours in the
        past and 24 hours in the future, are considered.

        Times returned are seconds since 1970 (UNIX epoch time).

        See also Arrived, Departed, and Enroute for other airport tracking
        functionality.


        airport string  the ICAO airport ID (e.g., KLAX, KSFO, KIAH, KHOU, KJFK, KEWR, KORD, KATL, etc.)

        howMany int determines the number of results. Must be a positive integer value less than or equal to 15, unless SetMaximumResultSize has been called.

        filter  string  can be "ga" to show only general aviation traffic, "airline" to only show airline traffic, or null/empty to show all traffic.

        offset  int must be an integer value of the offset row count you want the search to start at. Most requests should be 0.
        """
        data = {"airport": airport, "howMany": how_many, "filter": filter, "offset": offset}
        return self._request("Scheduled", data)

    def search(self, parameters={}, how_many=MAX_RECORD_LENGTH, offset=0):
        """
        Search performs a query for data on all airborne aircraft to find ones
        matching the search query. Query parameters include a
        latitude/longitude box, aircraft ident with wildcards, type with
        wildcards, prefix, suffix, origin airport, destination airport, origin
        or destination airport, groundspeed, and altitude. It takes search
        terms in a single string comprising "-key value" pairs and returns an
        array of flight structures. Codeshares and alternate idents are NOT
        searched when using the -idents clause.

        Keys include:

        -prefix STRING
        -type STRING
        -suffix STRING
        -idents STRING
        -destination STRING
        -origin STRING
        -originOrDestination STRING
        -aboveAltitude INTEGER
        -belowAltitude INTEGER
        -aboveGroundspeed INTEGER
        -belowGroundspeed INTEGER
        -latlong "MINLAT MINLON MAXLAT MAXLON"
        -filter {ga|airline}
        -inAir {0|1}

        To search for all aircraft below ten-thousand feet with a groundspeed
        over 200 kts:

        -belowAltitude 100 -aboveGroundspeed 200
        To search for all in-air Boeing 777s:

        -type B77*
        To search for all aircraft heading to Los Angeles International Airport
        (LAX) that are "heavy" aircraft:

        -destination LAX -prefix H
        To search for all United Airlines flights in Boeing 737s

        -idents UAL* -type B73*
        See the SearchBirdseyeInFlight function for additional functionality.


        query   string  search expression

        howMany int maximum number of flights to obtain. Must be a positive
        integer value less than or equal to 15, unless SetMaximumResultSize has
        been called.

        offset  int must be an integer value of the offset row count you want
        the search to start at. Most requests should be 0.
        """
        query = ""
        for key, value in parameters.items():
            query += "-%s %s " % (key, value)
        data = {"query": query, "howMany": how_many, "offset": offset}
        return self._request("Search", data)

    def search_birdseye_in_flight(self):
        raise NotImplementedError

    def search_birdseye_positions(self):
        raise NotImplementedError

    def search_count(self):
        raise NotImplementedError

    def set_maximum_result_sizes(self):
        raise NotImplementedError

    def tail_owner(self, ident):
        """
        TailOwner returns information about an the owner of an aircraft, given a flight number or N-number. Data returned
        includes owner's name, location (typically city and state), and website, if any. Codeshares and alternate idents are automatically searched.

        ident	string	requested tail number
        """
        data = {"ident": ident}
        return self._request("TailOwner", data)

    def zipcode_info(self, zipcode):
        """
        ZipcodeInfo returns information about a five-digit zipcode. Of particular importance is latitude and longitude.

        zipcode	string	a five-digit U.S. Postal Service zipcode.
        """
        data = {"zipcode": zipcode}
        return self._request("ZipcodeInfo", data)

    def get_alerts(self):
        """
        GetAlerts retrieves all of the FlightXML flight alerts that are
        currently scheduled for the user.

        The other methods SetAlert, DeleteAlert, and RegisterAlertEndpoint can
        be used to manage FlightXML flight alerts.

        Note: If other alerts have been defined by the user on the FlightAware
        website or mobile app, they will also be included in the returned
        listing.

        Inputs

        No inputs.
        Returns

        Type    Description
        FlightAlertListing  all defined alerts by the user
        """
        return self._request("GetAlerts", {})

    def delete_alert(self, alert_id=None):
        """
        DeleteAlert deletes a FlightXML flight alert.

        The other methods SetAlert, GetAlerts, and RegisterAlertEndpoint can be
        used to manage FlightXML flight alerts.

        Inputs

        Name        Type    Description
        alert_id    int     alert_id to delete

        Returns

        Type    Description
        int     returns 1 on success
        """
        if alert_id is not None:
            data = {"alert_id": alert_id}
            return self._request("DeleteAlert", data)

    def set_alert(self, alert_id=0, ident=None, origin=None, destination=None,
        aircrafttype=None, date_start=None, date_end=None, channels=[],
        enabled=True, max_weekly=1000):
        """
        SetAlert creates or updates a FlightXML flight alert. When the alert is
        triggered, a callback mechanism will be used to notify the address
        specified by RegisterAlertEndpoint. Each alert that is triggered is
        charged at the rate of one "class 2" FlightXML query.

        If the "alert_id" argument is specified, then an existing alert is
        updated to the new values specified, otherwise a 0 or blank alert_id
        will cause a new alert to be created.

        As a special case, if "alert_id" is specified as -1 and "ident" is not
        blank, update the most recently modified alert for the same "ident" to
        the arguments specified. If no existing alert for that "ident" exists,
        create it.

        For a single day alert, specify date_start and date_end with the same
        value. For a recurring alert, specify both date_start as 0 and date_end
        as 0.

        The "channel" argument is a Tcl-style string list that specifies the
        target channel ID and the triggering event types. At this time, the
        channel ID should always be specified as 16. Supported event types are:
        e_filed e_departure e_arrival e_diverted e_cancelled. For example this
        specifies a FlightXML Push channel with several flight statuses:
        "{16 e_filed e_departure e_arrival e_diverted e_cancelled}"

        The "max_weekly" argument is used to prevent the an alert from being
        created that might generate more alerts than desired. This check is
        only done at alert creation time based on historical trends for the
        filter selection, and is not an enforcement of alerts actually
        delivered.

        Returns a non-zero number (the alert_id that was added or updated) on
        success, otherwise an exception is raised. An error string beginning
        with "OVERLIMIT" means the user has exceeded the maximum number of
        enabled alerts permitted by their account type; consider disabling or
        deleting some alerts, or request an account upgrade. An error string
        beginning with "FLOODWARN" means that the new alert was rejected
        because it was predicted to exceed the number of alerts specified by
        the "max_weekly" argument.

        Inputs

        Name        Type    Description
        alert_id    int     alert_id of an existing alert to update.
                            specify 0 or "" to create a new alert.
                            specify -1 to upsert an alert.
                            otherwise an existing alert id.
        ident       string  optional ident or faFlightID of flight
        origin      string  optional origin airport code
        destination string  optional destination airport code
        aircrafttype    string  optional aircraft type
        date_start  int     optional starting date of alert (in epoch seconds,
                            will be rounded to whole day)
        date_end    int     optional ending date of alert (in epoch seconds,
                            will be rounded to whole day)
        channels    string  list of channels and event types (see description
                            for syntax)
        enabled     boolean whether the alert should be enabled or disabled (if
                            missing, default is true)
        max_weekly  int     reject the new alert if the estimated number of
                            alerts per week exceeds this amount (recommended
                            default 1000)

        Returns

        Type    Description
        int returns non-zero on success
        """
        data = {
            "alert_id": alert_id,
            "enabled": enabled,
            "max_weekly": max_weekly
        }
        if ident is not None:
            data["ident"] = ident
        if origin is not None:
            data["origin"] = origin
        if destination is not None:
            data["destination"] = destination
        if aircrafttype is not None:
            data["aircrafttype"] = aircrafttype
        if date_start is not None:
            data["date_start"] = date_start
        if date_end is not None:
            data["date_end"] = date_end
        if len(channels) > 0:
            data["channels"] = channels
        if enabled is not None:
            data["enabled"] = enabled

        return self._request("SetAlert", data)

    def register_alert_endpoint(self, address, format_type="json/post"):
        """
        RegisterAlertEndpoint specifies where pushed FlightXML flight alerts.
        Calling this method a second time will overwrite any previously
        registered endpoint.

        The other methods SetAlert, GetAlerts, and DeleteAlert can be used to
        manage FlightXML flight alerts.

        The "format_type" argument controls how the flight alert is delivered
        to the specified address. Currently "format_type" must always be
        "json/post", although other formats may be introduced in the future.
        When an alert occurs, FlightAware servers will deliver an HTTP POST to
        the specified address with the body containing a JSON-encoded message
        about the alert and flight.

        Returns 1 on success, otherwise an error record is returned.

        Inputs

        Name    Type    Description
        address string  URL of endpoint
        format_type string  Must be "json/post"
        Returns

        Type    Description
        int     returns 1 on success
        """
        data = {"address": address, "format_type": format_type}
        return self._request("RegisterAlertEndpoint", data)
