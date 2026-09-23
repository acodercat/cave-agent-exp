from typing import List, Dict, Any, Union, Tuple, Set 
def cellbio_get_proteins(cell_compartment:str, include_description:bool='false') -> str:
	"""
	cellbio_get_proteins : Get the list of proteins in a specific cell compartment.    
	Parameters:
	cell_compartment (str): The specific cell compartment.
	include_description (bool): Set true if you want a brief description of each protein.

	Required Parameter = [cell_compartment,]

	"""
	return 'Success'

tools = [cellbio_get_proteins]
