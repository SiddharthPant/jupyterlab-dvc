"""Initialize the backend server extension
"""
from jupyterlab_dvc.git import Git
from jupyterlab_dvc.handlers import setup_handlers

# need this in order to show version in `jupyter serverextension list`
from ._version import __version__


def _jupyter_server_extension_paths():
    """Declare the Jupyter server extension paths.
    """
    return [{"module": "jupyterlab_dvc"}]


def load_jupyter_server_extension(nbapp):
    """Load the Jupyter server extension.
    """
    git = Git(nbapp.web_app.settings['contents_manager'])
    nbapp.web_app.settings["dvc"] = git
    setup_handlers(nbapp.web_app)
