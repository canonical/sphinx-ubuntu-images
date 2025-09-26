"""Contains the core elements of the sphinx-ubuntu-images extension."""

from sphinx.application import Sphinx
from sphinx.util.typing import ExtensionMetadata

from sphinx_ubuntu_images.ubuntu_images import setup as ubuntu_images_setup

try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    from importlib.metadata import version, PackageNotFoundError

    try:
        __version__ = version("sphinx-ubuntu-images")
    except PackageNotFoundError:
        __version__ = "dev"


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the ubuntu-images directive."""
    return ubuntu_images_setup(app)


__all__ = ["__version__", "setup"]
