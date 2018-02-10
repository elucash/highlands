from typing import *
from pathlib import Path
from itertools import compress

class Sources(NamedTuple):
	source_path: str
	name: str
	path: str = ''
	alias: Dict[str, str] = {}
	link_generated_srcs: List[str] = []
	link_output_jars: List[str] = []


class MavenCoords(NamedTuple):
	group: str
	artifact: str
	version: str
	classifier: str = ''

	def filename(self):
		return '-'.join((e for e in [
				self.artifact,
				self.version,
				self.classifier] if e))

	def repo_path(self):
		g, a, v, _ = self
		g = g.replace('.', '/')
		f = self.filename()
		return f'{g}/{a}/{v}/{f}'

	def to_str(self):
		g, a, v, c = self
		return f'{g}:{a}:{c}:{v}' if c else f'{g}:{a}:{v}'


class LibraryJar(NamedTuple):
	source_path: str
	name: str
	maven_coords: MavenCoords
	deps: List[str] = []


def parse_maven_coords(coords):
	parts = coords.split(':')

	if len(parts) == 3:
		group, artifact, version = parts
		return MavenCoords(group, artifact, version)
	elif len(parts) == 4:
		group, artifact, classifier, version = parts
		return MavenCoords(group, artifact, version, classifier)
	else:
		raise Exception(f'Cannot parse maven coords: {coords}')


definitions_sources = []
definitions_library = []
current_path = None


# have to be invoked before any DSL methods, added to each
# copied and executed DEER file
def set_current_path(path):
	global current_path
	current_path = path


def sources(name, **kw):
	assert current_path is not None
	definitions_sources.append(
			Sources(
					source_path=current_path,
					name=name,
					**kw))


def library_jar(name, maven_coords, **kw):
	assert current_path is not None
	definitions_library.append(
			LibraryJar(
					source_path=current_path,
					name=name,
					maven_coords=parse_maven_coords(maven_coords),
					**kw))
