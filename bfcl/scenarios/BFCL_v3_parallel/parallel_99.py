from typing import List, Dict, Any, Union, Tuple, Set 
def thermo_calculate_energy(mass:int, phase_transition:str, substance:str=None) -> str:
	"""
	thermo_calculate_energy : Calculate the energy required or released during a phase change using mass, the phase transition temperature and the specific latent heat.    
	Parameters:
	mass (int): Mass of the substance in grams.
	phase_transition (str): Phase transition. Can be 'melting', 'freezing', 'vaporization', 'condensation'.
	substance (str): The substance which is undergoing phase change, default is 'water'

	Required Parameter = [mass,phase_transition,]

	"""
	return 'Success'

tools = [thermo_calculate_energy]
