from typing import List, Dict, Any, Union, Tuple, Set 
def get_protein_sequence(gene:str, species:str='Homo sapiens') -> str:
	"""
	get_protein_sequence : Retrieve the protein sequence encoded by a human gene.    
	Parameters:
	gene (str): The human gene of interest.
	species (str): The species for which the gene is to be analyzed.

	Required Parameter = [gene,]

	"""
	return 'Success'

tools = [get_protein_sequence]
