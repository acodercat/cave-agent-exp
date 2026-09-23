from typing import List, Dict, Any, Union, Tuple, Set 
def math_gcd(num1:int, num2:int) -> str:
	"""
	math_gcd : Calculate the greatest common divisor of two integers.    
	Parameters:
	num1 (int): First number.
	num2 (int): Second number.

	Required Parameter = [num1,num2,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_top_cases(field_of_law:str, top_number:int, country:str=None) -> str:
	"""
	get_top_cases : Retrieve a list of the most influential or landmark cases in a specific field of law.    
	Parameters:
	field_of_law (str): The specific field of law e.g., constitutional law, criminal law, etc.
	top_number (int): The number of top cases to retrieve.
	country (str): The country where the law cases should be retrieved from. Default is US.

	Required Parameter = [field_of_law,top_number,]

	"""
	return 'Success'

tools = [math_gcd, get_top_cases]
