ARG BASE_CONTAINER=jupyter/datascience-notebook:lab-2.0.1

FROM ${BASE_CONTAINER}

LABEL maintainer="Siddharth Pant <spsiddharthpant@gmail.com>"

RUN pip install git+git://github.com/jupyterlab/jupyterlab-git@master

RUN jupyter lab build

ARG SERVER_PASSWORD
ENV SERVER_PASSWORD ${SERVER_PASSWORD}
ARG LOGIN_TOKEN
ENV LOGIN_TOKEN ${LOGIN_TOKEN}

RUN echo "c.NotebookApp.token = ${LOGIN_TOKEN}" >> ~/.jupyter/jupyter_notebook_config.py
RUN echo "c.NotebookApp.password = ${SERVER_PASSWORD}" >> ~/.jupyter/jupyter_notebook_config.py
RUN echo "c.NotebookApp.allow_password_change = False" >> ~/.jupyter/jupyter_notebook_config.py

EXPOSE 8888