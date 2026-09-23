from typing import List, Dict, Any, Union, Tuple, Set 
def us_history_get_event_info(event_name:str, specific_info:str) -> str:
	"""
	us_history_get_event_info : Retrieve detailed information about a significant event in U.S. history.    
	Parameters:
	event_name (str): The name of the event.
	specific_info (str): Specific aspect of information related to event.

	Required Parameter = [event_name,specific_info,]

	"""
	return 'Success'

tools = [us_history_get_event_info]
