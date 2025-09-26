"""Unit tests for the sphinx-ubuntu-images extension."""

import datetime as dt
import re
from unittest.mock import Mock, patch

import pytest
from docutils import nodes
from sphinx_ubuntu_images.ubuntu_images import (
    Image,
    Release,
    UbuntuImagesDirective,
    filter_images,
    filter_releases,
    parse_set,
)


class TestParseSet:
    """Test the parse_set utility function."""

    def test_parse_comma_separated(self):
        """Test parsing comma-separated values."""
        result = parse_set("foo,bar,baz")
        assert result == {"foo", "bar", "baz"}

    def test_parse_space_separated(self):
        """Test parsing space-separated values."""
        result = parse_set("foo bar baz")
        assert result == {"foo", "bar", "baz"}

    def test_parse_mixed_separators(self):
        """Test parsing values with mixed separators."""
        result = parse_set("foo,bar baz")
        assert result == {"foo", "bar", "baz"}

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = parse_set("")
        assert result == set()


class TestRelease:
    """Test the Release named tuple."""

    def test_lts_release(self):
        """Test LTS release detection."""
        release = Release(
            codename="jammy",
            name="Jammy Jellyfish",
            version="22.04.5 LTS",
            date=dt.datetime(2022, 4, 21, 22, 4, 0),
            supported=True,
        )
        assert release.is_lts is True

    def test_non_lts_release(self):
        """Test non-LTS release detection."""
        release = Release(
            codename="disco",
            name="Disco Dingo",
            version="19.04",
            date=dt.datetime(2019, 4, 18, 19, 4, 0),
            supported=False,
        )
        assert release.is_lts is False


class TestImage:
    """Test the Image named tuple."""

    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing."""
        return Image(
            url="http://cdimage.ubuntu.com/releases/noble/release/ubuntu-24.04.1-preinstalled-desktop-arm64+raspi.img.xz",
            name="ubuntu-24.04.1-preinstalled-desktop-arm64+raspi.img.xz",
            date=dt.date(2024, 8, 27),
            sha256="5bd01d2a51196587b3fb2899a8f078a2a080278a83b3c8faa91f8daba750d00c",
        )

    def test_version_property(self, sample_image):
        """Test version extraction."""
        assert sample_image.version == "24.04.1"

    def test_image_type_property(self, sample_image):
        """Test image type extraction."""
        assert sample_image.image_type == "preinstalled-desktop"

    def test_arch_property(self, sample_image):
        """Test architecture extraction."""
        assert sample_image.arch == "arm64"

    def test_suffix_property(self, sample_image):
        """Test suffix extraction."""
        assert sample_image.suffix == "+raspi"

    def test_file_type_property(self, sample_image):
        """Test file type extraction."""
        assert sample_image.file_type == "img"

    def test_compression_property(self, sample_image):
        """Test compression extraction."""
        assert sample_image.compression == "xz"


class TestFilterReleases:
    """Test the filter_releases function."""

    @pytest.fixture
    def sample_releases(self):
        """Create sample releases for testing."""
        return [
            Release(
                "warty",
                "Warty Warthog",
                "04.10",
                dt.datetime(2004, 10, 20, 7, 28, 17),
                False,
            ),
            Release(
                "disco",
                "Disco Dingo",
                "19.04",
                dt.datetime(2019, 4, 18, 19, 4, 0),
                False,
            ),
            Release(
                "jammy",
                "Jammy Jellyfish",
                "22.04.5 LTS",
                dt.datetime(2022, 4, 21, 22, 4, 0),
                True,
            ),
        ]

    def test_filter_by_spec_single(self, sample_releases):
        """Test filtering by single release spec."""
        result = filter_releases(sample_releases, spec="disco")
        assert len(result) == 1
        assert result[0].codename == "disco"

    def test_filter_by_spec_multiple(self, sample_releases):
        """Test filtering by multiple release specs."""
        result = filter_releases(sample_releases, spec="warty,jammy")
        assert len(result) == 2
        assert {r.codename for r in result} == {"warty", "jammy"}

    def test_filter_by_spec_range(self, sample_releases):
        """Test filtering by release range."""
        result = filter_releases(sample_releases, spec="disco-")
        assert len(result) == 2
        assert {r.codename for r in result} == {"disco", "jammy"}

    def test_filter_by_lts(self, sample_releases):
        """Test filtering by LTS status."""
        result = filter_releases(sample_releases, lts=True)
        assert len(result) == 1
        assert result[0].codename == "jammy"

    def test_filter_by_supported(self, sample_releases):
        """Test filtering by supported status."""
        result = filter_releases(sample_releases, supported=True)
        assert len(result) == 1
        assert result[0].codename == "jammy"


class TestFilterImages:
    """Test the filter_images function."""

    @pytest.fixture
    def sample_images(self):
        """Create sample images for testing."""
        foo = b"foo" * 123456
        return [
            Image(
                "http://example.com/ubuntu-24.04.1-live-server-riscv64.img.gz",
                "ubuntu-24.04.1-live-server-riscv64.img.gz",
                dt.date(2024, 8, 27),
                "abcd1234" * 8,
            ),
            Image(
                "http://example.com/ubuntu-24.04.1-preinstalled-server-armhf+raspi.img.xz",
                "ubuntu-24.04.1-preinstalled-server-armhf+raspi.img.xz",
                dt.date(2024, 8, 27),
                "efgh5678" * 8,
            ),
            Image(
                "http://example.com/ubuntu-24.04.1-preinstalled-server-arm64+raspi.img.xz",
                "ubuntu-24.04.1-preinstalled-server-arm64+raspi.img.xz",
                dt.date(2024, 8, 27),
                "ijkl9012" * 8,
            ),
        ]

    def test_filter_by_archs(self, sample_images):
        """Test filtering by architectures."""
        result = filter_images(sample_images, archs={"armhf"})
        assert len(result) == 1
        assert result[0].arch == "armhf"

    def test_filter_by_image_types(self, sample_images):
        """Test filtering by image types."""
        result = filter_images(sample_images, image_types={"live-server"})
        assert len(result) == 1
        assert result[0].image_type == "live-server"

    def test_filter_by_suffix(self, sample_images):
        """Test filtering by suffix."""
        result = filter_images(sample_images, suffix="+raspi")
        assert len(result) == 2
        assert all("+raspi" in image.name for image in result)

    def test_filter_by_empty_suffix(self, sample_images):
        """Test filtering by empty suffix."""
        result = filter_images(sample_images, suffix="")
        assert len(result) == 1
        assert "+" not in result[0].name

    def test_filter_by_regex(self, sample_images):
        """Test filtering by regex pattern."""
        pattern = re.compile(r".*server.*")
        result = filter_images(sample_images, matches=pattern)
        assert len(result) == 3  # All have 'server' in the name


class TestUbuntuImagesDirective:
    """Test the UbuntuImagesDirective class."""

    @pytest.fixture
    def mock_directive(self):
        """Create a mock directive for testing."""
        directive = UbuntuImagesDirective(
            name="ubuntu-images",
            arguments=[],
            options={},
            content=[],
            lineno=1,
            content_offset=0,
            block_text="",
            state=Mock(),
            state_machine=Mock(),
        )
        return directive

    @patch("sphinx_ubuntu_images.ubuntu_images.get_releases")
    @patch("sphinx_ubuntu_images.ubuntu_images.get_images")
    def test_run_with_empty_option(
        self, mock_get_images, mock_get_releases, mock_directive
    ):
        """Test directive execution with empty option."""
        # Mock empty releases and images
        mock_get_releases.return_value = []
        mock_get_images.return_value = []

        # Set empty option
        mock_directive.options = {"empty": "No images available"}

        result = mock_directive.run()
        assert len(result) == 1
        assert isinstance(result[0], nodes.emphasis)
        assert result[0].astext() == "No images available"

    @patch("sphinx_ubuntu_images.ubuntu_images.get_releases")
    @patch("sphinx_ubuntu_images.ubuntu_images.get_images")
    def test_run_with_no_matches_raises_error(
        self, mock_get_images, mock_get_releases, mock_directive
    ):
        """Test directive execution with no matches raises ValueError."""
        # Mock empty releases and images
        mock_get_releases.return_value = []
        mock_get_images.return_value = []

        # No empty option set
        mock_directive.options = {}

        with pytest.raises(ValueError, match="no images found for specified filters"):
            mock_directive.run()
