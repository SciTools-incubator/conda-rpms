FROM continuumio/miniconda3

SHELL ["/bin/bash", "-c"]

ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini


COPY ./dev-env.yml environment.yml
RUN conda env create --quiet -n conda-rpms-dev --file environment.yml

RUN echo "source activate conda-rpms-dev" > ~/.bashrc
ENV PATH /opt/conda/envs/conda-rpms-dev/bin:$PATH

COPY . /conda-rpms
WORKDIR /conda-rpms
RUN pip install -e .[test]

ENTRYPOINT ["/tini", "--"]