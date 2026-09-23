from typing import List, Dict, Any, Union, Tuple, Set 
def geology_get_era(era_name:str, calculate_years_ago:bool=None) -> str:
	"""
	geology_get_era : Get the estimated date of a geological era.    
	Parameters:
	era_name (str): The name of the geological era. e.g Ice age
	calculate_years_ago (bool): True if years ago is to be calculated. False by default

	Required Parameter = [era_name,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def history_get_event_date(event_name:str, calculate_years_ago:bool=None) -> str:
	"""
	history_get_event_date : Get the date of an historical event.    
	Parameters:
	event_name (str): The name of the event.
	calculate_years_ago (bool): True if years ago is to be calculated. False by default

	Required Parameter = [event_name,]

	"""
	return 'Success'

tools = [geology_get_era, history_get_event_date]
