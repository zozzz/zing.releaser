
import re
import logging
from os import path

from .config import Config
from .version import Version
from .error import ReleaserError
from .task import Phase


class Releaser(object):

	def __init__(self, args, project_root, logger):
		self.args = args
		self.project_root = project_root
		self.logger = logger

		self.cfg_file = path.join(project_root, args.config or ".zingr")

		if not path.isfile(self.cfg_file):
			raise ReleaserError("missing config file: %s" % path.relpath(self.cfg_file, project_root))

		self.config = Config(self.cfg_file)

		for section_name in ["zingr", "target", "phase"]:
			if not hasattr(self.config, section_name):
				raise ReleaserError("missing %s section from config file" % section_name)

		self.tconfig = self.config.target.by_name(self.args.target)

	def release(self):
		self._determine_current_version()
		self._determine_next_version()

		self.version_changed = str(self.current_version) != str(self.next_version)

		if self.version_changed:
			self.logger.info("Version changed: %s -> %s" % (self.current_version, self.next_version))

		workflow = self.tconfig.workflow

		if not workflow:
			raise ReleaserError("no workflow specified this target: %s" % self.args.target)

		workflow = [s.strip() for s in workflow.split(",")]

		for phase in workflow:
			phasecfg = self.config.phase.by_name(phase)
			runner = Phase.factory(phase, self, phasecfg)
			runner.run()

	def _determine_current_version(self):
		self.vsyntax = re.compile(self.config.zingr.vsyntax, re.I | re.U)

		if not self.config.zingr.ref_file:
			raise ReleaserError("must define a reference file that hold version variable, eg.: setup.py")

		ref_file = path.join(self.project_root, self.config.zingr.ref_file)
		self.ref_file = ref_file

		with open(ref_file, "r", encoding="utf-8") as f:
			content = f.read()
			cv = self.vsyntax.search(content)
			if cv:
				version_string = cv.group("version") or "0.0.0"
				self.current_version = Version.parse(version_string)
			else:
				raise ReleaserError("The reference file is not contains any valid version descripton")

	def _determine_next_version(self):
		self.next_version = self.current_version.copy()

		if self.args.inc_major:
			self.next_version.bump("major")

		if self.args.inc_minor:
			self.next_version.bump("minor")

		if self.args.inc_patch:
			self.next_version.bump("patch")

		if self.tconfig.remove_suffix or self.args.remove_suffix:
			self.next_version.bump_suffix(None)
		else:
			suffix = self.args.suffix or self.tconfig.suffix
			suffix_or_inc = self.args.suffix_or_inc or (self.tconfig.inc_suffix and suffix)

			if suffix_or_inc:
				self.next_version.bump_suffix(suffix_or_inc, True)
			elif suffix:
				self.next_version.bump_suffix(suffix)
