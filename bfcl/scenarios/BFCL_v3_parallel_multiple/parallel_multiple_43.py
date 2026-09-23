from typing import List, Dict, Any, Union, Tuple, Set 
def get_sculpture_details(museum_location:str, sculpture_id:int) -> str:
	"""
	get_sculpture_details : Retrieves details of a sculpture, such as its material and size, from a museum database.    
	Parameters:
	museum_location (str): Location of the museum housing the sculpture.
	sculpture_id (int): Database ID of the sculpture.

	Required Parameter = [museum_location,sculpture_id,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_artwork_price(museum_location:str, sculpture_material:str, sculpture_size:List[int]) -> str:
	"""
	get_artwork_price : Retrieves the price of a sculpture based on size and material.    
	Parameters:
	museum_location (str): Location of the museum housing the sculpture.
	sculpture_material (str): Material of the sculpture.
	sculpture_size (List[int]): Dimensions of the sculpture.

	Required Parameter = [museum_location,sculpture_material,sculpture_size,]

	"""
	return 'Success'

tools = [get_sculpture_details, get_artwork_price]
