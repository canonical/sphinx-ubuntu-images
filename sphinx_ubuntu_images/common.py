"""Common utilities for the sphinx-ubuntu-images extension."""

from pathlib import Path
from typing import TYPE_CHECKING

from sphinx.util.fileutil import copy_asset_file

if TYPE_CHECKING:
    from sphinx.application import Sphinx


def copy_custom_files(app: "Sphinx", exc: Exception | None, filename: str) -> None:
    """Copy custom static files to the build output directory.

    This function is called after the build is finished to copy custom CSS/JS
    files to the output directory.
    """
    if not exc and app.builder.format == "html":
        staticfile = Path(app.builder.outdir) / "_static" / filename
        cssfile = Path(__file__).parent / "_static" / filename
        copy_asset_file(str(cssfile), str(staticfile))


def add_css(app: "Sphinx", filename: str) -> None:
    """Add a CSS file to the Sphinx application.

    This function registers the CSS file with Sphinx and ensures it's copied
    to the output directory after the build.
    """
    app.connect(  # pyright: ignore[reportUnknownMemberType]
        "build-finished",
        lambda app, exc: copy_custom_files(app, exc, filename),  # pyright: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    )
    app.add_css_file(filename)


def add_js(app: "Sphinx", filename: str) -> None:
    """Add a JavaScript file to the Sphinx application.

    This function registers the JS file with Sphinx and ensures it's copied
    to the output directory after the build.
    """
    app.connect(  # pyright: ignore[reportUnknownMemberType]
        "build-finished",
        lambda app, exc: copy_custom_files(app, exc, filename),  # pyright: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    )
    app.add_js_file(filename)
