from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_bmi(weight:int, height:int, unit:str=None) -> str:
	"""
	calculate_bmi : Calculate the Body Mass Index (BMI) of a person.    
	Parameters:
	weight (int): Weight of the person in kilograms.
	height (int): Height of the person in centimeters.
	unit (str): Optional parameter to choose between 'imperial' and 'metric' systems. Default is 'metric'.

	Required Parameter = [weight,height,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def celebrity_net_worth_get(name:str, currency:str) -> str:
	"""
	celebrity_net_worth_get : Get the total net worth of a sports celebrity based on most recent data.    
	Parameters:
	name (str): The full name of the sports celebrity.
	currency (str): The currency in which the net worth will be returned. Default is 'USD'.

	Required Parameter = [name,currency,]

	"""
	return 'Success'

tools = [calculate_bmi, celebrity_net_worth_get]
