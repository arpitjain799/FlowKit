# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Worked examples docker container
# Provides all worked examples from the FlowKit docs in a ready-to-go JupyterLab install
#

# Base image pinned due to https://github.com/Flowminder/FlowKit/issues/5374
FROM jupyter/scipy-notebook:2022-08-22

RUN rm -rf /home/$NB_USER/work
ARG SOURCE_VERSION=0+unknown
ENV SOURCE_VERSION=${SOURCE_VERSION}
ENV SOURCE_TREE=FlowKit-${SOURCE_VERSION}
COPY docs/source/analyst/worked_examples/*.ipynb /home/$NB_USER/
COPY docs/source/analyst/advanced_usage/worked_examples/*.ipynb /home/$NB_USER/
COPY flowmachine /${SOURCE_TREE}/flowmachine
COPY flowclient /${SOURCE_TREE}/flowclient
USER root
RUN cd /${SOURCE_TREE}/flowclient && python setup.py bdist_wheel && \
    cd /${SOURCE_TREE}/flowmachine && python setup.py bdist_wheel && \
    fix-permissions /${SOURCE_TREE}
USER $NB_UID
RUN pip install -q geopandas mapboxgl descartes \
    /${SOURCE_TREE}/flowclient/dist/*.whl \
    /${SOURCE_TREE}/flowmachine/dist/*.whl && \
    fix-permissions $CONDA_DIR && \
    fix-permissions /home/$NB_USER && \
    cd /home/$NB_USER/ && jupyter trust -y *
