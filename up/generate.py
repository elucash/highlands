import os
import imp
import sys
import shutil
import subprocess
from typing import *
from urllib.request import urlopen
from pathlib import Path, PurePath
from .define import definitions_sources, definitions_library
from .define import MavenCoords, LibraryJar

repo_url = 'https://repo1.maven.org/maven2/'
jar_suffixes = {
	'jar': '.jar',
	'src': '-sources.jar',
}


def generate(root_dir):
	print_banner()
	generate_defs(root_dir)
	generate_libraries(root_dir)
	run_buck_fetch()
	prepare_link_folder(root_dir)
	symlink_generated_srcs(root_dir)
	symlink_lib_jars(root_dir)
	symlink_output_jars(root_dir)
	generate_project(root_dir)


def print_banner():
	print('UP!')
	for s in definitions_sources:
		print(f'- {s.source_path}/DEER: *')


def run_buck_fetch():
	print('Fetching jar libraries')
	print(f'- buck fetch //lib/...')
	subprocess.check_output(['buck', 'fetch', '//lib/...'])


def generated_header():
	args = ' '.join([s.source_path for s in definitions_sources])
	return f'Generated using UP {args}'


def read_url(url):
	try:
		with urlopen(url) as r:
			return r.read().decode('utf-8').strip()
	except Exception as ex:
		print(f'Cannot download: {url}\n{ex}\nexiting...')
		exit()


def generate_libraries(root_dir):
	print('Generating jar libraries in //lib/BUCK')

	libs_content = f'''# {generated_header()}
'''

	for l in definitions_library:
		n, gav = l.name, l.maven_coords
		filename, repo_path = gav.filename(), gav.repo_path()

		print(f'- {l.source_path}/DEER: library_jar({n}, {gav.to_str()})')

		url_jar = f'{repo_url}{repo_path}.jar.sha1'
		sha1_jar = read_url(url_jar)
		print(f'\t{PurePath(url_jar).name} => {sha1_jar}')

		url_src = f'{repo_url}{repo_path}-sources.jar.sha1'
		sha1_src = read_url(url_src)
		print(f'\t{PurePath(url_src).name} => {sha1_src}')

		libs_content += f'''
# Generated from {l.source_path}/DEER:
# library_jar('{n}', '{gav.to_str()}'...
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

	(root_dir/'lib'/'BUCK').write_text(libs_content)


def prepare_link_folder(root_dir):
	link_dir = root_dir/'.link'
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
		content += f'\n  * `{l.maven_coords.to_str()}`'

	(link_dir/'readme.md').write_text(content)


def symlink_generated_srcs(root_dir):
	link_src = '.link/src'
	link_dir = root_dir/link_src

	print(f'Symlinking generated sources in {link_src}')

	for s in definitions_sources:
		if s.link_generated_srcs:
			print(f'- {s.source_path}/DEER: sources({s.name}, link_generated_srcs...)')

		for local_src_path in s.link_generated_srcs:
			path, goal = _get_path_and_goal(f'{s.path}/{local_src_path}'.lstrip('/'))
			full_path = f'{s.source_path}/{path}'
			target = root_dir/f'buck-out/annotation/{full_path}/__{goal}_gen__/{path}'

			mount = link_dir/path
			if not mount.parent.exists():
				mount.parent.mkdir(parents=True)
			mount.symlink_to(target, target_is_directory=True)
			print(f'\t{local_src_path} -> {link_src}/{path}')

def symlink_lib_jars(root_dir):
	link_jar = '.link/lib'
	link_dir = root_dir/link_jar
	path = 'lib'

	print(f'Symlinking library jars in {link_jar}')

	# we are not adding group to a filename unless
	# actual name colission happens
	already_linked_files = set()

	def symlink_lib_jar(library, kind):
		file_suffix = jar_suffixes[kind]
		goal = f'{library.name}_{kind}'
		filename = f'{library.maven_coords.filename()}{file_suffix}'
		target = root_dir/f'buck-out/gen/{path}/{goal}/{filename}'
		#full_path = f'{library.maven_coords.repo_path()}{file_suffix}'
		full_path = filename
		if filename in already_linked_files:
			full_path = f'{library.maven_coords.group}.{filename}'
		already_linked_files.add(full_path)

		mount = link_dir/full_path
		if not mount.parent.exists():
			mount.parent.mkdir(parents=True)
		mount.symlink_to(target, target_is_directory=False)
		print(f'\t{library.maven_coords.to_str()}:{kind} -> {link_jar}/{full_path}')

	for l in definitions_library:
		print(f'- `{l.source_path}/DEER: library_jar({l.name},...`')
		symlink_lib_jar(l, 'jar')
		symlink_lib_jar(l, 'src')


def symlink_output_jars(root_dir):
	link_jar = '.link/jar'
	link_dir = root_dir/link_jar

	print(f'Symlinking output jars for packages in {link_jar}')

	for s in definitions_sources:
		if s.link_output_jars:
			print(f'- {s.source_path}/DEER: sources({s.name}, link_output_jars...)')

		for local_jar_path in s.link_output_jars:
			path, goal = _get_path_and_goal(f'{s.path}/{local_jar_path}'.lstrip('/'))
			full_path = f'{s.source_path}/{path}'
			filename = f'{goal}.jar'
			target = root_dir/f'buck-out/gen/{full_path}/{filename}'

			mount = link_dir/path/filename
			if not mount.parent.exists():
				mount.parent.mkdir(parents=True)
			mount.symlink_to(target, target_is_directory = False)
			print(f'\t{local_jar_path} -> {link_jar}/{path}/{filename}')


def generate_defs(root_dir):
	print('Generating source variables in //lib/DEFS')
	# using '//' operator, then applying usual convention
	# of using goal as last segment if it's not specified
	# explicitly.

	defs_content = f'''# {generated_header()}
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

		for v in (root_dir/f'{d.source_path}/{d.path}').iterdir():
			print(f"\t{d.name}//'{v.name}'")

		defs_content += f'''
# Generated from {d.source_path}/DEER:
# sources('{d.name}'...
{d.name} = _GoalsPathVar('{d.source_path}', '{d.path}', alias = {d.alias})
'''

	(root_dir/'lib/DEFS').write_text(defs_content)


def generate_project(root_dir):
	generate_idea_libraries(root_dir)
	pass

def generate_idea_libraries(root_dir):
	ij_libraries = '.idea/libraries'
	libraries_dir = root_dir/ij_libraries

	print(f'Creating IJ libraries in {ij_libraries}')

	# we are not adding group to a filename unless
	# actual name colission happens
	# we replicate this logic in the same traversal order as
	# in linking lib jars
	already_linked_files = set()

	def symlink_lib_jar(library, kind):
		file_suffix = jar_suffixes[kind]
		goal = f'{library.name}_{kind}'
		filename = f'{library.maven_coords.filename()}{file_suffix}'
		target = root_dir/f'buck-out/gen/{path}/{goal}/{filename}'
		#full_path = f'{library.maven_coords.repo_path()}{file_suffix}'
		full_path = filename
		if filename in already_linked_files:
			full_path = f'{library.maven_coords.group}.{filename}'
		already_linked_files.add(full_path)

		mount = link_dir/full_path
		if not mount.parent.exists():
			mount.parent.mkdir(parents=True)
		mount.symlink_to(target, target_is_directory=False)
		print(f'\t{library.maven_coords.to_str()}:{kind} -> {link_jar}/{full_path}')

	for l in definitions_library:
		print(f'- `{l.source_path}/DEER: library_jar({l.name},...`')
		symlink_lib_jar(l, 'jar')
		symlink_lib_jar(l, 'src')

def _get_path_and_goal(path_goal):
	pg = path_goal.split(':')
	path = pg[0]
	goal = pg[1] if len(pg) == 2 else pg[0].split('/')[-1]
	return path, goal
