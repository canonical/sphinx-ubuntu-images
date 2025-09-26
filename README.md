# sphinx-ubuntu-images

sphinx-ubuntu-images is a Sphinx extension that provides a custom directive to generate bulleted download lists of supported Ubuntu distro images for specific release ranges, suffixes, image-types, and architectures.

## Basic usage

To generate a list of Ubuntu images, add the `ubuntu-images` directive to your document:

```rst
.. ubuntu-images::
```

This will generate a bulleted list of all supported Ubuntu images with download links.

### Filtering options

The directive supports various filtering options:

#### Filter by release

```rst
.. ubuntu-images::
   :releases: jammy-
```

Examples of valid release values:

- `jammy` - Just the 22.04 release
- `jammy, noble` - Just the 22.04 and 24.04 releases
- `focal-noble` - All releases from 20.04 to 24.04
- `jammy-` - All releases from 22.04 onwards
- `-noble` - All releases up to 24.04

#### Filter by architecture

```rst
.. ubuntu-images::
   :archs: armhf, arm64
```

#### Filter by image type

```rst
.. ubuntu-images::
   :image-types: preinstalled-server
```

#### Filter by suffix

```rst
.. ubuntu-images::
   :suffix: +raspi
```

#### LTS releases only

```rst
.. ubuntu-images::
   :lts-only:
```

#### Handle empty results

```rst
.. ubuntu-images::
   :empty: No images available at this time
```

### Complete examples

All supported raspi images from jammy onwards:

```rst
.. ubuntu-images::
   :releases: jammy-
   :suffix: +raspi
```

All supported LTS armhf and arm64 images:

```rst
.. ubuntu-images::
   :archs: armhf, arm64
   :lts-only:
```

## Project setup

sphinx-ubuntu-images can be installed with:

```bash
pip install sphinx-ubuntu-images
```

After installation, update your Sphinx's conf.py file to include sphinx-ubuntu-images as one of its extensions:

```python
extensions = [
    "sphinx_ubuntu_images"
]
```

## Directive Options Reference

The `ubuntu-images` directive supports the following options:

- **`:releases:`** _releases (list of ranges)_ - A comma or space-separated list of partial dash-delimited release ranges (as release codenames). If unspecified, all releases will be included.

- **`:lts-only:`** _(no value)_ - If specified, only LTS releases will be included in the output. Interim releases are excluded.

- **`:image-types:`** _image types (list of strings)_ - Filter images by their "type". This is the string after the release version, and before the architecture. The list may be comma or space separated. If unspecified, all image types are included.

- **`:archs:`** _architectures (list of strings)_ - Filter images by their architecture. The list may be comma or space separated. If unspecified, all architectures are included.

- **`:suffix:`** _image +suffix (string)_ - Filter images by their (plus-prefixed) suffix. If unspecified, any suffix (including images with no suffix) will be included. If specified but blank, only images with no suffix will be included.

- **`:matches:`** _regular expression (string)_ - Filter images to those with filenames matching the specified regular expression. Use of this filter is discouraged; try using other filters first.

- **`:empty:`** _string_ - If no images match the specified filters, output the given string instead of reporting an error and failing the build. The string may be blank for no output.

## Advanced Usage

### Regular Expression Filtering

For complex filtering requirements, you can use regular expressions:

```rst
.. ubuntu-images::
   :matches: .*server.*arm64.*
   :empty: No ARM64 server images found
```

### Combining Multiple Filters

You can combine multiple filters for precise control:

```rst
.. ubuntu-images::
   :releases: focal-jammy
   :archs: arm64
   :image-types: preinstalled-server, live-server
   :suffix: +raspi
   :empty: No Raspberry Pi images found for the specified criteria
```

## Community and support

You can report any issues or bugs on the project's [GitHub
repository](https://github.com/canonical/sphinx-ubuntu-images).

sphinx-ubuntu-images is covered by the [Ubuntu Code of
Conduct](https://ubuntu.com/community/ethos/code-of-conduct).

## License and copyright

sphinx-ubuntu-images is released under the [GPL-3.0 license](LICENSE).

© 2025 Canonical Ltd.
