from typing import List, Dict, Any, Union, Tuple, Set 
def flight_book(departure_location:str, destination_location:str, date:str, time:str=None, direct_flight:bool=None) -> str:
	"""
	flight_book : Book a direct flight for a specific date and time from departure location to destination location.    
	Parameters:
	departure_location (str): The location you are departing from.
	destination_location (str): The location you are flying to.
	date (str): The date of the flight. Accepts standard date format e.g., 2022-04-28.
	time (str): Preferred time of flight. Default is 'morning'.
	direct_flight (bool): If set to true, only direct flights will be searched. Default is false.

	Required Parameter = [departure_location,destination_location,date,]

	"""
	return 'Success'

tools = [flight_book]
