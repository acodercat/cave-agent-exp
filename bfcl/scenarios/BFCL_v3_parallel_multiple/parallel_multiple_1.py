from typing import List, Dict, Any, Union, Tuple, Set 
def volume_cylinder_calculate(radius:float, height:float) -> str:
	"""
	volume_cylinder_calculate : Calculate the volume of a cylinder given the radius and the height.    
	Parameters:
	radius (float): The radius of the cylinder.
	height (float): The height of the cylinder.

	Required Parameter = [radius,height,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def area_rectangle_calculate(length:float, breadth:float) -> str:
	"""
	area_rectangle_calculate : Calculate the area of a rectangle given the length and breadth.    
	Parameters:
	length (float): The length of the rectangle.
	breadth (float): The breadth of the rectangle.

	Required Parameter = [length,breadth,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def area_circle_calculate(radius:float) -> str:
	"""
	area_circle_calculate : Calculate the area of a circle given the radius.    
	Parameters:
	radius (float): The radius of the circle.

	Required Parameter = [radius,]

	"""
	return 'Success'

tools = [volume_cylinder_calculate, area_rectangle_calculate, area_circle_calculate]
