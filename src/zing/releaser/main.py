
import sys
import os
import logging

from argparse import ArgumentParser

from .releaser import Releaser
from .error import ReleaserError

argp = ArgumentParser(usage="zingr target [options]")
argp.add_argument("target", help="Name of the target.", default=None)
argp.add_argument("-M", help="Increase major version by one.", action="store_true", default=False, dest="inc_major")
argp.add_argument("-m", help="Increase minor version by one.", action="store_true", default=False, dest="inc_minor")
argp.add_argument("-p", help="Increase patch version by one.", action="store_true", default=False, dest="inc_patch")
argp.add_argument("-s", help="Add suffix to the current version.", default=None, dest="suffix")
argp.add_argument("-S", help="Add suffix to the current version, if it is exists increase their version", default=None, dest="suffix_or_inc")
argp.add_argument("-x", help="Remove suffix", action="store_true", default=False, dest="remove_suffix")
argp.add_argument("-d", help="Dry run, dot change anything on the filesystem, vcs", action="store_true", default=False, dest="dry")
argp.add_argument("-c", help="Config file path, relative to cwd", default=None, dest="config")
argp.add_argument("-q", help="Quite mode", action="store_true", default=False, dest="quite")


def entry_point():
	args = argp.parse_args()

	logger = logging.getLogger("zing.releaser")
	logger.addHandler(logging.StreamHandler(sys.stdout))

	if not args.quite:
		logger.setLevel(logging.INFO)
	else:
		logger.setLevel(logging.ERROR)

	try:
		Releaser(args, os.getcwd(), logger).release()
	except ReleaserError as e:
		print("Error occured during release: %s" % e)
		sys.exit(1)
	except KeyboardInterrupt:
		sys.exit(1)
