import sys, os, re
import mytextgrid
import yaml

from ftfy import fix_text as fxy
from pathlib import Path as P
from loguru import logger

sys.path.append('.')

from modules import Label

class labbu:
	def __init__(self,
				 lang: str = 'en',
				 debug: bool = False):
		super().__init__()

		# set logger up
		if not debug:
			logger.remove()
			logger.add(sys.stdout, level="INFO")
			
		self.lang_def_path = P('language')

		assert self.lang_def_path.exists()

		self.lang = lang
		self.load_language(lang)

		self.min_short = (0, 51000)

		self.lab = Label()

		logger.debug("Successfully initialized LABBU")

	@property
	def language(self):
		return self.lang

	@language.setter
	def language(self, value):
		self.load_language(value)

	@property
	def dictionary(self):
		return self.pho_dict

	@property
	def labrange(self):
		return range(len(self.lab))

	@property
	def full_label(self):
		return self.lab

	@full_label.setter
	def full_label(self, new_label):
		self.lab = new_label

	def load_language(self, lang):
		dict_path = self.lang_def_path / f"{lang}.yaml"
		assert dict_path.exists()

		self.pho_dict = yaml.safe_load(dict_path.read_text())

		# global language constants
		self.pho_dict['SP'] = ['silence']
		self.pho_dict['pau'] = ['silence']
		self.pho_dict['sil'] = ['silence']
		self.pho_dict['AP'] = ['breath', 'silence']
		self.pho_dict['br'] = ['breath', 'silence']

		logger.debug(f"Loaded Language : {lang}")

	def load_lab(self, fpath: str):
		try:
			self.lab.load(fpath)
		except Exception as e:
			logger.warning(f"Cannot load label. Error: {e}")

	def export_lab(self, fpath: str):
		if fpath.endswith('.lab') or fpath.endswith('.TextGrid'):
			self.lab.export(fpath)
		else:
			logger.warning(f"Cannot export label to {fpath}. Ensure file path is either '.lab' or '.TextGrid'")

	# debug/reference to print the phoneme dictionary.
	def validate_phonemes(self):
		print('PHONE - TYPE\n')
		for key in self.pho_dict:
			print(f"{key} - {self.pho_dict[key]}")

	# check if any stray phonemes are in the label
	def check_label(self):
		print(f"Checking label! {self.lab_name}")

		for i in range(self.get_length()):
			if not self.lab[i]['phone'] in self.pho_dict:
				print(f"Undefined label @ index {str(i+1)}:\t'{self.lab[i]['phone']}' is not a phoneme.")

		for i in range(self.get_length()):
			if self.get_pho_len(i) in range(self.min_short):
				print(f"Too short label @ index{str(i+1)}:\t'{self.lab[i]['phone']}' is too short. ({str(self.get_pho_len(i))})")

	#checks if current index is the first or last in the label
	def is_boe(self, i):
		return True if i == 0 or i == len(self.lab) else False

	#returns the length of the label as an int
	def get_length(self):
		return len(self.lab) 

	#overwrite the phoneme at a given index: labu.change_phone(i, 'aa')
	def change_phone(self, i, new_phone):
		self.lab[i]['phone'] = new_phone

	#merges the current index with the next index: labu.merge_phones(i, 'cl')
	def merge(self, i, new_phone):
		if not self.is_boe(i):
			try:
				new_start = self.lab[i]['start']
				new_end = self.lab[i+1]['end']
				self.lab.pop(i+1)
				self.lab[i]['start'] = new_start
				self.lab[i]['end'] = new_end
				self.lab[i]['phone'] = new_phone
			except:
				pass
		else:
			print(f'Unable to merge label at index {i}. Make sure it is not the end of the file!')

	def get_pho_len(self, i):
		return int(self.lab[i]['end']) - int(self.lab[i]['start'])

	def split_label(self, i, pho1, pho2):
		'''
		Splits a label exactly in half
		'''
		p1_start = int(self.lab[i]['start'])
		p2_end = int(self.lab[i]['end'])
		p1_end = p1_start + int(self.get_pho_len(i) / 2)
		p2_start = p1_end

		self.lab[i]['phone'] = pho1
		self.lab[i]['start'] = p1_start
		self.lab[i]['end'] = p1_end
		self.lab.insert(i+1, {'phone': pho2, 'start': p2_start, 'end': p2_end})

	def replace_all(self, old_phone, new_phone):
		'''
		Replace all phonemes in a label with a new phoneme
		'''
		for i in range(self.get_length()):
			if self.lab[i]['phone'] == old_phone:
				self.lab[i]['phone'] = new_phone

	def curr_phone(self, i):
		if self.is_boe(i):
			pass
		else:
			try:
				return self.lab[i]['phone']
			except IndexError:
				print('IndexError: Please verify your output is correct!')
				pass

	def prev_phone(self, i):
		if self.is_boe(i):
			pass
		else:
			try:
				return self.lab[i-1]['phone']
			except IndexError:
				print('IndexError: Please verify your output is correct!')
				pass

	def next_phone(self, i):
		if self.is_boe(i):
			pass
		else:
			try:
				return self.lab[i+1]['phone']
			except IndexError:
				print('IndexError: Please verify your output is correct!')
				pass

	#returns true if phoneme (arg1) is a certain type (arg2)
	# labu.is_type('aa', 'vowel') returns 'True'
	def is_type(self, phone, ph_type):
		try:
			if ph_type == 'plosive':
				return True if phone in self.plosive_consonants else False
			elif ph_type == 'palatal':
				return True if phone in self.palatal_consonants and not self.is_type(phone, 'vowel') else False
			elif ph_type == 'silence':
				return True if phone in self.silence_phones else False
			else:
				curr_type = self.pho_dict[phone]
				return True if curr_type == ph_type else False
		except KeyError as e:
			print(f"ERR: Phoneme not defined, returning False | {e}")
			return False

	#remove any numbers from the phone and lower it, but leave SP and AP alone
	def clean_phones(self, i):
		if self.curr_phone(i) != 'SP' or self.curr_phone(i) != 'AP':
			try:
				new_phone = re.sub(r'[0-9]', '', self.curr_phone(i))
				self.change_phone(i, new_phone.lower())
			except TypeError as e:
				print(f"Type Error at {i}: {e}")

	def clean_all_phones(self):
		for i in range(self.get_length()):
			self.clean_phones(i)

	#ensures there are no conflicts of timing in labels
	def normalize_time(self):
		for i in range(self.get_length()):
			if self.lab[i]['start'] == self.lab[i-1]['end']:
				pass
			else:
				self.lab[i]['start'] = self.lab[i-1]['end']

	#gets the mean of each occurance of a phoneme
	def get_mean_phone_length(self, phone):
		dur_list = []
		for i in range(self.get_length()):
			if self.lab.curr_phone(i) == phone:
				dur_list.append(self.get_pho_len(i))
		return dur_list.mean()

	#this is untested heehee
	def adjust_lab_end(self, i, factor):
		new_end = self.lab[i]['end'] + factor
		self.lab[i]['end'] = new_end
		self.lab[i+1]['start'] = new_end

	def is_between_vowels(self, i):
		return True if self.is_type(self.next_phone(i), 'vowel') and self.is_type(self.prev_phone(i), 'vowel') else False

	#converts lab from enunu-style to diffsinger-style
	#(pau, br) > (SP, AP)
	def enunu2diff(self):
		self.replace_all('pau', 'SP')
		self.replace_all('br', 'AP')

	def diff2enunu(self):
		self.replace_all('SP', 'pau')
		self.replace_all('AP', 'br')

	#unloads the label, you never know if you'll need it
	def unload_lab(self):
		del self.lab
		self.lab = []

	def count_phones(self):
		pho_list = []
		for i in range(self.get_length()):
			pho_list.append(self.curr_phone(i))
		return pho_list

	def fix_spap(self):
		for i in range(self.get_length()):
			if self.lab[i]['phone'] == 'sp' or self.lab[i]['phone'] == 'ap':
				self.lab[i]['phone'] = self.lab[i]['phone'].upper()


if __name__ == '__main__':
	labu = labbu(lang='en', debug=True)

	labu.language = "ja"

	print(labu.dictionary)
