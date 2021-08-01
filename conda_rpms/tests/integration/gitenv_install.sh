#!/usr/bin/env bash


REPO_ROOT=$(cd "$(dirname ${0})/../../.."; pwd;)

cat << 'EOF' | docker run -i \
                        -v ${REPO_ROOT}:/repo \
                        -a stdin -a stdout -a stderr \
                        centos:6 \
                        bash || exit ${?}


export MINICONDA_DIR=${HOME}/miniconda

echo "Install conda"
# ------------------
yum install -y wget
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh --no-verbose
bash Miniconda3-latest-Linux-x86_64.sh -b -p ${MINICONDA_DIR} && rm -f Miniconda*.sh

export PATH=${MINICONDA_DIR}/bin:${PATH}

conda config --set always_yes yes --set changeps1 no --set show_channel_urls yes


echo "Create an environment with the noarch packages `tqdm` and `xlrd`"
# ---------------------------------------------------------------------
# This will ensure that the noarch packages and all their dependencies are
# downloaded and in the cache.
TQDM_VERSION=4.19.8
XLRD_VERSION=2.0.1
conda create -n test-env -c conda-forge tqdm=${TQDM_VERSION} xlrd=${XLRD_VERSION} python=3.7
source activate test-env
conda uninstall tqdm
conda uninstall xlrd
source deactivate


echo "Check no tqdm or xlrd pyc files remain"
# -----------------------------------
if [ -d /root/miniconda/envs/test-env/lib/python3.7/site-packages/tqdm ]; then
    echo "The noarch packages tqdm was not successfully uninstalled."
    exit 1
fi
if [ -d /root/miniconda/envs/test-env/lib/python3.7/site-packages/xlrd ]; then
    echo "The noarch packages xlrd was not successfully uninstalled."
    exit 1
fi


echo "Create an env containing the python that will be used to run the installer"
# -------------------------------------------------------------------------------
conda create -n test-installer python
source activate test-installer


echo "Run the conda_rpms installer"
# ---------------------------------
# Get the name of the noarch_package, e.g. tqdm-4.19.8-py_0
noarch_tqdm=$(basename $(find ${MINICONDA_DIR}/pkgs -type d -name "tqdm-${TQDM_VERSION}-py*"))
echo ${noarch_tqdm}
python /repo/conda_rpms/install.py --pkgs-dir=${MINICONDA_DIR}/pkgs --prefix=${MINICONDA_DIR}/envs/test-env --link ${noarch_tqdm}

# Get the name of the noarch_package, e.g. xlrd-2.0.1-pyhd3eb1b0_0
noarch_xlrd=$(basename $(find ${MINICONDA_DIR}/pkgs -type d -name "xlrd-${xlrd_VERSION}-py*"))
echo ${noarch_xlrd}
python /repo/conda_rpms/install.py --pkgs-dir=${MINICONDA_DIR}/pkgs --prefix=${MINICONDA_DIR}/envs/test-env --link ${noarch_xlrd}



echo "Check that everything is there: tqdm"
# -----------------------------------------
source activate test-env

echo 'Check pyc files have been compiled:'
ls /root/miniconda/envs/test-env/lib/python3.6/site-packages/tqdm/*/*pyc

echo 'Check the noarch package imports'
python -c "import tqdm"

echo 'Check the entrypoint exists'
which tqdm


echo "Check that everything is there: xlrd"
# -----------------------------------------
echo 'Check pyc files have been compiled:'
ls /root/miniconda/envs/test-env/lib/python3.6/site-packages/xlrd/*/*pyc

echo 'Check the prefix in the shebang has been updated:'
sed -n '1{/^#!\/root\/miniconda\/envs\/test-env\/bin\/python/p};q' /root/miniconda/envs/test-env/bin/runxlrd.py

EOF

