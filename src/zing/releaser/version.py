
import re

MATCH_VERSION = re.compile(r"^\s*(\d+)\.(\d+).(\d+)(?:-([^\.]+)(?:\.(\d+))?)?\s*$", re.MULTILINE).match


class Version(object):
	__slots__ = ("major", "minor", "patch", "suffix", "suffixver")

	@classmethod
	def parse(cls, version):
		match = MATCH_VERSION(version)
		if match:
			groups = match.groups()
			return Version(
				int(groups[0]),  # major
				int(groups[1]),  # minor
				int(groups[2]),  # patch
				groups[3],  # suffix
				int(groups[4]) if groups[4] else None  # suffix version
			)
		else:
			raise ValueError("Invalid version string: %s" % version)

	def __init__(self, major, minor, patch, suffix, suffixver):
		self.major = major
		self.minor = minor
		self.patch = patch
		self.suffix = suffix
		self.suffixver = suffixver

	def bump(self, part):
		setattr(self, part, getattr(self, part) + 1)
		return self

	def bump_suffix(self, suffix, inc=False):
		if inc:
			if self.suffix == suffix:
				self.suffixver = (self.suffixver or 0) + 1
			else:
				self.suffixver = 1
		self.suffix = suffix

	def copy(self):
		return Version(self.major, self.minor, self.patch, self.suffix, self.suffixver)

	def __str__(self):
		if self.suffix:
			if self.suffixver:
				return "%d.%d.%d-%s.%s" % (self.major, self.minor, self.patch, self.suffix, self.suffixver)
			return "%d.%d.%d-%s" % (self.major, self.minor, self.patch, self.suffix)
		else:
			return "%d.%d.%d" % (self.major, self.minor, self.patch)
