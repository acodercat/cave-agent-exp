from typing import List, Dict, Any, Union, Tuple, Set 
def lawsuit_details_find(company_name:str, year:int, case_type:str=None) -> str:
	"""
	lawsuit_details_find : Find details of lawsuits involving a specific company from a given year.    
	Parameters:
	company_name (str): Name of the company.
	year (int): Year of the lawsuit.
	case_type (str): Type of the lawsuit, e.g., 'IPR', 'Patent', 'Commercial', etc. Default is 'all'.

	Required Parameter = [company_name,year,]

	"""
	return 'Success'

tools = [lawsuit_details_find]
