from typing import List, Dict, Any, Union, Tuple, Set 
def us_history_events_by_presidency(president_name:str, start_year:int=0, end_year:int=2000) -> str:
	"""
	us_history_events_by_presidency : Retrieve the major events during the presidency of a specified US president.    
	Parameters:
	president_name (str): The name of the US president.
	start_year (int): The start year of their presidency (optional).
	end_year (int): The end year of their presidency (optional).

	Required Parameter = [president_name,]

	"""
	return 'Success'

tools = [us_history_events_by_presidency]
