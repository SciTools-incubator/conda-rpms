import pytest

from conda_rpms.conda_compat import read_conda_lockfile

# def test_parse_url():
#     url = "https://conda.anaconda.org/conda-forge/linux-64/astropy-4.2.1-py37h27cfd23_1.tar.bz2"
#     pkg = parse_conda_url(url)
#     assert pkg.name == "astropy"
#     assert pkg.build == "py37h27cfd23_1"
#     assert pkg.format == "tar.bz2"
#     assert pkg.url == url

#     url = "https://conda.anaconda.org/conda-forge/linux-64/invalid-packagename.conda"
#     with pytest.raises(ValueError) as execinfo:
#         parse_conda_url(url)
#     assert "Cannot parse name" in str(execinfo.value)

#     url = "https://conda.anaconda.org/conda-forge/linux-64/invalid-package-format.zip"
#     with pytest.raises(ValueError) as execinfo:
#         parse_conda_url(url)
#     assert "file format" in str(execinfo.value)

# TODO: mock conda PackageCacheQuery instead of the parse_url above


def test_read_conda_lockfile():
    file = """# platform: linux-64
# env_hash: 2785ad92fa19c56df4d0b4315d6fea121ca9b6092185d5ea016d9571ef85efca
@EXPLICIT
https://conda.anaconda.org/conda-forge/linux-64/ca-certificates-2021.5.30-ha878542_0.tar.bz2#6a777890e94194dc94a29a76d2a7e721
https://conda.anaconda.org/conda-forge/noarch/font-ttf-dejavu-sans-mono-2.37-hab24e00_0.tar.bz2#0c96522c6bdaed4b1566d11387caaf45
https://conda.anaconda.org/conda-forge/noarch/font-ttf-inconsolata-3.000-h77eed37_0.tar.bz2#34893075a5c9e55cdafac56607368fc6
https://conda.anaconda.org/conda-forge/noarch/font-ttf-source-code-pro-2.038-h77eed37_0.tar.bz2#4d59c254e01d9cde7957100457e2d5fb
https://conda.anaconda.org/conda-forge/noarch/font-ttf-ubuntu-0.83-hab24e00_0.tar.bz2#19410c3df09dfb12d1206132a1d357c5
https://conda.anaconda.org/conda-forge/linux-64/ld_impl_linux-64-2.35.1-hea4e1c9_2.tar.bz2#83610dba766a186bdc7a116053b782a4
https://conda.anaconda.org/conda-forge/linux-64/libgfortran5-9.3.0-hff62375_19.tar.bz2#c2d8da3cb171e4aa642d20c6e4e42a04
https://conda.anaconda.org/conda-forge/linux-64/libstdcxx-ng-9.3.0-h6de172a_19.tar.bz2#cd9a24a8dde03ec0cf0e603b0bea85a1
https://conda.anaconda.org/conda-forge/linux-64/mpi-1.0-mpich.tar.bz2#c1fcff3417b5a22bbc4cf6e8c23648cf
https://conda.anaconda.org/conda-forge/linux-64/mysql-common-8.0.23-ha770c72_2.tar.bz2#ce876d0c998e1e2eb1dc67b01937737f
https://conda.anaconda.org/conda-forge/noarch/fonts-conda-forge-1-0.tar.bz2#f766549260d6815b0c52253f1fb1bb29
https://conda.anaconda.org/conda-forge/linux-64/libgfortran-ng-9.3.0-hff62375_19.tar.bz2#aea379bd68fdcdf9499fa1453f852ac1
https://conda.anaconda.org/conda-forge/linux-64/libgomp-9.3.0-h2828fa1_19.tar.bz2#ab0a307912033126da02507b59e79ec9""".split('\n')
    pkgs = read_conda_lockfile(file)
    assert len(pkgs) == 13
    assert pkgs[0].name == "ca-certificates"

