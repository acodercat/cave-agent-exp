from typing import List, Dict, Any, Union, Tuple, Set 
def court_case_find(location:str, case_number:List[str], case_type:str='Civil') -> str:
	"""
	court_case_find : Locate details of court cases based on specific parameters like case number and case type.    
	Parameters:
	location (str): The city and court where the lawsuit is filed.
	case_number (List[str]): The unique case numbers of the lawsuits.
	case_type (str): Type of the court case.

	Required Parameter = [location,case_number,]

	"""
	return 'Success'

tools = [court_case_find]
