from typing import List, Dict, Any, Union, Tuple, Set 
def biological_calc_biomass(energy:float, efficiency:float=0.1) -> str:
	"""
	biological_calc_biomass : Calculate the biomass from the energy given the energy conversion efficiency.    
	Parameters:
	energy (float): The total energy produced.
	efficiency (float): The conversion efficiency, default value is 10%.

	Required Parameter = [energy,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def biological_calc_energy(mols:int, substance:str, joules_per_mol:int=2800) -> str:
	"""
	biological_calc_energy : Calculate energy from amount of substance based on its molecular composition.    
	Parameters:
	mols (int): Amount of substance in moles.
	substance (str): The chemical formula of the substance.
	joules_per_mol (int): The energy produced or required for the reaction, default value for glucose is 2800 kJ/mol

	Required Parameter = [mols,substance,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def physical_calc_work(energy:float, distance:float) -> str:
	"""
	physical_calc_work : Calculate the work from energy.    
	Parameters:
	energy (float): The total energy produced.
	distance (float): The distance over which the work is done.

	Required Parameter = [energy,distance,]

	"""
	return 'Success'

tools = [biological_calc_biomass, biological_calc_energy, physical_calc_work]
