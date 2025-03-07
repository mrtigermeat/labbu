import mytextgrid

from pathlib import Path as P
from ftfy import fix_text as fxy #UNICODE Fixes

# inspired in part by how labels are handled in the nnsvs_db_converter
class Label:
	def __init__(self, lab_name: str = None):
		super().__init__()
		self.lab = [{'start': 0, 'end': 0, 'phone': None}]
		self.lab_name = ""
		self.breath_phonemes = ['AP', 'br', 'breath', 'inhale']
		self.silence_phonemes = ['SP', 'pau', 'sil', '<spn>']

		if lab_name != None:
			self.load(P(lab_name))

	def __len__(self):
		return len(self.lab)

	def __str__(self):
		#mostly for debug
		return f"LABBU Label - Name: {self.lab_name}, Entries: {len(self.lab)}, Length: {str(self.lab[-1]['end'])}, Phonemes: {self.phonemes}"

	@property
	def name(self):
		return self.lab_name

	@name.setter
	def name(self, value):
		self.lab_name = value

	@property
	def phonemes(self):
		phoneme_list = []
		for i, entry in enumerate(self.lab):
			if entry['phone'] not in phoneme_list:
				phoneme_list.append(entry['phone'])

		phoneme_list.sort()

		return phoneme_list

	def get(self, i: int):
		try:
			return self.lab[i]
		except IndexError as e:
			print(f"Index Error: {e}")

	def set(self, i: int, type, value):
		try:
			self.lab[i][type] = value
		except Exception as e:
			print(f"Cannot change label at index {i}: {e}")

	def delete(self, i: int):
		try:
			self.lab.pop(i)
		except Exception as e:
			print(f"Cannot delete label index {i}")

	def load(self, fpath: str):

		self.lab.clear()

		lab_path = P(fpath)
		self.lab_name = P(fpath).stem
		ext = lab_path.suffix
		
		try:
			with open(lab_path, 'r', encoding='utf-8') as f:
				# HTK label
				if ext == '.lab':
					for line in f:
						line = fxy(line) #unicode fixes, JUUUST in case
						split_line = line.rstrip().split(' ')
						self.lab.append({'start': int(split_line[0]), 'end': int(split_line[1]), 'phone': split_line[2]})
				# TextGrid to label
				if ext == '.TextGrid':
					tg = mytextgrid.read_from_file(lab_path)

					for tier in tg:
						if tier.name == 'phones' and tier.is_interval():
							for interval in tier:
								time_start = int(float(interval.xmin)*10000000)
								time_end = int(float(interval.xmax)*10000000)
								label = fxy(interval.text)
								if label == '':
									label = 'pau'
								if label in self.breath_phonemes:
									label = 'br'
								self.lab.append({'start': time_start, 'end': time_end, 'phone': label})
		except Exception as e:
			print(f"Error loading lab: {e}")

	def export(self, exp_path):
		exp = P(exp_path)
		ext = exp.suffix

		if ext not in ['.lab', '.TextGrid']:
			print('Cannot export label.')
		else:
			if ext == '.lab':
				exp_string = ''
				# build output string
				for i, entry in enumerate(self.lab):
					t1 = entry['start']
					t2 = entry['end']
					ph = entry['phone']
					exp_string += f"{t1} {t2} {ph}\n"

				exp_string.rstrip()

				#save as file
				with open(exp, 'w', encoding='utf-8') as f:
					f.write(exp_string)
					f.close()
			elif ext == '.TextGrid':
				#setup textgrid. adds 0.01 to the length cuz it wouldn't work otherwise
				tg_div = 10000000.0
				end_value = (float(self.lab[-1]['end']) / tg_div) + 0.01
				xmax = "%.2f" % end_value
				new_tg = mytextgrid.create_textgrid(xmin=0, xmax=xmax)
				phone_tier = new_tg.insert_tier('phones')
				for i, entry in enumerate(self.lab):
					xmax_value = float(self.lab[i]['end']) / tg_div
					b_xmax = float("%.2f" % xmax_value)
					b_ph = self.lab[i]['phone']

					if b_ph in self.silence_phonemes:
						b_ph = ''
					
					phone_tier.insert_boundaries(b_xmax)
					if i == 0:
						pass
					else:
						phone_tier.set_text_at_index(i, b_ph)

				new_tg.write(exp)

if __name__ == "__main__":
	print('Debugging LABEL class')

	lab_path = P('../sample/sample.lab')

	lab = Label(lab_path)

	lab.export('../sample/sample.TextGrid')