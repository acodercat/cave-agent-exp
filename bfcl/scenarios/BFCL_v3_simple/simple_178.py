from typing import List, Dict, Any, Union, Tuple, Set 
def get_lawsuit_details(case_number:str, court_location:str, additional_details:List[str]=None) -> str:
	"""
	get_lawsuit_details : Retrieve the detailed information about a lawsuit based on its case number and the court location.    
	Parameters:
	case_number (str): The case number of the lawsuit.
	court_location (str): The location of the court where the case is filed.
	additional_details (List[str]): Optional. Array containing additional details to be fetched. Default is all.

	Required Parameter = [case_number,court_location,]

	"""
	return 'Success'

tools = [get_lawsuit_details]
