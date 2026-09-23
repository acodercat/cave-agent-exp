from typing import List, Dict, Any, Union, Tuple, Set 
def integral(function:str, a:float, b:float) -> str:
	"""
	integral : Calculate the definite integral of a function over an interval [a, b].    
	Parameters:
	function (str): The function to integrate.
	a (float): The lower bound of the interval.
	b (float): The upper bound of the interval.

	Required Parameter = [function,a,b,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def derivative(function:str, x:float) -> str:
	"""
	derivative : Find the derivative of a function at a certain point.    
	Parameters:
	function (str): The function to differentiate.
	x (float): The point to calculate the derivative at.

	Required Parameter = [function,x,]

	"""
	return 'Success'

tools = [integral, derivative]
