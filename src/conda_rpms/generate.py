# documentation on the conda API
#   https://docs.conda.io/projects/conda/en/latest/api/index.html

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
import shutil
from pathlib import Path
import sys
from typing import List

import jinja2
import yaml

from .logger import log
from .conda_compat import (
    CondaPackage,
    CondaEnvironment,
    make_package_tarball,
    read_conda_lockfile,
    read_conda_environment_yml
)

# configure the installer to use the same version
# of python as the invoker of this routine
INSTALLER_VERSION = "{0}.{1}.{2}".format(*sys.version_info)


@dataclass
class PackageSpec:
    package: CondaPackage  # full name of the package
    spec: Path  # the path to a written RPM spec file
    tarball: Path  # the path the associated tar.bz2 tarball of files

@dataclass
class ModulefileConfig:
    prefix: Path = None # the path of where the modulefile will be written to
    modulefile: str = None # the contents of the modulefile that will be created
    default: str = None # the contents of the .version default file

_module_dir = Path(__file__).resolve().parent
install_script_path = _module_dir / "dist/install.py"
template_dir = _module_dir / "templates"

loader = jinja2.FileSystemLoader(template_dir)
env = jinja2.Environment(loader=loader)
pkg_spec_tmpl = env.get_template("pkg.spec.template")
env_spec_tmpl = env.get_template("env.spec.template")
installer_spec_tmpl = env.get_template("installer.spec.template")


def render_package_spec(pkg_dir: Path, rpm_namespace: str, install_prefix: Path) -> str:
    """Render a package RPM spec.

    This relies on the conda package cache having already
    downloaded and extracted the specific package and
    stored it in the local cache.

    Returns the rendered RPM spec as a string.
    """
    if not pkg_dir.exists():
        raise FileNotFoundError(f"Package dir {pkg_dir} does not exist.")

    with open(pkg_dir / "info/index.json", "r") as fh:
        pkginfo = json.load(fh)

    recipe_yaml = pkg_dir / "info/recipe/meta.yaml"
    if recipe_yaml.exists():
        with open(recipe_yaml, "r") as fh:
            meta = yaml.safe_load(fh)
    else:
        meta = {}

    return pkg_spec_tmpl.render(
        pkginfo=pkginfo,
        meta=meta,
        rpm_prefix=rpm_namespace,
        install_prefix=install_prefix,
    )


def write_spec(spec: str, filename: Path, overwrite=True) -> Path:
    if filename.exists():
        with open(filename, "r") as fh:
            existing_spec = fh.read()
            if spec == existing_spec:
                log.info(f"Spec {filename} already exists and is identical, continue.")
                return filename
            else:
                if overwrite:
                    log.warn(f"Spec {filename} will be overwritten.")
                else:
                    log.warn(f"Spec {filename} exists and is different. Abort!")
                    raise AttributeError(
                        "Spec differs from existing and overwrite=False"
                    )

    log.info(f"Writing spec {filename}")
    with open(filename, "w") as fh:
        fh.write(spec)
    return filename


def render_environment_spec(
    environment: CondaEnvironment,
    packages: List[CondaPackage],
    install_prefix: Path,
    rpm_namespace: str,
    modulefile_config: ModulefileConfig,
) -> str:
    return env_spec_tmpl.render(
        env=asdict(environment),
        pkgs=[p.id for p in packages],
        install_prefix=str(install_prefix),
        rpm_prefix=rpm_namespace,
        module=modulefile_config
    )


def write_package_rpm_spec(
    pkg: CondaPackage, outdir: Path, install_prefix: Path, rpm_namespace: str
) -> Path:
    pkg_dir = Path(pkg.extracted_package_dir)
    spec = render_package_spec(pkg_dir, rpm_namespace, install_prefix)
    spec_filename = "{namespace}-pkg-{id}.spec".format(
        namespace=rpm_namespace, id=pkg.id
    )
    return write_spec(spec, outdir / "SPECS" / spec_filename)


def write_environment_rpm_spec(
    environment: CondaEnvironment,
    packages: List[CondaPackage],
    outdir: Path,
    install_prefix: Path,
    rpm_namespace: str,
    modulefile_config: ModulefileConfig
) -> Path:
    """Write an environment RPM spec to disk.

    An environment spec consists of:

    1. Dependencies on all package RPMs that make up the environment.
    2. A dependency on the Installer package required to deploy the environment on the host.

    Writes an rpm .spec file to `outdir/SPECS`.
    """
    spec = render_environment_spec(environment, packages, install_prefix,
                                   rpm_namespace, modulefile_config)
    spec_filename = f"{rpm_namespace}-env-{environment.id}.spec"
    return write_spec(spec, outdir / "SPECS" / spec_filename)


def render_installer_rpm_spec(
    python_package: CondaPackage, install_prefix: Path, rpm_namespace: str
) -> str:
    return installer_spec_tmpl.render(
        install_prefix=install_prefix, rpm_prefix=rpm_namespace, pkg_info=python_package
    )


def write_installer_rpm_spec(
    python_package: CondaPackage, outdir: Path, install_prefix: Path, rpm_namespace: str
) -> Path:
    spec = render_installer_rpm_spec(python_package, install_prefix, rpm_namespace)
    spec_filename = f"{rpm_namespace}-installer.spec"
    return write_spec(spec, outdir / "SPECS" / spec_filename, overwrite=False)


def create_installer(
    py_ver: str, outdir: Path, install_prefix: Path, rpm_namespace: str
) -> PackageSpec:
    pkg = CondaPackage.from_url(f"python=={py_ver}")
    spec = write_installer_rpm_spec(pkg, outdir, install_prefix, rpm_namespace)
    tarball = make_package_tarball(pkg)
    shutil.copy(install_script_path, outdir / "SOURCES" / install_script_path.name)
    return PackageSpec(pkg, spec, tarball)


def create_rpm_spec(pkg, outdir, install_prefix, rpm_namespace):
    spec = write_package_rpm_spec(pkg, outdir, install_prefix, rpm_namespace)
    tarball = make_package_tarball(pkg)
    return PackageSpec(pkg.id, spec, tarball)


def get_modulefile_config(
        template, prefix, default_version_file, env, install_prefix
) -> ModulefileConfig:
    modulefile_config = ModulefileConfig(prefix=prefix)

    # Render the modulefile template 
    if template:
        template = Path(template)
        module_loader = jinja2.FileSystemLoader(template.parent)
        module_env = jinja2.Environment(loader=module_loader)
        module_template = module_env.get_template(template.name)
        modulefile_config.modulefile = module_template.render(env=env, install_prefix=install_prefix)

        # Load the modulefile default version file
        if default_version_file:
            with open(default_version_file) as fh:
                modulefile_config.default = fh.read()

    return modulefile_config


def environment_to_rpms(
    environment_yml: Path,
    lockfile: Path,
    outdir: Path,
    install_prefix: Path = Path("/opt/conda-dist"),
    rpm_namespace: str = "CondaDist",
    modulefile_template: Path = None,
    modulefile_prefix: Path = None,
    modulefile_default: Path = None
):
    """Take an explicit conda lock file and turn it into a set of RPMs."""
    config = outdir, install_prefix, rpm_namespace

    with open(lockfile, "r") as f:
        urls = read_conda_lockfile(f)

    sourcedir = outdir / "SOURCES"
    specdir = outdir / "SPECS"
    for directory in (outdir, sourcedir, specdir):
        directory.mkdir(exist_ok=True)

    log.info(f"Generating RPM environment from {lockfile}.")
    log.info(f"{len(urls)} packages to be rendered.")

    # Note that this requires all packages to be available in the cache.
    log.info(f"Checking conda cache for packages.")
    pkgs = [CondaPackage.from_url(url) for url in urls]

    log.info("Rendering all package specs.")
    specs: List[PackageSpec] = [create_rpm_spec(pkg, *config) for pkg in pkgs]

    log.info("Rendering installer")
    installer = create_installer(INSTALLER_VERSION, *config)
    specs.append(installer)

    log.info("Copying sources")
    for spec in specs:
        log.info("Coping %s to %s", spec.tarball, sourcedir / spec.tarball.name)
        shutil.copy(spec.tarball, sourcedir / spec.tarball.name)

    log.info("Rendering env spec.")
    with open(environment_yml, "r") as f:
        environment = read_conda_environment_yml(f)
    modulefile_config  = get_modulefile_config(modulefile_template,
                                               modulefile_prefix,
                                               modulefile_default,
                                               environment,
                                               install_prefix)
    write_environment_rpm_spec(environment,
                               pkgs,
                               outdir,
                               install_prefix,
                               rpm_namespace,
                               modulefile_config)


if __name__ == "__main__":
    import argparse
    from textwrap import dedent

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "environment_yml", help="The conda environment.yml to produce an RPM package for."
    )
    parser.add_argument(
        "lockfile", help="The conda lockfile to produce an RPM package for."
    )
    parser.add_argument(
        "--output",
        "-o",
        default="rpmbuild",
        help="The directory to write out the RPM spec files and sources. Default: rpmbuild",
    )
    parser.add_argument(
        "--rpm-namespace",
        default="CondaDist",
        help=dedent(
            r"""The namespace of the RPMs produced. e.g. a package will be named
            {rpm-namespace}-{package}.rpm"""
        ),
    )
    parser.add_argument(
        "--install-prefix",
        "-p",
        default="/opt/conda-dist",
        help=dedent(
            r"""The destination prefix where packages will be
            installed by the RPM.
            The environment will go to {install-prefix}/envs/{name}.
            Shared packages will go to {install-prefix}/pkgs/{package}"""
        ),
    )
    parser.add_argument(
        "--modulefile_template",
        default=None,
        help="The template for the modulefile that will be created."
    )
    parser.add_argument(
        "--modulefile_prefix",
        default="/opt/conda-dist/modulefiles",
        help="The destination prefix where modulefiles will be installed."
    )
    parser.add_argument(
        "--modulefile_default",
        default=None,
        help=dedent(
            r"""The .version file that sets the environment being created as
            the default environment."""
        ),
    )
    args = parser.parse_args()

    environment_to_rpms(
        Path(args.environment_yml),
        Path(args.lockfile),
        Path(args.output),
        Path(args.install_prefix),
        args.rpm_namespace,
        args.modulefile_template,
        args.modulefile_prefix,
        args.modulefile_default,
    )
