from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_final_speed(time:int, initial_speed:int=None, gravity:float=None) -> str:
	"""
	calculate_final_speed : Calculate the final speed of an object in free fall after a certain time, neglecting air resistance. The acceleration due to gravity is considered as -9.81 m/s^2    
	Parameters:
	initial_speed (int): The initial speed of the object in m/s. Default is 0 for an object at rest.
	time (int): The time in seconds for which the object is in free fall.
	gravity (float): The acceleration due to gravity. Default is -9.81 m/s^2.

	Required Parameter = [time,]

	"""
	return 'Success'

tools = [calculate_final_speed]
