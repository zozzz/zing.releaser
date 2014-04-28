
import shlex
import os
import re
import sys
from os import path
from datetime import datetime

from subprocess import Popen, PIPE

from .error import ReleaserError


class Task(object):

	def __init__(self, releaser):
		self.releaser = releaser
		self.logger = releaser.logger

	def run(self):
		raise NotImplemented(self.__class__.__name__ + ".run")

	def run_command(self, cmd, catch_output=False):
		commands = [shlex.split(c) for c in cmd.splitlines() if c.strip()]

		for command in commands:
			try:
				with Popen(command, stdout=PIPE, stderr=PIPE) as process:
					output, stderr = process.communicate()
					exitcode = process.poll()

					output = output.decode("utf-8").strip()
					if not catch_output:
						self.logger.info(output)

					if exitcode:
						if output:
							self.logger.info(os.linesep)
						raise ReleaserError("Failed to execute this command: `%s`, exitcode: %s\n%s" % (" ".join(command), exitcode, stderr.decode("utf-8").strip()))

					if catch_output:
						return output

			except Exception as e:
				if not isinstance(e, ReleaserError):
					self.logger.error("Failed to execute this command: `%s`, because %s" % (" ".join(command), e))
					sys.exit(1)
				else:
					raise


class VCSTask(Task):
	_registry = {}

	@classmethod
	def register(cls, name):
		def decorator(phase_cls):
			cls._registry[name] = phase_cls
			return phase_cls
		return decorator

	def commit(self, nsg, tag=None):
		self.logger.info("Commit changes")

	def switch_branch(self, name):
		cbranch = self.get_current_branch()
		if cbranch is None:
			raise ReleaserError("Can't determine the current barnch")

		if cbranch != name:
			self.logger.info("Switch branch: %s -> %s" % (cbranch, name))
			self._switch_branch(cbranch, name)

	def test_current_branch(self, name):
		self.logger.debug("Test current branch: %s" % name)

		cbranch = self.get_current_branch()
		if cbranch is None:
			raise ReleaserError("Can't determine the current barnch")

		if cbranch != name:
			raise ReleaserError("Current branch (%s) not match with %s" % (cbranch, name))

	def get_current_branch(self):
		raise NotImplemented()

	def wcd_is_clean(self):
		raise NotImplemented()


@VCSTask.register("git")
class Git(VCSTask):

	def get_current_branch(self):
		o = self.run_command("git branch", True)
		m = re.search("^\*\s*(.*?)$", o, re.MULTILINE)
		if m:
			return m.group(1)
		return None

	def _switch_branch(self, from_name, to_name):
		self.run_command("git checkout %s" % to_name)
		self.run_command("git merge %s" % from_name)

	def commit(self, msg, tag=None):
		self.run_command('git commit -a -m "%s"' % msg)

		if tag:
			self.run_command('git tag -a "%s" -m "%s"' % (tag, msg))

	def wcd_is_clean(self):
		o = self.run_command("git status", True)
		return bool(re.search(r"working directory clean\s*$", o))


class Phase(Task):

	_registry = {}

	@classmethod
	def register(cls, name):
		def decorator(phase_cls):
			cls._registry[name] = phase_cls
			return phase_cls
		return decorator

	@classmethod
	def factory(cls, name, *args, **kwargs):
		phase_cls = cls._registry.get(name, cls)
		instance = phase_cls(*args, **kwargs)
		instance.name = name
		return instance

	def __init__(self, releaser, cfg):
		Task.__init__(self, releaser)
		self.cfg = cfg

	def run(self):
		self.logger.info(os.linesep + "PHASE: %s" % self.name)

		if self.releaser.config.zingr.get("vcs", None):
			self.vcs = VCSTask._registry.get(self.releaser.config.zingr.vcs, None)
			if self.vcs is None:
				raise ReleaserError("Unsupported version control system: %s" % self.releaser.config.zingr.vcs)
			self.vcs = self.vcs(self.releaser)
		else:
			self.vcs = None

		if self.vcs:
			if not self.vcs.wcd_is_clean():
				raise ReleaserError("Your working directory is contains changes, pleas commit it before run this command")

			if self.releaser.tconfig.branch:
				self.vcs.test_current_branch(self.releaser.tconfig.branch)

		if self.cfg.command:
			print("run `%s`" % self.cfg.command)
			self.run_command(self.cfg.command)

		result = self._run() or {}

		if self.vcs:
			commit_message = result.get("commit_message", None)
			if self.cfg.vcs_commit and commit_message:
				self.vcs.commit(commit_message, result.get("commit_tag", None))

			if self.cfg.next_branch:
				self.vcs.switch_branch(self.cfg.next_branch)

	def _run(self):
		pass


@Phase.register("bump")
class BumpPhase(Phase):

	def _run(self):
		Phase._run(self)

		if not self.releaser.version_changed:
			self.logger.info("version not changed")
			return

		files = [self.releaser.ref_file] \
				+ [path.join(self.releaser.project_root, f.strip())
				   for f in (self.cfg.files or "").splitlines() if f.strip()]

		for fpath in files:
			modified = False

			# read file contents and replace version
			with open(fpath, "r", encoding="utf-8") as f:
				_content = f.read()
				content = self._replace_version(_content)
				modified = _content != content
				del _content

			# write modified file contents ony if modified
			if modified:
				with open(fpath, "w", encoding="utf-8") as f:
					f.write(content)

			normpath = path.normpath(path.relpath(fpath, self.releaser.project_root))
			if modified:
				self.logger.info("bumped    %s" % normpath)
			else:
				self.logger.info("unchanged %s" % normpath)

		changelog = self.cfg.changelog
		if changelog:
			changelog_path = path.join(self.releaser.project_root, changelog)
			underline = self.cfg.changelog_underline or "~"
			dev_headline = self.cfg.changelog_dev_headline or "Next release"

			modified = False
			with open(changelog_path, "r", encoding="utf-8") as f:
				changelog_contet = f.read()
				mod_content = self._update_changelog(changelog_contet, dev_headline, underline)
				modified = changelog_contet != mod_content

			if modified:
				with open(changelog_path, "w", encoding="utf-8") as f:
					f.write(mod_content)

			normpath = path.normpath(path.relpath(changelog_path, self.releaser.project_root))
			if modified:
				self.logger.info("bumped    %s" % normpath)
			else:
				self.logger.info("unchanged %s" % normpath)

		return dict(
			commit_message="Version bumped to %s" % self.releaser.next_version,
			commit_tag=str(self.releaser.next_version)
		)

	def _replace_version(self, content):
		vsyntax = self.releaser.vsyntax
		new_ver = str(self.releaser.next_version)

		def replacer(match):
			fm = match.group(0)
			vstart, vend = match.span("version")
			return fm[:vstart - 1] + new_ver + fm[vend - 1:]

		return vsyntax.sub(replacer, content)

	def _update_changelog(self, content, dev_headline, underline):
		new_ver = str(self.releaser.next_version)
		regex = r"(?im)%s\s*\n%s{%d,}.*?$" % (dev_headline, underline, len(dev_headline))

		composed_dev_header = "%s\n%s" % (dev_headline, underline * len(dev_headline))

		if not re.search(regex, content):
			self.logger.warn("%s header not found in changelog." % dev_headline)
			return content
		else:
			composed_dev_header = "%s\n%s" % (dev_headline, underline * len(dev_headline))
			ver = "%s (%s)" % (new_ver, datetime.now().strftime("%Y-%m-%d"))
			composed_new_header = "%s\n%s" % (ver, underline * len(ver))

			return re.sub(regex, composed_dev_header + "\n\n\t* entries...\n\n" + composed_new_header, content)
