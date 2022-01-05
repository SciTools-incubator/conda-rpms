from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Iterable, List, Optional
import yaml

from conda.api import PackageCacheData
from conda_package_handling.api import create as create_conda_tarball

from .logger import log

class SpecTarget:
    _ident = "__none__"
    _id_string = "UndefinedSpec"

    @property
    def id(self) -> str:
        return self._id_string.format(**asdict(self))


@dataclass
class CondaPackage(SpecTarget):
    # The subset of conda package information we require
    _ident = "pkg"
    _id_string = "{name}-{version}-{build}"
    name: str
    version: str
    build: str
    url: str
    package_tarball_full_path: str
    extracted_package_dir: str
    fn: str

    @classmethod
    def from_url(cls, url: str) -> CondaPackage:
        cached_pkgs = PackageCacheData.query_all(url)
        if not cached_pkgs:
            raise ValueError(f"No cache for {url}")
        if len(cached_pkgs) > 1:
            log.warn(f"Multiple cache records found for {url}, using the first.")
        return CondaPackage(
            *[getattr(cached_pkgs[0], f.name) for f in fields(CondaPackage)]
        )


@dataclass
class CondaEnvironment(SpecTarget):
    _ident = "env"
    _id_string = "{name}-{label}-{version}"
    name: str
    label: str
    tag: str
    version: str
    summary: Optional[str]


def read_conda_lockfile(lockfile: Iterable[str]) -> List[str]:
    """Returns a list of package urls included in conda lock file.

    The file must include an @EXPLICIT marker.
    """
    seen_explicit = False

    urls = []
    for line in lockfile:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line == "@EXPLICIT":
            seen_explicit = True
            continue
        urls.append(line)
    if not seen_explicit:
        raise ValueError("Provided lockfile does not include @EXPLICIT tag.")
    return urls


def read_conda_environment_yml(env_yml: Iterable[str]) -> CondaEnvironment:
    """Returns a CondaEnvironemnt instance using metadata from the 
    environment.yml file.

    """
    env = yaml.safe_load(env_yml)
    return CondaEnvironment(*env['name'].split('-'), env['meta']['released'],
                            env['meta']['version'], None)


def make_package_tarball(pkg: CondaPackage) -> Path:
    """Returns the path to a package's associated tar.bz2 tarball.

    If the conda package is in the .conda format, this function
    will also convert to the .tar.bz2 format and place it alongside
    the .conda package.

    Returns the path to the tarball on disk.
    """
    if not pkg.package_tarball_full_path.endswith(".tar.bz2"):
        # we need to deal with the new .conda file type.
        # Luckily, there is a library to do this so we will use it
        # to convert .conda files into .tar.bz2 files and save them
        # alongside the .conda and extracted package in the conda cache
        cache_dir = Path(pkg.extracted_package_dir).parent
        new_fn = pkg.fn.replace(".conda", ".tar.bz2")
        tarball = create_conda_tarball(
            pkg.extracted_package_dir, file_list=None, out_fn=str(cache_dir / new_fn)
        )
        log.info(f"Created tar.bz2 from {pkg.fn}")
    else:
        tarball = pkg.package_tarball_full_path
    return Path(tarball)
