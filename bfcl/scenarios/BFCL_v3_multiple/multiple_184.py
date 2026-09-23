from typing import List, Dict, Any, Union, Tuple, Set 
def detailed_weather_forecast(location:str, duration:int, include_precipitation:bool=None) -> str:
	"""
	detailed_weather_forecast : Retrieve a detailed weather forecast for a specific location and duration including optional precipitation details.    
	Parameters:
	location (str): The city that you want to get the weather for.
	duration (int): Duration in hours for the detailed forecast.
	include_precipitation (bool): Whether to include precipitation data in the forecast. Default is false.

	Required Parameter = [location,duration,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def recipe_search(dietary_restriction:str, ingredients:List[str], servings:int) -> str:
	"""
	recipe_search : Search for a recipe given dietary restriction, ingredients, and number of servings.    
	Parameters:
	dietary_restriction (str): The dietary restriction, e.g., 'Vegetarian'.
	ingredients (List[str]): The list of ingredients.
	servings (int): The number of servings the recipe should make

	Required Parameter = [dietary_restriction,ingredients,servings,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_time_difference(place1:str, place2:str) -> str:
	"""
	get_time_difference : Get the time difference between two places.    
	Parameters:
	place1 (str): The first place for time difference.
	place2 (str): The second place for time difference.

	Required Parameter = [place1,place2,]

	"""
	return 'Success'

tools = [detailed_weather_forecast, recipe_search, get_time_difference]
