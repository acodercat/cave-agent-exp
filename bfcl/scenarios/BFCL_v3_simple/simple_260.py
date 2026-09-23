from typing import List, Dict, Any, Union, Tuple, Set 
def paint_requirement_calculate(area:Dict[str, int], paint_coverage:int, exclusion:Dict[str, Union[str, int]]=None) -> str:
	"""
	paint_requirement_calculate : Calculate the amount of paint required to paint a given area. Account for coverage efficiency of the paint and exclusions (like windows).    
	Parameters:
	area (Dict[str, int]): The area to be painted.
	paint_coverage (int): Coverage area per gallon of the paint in square feet.
	exclusion (Dict[str, Union[str, int]]): Area not to be painted. Default to not use any exclusion if not specified.

	Required Parameter = [area,paint_coverage,]

	"""
	return 'Success'

tools = [paint_requirement_calculate]
