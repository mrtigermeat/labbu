import sys, os, re
import mytextgrid
import yaml

from ftfy import fix_text as fxy
from pathlib import Path as P
from loguru import logger

from .modules import Label

logger_format = "{time:HH:mm:ss} | <lvl>{level}</lvl> | <lvl>{message}</lvl>"
logger.remove()
logger.add(sys.stdout, format=logger_format, level="DEBUG")

class labbu:
	def __init__(self,
				 lang: str = 'en',
				 debug: bool = False,
				 verbose: bool = False):
		super().__init__()

		# set up logger
		if verbose:
			if debug: 
				log_lvl = "DEBUG"
			else: 
				log_lvl = "INFO"
			logger.remove()
			logger.add(sys.stdout, format=logger_format, level=log_lvl)
		elif not verbose:
			logger.remove()
			logger.add(sys.stdout, format=logger_format, level="CRITICAL")
		
		# set up language
		self.lang_def_path = P('language')
		assert self.lang_def_path.exists()
		self.lang = lang
		self.__setattr__('lang', self.lang)
		self.load_language(lang)

		# set up constants
		self.short_range = range(0, 51000)

		# set up Label module
		self.lab = Label()
		self.lab_name = ""

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
	def full_lab(self):
		return self.lab

	def load_language(self, lang):
		try:
			if lang.endswith('.yaml'):
				dict_path = P(lang)
			else:
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
		except Exception as e:
			logger.error(f"Cannot load language: {e}")

	# load lab with the Label class
	def load(self, fpath: str):
		try:
			self.lab.load(fpath)
			self.lab_name = self.lab.name
		except Exception as e:
			logger.warning(f"Cannot load label. Error: {e}")

	# export lab with the Label class
	def export(self, fpath: str):
		if fpath.endswith('.lab') or fpath.endswith('.TextGrid'):
			self.lab.export(fpath)
		else:
			logger.warning(f"Cannot export label to {fpath}. Ensure file path is either '.lab' or '.TextGrid'")

	#checks if current index is the first or last in the label
	def is_boe(self, i):
		return True if i == 0 or i == len(self.lab) else False

	#returns the length of the label as an int
	def get_length(self):
		return len(self.lab)

	# get's the length of a phoneme as an int
	def get_pho_len(self, i):
		return int(self.lab.get(i)['end']) - int(self.lab.get(i)['start'])

	# check if any stray phonemes are in the label
	def check_label(self):
		logger.opt(colors=True).info(f"Checking label! <green>{self.lab_name}</green>")
		err_count = False

		for i in range(self.get_length()):
			if not self.lab.get(i)['phone'] in self.pho_dict:
				logger.opt(colors=True).warning(f"<white>Undefined label @ index {str(i+1)}: '</white><red>{self.lab.get(i)['phone']}</red><white>' is not a phoneme.</white>")
				err_count = True

		for i in range(self.get_length()):
			if self.get_pho_len(i) in self.short_range:
				label_length = float(self.get_pho_len(i)) / 10000000.0
				logger.opt(colors=True).warning(f"<white>Too short label @ index {str(i+1)}: '</white><magenta>{self.lab.get(i)['phone']}</magenta><white>' is too short.</white> <blue>(Length: {label_length:.2f}s)</blue>")
				err_count = True

		if not err_count:
			logger.success(f"No errors detected in {self.lab_name}")

	#overwrite the phoneme at a given index: labu.change_phone(i, 'aa')
	def change_phone(self, i, new_phone):
		self.lab.set(i)['phone'] = new_phone

	#merges the current index with the next index: labu.merge_phones(i, 'cl')
	def merge(self, i, new_phone):
		if not self.is_boe(i):
			try:
				new_start = self.lab.get(i)['start']
				new_end = self.lab.get(i+1)['end']
				self.lab.delete(i+1)
				self.lab.set(i)['start'] = new_start
				self.lab.set(i)['end'] = new_end
				self.lab.set(i)['phone'] = new_phone
			except Exception as e:
				logger.error(f"Unable to merge phoneme at index {i}: {e}")
		else:
			logger.error(f'Unable to merge label at index {i}. Make sure it is not the end of the file!')

	# splits a label in half
	def split(self, i, pho1, pho2):
		try:
			p1_start = int(self.lab.get(i)['start'])
			p2_end = int(self.lab.get(i)['end'])
			p1_end = p1_start + int(self.get_pho_len(i) / 2)
			p2_start = p1_end

			self.lab.set(i)['phone'] = pho1
			self.lab.set(i)['start'] = p1_start
			self.lab.set(i)['end'] = p1_end
			self.lab.insert(i+1, p2_start, p2_end, pho2)
		except Exception as e:
			logger.error(f"Unable to split entry at index {i}: {e}")

	# replaces all instances of a phoneme with a new one in a label
	def replace_all(self, old_phone, new_phone):
		for i in range(self.get_length()):
			if self.lab.get(i)['phone'] == old_phone:
				self.lab.get(i)['phone'] = new_phone

	# returns the previous, current and next phoneme
	@logger.catch
	def context(self, i):
		cp = self.lab.get(i)['phone']
		try:
			pp = self.lab.get(i-1)['phone']
		except:
			pp = ''
		try:
			np = self.lab.get(i+1)['phone']
		except:
			np = ''

		return pp, cp, np

	#returns true if phoneme (arg1) is a certain type (arg2)
	# labu.is_type('aa', 'vowel') returns 'True'
	def is_type(self, phone, ph_type):
		try:
			if phone in self.pho_dict:
				if ph_type in self.pho_dict[phone]:
					return True
				else:
					return False
		except KeyError as e:
			logger.error(f"'{phone}' or '{ph_type}' not defined, returning False: {e}")
			return False

	#remove any numbers from the phone and lower it, but leave SP and AP alone
	def clean_phones(self, i):
		pp, cp, np = self.context(i)
		if not self.is_type(cp, 'silence') or not self.is_type(cp, 'breath'):
			try:
				new_phone = re.sub(r'[0-9]', '', cp)
				self.change_phone(i, new_phone.lower())
			except TypeError as e:
				print(f"Type Error at {i}: {e}")

	def clean_all_phones(self):
		for i in range(self.get_length()):
			self.clean_phones(i)

	#ensures there are no conflicts of timing in labels
	def normalize_time(self):
		for i in range(self.get_length()):
			if self.lab.get(i)['start'] == self.lab.get(i-1)['end']:
				pass
			else:
				self.lab.set(i, 'start', self.lab.get(i-1)['end'])

	#this is untested heehee
	def adjust_lab_end(self, i, factor):
		new_end = self.lab.get(i)['end'] + factor
		self.lab.set(i, 'end', new_end)
		self.lab.set(i+1, 'start', new_end)

	def is_between_vowels(self, i):
		pp, cp, np = self.context(i)
		return True if self.is_type(np, 'vowel') and self.is_type(pp, 'vowel') else False

	def count_phones(self):
		pho_list = []
		for i in range(self.get_length()):
			pp, cp, np = self.context(i)
			pho_list.append(cp)
		return pho_list

if __name__ == '__main__':
	labu = labbu(lang='en', debug=True, verbose=True)

	labu.load('sample/sample.lab')

	labu.check_label()