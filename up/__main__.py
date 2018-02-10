from .generate import generate
import os
import imp
import sys
from pathlib import Path

root_dir = Path(os.getcwd())

# We copy and then load files just to avoid littering with __pycache__|*.pyc.
def copy_and_load(work_path):
	deer_file = f'{work_path}/DEER'
	source_file = root_dir/deer_file
	copied_file = root_dir/'.out/.deer'/deer_file
	copied_file.parent.mkdir(parents=True, exist_ok=True)
	prefix_import_up = f"""# generated up script
from up import *
set_current_path('{work_path}')
"""
	copied_file.write_text(prefix_import_up + source_file.read_text())
	imp.load_source(source_file.name, str(copied_file))

def register_sources(paths):
	for p in paths:
		copy_and_load(p)

register_sources(sys.argv[1:])

generate(root_dir)
