from typing import List, Dict, Any, Union, Tuple, Set 
def lawsuits_search(company_name:str, location:str, year:int, case_type:str=None) -> str:
	"""
	lawsuits_search : Search for lawsuits against a specific company within a specific time and location.    
	Parameters:
	company_name (str): The name of the company.
	location (str): The location where the lawsuit was filed.
	year (int): The year when the lawsuit was filed.
	case_type (str): The type of the case. Options include: 'civil', 'criminal', 'small_claims', etc. Default is 'all'.

	Required Parameter = [company_name,location,year,]

	"""
	return 'Success'

tools = [lawsuits_search]
