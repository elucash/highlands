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

import shutil
from typing import *
from urllib.request import urlopen
from pathlib import Path, PurePath
from .define import definitions_sources, definitions_library

repo_url = 'https://repo1.maven.org/maven2/'

link_lib = '.link/lib'
link_jar = '.link/jar'
link_src = '.link/src'
ij_idea = '.idea'
ij_libraries = '.idea/libraries'

jar_suffixes = {
    'jar': '.jar',
    'src': '-sources.jar',
}


def generate(root_dir: Path):
    print_banner()
    generate_defs(root_dir)
    generate_libraries(root_dir)
    prepare_link_folder(root_dir)
    symlink_generated_srcs(root_dir)
    symlink_lib_jars(root_dir)
    symlink_output_jars(root_dir)
    generate_project(root_dir)
    print_final()


def print_banner():
    print('UP!')
    for s in definitions_sources:
        print(f'- {s.source_path}/DEER: *')


def print_final():
    print('\nNow you can execute:')
    print('\tbuck fetch //lib/...')
    print('\tbuck build //...')


def generated_header():
    args = ' '.join([s.source_path for s in definitions_sources])
    return f'Generated using UP {args}'


def read_url(url: str):
    try:
        with urlopen(url) as r:
            return r.read().decode('utf-8').strip()
    except IOError as ex:
        print(f'Cannot download: {url}\n{ex}\nexiting...')
        exit()


def generate_libraries(root_dir: Path):
    print('\nGenerating jar libraries in //lib/BUCK')

    libs_content = f'''# {generated_header()}
'''

    for l in definitions_library:
        n, gav = l.name, l.maven_coords
        filename, repo_path = gav.filename(), gav.repo_path()

        print(f'- {l.source_path}/DEER: library_jar({n}, {gav})')

        url_jar = f'{repo_url}{repo_path}.jar.sha1'
        sha1_jar = read_url(url_jar)
        print(f'\t{PurePath(url_jar).name} <= {sha1_jar}')

        url_src = f'{repo_url}{repo_path}-sources.jar.sha1'
        sha1_src = read_url(url_src)
        print(f'\t{PurePath(url_src).name} <= {sha1_src}')

        libs_content += f'''
# Generated from {l.source_path}/DEER:
# library_jar('{n}', '{gav}'...
prebuilt_jar(
  name = '{n}',
  binary_jar = ':{n}_jar',
  source_jar = ':{n}_src',
    visibility = public,
    deps = {l.deps},
)

remote_file(
  name = '{n}_jar',
  out = '{filename}.jar',
  url = '{repo_url}{repo_path}.jar',
  sha1 = '{sha1_jar}'
)

remote_file(
  name = '{n}_src',
  out = '{filename}-sources.jar',
  url = '{repo_url}{repo_path}-sources.jar',
  sha1 = '{sha1_src}'
)
'''

    (root_dir / 'lib' / 'BUCK').write_text(libs_content)


def prepare_link_folder(root_dir: Path):
    link_dir = root_dir / '.link'
    if link_dir.exists():
        shutil.rmtree(str(link_dir))

    link_dir.mkdir()
    content = f'''
#### {generated_header()}

This folder is generated to symlink generated sources and jars for
the build output. By referencing this sources/jars, IDE can avoid any
dependency or clash with internal storages of a Buck build system
'''
    for s in definitions_sources:
        if s.link_generated_srcs or s.link_output_jars:
            content += f'\n- `{s.source_path}/DEER: sources({s.name},...`'
            if s.link_generated_srcs:
                content += f'\n  * `link_generated_srcs = {s.link_generated_srcs}`'
            if s.link_output_jars:
                content += f'\n  * `link_output_jars = {s.link_output_jars}`'

    for l in definitions_library:
        content += f'\n- `{l.source_path}/DEER: library_jar({l.name},...`'
        content += f'\n  * `{l.maven_coords}`'

    (link_dir / 'readme.md').write_text(content)


def symlink_generated_srcs(root_dir: Path):
    link_dir = root_dir/link_src

    print(f'\nSymlinking generated sources in {link_src}')

    for s in definitions_sources:
        if s.link_generated_srcs:
            print(f'- {s.source_path}/DEER: sources({s.name}, link_generated_srcs...)')

        for local_src_path in s.link_generated_srcs:
            path, goal = _get_path_and_goal(f'{s.path}/{local_src_path}'.lstrip('/'))
            full_path = f'{s.source_path}/{path}'
            target = root_dir / f'buck-out/annotation/{full_path}/__{goal}_gen__/{path}'

            mount = link_dir / path
            if not mount.parent.exists():
                mount.parent.mkdir(parents=True)
            mount.symlink_to(target, target_is_directory=True)
            print(f'\t{local_src_path} -> {link_src}/{path}')


def symlink_lib_jars(root_dir: Path):
    link_dir = root_dir/link_lib
    path = 'lib'

    print(f'\nSymlinking library jars in {link_lib}')

    def symlink_lib_jar(library, kind):
        file_suffix = jar_suffixes[kind]
        goal = f'{library.name}_{kind}'
        filename = f'{library.maven_coords.filename()}{file_suffix}'
        target = root_dir / f'buck-out/gen/{path}/{goal}/{filename}'

        lib_jar_name = f'{library.name}{file_suffix}'
        mount = link_dir / lib_jar_name
        if not mount.parent.exists():
            mount.parent.mkdir(parents=True)
        mount.symlink_to(target, target_is_directory=False)
        print(f'\t{library.maven_coords}:{kind} -> {link_lib}/{lib_jar_name}')

    for l in definitions_library:
        print(f'- {l.source_path}/DEER: library_jar({l.name},...')
        symlink_lib_jar(l, 'jar')
        symlink_lib_jar(l, 'src')


def symlink_output_jars(root_dir: Path):
    link_dir = root_dir / link_jar

    print(f'\nSymlinking output jars for packages in {link_jar}')

    for s in definitions_sources:
        if s.link_output_jars:
            print(f'- {s.source_path}/DEER: sources({s.name}, link_output_jars...)')

        for local_jar_path in s.link_output_jars:
            path, goal = _get_path_and_goal(f'{s.path}/{local_jar_path}'.lstrip('/'))
            full_path = f'{s.source_path}/{path}'
            filename = f'{goal}.jar'
            target = root_dir / f'buck-out/gen/{full_path}/{filename}'

            mount = link_dir / path / filename
            if not mount.parent.exists():
                mount.parent.mkdir(parents=True)
            mount.symlink_to(target, target_is_directory=False)
            print(f'\t{local_jar_path} -> {link_jar}/{path}/{filename}')


def generate_defs(root_dir):
    print('\nGenerating source variables in //lib/DEFS')
    # using '//' operator, then applying usual convention
    # of using goal as last segment if it's not specified
    # explicitly.

    defs_content = f'# {generated_header()}'

    defs_content += '''
def _normalize_path_and_goal(path_goal):
    pg = path_goal.split(':')
    if len(pg) == 2:
        return pg[0] + ':' + pg[1]
    else:
        return pg[0] + ':' + pg[0].split('/')[-1]

def _normalize_path_and_goal_dict(d):
    return {_normalize_path_and_goal(k): _normalize_path_and_goal(v)
            for k, v in d.iteritems()}

class _GoalsPathVar(object):
    def __init__(self, root, path, alias = None):
        self.root = root
        self.path = path
        self.alias = _normalize_path_and_goal_dict(alias or {})

    def __floordiv__(self, path_goal):
        suffix = _normalize_path_and_goal(path_goal)
        # try to find library var substitution
        if suffix in self.alias:
            return self.alias[suffix]

        return str(self) + '/' + suffix

    def __str__(self):
        return '//' + (self.root + self.path).lstrip('/')
'''

    defs_content += '''
public = ['PUBLIC']
root = _GoalsPathVar('', '')
'''

    for d in definitions_sources:
        print(f'- {d.source_path}/DEER: sources({d.name})')

        for v in (root_dir / f'{d.source_path}/{d.path}').iterdir():
            print(f"\t{d.name}//'{v.name}'")

        defs_content += f'''
# Generated from {d.source_path}/DEER:
# sources('{d.name}'...
{d.name} = _GoalsPathVar('{d.source_path}', '{d.path}', alias = {d.alias})
'''

    (root_dir / 'lib/DEFS').write_text(defs_content)


def generate_project(root_dir: Path):
    project_name = root_dir.name

    generate_idea_libraries(root_dir)
    generate_idea_project(root_dir, project_name)
    generate_eclipse_project(root_dir, project_name)


def generate_idea_libraries(root_dir: Path):
    libraries_dir = root_dir/ij_libraries
    # just as cleanup
    if libraries_dir.exists():
        shutil.rmtree(str(libraries_dir))

    print(f'\nCreating IJ libraries in {ij_libraries}')

    for l in definitions_library:
        print(f'- {l.source_path}/DEER: library_jar({l.name},...')

        xml_path = f'lib_{l.name}.xml'
        library_xml = libraries_dir/xml_path

        if not library_xml.parent.exists():
            library_xml.parent.mkdir(parents=True)

        jar_filename = link_lib + '/' + l.name + jar_suffixes['jar']
        src_filename = link_lib + '/' + l.name + jar_suffixes['src']

        library_xml.write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<component name="libraryTable">
  <library name="lib_{l.name}">
    <CLASSES>
      <root url="jar://$PROJECT_DIR$/{jar_filename}!/" />
    </CLASSES>
    <JAVADOC />
    <SOURCES>
      <root url="jar://$PROJECT_DIR$/{src_filename}!/" />
    </SOURCES>
  </library>
</component>
''')
        print(f'\t{l.maven_coords} => {ij_libraries}/{xml_path}')


def generate_idea_project(root_dir: Path, project_name: str):
    print('\nCreating IJ modules')

    idea_dir = root_dir/ij_idea

    if not idea_dir.exists():
        idea_dir.mkdir()

    content_sources = []

    for s in definitions_sources:
        content_sources += [
            f'<sourceFolder url="file://$MODULE_DIR$/{s.source_path}" isTestSource="false" />']

    if any(s.link_generated_srcs for s in definitions_sources):
        content_sources += [
            f'<sourceFolder url="file://$MODULE_DIR$/{link_src}" isTestSource="false" generated="true" />']

    content_source_folders = '\n      '.join(content_sources)

    libraries = '\n    '.join((
        f'<orderEntry type="library" name="lib_{l.name}" scope="COMPILE" level="project" />'
        for l in definitions_library))

    (root_dir/f'{project_name}.iml').write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<module type="JAVA_MODULE" version="4">
  <component name="NewModuleRootManager" inherit-compiler-output="true">
    <exclude-output />
    <content url="file://$MODULE_DIR$">
      <excludeFolder url="file://$MODULE_DIR$/.out" isTestSource="false" />
      <excludeFolder url="file://$MODULE_DIR$/buck-out" isTestSource="false" />{content_source_folders}
    </content>
    <orderEntry type="inheritedJdk" />
    <orderEntry type="sourceFolder" forTests="false" />{libraries}
  </component>
</module>''')
    print(f'\t{project_name}.iml')

    (idea_dir/'modules.xml').write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="ProjectModuleManager">
    <modules>
      <module fileurl="file://$PROJECT_DIR$/{project_name}.iml" filepath="$PROJECT_DIR$/{project_name}.iml" />
    </modules>
  </component>
</project>''')
    print(f'\t{ij_idea}/modules.xml')

    (idea_dir/'misc.xml').write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="ProjectRootManager" version="2" languageLevel="JDK_1_9"
      default="false" project-jdk-name="1.8" project-jdk-type="JavaSDK">
    <output url="file://$PROJECT_DIR$/.out/.ij" />
  </component>
</project>''')
    print(f'\t{ij_idea}/misc.xml')


def generate_eclipse_project(root_dir: Path, project_name: str):
    print('\nCreating Eclipse project')

    (root_dir/'.project').write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<projectDescription>
  <name>{project_name}</name>
  <comment></comment>
  <projects>
  </projects>
  <buildSpec>
    <buildCommand>
      <name>org.eclipse.jdt.core.javabuilder</name>
      <arguments>
      </arguments>
    </buildCommand>
  </buildSpec>
  <natures>
    <nature>org.eclipse.jdt.core.javanature</nature>
  </natures>
</projectDescription>
''')
    print('\t.project')

    entries = []

    for s in definitions_sources:
        entries += [f'<classpathentry kind="src" path="{s.source_path}"/>']

    if any(s.link_generated_srcs for s in definitions_sources):
        entries += [f'<classpathentry kind="src" path="{link_src}">'
                    f'<attributes><attribute name="optional" value="true"/></attributes>'
                    f'</classpathentry>']

    entries += ['<classpathentry kind="output" path=".out/.ecj/classes"/>']

    entries += ['<classpathentry kind="con" '
                'path="org.eclipse.jdt.launching.JRE_CONTAINER/'
                'org.eclipse.jdt.internal.debug.ui.launcher.StandardVMType/JavaSE-1.8"/>']

    for l in definitions_library:
        jar_filename = link_lib + '/' + l.name + jar_suffixes['jar']
        src_filename = link_lib + '/' + l.name + jar_suffixes['src']

        if not l.exclude:
            entries += [f'<classpathentry kind="lib" path="{jar_filename}" sourcepath="{src_filename}"/>']

    entries_content = '\n  '.join(entries)

    (root_dir/'.classpath').write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<classpath>{entries_content}
</classpath>
''')
    print('\t.classpath')

## This is omited for now, manual setup
#     processors = set((for s in definitions_sources for p in s.ecj_processors))
#     if processors:
#         factory_entries = []
#
#         for p in processors:
#             factory_entries += [f'<factorypathentry kind="WKSPJAR" id="/{project_name}/{link}"
#  enabled="true" runInBatchMode="false"/>']
#
#         factory_entries_content = '\n  '.join(factory_entries)
#
#         (root_dir/'.factorypath').write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
# <factorypath>{factory_entries_content}
# </factorypath>''')
#         print('\t.factorypath')


def _get_path_and_goal(path_goal):
    pg = path_goal.split(':')
    path = pg[0]
    goal = pg[1] if len(pg) == 2 else pg[0].split('/')[-1]
    return path, goal
