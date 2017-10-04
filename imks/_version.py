__all__ = (
    '__date__',
    '__version__',
    'version_info'
)

from pbr.version import VersionInfo

_v = VersionInfo('imks').semantic_version()
__version__ = _v.release_string()
version_info = _v.version_tuple()
__date__ = '2017'
