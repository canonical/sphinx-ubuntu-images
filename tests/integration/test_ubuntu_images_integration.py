"""Integration tests for the sphinx-ubuntu-images extension."""

import shutil
import subprocess
from pathlib import Path

import bs4
import pytest
from sphinx_ubuntu_images.ubuntu_images import (
    _make_index,  # pyright: ignore[reportPrivateUsage]
    _make_releases,  # pyright: ignore[reportPrivateUsage]
    _make_sums,  # pyright: ignore[reportPrivateUsage]
    _test_server,  # pyright: ignore[reportPrivateUsage]
)

# Images served by the fake cdimage site. Jammy is marked upgradable in the fake
# meta-release, so it always counts as supported, whatever today's date is.
FAKE_IMAGES = {
    "releases/jammy/release/ubuntu-22.04.5-live-server-amd64.iso": b"jammy" * 1024,
    "releases/noble/release/ubuntu-24.04-live-server-arm64.iso": b"noble" * 1024,
}


@pytest.fixture
def example_project(request) -> Path:
    """Create an example project directory for integration testing."""
    project_root = request.config.rootpath
    example_dir = project_root / "tests/integration/example"

    target_dir = Path().resolve() / "example"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(example_dir, target_dir, dirs_exist_ok=True)

    return target_dir


@pytest.fixture
def fake_site_options():
    """Serve fake changelogs and cdimage content on localhost.

    The build then doesn't depend on changelogs.ubuntu.com or cdimage.ubuntu.com
    being reachable. Yields the directive options that point at the fake site.
    """
    files = {**_make_releases(), **_make_index(_make_sums(FAKE_IMAGES))}
    with _test_server(files) as url:
        yield (
            f"   :meta-release: {url}meta-release\n"
            f"   :meta-release-development: {url}meta-release-development\n"
            f"   :cdimage-template: {url}releases/{{release.codename}}/release/\n"
        )


@pytest.mark.slow
def test_ubuntu_images_integration(example_project, fake_site_options):
    """Test that the ubuntu-images directive works end-to-end."""
    index_rst = example_project / "index.rst"
    index_rst.write_text(
        index_rst.read_text().replace(
            ".. ubuntu-images::\n", ".. ubuntu-images::\n" + fake_site_options
        )
    )
    build_dir = example_project / "_build"

    # Run sphinx-build to generate HTML
    try:
        subprocess.check_call(
            ["sphinx-build", "-b", "html", "-W", str(example_project), str(build_dir)],
        )
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Sphinx build failed: {e}")

    index = build_dir / "index.html"

    if not index.exists():
        pytest.fail("Generated index.html not found")

    # Rename the test output to something more meaningful for debugging
    output_dir = build_dir.parents[1] / ".test_output"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(build_dir, output_dir, dirs_exist_ok=True)

    # Parse the HTML output
    soup = bs4.BeautifulSoup(index.read_text(), features="lxml")

    # Clean up the example project
    if example_project.exists():
        shutil.rmtree(example_project)

    # The jammy image from the fake site should be listed as a download link
    links = [a.get_text() for a in soup.find_all("a")]
    if "ubuntu-22.04.5-live-server-amd64.iso" not in links:
        print("Generated HTML:")
        print(soup.prettify())
        pytest.fail("Expected the jammy image from the fake cdimage site")


@pytest.mark.slow
def test_ubuntu_images_with_empty_option(example_project, fake_site_options):
    """Test that the ubuntu-images directive handles the empty option correctly."""
    # Modify the example to use the empty option
    index_rst = example_project / "index.rst"
    content = index_rst.read_text()

    # Replace the entire directive block with one that has unlikely filters
    new_content = content.replace(
        ".. ubuntu-images::\n   :empty: No Ubuntu images available at this time",
        ".. ubuntu-images::\n"
        + fake_site_options
        + "   :releases: nonexistent-release\n"
        "   :empty: No images found for the specified criteria",
    )
    index_rst.write_text(new_content)

    build_dir = example_project / "_build"

    # Run sphinx-build
    try:
        subprocess.check_call(
            ["sphinx-build", "-b", "html", "-W", str(example_project), str(build_dir)],
        )
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Sphinx build failed: {e}")

    index = build_dir / "index.html"
    soup = bs4.BeautifulSoup(index.read_text(), features="lxml")

    # Clean up
    if example_project.exists():
        shutil.rmtree(example_project)

    # Should find the empty message
    emphasis_tags = soup.find_all("em")
    found_empty_message = any(
        "No images found" in em.get_text() for em in emphasis_tags
    )

    if not found_empty_message:
        print("Generated HTML:")
        print(soup.prettify())
        pytest.fail("Expected to find the empty message in the output")
