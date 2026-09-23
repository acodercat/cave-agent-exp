from typing import List, Dict, Any, Union, Tuple, Set 
def law_civil_get_case_details(case_title:str, include_dissent:bool) -> str:
	"""
	law_civil_get_case_details : Retrieve the details of a Supreme Court case given its title.    
	Parameters:
	case_title (str): Title of the Supreme Court case.
	include_dissent (bool): If true, the output will include details of the dissenting opinion.

	Required Parameter = [case_title,include_dissent,]

	"""
	return 'Success'

tools = [law_civil_get_case_details]
