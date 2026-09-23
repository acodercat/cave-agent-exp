from typing import List, Dict, Any, Union, Tuple, Set 
def crime_record_get_record(case_number:str, county:str, details:bool=None) -> str:
	"""
	crime_record_get_record : Retrieve detailed felony crime records using a specific case number and location.    
	Parameters:
	case_number (str): The case number related to the crime.
	county (str): The county in which the crime occurred.
	details (bool): To get a detailed report, set as true. Defaults to false.

	Required Parameter = [case_number,county,]

	"""
	return 'Success'

tools = [crime_record_get_record]
