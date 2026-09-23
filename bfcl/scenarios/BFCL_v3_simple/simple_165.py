from typing import List, Dict, Any, Union, Tuple, Set 
def civil_cases_retrieve(year:int, crime_type:str, location:str) -> str:
	"""
	civil_cases_retrieve : Retrieve civil cases based on given parameters, including year, crime type, and location.    
	Parameters:
	year (int): Year of the cases
	crime_type (str): Type of the crime.
	location (str): Location of the case in the format of city name.

	Required Parameter = [year,crime_type,location,]

	"""
	return 'Success'

tools = [civil_cases_retrieve]
