from typing import List, Dict, Any, Union, Tuple, Set 
def museum_info(museum:str, date:str, information:List[str]='all') -> str:
	"""
	museum_info : Get information about a museum including its opening hours and ticket prices for a specific date range.    
	Parameters:
	museum (str): The name of the museum.
	date (str): The specific date for which information is needed, in the format of YYYY-MM-DD such as '2022-12-01'.
	information (List[str]): The type of information needed from the museum. This is optional and defaults to 'all' if not specified.

	Required Parameter = [museum,date,]

	"""
	return 'Success'

tools = [museum_info]
