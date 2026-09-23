from typing import List, Dict, Any, Union, Tuple, Set 
def patient_get_mri_report(patient_id:str, status:str, mri_type:str=None) -> str:
	"""
	patient_get_mri_report : Fetch the brain MRI report of the patient for a given status.    
	Parameters:
	patient_id (str): The patient identifier.
	mri_type (str): Type of the MRI. Default to be 'brain'.
	status (str): Status of the report, could be 'in progress', 'concluded' or 'draft'.

	Required Parameter = [patient_id,status,]

	"""
	return 'Success'

tools = [patient_get_mri_report]
