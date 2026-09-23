from typing import List, Dict, Any, Union, Tuple, Set 
def event_finder_find_upcoming(location:str, genre:str, days_ahead:int=7) -> str:
	"""
	event_finder_find_upcoming : Find upcoming events of a specific genre in a given location.    
	Parameters:
	location (str): The city and state where the search will take place, e.g. New York, NY.
	genre (str): The genre of events.
	days_ahead (int): The number of days from now to include in the search.

	Required Parameter = [location,genre,]

	"""
	return 'Success'

tools = [event_finder_find_upcoming]
