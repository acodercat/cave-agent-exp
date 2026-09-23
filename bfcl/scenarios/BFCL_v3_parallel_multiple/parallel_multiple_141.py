from typing import List, Dict, Any, Union, Tuple, Set 
def cellbio_get_proteins(cell_compartment:str, include_description:bool=False) -> str:
	"""
	cellbio_get_proteins : Get the list of proteins in a specific cell compartment.    
	Parameters:
	cell_compartment (str): The specific cell compartment.
	include_description (bool): Set true if you want a brief description of each protein.

	Required Parameter = [cell_compartment,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def mutation_type_find(snp_id:str, species:str=None) -> str:
	"""
	mutation_type_find : Finds the type of a genetic mutation based on its SNP (Single Nucleotide Polymorphism) ID.    
	Parameters:
	snp_id (str): The ID of the Single Nucleotide Polymorphism (SNP) mutation.
	species (str): Species in which the SNP occurs, default is 'Homo sapiens' (Humans).

	Required Parameter = [snp_id,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def find_exhibition(location:str, art_form:str, month:str, user_ratings:str=None) -> str:
	"""
	find_exhibition : Locate the most popular exhibitions based on criteria like location, time, art form, and user ratings.    
	Parameters:
	location (str): The city where the exhibition is held, e.g., New York, NY.
	art_form (str): The form of art the exhibition is displaying e.g., sculpture.
	month (str): The month (in full name) of exhibition.
	user_ratings (str): Select exhibitions with user rating threshold. Default is all if not specified.

	Required Parameter = [location,art_form,month,]

	"""
	return 'Success'

tools = [cellbio_get_proteins, mutation_type_find, find_exhibition]
