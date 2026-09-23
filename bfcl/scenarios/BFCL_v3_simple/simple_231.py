from typing import List, Dict, Any, Union, Tuple, Set 
def history_get_key_events(country:str, start_year:int, end_year:int, event_type:List[str]=None) -> str:
	"""
	history_get_key_events : Retrieve key historical events within a specific period for a certain country.    
	Parameters:
	country (str): The name of the country for which history is queried.
	start_year (int): Start year of the period for which history is queried.
	end_year (int): End year of the period for which history is queried.
	event_type (List[str]): Types of event. Default to 'all', which all types will be considered.

	Required Parameter = [country,start_year,end_year,]

	"""
	return 'Success'

tools = [history_get_key_events]
