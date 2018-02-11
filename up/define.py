# Copyright 2018 Immutables Authors and Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import *


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

    def __str__(self):
        g, a, v, c = self
        return f'{g}:{a}:{c}:{v}' if c else f'{g}:{a}:{v}'


class LibraryJar(NamedTuple):
    source_path: str
    name: str
    maven_coords: MavenCoords
    exclude: bool = False
    deps: List[str] = []


def parse_maven_coords(coords) -> MavenCoords:
    parts = coords.split(':')

    if len(parts) == 3:
        group, artifact, version = parts
        return MavenCoords(group, artifact, version)
    elif len(parts) == 4:
        group, artifact, classifier, version = parts
        return MavenCoords(group, artifact, version, classifier)
    else:
        raise Exception(f'Cannot parse maven coords: {coords}')


definitions_sources: List[Sources] = []
definitions_library: List[LibraryJar] = []
current_path: str = None


# have to be invoked before any DSL methods, added to each
# copied and executed DEER file
def set_current_path(path):
    global current_path
    current_path = path


# DSL sources
def sources(name, **kw):
    assert current_path is not None
    definitions_sources.append(Sources(
        source_path=current_path,
        name=name,
        **kw))


# DSL library_jar
def library_jar(name, maven_coords, **kw):
    assert current_path is not None
    definitions_library.append(LibraryJar(
        source_path=current_path,
        name=name,
        maven_coords=parse_maven_coords(maven_coords),
        **kw))
