Create RPMs from a conda environment
===================================

conda-rpms is designed to convert a conda environment into a collection of RPM specs suitable for deployment on compatible platforms (Red Hat Enterprise Linux, Fedora, etc.).

Because a built RPM knows its destined installation location, a number of RPM abstractions have been made that enable us to retain conda's hard-linking and relocatability benefits.


Usage
=====

There is a single conda-rpms command entrypoint:

`python -m conda_rpms.generate` creates the RPM specs and sources.

`conda-rpms` no longer builds specs to RPMs, this is left to the user as may
require context-specific congfiguration.  However, typically it can be achieved
with something like the example below.
Assuming you have a [conda-lock](https://github.com/conda-incubator/conda-lock)
named `~/data_science.lock`:
```
# create the specs and copy source files to ./dist/SPECS and ./dist/SOURCES
python -m conda_rpms.generate ~/data_science.lock data_science.yml --output dist --modulefile_template modulefile.tmpl 
# build the RPMs to ./dist/RPMS
rpmbuild -bb --define "_topdir $(pwd)/dist"  dist/SPECS/*.spec
```

RPM Types
=========

Package RPM
-----------

RPM name format: ``<RPM namespace>-pkg-<pkg name>-<pkg version>-<pkg build id>``

A package RPM represents the conda "package cache" (the thing that normally lives in `<conda root prefix>/pkgs/<pkg name>-<pkg version>-<pkg build id>`).
A package RPM *does not* express its dependencies and can not be usefully installed as a standalone entity.

Environment RPM
---------------

RPM name format: ``<RPM namespace>-env-<env name>``

An environment RPM represents a resolved conda environment.
It depends on all Package RPMs that should be installed in order to produce a working environment. The environment RPM knows its target installation prefix, and uses conda functionality at install time to link the Package RPMs to the desired installation prefix.


Testing
=======

```pytest cov=conda_rpms tests/```
