from typing import List, Dict, Any, Union, Tuple, Set 
def geometry_square_calculate(side:int) -> str:
	"""
	geometry_square_calculate : Calculates the area and perimeter of a square given the side length.    
	Parameters:
	side (int): The length of a side of the square.

	Required Parameter = [side,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def geometry_circle_calculate(radius:int) -> str:
	"""
	geometry_circle_calculate : Calculates the area and circumference of a circle given the radius.    
	Parameters:
	radius (int): The radius of the circle.

	Required Parameter = [radius,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def geometry_rectangle_calculate(width:int, length:int) -> str:
	"""
	geometry_rectangle_calculate : Calculates the area and perimeter of a rectangle given the width and length.    
	Parameters:
	width (int): The width of the rectangle.
	length (int): The length of the rectangle.

	Required Parameter = [width,length,]

	"""
	return 'Success'

tools = [geometry_square_calculate, geometry_circle_calculate, geometry_rectangle_calculate]
