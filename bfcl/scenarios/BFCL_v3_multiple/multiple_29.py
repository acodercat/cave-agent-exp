from typing import List, Dict, Any, Union, Tuple, Set 
def functions_zero(function:str) -> str:
	"""
	functions_zero : Find the zero points of a function.    
	Parameters:
	function (str): Function given as a string with x as the variable, e.g. 3x+2

	Required Parameter = [function,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def functions_intersect(function1:str, function2:str) -> str:
	"""
	functions_intersect : Locate the intersection points of two functions.    
	Parameters:
	function1 (str): First function given as a string with x as the variable, e.g. 3x+2
	function2 (str): Second function given as a string with x as the variable, e.g. 2x+3

	Required Parameter = [function1,function2,]

	"""
	return 'Success'

tools = [functions_zero, functions_intersect]
