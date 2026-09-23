from typing import List, Dict, Any, Union, Tuple, Set 
def fetch_law_case_details(case_number:int, court:str, year:int) -> str:
	"""
	fetch_law_case_details : Fetch details of a specific law case based on case number, year and court.    
	Parameters:
	case_number (int): The specific number of the law case.
	court (str): The city name where the court takes place
	year (int): The year in which the law case took place.

	Required Parameter = [case_number,court,year,]

	"""
	return 'Success'

tools = [fetch_law_case_details]
