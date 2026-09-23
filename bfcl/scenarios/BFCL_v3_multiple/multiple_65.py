from typing import List, Dict, Any, Union, Tuple, Set 
def timezones_get_difference(city1:str, city2:str) -> str:
	"""
	timezones_get_difference : Find the time difference between two cities.    
	Parameters:
	city1 (str): The first city.
	city2 (str): The second city.

	Required Parameter = [city1,city2,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def geodistance_find(origin:str, destination:str, unit:str='miles') -> str:
	"""
	geodistance_find : Find the distance between two cities on the globe.    
	Parameters:
	origin (str): The originating city for the distance calculation.
	destination (str): The destination city for the distance calculation.
	unit (str): The unit of measure for the distance calculation.

	Required Parameter = [origin,destination,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def flights_search(from_city:str, to_city:str, date:str='next monday') -> str:
	"""
	flights_search : Find flights between two cities.    
	Parameters:
	from_city (str): The city to depart from.
	to_city (str): The city to arrive at.
	date (str): The date to fly.

	Required Parameter = [from_city,to_city,]

	"""
	return 'Success'

tools = [timezones_get_difference, geodistance_find, flights_search]
