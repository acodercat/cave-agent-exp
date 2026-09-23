from typing import List, Dict, Any, Union, Tuple, Set 
def history_api_get_president_by_year(year:int, full_term_only:bool=False) -> str:
	"""
	history_api_get_president_by_year : Get the name of the U.S. President for a specified year.    
	Parameters:
	year (int): The year you want to know the U.S. president of.
	full_term_only (bool): Flag to determine if we should only return presidents that served a full term for the specified year.

	Required Parameter = [year,]

	"""
	return 'Success'

tools = [history_api_get_president_by_year]
