from typing import List, Dict, Any, Union, Tuple, Set 
def history_get_key_events(country:str, start_year:int, end_year:int, event_type:List[str]=None) -> str:
	"""
	history_get_key_events : Retrieve key historical events within a specific period for a certain country.    
	Parameters:
	country (str): The name of the country for which history is queried.
	start_year (int): Start year of the period for which history is queried.
	end_year (int): End year of the period for which history is queried.
	event_type (List[str]): Types of event. If none is provided, all types will be considered. Default is ['all'].

	Required Parameter = [country,start_year,end_year,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_sculpture_value(sculpture:str, artist:str, year:int=None) -> str:
	"""
	get_sculpture_value : Retrieve the current market value of a particular sculpture by a specific artist.    
	Parameters:
	sculpture (str): The name of the sculpture.
	artist (str): The name of the artist who created the sculpture.
	year (int): The year the sculpture was created. This is optional and is not required for all sculptures. Default is the 2024.

	Required Parameter = [sculpture,artist,]

	"""
	return 'Success'

tools = [history_get_key_events, get_sculpture_value]
