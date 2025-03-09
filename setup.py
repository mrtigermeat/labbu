from setuptools import setup, find_packages

setup(
	name='labbu',
	version='1.0.0',
	author='tigermeat',
	author_email='mrtigermeat@gmail.com',
	description='Tool to make contextual editing of HTK-style lab files more intuitive and user friendly.',
	packages=find_packages(),
	classifiers=['Programming Language :: Python :: 3'],
	python_requires='>=3.6'
)