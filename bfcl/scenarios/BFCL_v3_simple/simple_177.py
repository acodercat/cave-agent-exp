from typing import List, Dict, Any, Union, Tuple, Set 
def get_lawsuit_cases(company_name:str, year:int, status:str=None) -> str:
	"""
	get_lawsuit_cases : Retrieve all lawsuit cases related to a specific company during a particular year.    
	Parameters:
	company_name (str): The name of the company.
	year (int): The specific year to search for lawsuit cases.
	status (str): The status of the lawsuit cases to retrieve. If not specified, defaults to 'all'.

	Required Parameter = [company_name,year,]

	"""
	return 'Success'

tools = [get_lawsuit_cases]
