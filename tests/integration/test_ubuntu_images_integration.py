"""Integration tests for the sphinx-ubuntu-images extension."""

import shutil
import subprocess
from pathlib import Path

import bs4
import pytest


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


@pytest.mark.slow
def test_ubuntu_images_integration(example_project):
    """Test that the ubuntu-images directive works end-to-end."""
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

    # Look for the directive output - either image lists or empty message
    # The directive should either generate a bullet list of images or an emphasis with empty message
    bullet_lists = soup.find_all("ul")
    emphasis_tags = soup.find_all("em")

    # At least one of these should be present
    has_bullet_list = any("ubuntu-" in str(ul) for ul in bullet_lists)
    has_empty_message = any(
        "empty" in str(em).lower() or "available" in str(em).lower()
        for em in emphasis_tags
    )

    if not (has_bullet_list or has_empty_message):
        # For debugging, let's see what we actually got
        print("Generated HTML:")
        print(soup.prettify())
        pytest.fail(
            "Expected either Ubuntu image links or an empty message, but found neither"
        )


@pytest.mark.slow
def test_ubuntu_images_with_empty_option(example_project):
    """Test that the ubuntu-images directive handles the empty option correctly."""
    # Modify the example to use the empty option
    index_rst = example_project / "index.rst"
    content = index_rst.read_text()

    # Replace the entire directive block with one that has unlikely filters
    new_content = content.replace(
        ".. ubuntu-images::\n   :empty: No Ubuntu images available at this time",
        ".. ubuntu-images::\n   :releases: nonexistent-release\n   :empty: No images found for the specified criteria",
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
