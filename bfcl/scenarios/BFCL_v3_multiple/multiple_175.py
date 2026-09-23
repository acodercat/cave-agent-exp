from typing import List, Dict, Any, Union, Tuple, Set 
def find_instrument(budget:float, type:str, make:str=None) -> str:
	"""
	find_instrument : Search for a musical instrument within specified budget and of specific type.    
	Parameters:
	budget (float): Your budget for the instrument.
	type (str): Type of the instrument
	make (str): Maker of the instrument, Optional parameter. Default is ''

	Required Parameter = [budget,type,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_binomial_probability(number_of_trials:int, number_of_successes:int, probability_of_success:float=0.5) -> str:
	"""
	calculate_binomial_probability : Calculates the binomial probability given the number of trials, successes and the probability of success on an individual trial.    
	Parameters:
	number_of_trials (int): The total number of trials.
	number_of_successes (int): The desired number of successful outcomes.
	probability_of_success (float): The probability of a successful outcome on any given trial.

	Required Parameter = [number_of_trials,number_of_successes,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def electromagnetic_force(charge1:float, charge2:float, distance:float, medium_permittivity:float=None) -> str:
	"""
	electromagnetic_force : Calculate the electromagnetic force between two charges placed at a certain distance.    
	Parameters:
	charge1 (float): The magnitude of the first charge in coulombs.
	charge2 (float): The magnitude of the second charge in coulombs.
	distance (float): The distance between the two charges in meters.
	medium_permittivity (float): The relative permittivity of the medium in which the charges are present. Default is 8.854 x 10^-12 F/m (vacuum permittivity).

	Required Parameter = [charge1,charge2,distance,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def sports_ranking_get_top_player(sport:str, gender:str='men') -> str:
	"""
	sports_ranking_get_top_player : Get the top player in a specific sport.    
	Parameters:
	sport (str): The type of sport.
	gender (str): The gender of the sport category. Optional.

	Required Parameter = [sport,]

	"""
	return 'Success'

tools = [find_instrument, calculate_binomial_probability, electromagnetic_force, sports_ranking_get_top_player]
