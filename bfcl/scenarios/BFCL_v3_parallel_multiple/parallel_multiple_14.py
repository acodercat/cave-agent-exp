from typing import List, Dict, Any, Union, Tuple, Set 
def crop_yield_get_history(country:str, crop:str, years:int) -> str:
	"""
	crop_yield_get_history : Retrieve historical crop yield data of a specific crop in a given country.    
	Parameters:
	country (str): The country of interest.
	crop (str): Type of crop.
	years (int): Number of years of history to retrieve.

	Required Parameter = [country,crop,years,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def animal_population_get_history(country:str, species:str, years:int) -> str:
	"""
	animal_population_get_history : Retrieve historical population size of a specific species in a given country.    
	Parameters:
	country (str): The country of interest.
	species (str): Species of the animal.
	years (int): Number of years of history to retrieve.

	Required Parameter = [country,species,years,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def animal_population_get_projection(country:str, species:str, years:int) -> str:
	"""
	animal_population_get_projection : Predict the future population size of a specific species in a given country.    
	Parameters:
	country (str): The country of interest.
	species (str): Species of the animal.
	years (int): Number of years in the future to predict.

	Required Parameter = [country,species,years,]

	"""
	return 'Success'

tools = [crop_yield_get_history, animal_population_get_history, animal_population_get_projection]
