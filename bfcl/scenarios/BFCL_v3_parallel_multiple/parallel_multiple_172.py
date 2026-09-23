from typing import List, Dict, Any, Union, Tuple, Set 
def grocery_store_find_best(my_location:str, products:List[str], rating:float=None) -> str:
	"""
	grocery_store_find_best : Find the closest high-rated grocery stores based on certain product availability.    
	Parameters:
	my_location (str): The current location of the user.
	rating (float): The minimum required store rating. Default is 5.0.
	products (List[str]): Required products in a list.

	Required Parameter = [my_location,products,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_emissions(distance:int, fuel_type:str, fuel_efficiency:int, efficiency_reduction:int=None) -> str:
	"""
	calculate_emissions : Calculates the annual carbon dioxide emissions produced by a vehicle based on the distance traveled, the fuel type and the fuel efficiency of the vehicle.    
	Parameters:
	distance (int): The distance travelled in miles.
	fuel_type (str): Type of fuel used by the vehicle.
	fuel_efficiency (int): The vehicle's fuel efficiency in miles per gallon.
	efficiency_reduction (int): The percentage decrease in fuel efficiency per year (optional). Default is 0

	Required Parameter = [distance,fuel_type,fuel_efficiency,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def sculpture_get_details(artist:str, title:str, detail:str=None) -> str:
	"""
	sculpture_get_details : Retrieve details of a sculpture based on the artist and the title of the sculpture.    
	Parameters:
	artist (str): The artist who made the sculpture.
	title (str): The title of the sculpture.
	detail (str): The specific detail wanted about the sculpture. Default is 'general information'.

	Required Parameter = [artist,title,]

	"""
	return 'Success'

tools = [grocery_store_find_best, calculate_emissions, sculpture_get_details]
