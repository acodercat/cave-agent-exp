from typing import List, Dict, Any, Union, Tuple, Set 
def generate_sound_wave(frequency:float, duration:int, wave_type:str='sine') -> str:
	"""
	generate_sound_wave : This function is for generating a sinusoidal sound wave file of a certain frequency for a specific duration and save it to a WAV file.    
	Parameters:
	frequency (float): The frequency of the sound wave in Hz.
	duration (int): The duration of the sound in seconds.
	wave_type (str): The waveform to be used to generate the sound.

	Required Parameter = [frequency,duration,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def play_sound_wave(wave_file:str, volume:float=1) -> str:
	"""
	play_sound_wave : This function is for playing a sound wave file.    
	Parameters:
	wave_file (str): The filename of the sound wave file to be played.
	volume (float): The volume level at which the sound is to be played (1 is 100%).

	Required Parameter = [wave_file,]

	"""
	return 'Success'

tools = [generate_sound_wave, play_sound_wave]
