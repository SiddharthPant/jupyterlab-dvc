"""Setup Module to setup Python serverextension for the jupyterlab git
extension. For non-dev installs, will also automatically
build (if package.json is present) and install (if the labextension exists,
eg the build succeeded) the corresponding labextension.
"""
from pathlib import Path
from subprocess import CalledProcessError

from setupbase import (
    command_for_func, create_cmdclass, ensure_python,
    get_version, HERE, run
)

import setuptools

# The name of the project
name='jupyterlab_dvc'

# Ensure a valid python version
ensure_python('>=3.5')

# Get our version
version = get_version(str(Path(name) / '_version.py'))

lab_path = Path(HERE) / name / 'labextension'

data_files_spec = [
    ('share/jupyter/lab/extensions', str(lab_path), '*.tgz'),
    ('etc/jupyter/jupyter_notebook_config.d',
     'jupyter-config/jupyter_notebook_config.d', 'jupyterlab_dvc.json'),
]

def runPackLabextension():
    if Path('package.json').is_file():
        try:
            run(['jlpm', 'build:labextension'])
        except CalledProcessError:
            pass
pack_labext = command_for_func(runPackLabextension)

cmdclass = create_cmdclass('pack_labext', data_files_spec=data_files_spec)
cmdclass['pack_labext'] = pack_labext
cmdclass.pop('develop')

with open("README.md", "r") as fh:
    long_description = fh.read()

setup_args = dict(
    name            = name,
    description     = "A server extension for DVC",
    long_description= long_description,
    long_description_content_type="text/markdown",
    version         = version,
    cmdclass        = cmdclass,
    packages        = setuptools.find_packages(),
    author          = 'Siddharth Pant',
    url             = 'https://github.com/SiddharthPant/jupyterlab-dvc',
    license         = 'BSD',
    platforms       = "Linux, Mac OS X, Windows",
    keywords        = ['Jupyter', 'JupyterLab', 'Git'],
    classifiers     = [
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Framework :: Jupyter',
    ],
    install_requires = [
        'notebook',
        'nbdime ~=2.0',
        'pexpect'
    ],
    extras_require = {
        'test': [
            'pytest',
            'pytest-asyncio',
            'jupyterlab~=2.0',
        ],
    },
)

setuptools.setup(**setup_args)
