from typing import List, Dict, Any, Union, Tuple, Set 
def math_gaussian_integral(function:str, lower_limit:float, upper_limit:float) -> str:
	"""
	math_gaussian_integral : Perform Gaussian integration over the range of the function.    
	Parameters:
	function (str): The function to integrate, given in terms of x.
	lower_limit (float): The lower limit of the integral.
	upper_limit (float): The upper limit of the integral.

	Required Parameter = [function,lower_limit,upper_limit,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def math_definite_integral(function:str, lower_limit:float, upper_limit:float) -> str:
	"""
	math_definite_integral : Calculate the definite integral of a function within specified bounds.    
	Parameters:
	function (str): The function to integrate, given in terms of x.
	lower_limit (float): The lower limit of the integral.
	upper_limit (float): The upper limit of the integral.

	Required Parameter = [function,lower_limit,upper_limit,]

	"""
	return 'Success'

tools = [math_gaussian_integral, math_definite_integral]
