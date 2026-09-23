from typing import List, Dict, Any, Union, Tuple, Set 
def events_find_event(location:str, group_size:int, event_type:List[str]=None) -> str:
	"""
	events_find_event : Find events suitable for groups based on specified criteria such as location and event type.    
	Parameters:
	location (str): The city and state, e.g. Seattle, WA
	event_type (List[str]): Type of event. Default empty array
	group_size (int): Size of the group that the event should accommodate.

	Required Parameter = [location,group_size,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def restaurant_find_group(location:str, group_size:int, cuisine:List[str]=None) -> str:
	"""
	restaurant_find_group : Find restaurants suitable for groups based on specified criteria such as location and cuisine.    
	Parameters:
	location (str): The city and state, e.g. Seattle, WA
	cuisine (List[str]): Preferred cuisine at the restaurant. Default empty array
	group_size (int): Size of the group that the restaurant should accommodate.

	Required Parameter = [location,group_size,]

	"""
	return 'Success'

tools = [events_find_event, restaurant_find_group]
