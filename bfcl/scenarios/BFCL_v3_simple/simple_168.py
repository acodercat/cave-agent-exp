from typing import List, Dict, Any, Union, Tuple, Set 
def lawsuit_search(company:str, start_date:str, location:str, status:str=None) -> str:
	"""
	lawsuit_search : Search for lawsuits related to a specific company within a specific date range and location.    
	Parameters:
	company (str): The company related to the lawsuit.
	start_date (str): Start of the date range for when the lawsuit was filed in the format of MM-DD-YYY.
	location (str): Location where the lawsuit was filed in the format of full state name.
	status (str): The status of the lawsuit. Default is 'ongoing'.

	Required Parameter = [company,start_date,location,]

	"""
	return 'Success'

tools = [lawsuit_search]
