from typing import List, Dict, Any, Union, Tuple, Set 
def prediction_evolution(species:str, years:int, model:str=None) -> str:
	"""
	prediction_evolution : Predict the evolutionary rate for a specific species for a given timeframe.    
	Parameters:
	species (str): The species that the evolution rate will be predicted for.
	years (int): Number of years for the prediction.
	model (str): The model used to make the prediction, options: 'Darwin', 'Lamarck', default is 'Darwin'.

	Required Parameter = [species,years,]

	"""
	return 'Success'

tools = [prediction_evolution]
