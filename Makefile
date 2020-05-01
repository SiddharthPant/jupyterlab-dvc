.PHONY: all help run_lab run_frontend

# target: all - With -j arg runs both watchers of backend and frontend
all: run_lab run_frontend


# target: help - Display callable targets.
help:
	@egrep "^# target:" [Mm]akefile

# target: run_lab - Runs jupyterlab in watch mode at localhost:8888
run_lab:
	jupyter lab --watch --notebook-dir=~/work

# target: run_frontend - Runs npm server in watch mode at localhost:3000
run_frontend:
	jlpm run watch