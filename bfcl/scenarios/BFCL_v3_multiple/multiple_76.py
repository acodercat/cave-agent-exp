from typing import List, Dict, Any, Union, Tuple, Set 
def painting_create_custom(subject:str, color:str, size:int=None) -> str:
	"""
	painting_create_custom : Order a custom painting with your preferred color.    
	Parameters:
	subject (str): The subject of the painting, e.g. horse
	color (str): Preferred main color for the painting.
	size (int): The desired size for the painting in inches. This parameter is optional. Default 12

	Required Parameter = [subject,color,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def sculpture_create_custom(item:str, material:str, size:int=None) -> str:
	"""
	sculpture_create_custom : Order a custom sculpture with your preferred material.    
	Parameters:
	item (str): The subject of the sculpture, e.g. horse
	material (str): Preferred material for the sculpture.
	size (int): The desired size for the sculpture in inches. This parameter is optional. Default 12

	Required Parameter = [item,material,]

	"""
	return 'Success'

tools = [painting_create_custom, sculpture_create_custom]
