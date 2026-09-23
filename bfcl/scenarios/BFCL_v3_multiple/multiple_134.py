from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_density(country:str, year:str, population:int, land_area:float) -> str:
	"""
	calculate_density : Calculate the population density of a specific country in a specific year.    
	Parameters:
	country (str): The country for which the density needs to be calculated.
	year (str): The year in which the density is to be calculated.
	population (int): The population of the country.
	land_area (float): The land area of the country in square kilometers.

	Required Parameter = [country,year,population,land_area,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def crime_record_get_record(case_number:str, county:str, details:bool=None) -> str:
	"""
	crime_record_get_record : Retrieve detailed felony crime records using a specific case number and location.    
	Parameters:
	case_number (str): The case number related to the crime.
	county (str): The county in which the crime occurred.
	details (bool): To get a detailed report, set as true. Defaults to false.

	Required Parameter = [case_number,county,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_highest_scoring_player(game:str, season:str, region:str=None) -> str:
	"""
	get_highest_scoring_player : Retrieve the highest scoring player in a specific game and season.    
	Parameters:
	game (str): The game in which you want to find the highest scoring player.
	season (str): The season during which the high score was achieved.
	region (str): The geographical region in which the game is being played (Optional). Defaults to 'USA'

	Required Parameter = [game,season,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_compound_interest(principle:float, interest_rate:float, time:int, compounds_per_year:int=None) -> str:
	"""
	calculate_compound_interest : Calculates the compound interest of an investment over a given time period.    
	Parameters:
	principle (float): The initial amount of the investment.
	interest_rate (float): The yearly interest rate of the investment.
	time (int): The time, in years, the money is invested or borrowed for.
	compounds_per_year (int): The number of times the interest is compounded per year. Default is 1 (interest is compounded yearly).

	Required Parameter = [principle,interest_rate,time,]

	"""
	return 'Success'

tools = [calculate_density, crime_record_get_record, get_highest_scoring_player, calculate_compound_interest]
