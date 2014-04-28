
from configparser import ConfigParser
from .error import ReleaserError


class Config(object):
	_section_cls = {}

	@classmethod
	def section_handler(cls, section_prefix):
		def decorator(section_cls):
			cls._section_cls[section_prefix] = section_cls
		return decorator

	def __init__(self, file):
		self._cfg = ConfigParser()
		self._cfg.read(file)
		self._process_config()

	def _process_config(self):
		for section in self._cfg.sections():
			parts = section.split(":")
			if len(parts) >= 2:
				prefix = parts.pop(0)
				name = ":".join(parts)
			else:
				prefix = parts[0]
				name = None

			if prefix in self._section_cls:
				if hasattr(self, prefix):
					if name:
						getattr(self, prefix)._by_name[name] = self._section_cls[prefix](self, prefix, name)
					else:
						raise ReleaserError("Duplicate section in config: %s:%s" % (prefix, name))
				else:
					cfg = self._section_cls[prefix](self, prefix, name)
					setattr(self, prefix, cfg)
					if name:
						cfg._by_name[name] = cfg
			else:
				raise ReleaserError("Invalid section prefix: %s" % prefix)


class _None(object):
	pass


NONE = _None()


class _Section(object):

	def __init__(self, config, prefix, name):
		self._config = config
		self._prefix = prefix
		self._name = name
		self._by_name = {}

		if name:
			section_name = "%s:%s" % (prefix, name)
		else:
			section_name = prefix

		section = config._cfg[section_name]
		for k in section:
			setattr(self, k, section.get(k))

	def by_name(self, name):
		try:
			return self._by_name[name]
		except:
			return self

	def get(self, name, default=NONE):
		try:
			return getattr(self, name)
		except AttributeError:
			if default is NONE:
				raise
			else:
				return default

	def __getattr__(self, name):
		parent = getattr(self._config, self._prefix)
		if parent is self:
			return None
		else:
			return getattr(parent, name)


@Config.section_handler("zingr")
class _Zingr(_Section):

	vsyntax = r"(__version__|VERSION)\s*=\s*('|\")(?P<version>.*?)(\2)"


@Config.section_handler("target")
class _Target(_Section):
	pass


@Config.section_handler("phase")
class _Phase(_Section):
	pass
