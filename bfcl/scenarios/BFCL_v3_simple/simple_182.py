from typing import List, Dict, Any, Union, Tuple, Set 
def lawsuit_info(case_number:str, year:int=2023, location:str=None) -> str:
	"""
	lawsuit_info : Retrieves details of a lawsuit given a case number    
	Parameters:
	case_number (str): The unique identifier of the lawsuit case
	year (int): The year in which the lawsuit case was initiated. Default is 2023 if not specified.
	location (str): The location or court jurisdiction where the case was filed. Default is 'all'.

	Required Parameter = [case_number,]

	"""
	return 'Success'

tools = [lawsuit_info]
