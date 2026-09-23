from typing import List, Dict, Any, Union, Tuple, Set 
def hotel_find(location:str, stars:int, amenities:List[str]=None) -> str:
	"""
	hotel_find : Search for hotels given the location, minimum stars and specific amenities.    
	Parameters:
	location (str): The city where you want to find the hotel
	stars (int): Minimum number of stars the hotel should have. Default 1
	amenities (List[str]): List of preferred amenities in hotel. Default to empty array

	Required Parameter = [location,stars,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def flight_search(origin:str, destination:str, date:Any=None, passengers:int=1) -> str:
	"""
	flight_search : Search for flights given the origin, destination, date, and number of passengers.    
	Parameters:
	origin (str): The origin of the flight
	destination (str): The destination of the flight
	date (Any): The date of the flight. Default ''
	passengers (int): The number of passengers

	Required Parameter = [origin,destination,]

	"""
	return 'Success'

tools = [hotel_find, flight_search]
