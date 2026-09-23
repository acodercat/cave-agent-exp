from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_bacteria_evolution_rate(start_population:int, duplication_frequency:int, duration:int, generation_time:int=None) -> str:
	"""
	calculate_bacteria_evolution_rate : Calculate the evolution rate of bacteria given the starting number, duplication frequency and total duration.    
	Parameters:
	start_population (int): The starting population of bacteria.
	duplication_frequency (int): The frequency of bacteria duplication per hour.
	duration (int): Total duration in hours.
	generation_time (int): The average generation time of the bacteria in minutes. Default is 20 minutes

	Required Parameter = [start_population,duplication_frequency,duration,]

	"""
	return 'Success'

tools = [calculate_bacteria_evolution_rate]
