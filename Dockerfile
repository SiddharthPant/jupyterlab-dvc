ARG BASE_CONTAINER=jupyter/datascience-notebook:lab-2.0.1

FROM ${BASE_CONTAINER}

LABEL maintainer="Siddharth Pant <spsiddharthpant@gmail.com>"

ARG SERVER_PASSWORD
ENV SERVER_PASSWORD ${SERVER_PASSWORD}
ARG LOGIN_TOKEN
ENV LOGIN_TOKEN ${LOGIN_TOKEN}

RUN echo "c.NotebookApp.token = ${LOGIN_TOKEN}" >> ~/.jupyter/jupyter_notebook_config.py
RUN echo "c.NotebookApp.password = ${SERVER_PASSWORD}" >> ~/.jupyter/jupyter_notebook_config.py
RUN echo "c.NotebookApp.allow_password_change = False" >> ~/.jupyter/jupyter_notebook_config.py

WORKDIR /usr/src/app

COPY dev-requirements.txt .
RUN pip install -r dev-requirements.txt

COPY . .
USER root
RUN chown -R ${NB_UID}:${NB_UID} .

USER ${NB_UID}
RUN ls -la
RUN pwd
RUN pip install -e .[test]
RUN jupyter serverextension enable --py jupyterlab_dvc
RUN jlpm build
RUN jupyter labextension link .

EXPOSE 8888