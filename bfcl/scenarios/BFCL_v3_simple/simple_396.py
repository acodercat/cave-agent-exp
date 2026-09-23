from typing import List, Dict, Any, Union, Tuple, Set 
def hospital_locate(location:str, radius:int, department:str=None) -> str:
	"""
	hospital_locate : Locate nearby hospitals based on location and radius. Options to include specific departments are available.    
	Parameters:
	location (str): The city and state, e.g. Denver, CO
	radius (int): The radius within which you want to find the hospital in kms.
	department (str): Specific department within the hospital. Default is 'General Medicine'.

	Required Parameter = [location,radius,]

	"""
	return 'Success'

tools = [hospital_locate]
