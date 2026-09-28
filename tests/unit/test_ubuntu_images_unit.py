"""Unit tests for the sphinx-ubuntu-images extension."""

import datetime as dt
import re
from unittest.mock import Mock, patch

import pytest
from docutils import nodes
from docutils.statemachine import StringList
from sphinx_ubuntu_images.ubuntu_images import (
    Image,
    ImagesNotFoundError,
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
            date=dt.datetime(2022, 4, 21, 22, 4, 0, tzinfo=dt.timezone.utc),
            upgradable=True,
        )
        assert release.is_lts is True

    def test_non_lts_release(self):
        """Test non-LTS release detection."""
        release = Release(
            codename="disco",
            name="Disco Dingo",
            version="19.04",
            date=dt.datetime(2019, 4, 18, 19, 4, 0, tzinfo=dt.timezone.utc),
            upgradable=False,
        )
        assert release.is_lts is False

    def test_version_yymm(self):
        """Test version_yymm property."""
        release = Release(
            codename="jammy",
            name="Jammy Jellyfish",
            version="22.04.5 LTS",
            date=dt.datetime(2022, 4, 21, 22, 4, 0, tzinfo=dt.timezone.utc),
            upgradable=True,
        )
        assert release.version_yymm == "22.04"

    def test_supported_upgradable(self):
        """Test that an upgradable release is always supported."""
        release = Release(
            codename="jammy",
            name="Jammy Jellyfish",
            version="22.04.5 LTS",
            date=dt.datetime(2022, 4, 21, 22, 4, 0, tzinfo=dt.timezone.utc),
            upgradable=True,
        )
        assert release.supported is True

    def test_supported_eol_interim(self):
        """Test that an old interim release is not supported."""
        release = Release(
            codename="disco",
            name="Disco Dingo",
            version="19.04",
            date=dt.datetime(2019, 4, 18, 19, 4, 0, tzinfo=dt.timezone.utc),
            upgradable=False,
        )
        assert release.supported is False

    def test_supported_recent_lts(self):
        """Test that a recent LTS release (not yet upgradable) is still supported."""
        release = Release(
            codename="noble",
            name="Noble Numbat",
            version="24.04 LTS",
            date=dt.datetime(2024, 4, 25, 0, 24, 4, tzinfo=dt.timezone.utc),
            upgradable=False,
        )
        assert release.supported is True


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

    def test_flavor_property(self, sample_image):
        """Test flavor extraction."""
        assert sample_image.flavor == "ubuntu"

    def test_flavor_property_alternate_flavor(self):
        """Test flavor extraction for a non-default flavor."""
        image = Image(
            url="http://cdimage.ubuntu.com/xubuntu/releases/resolute/release/xubuntu-26.04-minimal-amd64.iso",
            name="xubuntu-26.04-minimal-amd64.iso",
            date=dt.date(2026, 8, 26),
            sha256="2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886c678605d1b7f",
        )
        assert image.flavor == "xubuntu"
        assert image.version == "26.04"
        assert image.image_type == "minimal"
        assert image.arch == "amd64"

    def test_flavor_property_multi_hyphen(self):
        """Test flavor extraction for multi-hyphen flavor prefixes."""
        image = Image(
            url="http://cdimage.ubuntu.com/releases/noble/release/ubuntu-mate-24.04-desktop-arm64+raspi.img.xz",
            name="ubuntu-mate-24.04-desktop-arm64+raspi.img.xz",
            date=dt.date(2024, 8, 27),
            sha256="5bd01d2a51196587b3fb2899a8f078a2a080278a83b3c8faa91f8daba750d00c",
        )
        assert image.flavor == "ubuntu-mate"
        assert image.version == "24.04"
        assert image.suffix == "+raspi"


class TestFilterReleases:
    """Test the filter_releases function."""

    @pytest.fixture
    def sample_releases(self):
        """Create sample releases for testing."""
        return [
            Release(
                codename="warty",
                name="Warty Warthog",
                version="04.10",
                date=dt.datetime(2004, 10, 20, 7, 28, 17, tzinfo=dt.timezone.utc),
                upgradable=False,
            ),
            Release(
                codename="disco",
                name="Disco Dingo",
                version="19.04",
                date=dt.datetime(2019, 4, 18, 19, 4, 0, tzinfo=dt.timezone.utc),
                upgradable=False,
            ),
            Release(
                codename="jammy",
                name="Jammy Jellyfish",
                version="22.04.5 LTS",
                date=dt.datetime(2022, 4, 21, 22, 4, 0, tzinfo=dt.timezone.utc),
                upgradable=True,
            ),
        ]

    def test_filter_by_spec_single(self, sample_releases):
        """Test filtering by single release spec."""
        result = filter_releases(sample_releases, spec="disco")
        assert len(result) == 1
        assert result[0].codename == "disco"

    def test_filter_by_spec_numeric(self, sample_releases):
        """Test filtering by numeric version spec."""
        result = filter_releases(sample_releases, spec="19.04")
        assert len(result) == 1
        assert result[0].codename == "disco"

    def test_filter_by_spec_numeric_range(self, sample_releases):
        """Test filtering by numeric version range."""
        result = filter_releases(sample_releases, spec="19.04-")
        assert len(result) == 2
        assert {r.codename for r in result} == {"disco", "jammy"}

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

    def test_filter_by_upgradable(self, sample_releases):
        """Test filtering by upgradable status."""
        result = filter_releases(sample_releases, upgradable=True)
        assert len(result) == 1
        assert result[0].codename == "jammy"


class TestFilterImages:
    """Test the filter_images function."""

    @pytest.fixture
    def sample_images(self):
        """Create sample images for testing."""
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
        """Test filtering by suffix set."""
        result = filter_images(sample_images, suffixes={"+raspi"})
        assert len(result) == 2
        assert all("+raspi" in image.name for image in result)

    def test_filter_by_empty_suffix(self, sample_images):
        """Test filtering by empty suffix (images with no suffix)."""
        result = filter_images(sample_images, suffixes={""})
        assert len(result) == 1
        assert "+" not in result[0].name

    def test_filter_by_multiple_suffixes(self, sample_images):
        """Test filtering by multiple suffixes."""
        result = filter_images(sample_images, suffixes={"+raspi", ""})
        assert len(result) == 3

    def test_filter_by_flavors(self, sample_images):
        """Test filtering by flavors."""
        result = filter_images(sample_images, flavors={"ubuntu"})
        assert len(result) == 3

    def test_filter_by_flavors_no_match(self, sample_images):
        """Test filtering by a flavor with no matching images."""
        result = filter_images(sample_images, flavors={"xubuntu"})
        assert result == []

    def test_filter_by_flavors_none_includes_all(self, sample_images):
        """Test that flavors=None includes images of any flavor."""
        assert list(filter_images(sample_images)) == list(sample_images)

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
        return UbuntuImagesDirective(
            name="ubuntu-images",
            arguments=[],
            options={},
            content=StringList([]),  # pyright: ignore[reportArgumentType]
            lineno=1,
            content_offset=0,
            block_text="",
            state=Mock(),
            state_machine=Mock(),
        )

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
    def test_run_with_no_matches_returns_error_node(
        self, mock_get_images, mock_get_releases, mock_directive
    ):
        """Test directive execution with no matches returns an error node."""
        # Mock empty releases and images
        mock_get_releases.return_value = []
        mock_get_images.return_value = []

        # No empty option set
        mock_directive.options = {}
        mock_directive.state.document.reporter.error = Mock(
            return_value=nodes.system_message()
        )

        result = mock_directive.run()
        assert len(result) == 1
        assert isinstance(result[0], nodes.system_message)
        mock_directive.state.document.reporter.error.assert_called_once_with(
            "no images found for specified filters", line=mock_directive.lineno
        )

    @patch("sphinx_ubuntu_images.ubuntu_images.get_releases")
    @patch("sphinx_ubuntu_images.ubuntu_images.get_images")
    def test_run_suffix_deprecated(
        self, mock_get_images, mock_get_releases, mock_directive
    ):
        """Test that :suffix: emits a deprecation warning."""
        mock_get_releases.return_value = []
        mock_get_images.return_value = []

        mock_directive.options = {"suffix": "+raspi", "empty": ""}
        mock_directive.state.document.reporter.warning = Mock(
            return_value=nodes.system_message()
        )

        result = mock_directive.run()
        mock_directive.state.document.reporter.warning.assert_called_once()
        # Warning about deprecation should be included in result
        assert any(isinstance(n, nodes.system_message) for n in result)

    @patch("sphinx_ubuntu_images.ubuntu_images.get_releases")
    @patch("sphinx_ubuntu_images.ubuntu_images.get_images")
    def test_run_suffix_and_suffixes_error(
        self, mock_get_images, mock_get_releases, mock_directive
    ):
        """Test that specifying both :suffix: and :suffixes: returns an error."""
        mock_get_releases.return_value = []
        mock_get_images.return_value = []

        mock_directive.options = {"suffix": "+raspi", "suffixes": {"+visionfive"}}
        mock_directive.state.document.reporter.warning = Mock(
            return_value=nodes.system_message()
        )
        mock_directive.state.document.reporter.error = Mock(
            return_value=nodes.system_message()
        )

        result = mock_directive.run()
        assert len(result) == 1
        mock_directive.state.document.reporter.error.assert_called_once_with(
            "cannot specify both :suffix: and :suffixes: options",
            line=mock_directive.lineno,
        )

    @patch("sphinx_ubuntu_images.ubuntu_images.get_releases")
    @patch("sphinx_ubuntu_images.ubuntu_images.get_images")
    def test_run_with_flavor(self, mock_get_images, mock_get_releases, mock_directive):
        """Test that :flavor: customizes heading, filtering and default URL."""
        mock_get_releases.return_value = [
            Release(
                codename="noble",
                name="Noble Numbat",
                version="24.04 LTS",
                date=dt.datetime(2024, 4, 25, tzinfo=dt.timezone.utc),
                upgradable=True,
            )
        ]
        mock_get_images.return_value = [
            Image(
                url="http://example.com/xubuntu-24.04-desktop-amd64.iso",
                name="xubuntu-24.04-desktop-amd64.iso",
                date=dt.date(2024, 4, 25),
                sha256="abcd1234" * 8,
            ),
            Image(
                url="http://example.com/ubuntu-24.04-desktop-amd64.iso",
                name="ubuntu-24.04-desktop-amd64.iso",
                date=dt.date(2024, 4, 25),
                sha256="efgh5678" * 8,
            ),
        ]
        mock_directive.options = {"flavor": "xubuntu"}

        result = mock_directive.run()

        assert len(result) == 1
        assert isinstance(result[0], nodes.bullet_list)
        # Heading uses the flavor title
        assert result[0][0][0].astext() == "Xubuntu 24.04 LTS (Noble Numbat) images:"
        # Only xubuntu images listed (flavors passed through to filter_images)
        image_items = result[0][0][1]
        assert [item.astext() for item in image_items.children] == [
            "xubuntu-24.04-desktop-amd64.iso"
        ]
        # Flavor-aware default cdimage URL used
        mock_get_images.assert_called_once_with(
            url="https://cdimage.ubuntu.com/xubuntu/releases/noble/release/",
            supported=True,
        )

    @patch("sphinx_ubuntu_images.ubuntu_images.get_releases")
    @patch("sphinx_ubuntu_images.ubuntu_images.get_images")
    def test_run_flavor_xubuntu_default_url(
        self, mock_get_images, mock_get_releases, mock_directive
    ):
        """Test that :flavor: changes the default cdimage URL."""
        mock_get_releases.return_value = [
            Release(
                codename="noble",
                name="Noble Numbat",
                version="24.04 LTS",
                date=dt.datetime(2024, 4, 25, tzinfo=dt.timezone.utc),
                upgradable=True,
            )
        ]
        mock_get_images.return_value = []
        mock_directive.options = {"flavor": "xubuntu", "empty": "none"}

        mock_directive.run()

        mock_get_images.assert_called_once_with(
            url="https://cdimage.ubuntu.com/xubuntu/releases/noble/release/",
            supported=True,
        )

    @patch("sphinx_ubuntu_images.ubuntu_images.get_releases")
    @patch("sphinx_ubuntu_images.ubuntu_images.get_images")
    def test_run_with_flavor_titles(
        self, mock_get_images, mock_get_releases, mock_directive
    ):
        """Test that headings use known flavor display titles."""
        mock_get_releases.return_value = [
            Release(
                codename="noble",
                name="Noble Numbat",
                version="24.04 LTS",
                date=dt.datetime(2024, 4, 25, tzinfo=dt.timezone.utc),
                upgradable=True,
            )
        ]
        mock_directive.options = {"flavor": "ubuntustudio"}
        mock_get_images.return_value = [
            Image(
                url="http://example.com/ubuntustudio-24.04-desktop-amd64.iso",
                name="ubuntustudio-24.04-desktop-amd64.iso",
                date=dt.date(2024, 4, 25),
                sha256="abcd1234" * 8,
            )
        ]

        result = mock_directive.run()

        assert result[0][0][0].astext() == (
            "Ubuntu Studio 24.04 LTS (Noble Numbat) images:"
        )

        mock_directive.options = {"flavor": "ubuntu-mate"}
        mock_get_images.return_value = [
            Image(
                url="http://example.com/ubuntu-mate-24.04-desktop-amd64.iso",
                name="ubuntu-mate-24.04-desktop-amd64.iso",
                date=dt.date(2024, 4, 25),
                sha256="efgh5678" * 8,
            )
        ]

        result = mock_directive.run()

        assert result[0][0][0].astext() == (
            "Ubuntu MATE 24.04 LTS (Noble Numbat) images:"
        )

    @patch("sphinx_ubuntu_images.ubuntu_images.get_releases")
    @patch("sphinx_ubuntu_images.ubuntu_images.get_images")
    def test_run_flavor_cdimage_template_override(
        self, mock_get_images, mock_get_releases, mock_directive
    ):
        """Test that explicit :cdimage-template: beats the flavor default."""
        mock_get_releases.return_value = [
            Release(
                codename="noble",
                name="Noble Numbat",
                version="24.04 LTS",
                date=dt.datetime(2024, 4, 25, tzinfo=dt.timezone.utc),
                upgradable=True,
            )
        ]
        mock_get_images.return_value = []
        mock_directive.options = {
            "flavor": "xubuntu",
            "cdimage-template": "https://example.com/{release.codename}/",
            "empty": "none",
        }

        mock_directive.run()

        mock_get_images.assert_called_once_with(
            url="https://example.com/noble/", supported=True
        )

    @patch("sphinx_ubuntu_images.ubuntu_images.get_releases")
    @patch("sphinx_ubuntu_images.ubuntu_images.get_images")
    def test_run_without_flavor_defaults_to_ubuntu(
        self, mock_get_images, mock_get_releases, mock_directive
    ):
        """Test that omitting :flavor: keeps current behavior unchanged."""
        mock_get_releases.return_value = [
            Release(
                codename="noble",
                name="Noble Numbat",
                version="24.04 LTS",
                date=dt.datetime(2024, 4, 25, tzinfo=dt.timezone.utc),
                upgradable=True,
            )
        ]
        mock_get_images.return_value = []
        mock_directive.options = {"empty": "none"}

        mock_directive.run()

        mock_get_images.assert_called_once_with(
            url="https://cdimage.ubuntu.com/releases/noble/release/",
            supported=True,
        )

    def test_flavor_option_empty_value(self):
        """Test that :flavor: with no value converts to an empty string."""
        assert (
            UbuntuImagesDirective.option_spec["flavor"](None)  # pyright: ignore[reportOptionalSubscript, reportArgumentType]
            == ""
        )
        assert (
            UbuntuImagesDirective.option_spec["flavor"](  # pyright: ignore[reportOptionalSubscript]
                " Xubuntu "
            )
            == "xubuntu"
        )

    @patch("sphinx_ubuntu_images.ubuntu_images.get_releases")
    @patch("sphinx_ubuntu_images.ubuntu_images.get_images")
    def test_run_with_empty_flavor_value(
        self, mock_get_images, mock_get_releases, mock_directive
    ):
        """Test that an empty :flavor: value falls back to the default."""
        mock_get_releases.return_value = [
            Release(
                codename="noble",
                name="Noble Numbat",
                version="24.04 LTS",
                date=dt.datetime(2024, 4, 25, tzinfo=dt.timezone.utc),
                upgradable=True,
            )
        ]
        mock_get_images.return_value = []
        mock_directive.options = {"flavor": "", "empty": "none"}

        mock_directive.run()

        mock_get_images.assert_called_once_with(
            url="https://cdimage.ubuntu.com/releases/noble/release/",
            supported=True,
        )

    @patch("sphinx_ubuntu_images.ubuntu_images.get_releases")
    @patch("sphinx_ubuntu_images.ubuntu_images.get_images")
    def test_run_flavor_skips_missing_release_dirs(
        self, mock_get_images, mock_get_releases, mock_directive
    ):
        """Test that releases missing from a flavor's tree are skipped."""
        mock_get_releases.return_value = [
            Release(
                codename="trusty",
                name="Trusty Tahr",
                version="14.04 LTS",
                date=dt.datetime(2014, 4, 17, tzinfo=dt.timezone.utc),
                upgradable=True,
            ),
            Release(
                codename="noble",
                name="Noble Numbat",
                version="24.04 LTS",
                date=dt.datetime(2024, 4, 25, tzinfo=dt.timezone.utc),
                upgradable=True,
            ),
        ]

        def get_images(url, supported):
            if "trusty" in url:
                raise ImagesNotFoundError(
                    f"unable to get {url}; are you sure the path is correct?"
                )
            return [
                Image(
                    url="http://example.com/xubuntu-24.04-desktop-amd64.iso",
                    name="xubuntu-24.04-desktop-amd64.iso",
                    date=dt.date(2024, 4, 25),
                    sha256="abcd1234" * 8,
                )
            ]

        mock_get_images.side_effect = get_images
        mock_directive.options = {"flavor": "xubuntu"}

        result = mock_directive.run()

        assert len(result) == 1
        assert result[0][0][0].astext() == "Xubuntu 24.04 LTS (Noble Numbat) images:"
        assert mock_get_images.call_count == 2

    @patch("sphinx_ubuntu_images.ubuntu_images.get_releases")
    @patch("sphinx_ubuntu_images.ubuntu_images.get_images")
    def test_run_flavor_explicit_template_missing_dir_raises(
        self, mock_get_images, mock_get_releases, mock_directive
    ):
        """Test that missing dirs stay fatal with an explicit template."""
        mock_get_releases.return_value = [
            Release(
                codename="noble",
                name="Noble Numbat",
                version="24.04 LTS",
                date=dt.datetime(2024, 4, 25, tzinfo=dt.timezone.utc),
                upgradable=True,
            )
        ]
        mock_get_images.side_effect = ImagesNotFoundError("unable to get")
        mock_directive.options = {
            "flavor": "xubuntu",
            "cdimage-template": "https://example.com/{release.codename}/",
        }

        with pytest.raises(ImagesNotFoundError):
            mock_directive.run()

    @patch("sphinx_ubuntu_images.ubuntu_images.get_releases")
    @patch("sphinx_ubuntu_images.ubuntu_images.get_images")
    def test_run_ubuntu_missing_dir_raises(
        self, mock_get_images, mock_get_releases, mock_directive
    ):
        """Test that missing dirs stay fatal for the default flavor."""
        mock_get_releases.return_value = [
            Release(
                codename="noble",
                name="Noble Numbat",
                version="24.04 LTS",
                date=dt.datetime(2024, 4, 25, tzinfo=dt.timezone.utc),
                upgradable=True,
            )
        ]
        mock_get_images.side_effect = ImagesNotFoundError("unable to get")
        mock_directive.options = {}

        with pytest.raises(ImagesNotFoundError):
            mock_directive.run()
