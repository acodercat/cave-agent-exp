from typing import List, Dict, Any, Union, Tuple, Set 
def EuclideanDistance_calculate(pointA:List[int], pointB:List[int], rounding:int=None) -> str:
	"""
	EuclideanDistance_calculate : Calculate the Euclidean distance between two points.    
	Parameters:
	pointA (List[int]): Coordinates for Point A.
	pointB (List[int]): Coordinates for Point B.
	rounding (int): Optional: The number of decimals to round off the result. Default 0

	Required Parameter = [pointA,pointB,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def angleToXAxis_calculate(pointA:List[int], pointB:List[int], rounding:int=None) -> str:
	"""
	angleToXAxis_calculate : Calculate the angle between two points with respect to x-axis.    
	Parameters:
	pointA (List[int]): Coordinates for Point A.
	pointB (List[int]): Coordinates for Point B.
	rounding (int): Optional: The number of decimals to round off the result. Default 0

	Required Parameter = [pointA,pointB,]

	"""
	return 'Success'

tools = [EuclideanDistance_calculate, angleToXAxis_calculate]
