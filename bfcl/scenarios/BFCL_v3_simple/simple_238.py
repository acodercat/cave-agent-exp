from typing import List, Dict, Any, Union, Tuple, Set 
def us_history_get_president(event:str, year:int) -> str:
	"""
	us_history_get_president : Retrieve the U.S. president during a specific event in American history.    
	Parameters:
	event (str): The event in U.S. history.
	year (int): The specific year of the event.

	Required Parameter = [event,year,]

	"""
	return 'Success'

tools = [us_history_get_president]
