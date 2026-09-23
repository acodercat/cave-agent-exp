from typing import List, Dict, Any, Union, Tuple, Set 
def get_discoverer(discovery:str, detail:bool) -> str:
	"""
	get_discoverer : Get the person or team who made a particular scientific discovery    
	Parameters:
	discovery (str): The discovery for which the discoverer's information is needed.
	detail (bool): Optional flag to get additional details about the discoverer, such as birth date and nationality. Defaults to false.

	Required Parameter = [discovery,detail,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def museum_working_hours_get(museum:str, location:str, day:str=None) -> str:
	"""
	museum_working_hours_get : Get the working hours of a museum in a specific location.    
	Parameters:
	museum (str): The name of the museum.
	location (str): The location of the museum.
	day (str): Specific day of the week. Optional parameter. Default is 'Monday'.

	Required Parameter = [museum,location,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def diabetes_prediction(weight:int, height:int, activity_level:str) -> str:
	"""
	diabetes_prediction : Predict the likelihood of diabetes type 2 based on a person's weight and height.    
	Parameters:
	weight (int): Weight of the person in lbs.
	height (int): Height of the person in inches.
	activity_level (str): Physical activity level of the person.

	Required Parameter = [weight,height,activity_level,]

	"""
	return 'Success'

tools = [get_discoverer, museum_working_hours_get, diabetes_prediction]
