from typing import List, Dict, Any, Union, Tuple, Set 
def painting_create(shape:str, background_color:str, dimensions:List[int]) -> str:
	"""
	painting_create : Creates a new painting with specified parameters    
	Parameters:
	shape (str): Shape of the painting to be created.
	background_color (str): Background color of the painting.
	dimensions (List[int]): Dimensions of the painting in inches.

	Required Parameter = [shape,background_color,dimensions,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def display_set_screen_brightness(percentage:int, duration:int) -> str:
	"""
	display_set_screen_brightness : Sets the screen brightness for viewing the painting    
	Parameters:
	percentage (int): Screen brightness level in percentage.
	duration (int): Duration to maintain the brightness level in seconds.

	Required Parameter = [percentage,duration,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def painting_display(time:int) -> str:
	"""
	painting_display : Displays a created painting for a specific amount of time    
	Parameters:
	time (int): Time in seconds the painting will be displayed for.

	Required Parameter = [time,]

	"""
	return 'Success'

tools = [painting_create, display_set_screen_brightness, painting_display]
