# -*- coding: utf-8 -*-

VERSION = ""

import os

from setuptools import setup, find_packages


with open("README.rst", "r") as f:
	README = f.read()


setup(
	name="zing.releaser",
	namespace_packages=["zing"],
	version=VERSION,
	zip_safe=False,

	packages=find_packages("./src"),
	package_dir={
		# "": os.path.join(os.path.dirname(__file__), "src"),
		# "zing": "./src/zing"
		"": "src"
	},
	test_suite="test",

	author="Zoltán Vetési",
	author_email="vetesi.zoltan@gmail.com",
	license="BSD (3-Clause) License",
	description="",
	long_description=README,

	entry_points={
		"console_scripts": [
			"zingr = zing.releaser:entry_point",
		]
	}
)
