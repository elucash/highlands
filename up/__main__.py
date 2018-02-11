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
from .generate import generate
import os
import imp
import sys
import shutil
from pathlib import Path

root_dir = Path(os.getcwd())


# We copy and then load files just to avoid littering with __pycache__|*.pyc.
def copy_and_load(work_path):
    deer_file = f'{work_path}/DEER'
    source_file = root_dir/deer_file
    script_dir = root_dir/'.out/.deer'
    shutil.rmtree(str(script_dir), ignore_errors=True)
    copied_file = script_dir/deer_file
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
