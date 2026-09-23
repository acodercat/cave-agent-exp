from typing import List, Dict, Any, Union, Tuple, Set 
def get_zodiac_compatibility(sign1:str, sign2:str, scale:str=None) -> str:
	"""
	get_zodiac_compatibility : Retrieve the compatibility score between two Zodiac signs.    
	Parameters:
	sign1 (str): The first Zodiac sign.
	sign2 (str): The second Zodiac sign.
	scale (str): The scale on which compatibility should be shown. Default is 'percentage'.

	Required Parameter = [sign1,sign2,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def local_nursery_find(location:str, plant_types:List[str]) -> str:
	"""
	local_nursery_find : Locate local nurseries based on location and plant types availability.    
	Parameters:
	location (str): The city or locality where the nursery needs to be located.
	plant_types (List[str]): Type of plants the nursery should provide.

	Required Parameter = [location,plant_types,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_sculpture_info(artist_name:str, detail:bool=None) -> str:
	"""
	get_sculpture_info : Retrieves the most recent artwork by a specified artist with its detailed description.    
	Parameters:
	artist_name (str): The name of the artist.
	detail (bool): If True, it provides detailed description of the sculpture. Defaults to False.

	Required Parameter = [artist_name,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def monarch_getMonarchOfYear(location:str, year:int, fullName:bool='false') -> str:
	"""
	monarch_getMonarchOfYear : Retrieve the monarch of a specific location during a specified year.    
	Parameters:
	location (str): The location (e.g., country) whose monarch needs to be found.
	year (int): The year to search the monarch.
	fullName (bool): If true, returns the full name and title of the monarch.

	Required Parameter = [location,year,]

	"""
	return 'Success'

tools = [get_zodiac_compatibility, local_nursery_find, get_sculpture_info, monarch_getMonarchOfYear]
