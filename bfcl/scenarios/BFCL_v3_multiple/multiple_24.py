from typing import List, Dict, Any, Union, Tuple, Set 
def route_planner_calculate_route(start:str, destination:str, method:str='fastest') -> str:
	"""
	route_planner_calculate_route : Determines the best route between two points.    
	Parameters:
	start (str): The starting point of the journey.
	destination (str): The destination of the journey.
	method (str): The method to use when calculating the route (default is 'fastest').

	Required Parameter = [start,destination,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def chess_club_details_find(name:str, city:str, event:str='null') -> str:
	"""
	chess_club_details_find : Provides details about a chess club, including location.    
	Parameters:
	name (str): The name of the chess club.
	city (str): The city in which the chess club is located.
	event (str): The event hosted by the club.

	Required Parameter = [name,city,]

	"""
	return 'Success'

tools = [route_planner_calculate_route, chess_club_details_find]
