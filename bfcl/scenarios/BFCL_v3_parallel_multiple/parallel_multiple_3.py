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
def get_rectangle_property(perimeter:int, area:int, property:str, tolerance:float=None) -> str:
	"""
	get_rectangle_property : Get specific property of the rectangle (like length, width) based on perimeter and area.    
	Parameters:
	perimeter (int): Perimeter of the rectangle.
	area (int): Area of the rectangle.
	property (str): Specific property required. It can be length, width or diagonal.
	tolerance (float): Allowed error for calculations. (optional) Default 0.1

	Required Parameter = [perimeter,area,property,]

	"""
	return 'Success'

tools = [integral, get_rectangle_property]
