from typing import List, Dict, Any, Union, Tuple, Set 
def board_game_chess_get_top_players(location:str, minimum_rating:int, number_of_players:int=10) -> str:
	"""
	board_game_chess_get_top_players : Find top chess players in a location based on rating.    
	Parameters:
	location (str): The city you want to find the players from.
	minimum_rating (int): Minimum rating to filter the players.
	number_of_players (int): Number of players you want to retrieve, default value is 10

	Required Parameter = [location,minimum_rating,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_historical_GDP(country:str, start_year:int, end_year:int) -> str:
	"""
	get_historical_GDP : Retrieve historical GDP data for a specific country and time range.    
	Parameters:
	country (str): The country for which the historical GDP data is required.
	start_year (int): Starting year of the period for which GDP data is required.
	end_year (int): Ending year of the period for which GDP data is required.

	Required Parameter = [country,start_year,end_year,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def maps_get_distance_duration(start_location:str, end_location:str, traffic:bool=None) -> str:
	"""
	maps_get_distance_duration : Retrieve the travel distance and estimated travel time from one location to another via car    
	Parameters:
	start_location (str): Starting point of the journey
	end_location (str): Ending point of the journey
	traffic (bool): If true, considers current traffic. Default is false.

	Required Parameter = [start_location,end_location,]

	"""
	return 'Success'

tools = [board_game_chess_get_top_players, get_historical_GDP, maps_get_distance_duration]
