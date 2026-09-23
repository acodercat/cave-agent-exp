from typing import List, Dict, Any, Union, Tuple, Set 
def math_triangle_area_heron(side1:float, side2:float, side3:float) -> str:
	"""
	math_triangle_area_heron : Calculates the area of a triangle using Heron's formula, given the lengths of its three sides.    
	Parameters:
	side1 (float): Length of the first side of the triangle.
	side2 (float): Length of the second side of the triangle.
	side3 (float): Length of the third side of the triangle.

	Required Parameter = [side1,side2,side3,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def math_triangle_area_base_height(base:float, height:float) -> str:
	"""
	math_triangle_area_base_height : Calculates the area of a triangle using the formula (1/2)base*height.    
	Parameters:
	base (float): The base length of the triangle.
	height (float): The height of the triangle.

	Required Parameter = [base,height,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def math_circle_area(radius:float) -> str:
	"""
	math_circle_area : Calculates the area of a circle given its radius.    
	Parameters:
	radius (float): The radius of the circle.

	Required Parameter = [radius,]

	"""
	return 'Success'

tools = [math_triangle_area_heron, math_triangle_area_base_height, math_circle_area]
