from typing import List, Dict, Any, Union, Tuple, Set 
def get_case_info(docket:str, court:str, info_type:str) -> str:
	"""
	get_case_info : Retrieve case details using a specific case docket number and court location.    
	Parameters:
	docket (str): Docket number for the specific court case.
	court (str): Court in which the case was heard.
	info_type (str): Specify the information type needed for the case. i.e., victim, accused, verdict etc.

	Required Parameter = [docket,court,info_type,]

	"""
	return 'Success'

tools = [get_case_info]
