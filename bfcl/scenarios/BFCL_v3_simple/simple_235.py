from typing import List, Dict, Any, Union, Tuple, Set 
def get_event_date(event:str, location:str=None) -> str:
	"""
	get_event_date : Retrieve the date of a historical event.    
	Parameters:
	event (str): The name of the historical event.
	location (str): Location where the event took place. Default to global if not specified.

	Required Parameter = [event,]

	"""
	return 'Success'

tools = [get_event_date]
