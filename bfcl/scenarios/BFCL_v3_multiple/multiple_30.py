from typing import List, Dict, Any, Union, Tuple, Set 
def rectangle_area(length:int, width:int) -> str:
	"""
	rectangle_area : Calculate the area of a rectangle with given length and width    
	Parameters:
	length (int): Length of the rectangle
	width (int): Width of the rectangle

	Required Parameter = [length,width,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def circle_area(radius:float, isDiameter:bool=False) -> str:
	"""
	circle_area : Calculate the area of a circle with given radius    
	Parameters:
	radius (float): Radius of the circle
	isDiameter (bool): Whether the given length is the diameter of the circle, default is false

	Required Parameter = [radius,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def triangle_area(base:float, height:float) -> str:
	"""
	triangle_area : Calculate the area of a triangle with given base and height    
	Parameters:
	base (float): Base of the triangle
	height (float): Height of the triangle

	Required Parameter = [base,height,]

	"""
	return 'Success'

tools = [rectangle_area, circle_area, triangle_area]
