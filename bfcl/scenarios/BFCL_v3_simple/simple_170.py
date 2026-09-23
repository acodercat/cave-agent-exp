from typing import List, Dict, Any, Union, Tuple, Set 
def law_case_search_find_historical(subject:str, from_year:int, to_year:int) -> str:
	"""
	law_case_search_find_historical : Search for a historical law case based on specific criteria like the subject and year.    
	Parameters:
	subject (str): The subject matter of the case, e.g., 'fraud'
	from_year (int): The start year for the range of the case. The case should happen after this year.
	to_year (int): The end year for the range of the case. The case should happen before this year.

	Required Parameter = [subject,from_year,to_year,]

	"""
	return 'Success'

tools = [law_case_search_find_historical]
