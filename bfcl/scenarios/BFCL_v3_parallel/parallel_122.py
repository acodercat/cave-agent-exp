from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_vehicle_emission(vehicle_type:str, miles_driven:int, emission_factor:float=None) -> str:
	"""
	calculate_vehicle_emission : Calculate the annual carbon emissions produced by a specific type of vehicle based on mileage.    
	Parameters:
	vehicle_type (str): The type of vehicle. 'gas' refers to a gasoline vehicle, 'diesel' refers to a diesel vehicle, and 'EV' refers to an electric vehicle.
	miles_driven (int): The number of miles driven per year.
	emission_factor (float): Optional emission factor to calculate emissions. Default factor is set for gas vehicles of 1.4

	Required Parameter = [vehicle_type,miles_driven,]

	"""
	return 'Success'

tools = [calculate_vehicle_emission]
