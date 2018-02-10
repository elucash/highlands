
Highlands
=========

Template-like project automation on top of Facebook Buck build system. Main idea is to make possible both standalone development of the project and combined development of multiple projects using them as source folder (as submodule or just regular local repo inside ignored folder). Currently include some generation of project files for IJ Idea and Eclipse. `buck project` never worked well if ever, even if not broken it's not what we need.

### Usage

Working directory should be target project root, `<src>` are space separated relative location of source directories containing special `DEER` descriptor file.

```
python3 -m up <src>[ <src1>]...
```

In practice it might look like this.

```
PYTHONPATH=$this_repo_dir python3 -m up src lib/repo/src
```

This is to be invoked every time libraries or linked source projects added or they descriptors are changed. This will create project with specified source folders (for example, `src` and `lib/repo/src` like in the example above).

Each source folder must contain "bill of materials" file called `DEER`. The special file contains python-DSL to define external downloaded dependencies and information useful for creation of IDE projects.

### Path-goal variables

The system allows for developing a project as a single mono-repo combined from multiple source repos. Each such source folder should have `DEER` descriptor file. In order for interdependencies to work in both standalone and nested development to work, special path variables are created (in `//lib/DEFS`) and should be used to reference dependency goals inside and outside a source folder. For example if `DEER` file specifies `sources(name=highlands)`, we will have `highlands` object defined to be used to conveniently reference goals inside it as `highlands//'path/path2:goal'`. The convention is supported for omitting the goal if it's the same as last path segment.

### Connecting the dots

`.buckconfig` should have auto-included generated `lib/DEFS` file if goal aliases are to be used.

```toml
[buildfile]
	includes = //lib/DEFS
```

### Examples of DEER file

```python
# src/DEER
sources(
  # name of the source library, used as variable to resolve sub-libraries
	# like `highlands//'sample'`
	name = 'highlands',
	# additional prefix inside directory, this is mainly so that
	# we can have have `highlands//'sample'` and not `highlands//'highlands/sample'`
	# if empty, we will have the latter and this is ok too, in many cases
	path = '/highlands',
	# aliases are special ad-hoc aliases to `highlands//'<alias>'` to be resolved
	# to arbitrary targets
	alias = {
		'google/common': '//lib:guava',
		'immutables/value': '//lib:immutables',
		'immutables/value:annotations': '//lib:immutables_annotations'
	},
	# relative path (prepended with sources.path) to goals
	# which produce generated sources, so they will be symlinked to .link/src
	# for easy access in IDE configuration
	link_generated_srcs = [
		'sample'
	],
	# relative path (prepended with sources.path) to goals which produce
	# jar files to be symlinked to .link/jar for easy access for IDE project setup
	link_output_jars = [
		'sample:jar'
	],
)
# Dependency jar, to be referenced as //lib:<name> or can be added to alias, see above
# the downloaded remote files also symlinked to .link/lib for IDEs
library_jar('immutables', 'org.immutables:value:2.5.6')
library_jar('immutables_annotations', 'org.immutables:value:annotations:2.5.6')
library_jar('guava', 'com.google.guava:guava:22.0')
library_jar('junit', 'junit:junit:4.12')
```
