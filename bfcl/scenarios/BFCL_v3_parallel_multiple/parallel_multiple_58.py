from typing import List, Dict, Any, Union, Tuple, Set 
def circle_properties_get(radius:float, get_area:bool=None, get_circumference:bool=None) -> str:
	"""
	circle_properties_get : Retrieve the dimensions, such as area and circumference, of a circle if radius is given.    
	Parameters:
	radius (float): The length of radius of the circle.
	get_area (bool): A flag to determine whether to calculate the area of circle. Default is true.
	get_circumference (bool): A flag to determine whether to calculate the circumference of circle. Default is true.

	Required Parameter = [radius,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def triangle_properties_get(side1:float, side2:float, side3:float, get_area:bool=None, get_perimeter:bool=None, get_angles:bool=None) -> str:
	"""
	triangle_properties_get : Retrieve the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given.    
	Parameters:
	side1 (float): The length of first side of the triangle.
	side2 (float): The length of second side of the triangle.
	side3 (float): The length of third side of the triangle.
	get_area (bool): A flag to determine whether to calculate the area of triangle. Default is true.
	get_perimeter (bool): A flag to determine whether to calculate the perimeter of triangle. Default is true.
	get_angles (bool): A flag to determine whether to calculate the internal angles of triangle. Default is true.

	Required Parameter = [side1,side2,side3,]

	"""
	return 'Success'

tools = [circle_properties_get, triangle_properties_get]
