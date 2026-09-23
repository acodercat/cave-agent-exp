from typing import List, Dict, Any, Union, Tuple, Set 
def kinematics_calculate_displacement(initial_speed:int, acceleration:int, time:int, rounding:int=2) -> str:
	"""
	kinematics_calculate_displacement : Calculate displacement based on initial speed, acceleration, and time interval for a motion along a straight line.    
	Parameters:
	initial_speed (int): The initial speed of the moving object in m/s.
	acceleration (int): The rate of change of speed, m/s^2.
	time (int): The time interval during which the acceleration is applied, in seconds.
	rounding (int): The number of decimals to round off the result (optional).

	Required Parameter = [initial_speed,acceleration,time,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def kinematics_calculate_final_speed(initial_speed:float, acceleration:float, time:float, rounding:int=2) -> str:
	"""
	kinematics_calculate_final_speed : Calculate the final speed of an object that starts from an initial speed and then accelerates for a certain duration.    
	Parameters:
	initial_speed (float): The initial speed of the moving object in m/s.
	acceleration (float): The rate of change of speed, m/s^2.
	time (float): The time interval during which the acceleration is applied, in seconds.
	rounding (int): The number of decimals to round off the result (optional).

	Required Parameter = [initial_speed,acceleration,time,]

	"""
	return 'Success'

tools = [kinematics_calculate_displacement, kinematics_calculate_final_speed]
