from typing import List, Dict, Any, Union, Tuple, Set 
def lawsuit_search(entity:str, county:str, state:str=None) -> str:
	"""
	lawsuit_search : Retrieve all lawsuits involving a particular entity from specified jurisdiction.    
	Parameters:
	entity (str): The entity involved in lawsuits.
	county (str): The jurisdiction for the lawsuit search.
	state (str): The state for the lawsuit search. Default is California.

	Required Parameter = [entity,county,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_probability(total_outcomes:int, favorable_outcomes:int, round_to:int=2) -> str:
	"""
	calculate_probability : Calculate the probability of an event.    
	Parameters:
	total_outcomes (int): Total number of possible outcomes.
	favorable_outcomes (int): Number of outcomes considered as 'successful'.
	round_to (int): Number of decimal places to round the result to.

	Required Parameter = [total_outcomes,favorable_outcomes,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def predict_house_price(area:int, rooms:int, year:int, location:str) -> str:
	"""
	predict_house_price : Predict house price based on area, number of rooms and year of construction.    
	Parameters:
	area (int): Area of the house in square feet.
	rooms (int): Number of rooms in the house.
	year (int): Year when the house was constructed.
	location (str): The location or city of the house.

	Required Parameter = [area,rooms,year,location,]

	"""
	return 'Success'

tools = [lawsuit_search, calculate_probability, predict_house_price]
