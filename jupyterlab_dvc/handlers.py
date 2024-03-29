"""
Module with all the individual handlers, which execute git commands and return the results to the frontend.
"""
import json
import os
from pathlib import Path

from notebook.base.handlers import APIHandler
from notebook.utils import url2path
from notebook.utils import url_path_join as ujoin
from tornado import web

from .git import DEFAULT_REMOTE_NAME


class GitHandler(APIHandler):
    """
    Top-level parent class.
    """

    @property
    def git(self):
        return self.settings["dvc"]


class GitCloneHandler(GitHandler):
    @web.authenticated
    async def post(self):
        """
        Handler for the `git clone`

        Input format:
            {
              'current_path': 'current_file_browser_path',
              'repo_url': 'https://github.com/path/to/myrepo',
              OPTIONAL 'auth': '{ 'username': '<username>',
                                  'password': '<password>'
                                }'
            }
        """
        data = self.get_json_body()
        response = await self.git.clone(
            data["current_path"], data["clone_url"], data.get("auth", None)
        )
        self.finish(json.dumps(response))


class GitAllHistoryHandler(GitHandler):
    """
    Parent handler for all four history/status git commands:
    1. git show_top_level
    2. git branch
    3. git log
    4. git status
    Called on refresh of extension's widget
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, calls individual handlers for
        'git show_top_level', 'git branch', 'git log', and 'git status'
        """
        body = self.get_json_body()
        current_path = body["current_path"]
        history_count = body["history_count"]

        show_top_level = await self.git.show_top_level(current_path)
        if show_top_level["code"] != 0:
            self.finish(json.dumps(show_top_level))
        else:
            branch = await self.git.branch(current_path)
            log = await self.git.log(current_path, history_count)
            status = await self.git.status(current_path)

            result = {
                "code": show_top_level["code"],
                "data": {
                    "show_top_level": show_top_level,
                    "branch": branch,
                    "log": log,
                    "status": status,
                },
            }
            self.finish(json.dumps(result))


class GitShowTopLevelHandler(GitHandler):
    """
    Handler for 'git rev-parse --show-toplevel'.
    Displays the git root directory inside a repository.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, displays the git root directory inside a repository.
        """
        current_path = self.get_json_body()["current_path"]
        result = await self.git.show_top_level(current_path)
        self.finish(json.dumps(result))


class GitShowPrefixHandler(GitHandler):
    """
    Handler for 'git rev-parse --show-prefix'.
    Displays the prefix path of a directory in a repository,
    with respect to the root directory.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, displays the prefix path of a directory in a repository,
        with respect to the root directory.
        """
        current_path = self.get_json_body()["current_path"]
        result = await self.git.show_prefix(current_path)
        self.finish(json.dumps(result))


class GitStatusHandler(GitHandler):
    """
    Handler for 'git status --porcelain', fetches the git status.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, fetches the git status.
        """
        current_path = self.get_json_body()["current_path"]
        result = await self.git.status(current_path)
        self.finish(json.dumps(result))


class GitLogHandler(GitHandler):
    """
    Handler for 'git log --pretty=format:%H-%an-%ar-%s'.
    Fetches Commit SHA, Author Name, Commit Date & Commit Message.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler,
        fetches Commit SHA, Author Name, Commit Date & Commit Message.
        """
        body = self.get_json_body()
        current_path = body["current_path"]
        history_count = body.get("history_count", 25)
        result = await self.git.log(current_path, history_count)
        self.finish(json.dumps(result))


class GitDetailedLogHandler(GitHandler):
    """
    Handler for 'git log -1 --stat --numstat --oneline' command.
    Fetches file names of committed files, Number of insertions &
    deletions in that commit.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, fetches file names of committed files, Number of
        insertions & deletions in that commit.
        """
        data = self.get_json_body()
        selected_hash = data["selected_hash"]
        current_path = data["current_path"]
        result = await self.git.detailed_log(selected_hash, current_path)
        self.finish(json.dumps(result))


class GitDiffHandler(GitHandler):
    """
    Handler for 'git diff --numstat'. Fetches changes between commits & working tree.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, fetches differences between commits & current working
        tree.
        """
        top_repo_path = self.get_json_body()["top_repo_path"]
        my_output = await self.git.diff(top_repo_path)
        self.finish(my_output)


class GitBranchHandler(GitHandler):
    """
    Handler for 'git branch -a'. Fetches list of all branches in current repository
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, fetches all branches in current repository.
        """
        current_path = self.get_json_body()["current_path"]
        result = await self.git.branch(current_path)
        self.finish(json.dumps(result))


class GitAddHandler(GitHandler):
    """
    Handler for git add <filename>'.
    Adds one or all files to the staging area.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, adds one or all files into the staging area.
        """
        data = self.get_json_body()
        top_repo_path = data["top_repo_path"]
        if data["add_all"]:
            body = await self.git.add_all(top_repo_path)
        else:
            filename = data["filename"]
            body = await self.git.add(filename, top_repo_path)

        if body["code"] != 0:
            self.set_status(500)
        self.finish(json.dumps(body))


class GitAddAllUnstagedHandler(GitHandler):
    """
    Handler for 'git add -u'. Adds ONLY all unstaged files, does not touch
    untracked or staged files.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, adds all the changed files.
        """
        body = await self.git.add_all_unstaged(self.get_json_body()["top_repo_path"])
        if body["code"] != 0:
            self.set_status(500)
        self.finish(json.dumps(body))


class GitAddAllUntrackedHandler(GitHandler):
    """
    Handler for 'echo "a\n*\nq\n" | git add -i'. Adds ONLY all
    untracked files, does not touch unstaged or staged files.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, adds all the untracked files.
        """
        body = await self.git.add_all_untracked(self.get_json_body()["top_repo_path"])
        if body["code"] != 0:
            self.set_status(500)
        self.finish(json.dumps(body))


class GitRemoteAddHandler(GitHandler):
    """Handler for 'git remote add <name> <url>'."""

    def post(self):
        """POST request handler to add a remote."""
        data = self.get_json_body()
        top_repo_path = data["top_repo_path"]
        name = data.get("name", DEFAULT_REMOTE_NAME)
        url = data["url"]
        output = self.git.remote_add(top_repo_path, url, name)
        if output["code"] == 0:
            self.set_status(201)
        else:
            self.set_status(500)
        self.finish(json.dumps(output))


class GitResetHandler(GitHandler):
    """
    Handler for 'git reset <filename>'.
    Moves one or all files from the staged to the unstaged area.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler,
        moves one or all files from the staged to the unstaged area.
        """
        data = self.get_json_body()
        top_repo_path = data["top_repo_path"]
        if data["reset_all"]:
            body = await self.git.reset_all(top_repo_path)
        else:
            filename = data["filename"]
            body = await self.git.reset(filename, top_repo_path)

        if body["code"] != 0:
            self.set_status(500)
        self.finish(json.dumps(body))


class GitDeleteCommitHandler(GitHandler):
    """
    Handler for 'git revert --no-commit <SHA>'.
    Deletes the specified commit from the repository, leaving history intact.
    """

    @web.authenticated
    async def post(self):
        data = self.get_json_body()
        top_repo_path = data["top_repo_path"]
        commit_id = data["commit_id"]
        body = await self.git.delete_commit(commit_id, top_repo_path)

        if body["code"] != 0:
            self.set_status(500)
        self.finish(json.dumps(body))


class GitResetToCommitHandler(GitHandler):
    """
    Handler for 'git reset --hard <SHA>'.
    Deletes all commits from head to the specified commit, making the specified commit the new head.
    """

    @web.authenticated
    async def post(self):
        data = self.get_json_body()
        top_repo_path = data["top_repo_path"]
        commit_id = data["commit_id"]
        body = await self.git.reset_to_commit(commit_id, top_repo_path)

        if body["code"] != 0:
            self.set_status(500)
        self.finish(json.dumps(body))


class GitCheckoutHandler(GitHandler):
    """
    Handler for 'git checkout <branchname>'. Changes the current working branch.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, changes between branches.
        """
        data = self.get_json_body()
        top_repo_path = data["top_repo_path"]
        if data["checkout_branch"]:
            if data["new_check"]:
                body = await self.git.checkout_new_branch(
                    data["branchname"], data["startpoint"], top_repo_path
                )
            else:
                body = await self.git.checkout_branch(data["branchname"], top_repo_path)
        elif data["checkout_all"]:
            body = await self.git.checkout_all(top_repo_path)
        else:
            body = await self.git.checkout(data["filename"], top_repo_path)

        if body["code"] != 0:
            self.set_status(500)
        self.finish(json.dumps(body))


class GitCommitHandler(GitHandler):
    """
    Handler for 'git commit -m <message>'. Commits files.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, commits files.
        """
        data = self.get_json_body()
        top_repo_path = data["top_repo_path"]
        commit_msg = data["commit_msg"]
        body = await self.git.commit(commit_msg, top_repo_path)

        if body["code"] != 0:
            self.set_status(500)
        self.finish(json.dumps(body))


class GitUpstreamHandler(GitHandler):
    @web.authenticated
    async def post(self):
        """
        Handler for the `git rev-parse --abbrev-ref $CURRENT_BRANCH_NAME@{upstream}` on the repo. Used to check if there
        is a upstream branch defined for the current Git repo (and a side-effect is disabling the Git push/pull actions)

        Input format:
            {
              'current_path': 'current_file_browser_path',
            }
        """
        current_path = self.get_json_body()["current_path"]
        current_branch = await self.git.get_current_branch(current_path)
        upstream = await self.git.get_upstream_branch(current_path, current_branch)
        self.finish(json.dumps({"upstream": upstream}))


class GitPullHandler(GitHandler):
    """
    Handler for 'git pull'. Pulls files from a remote branch.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, pulls files from a remote branch to your current branch.
        """
        data = self.get_json_body()
        response = await self.git.pull(
            data["current_path"],
            data.get("auth", None),
            data.get("cancel_on_conflict", False),
        )

        self.finish(json.dumps(response))


class GitPushHandler(GitHandler):
    """
    Handler for 'git push <first-branch> <second-branch>.
    Pushes committed files to a remote branch.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler,
        pushes committed files from your current branch to a remote branch
        """
        data = self.get_json_body()
        current_path = data["current_path"]

        current_local_branch = await self.git.get_current_branch(current_path)
        current_upstream_branch = await self.git.get_upstream_branch(
            current_path, current_local_branch
        )

        if current_upstream_branch and current_upstream_branch.strip():
            upstream = current_upstream_branch.split("/")
            if len(upstream) == 1:
                # If upstream is a local branch
                remote = "."
                branch = ":".join(["HEAD", upstream[0]])
            else:
                # If upstream is a remote branch
                remote = upstream[0]
                branch = ":".join(["HEAD", upstream[1]])

            response = await self.git.push(
                remote, branch, current_path, data.get("auth", None)
            )

        else:
            response = {
                "code": 128,
                "message": "fatal: The current branch {} has no upstream branch.".format(
                    current_local_branch
                ),
            }
        self.finish(json.dumps(response))


class GitInitHandler(GitHandler):
    """
    Handler for 'git init'. Initializes a repository.
    """

    @web.authenticated
    async def post(self):
        """
        POST request handler, initializes a repository.
        """
        current_path = self.get_json_body()["current_path"]
        body = await self.git.init(current_path)

        if body["code"] != 0:
            self.set_status(500)

        self.finish(json.dumps(body))


class GitChangedFilesHandler(GitHandler):
    @web.authenticated
    async def post(self):
        body = await self.git.changed_files(**self.get_json_body())
        self.finish(json.dumps(body))


class GitConfigHandler(GitHandler):
    """
    Handler for 'git config' commands
    """

    @web.authenticated
    async def post(self):
        """
        POST get (if no options are passed) or set configuration options
        """
        data = self.get_json_body()
        top_repo_path = data["path"]
        options = data.get("options", {})
        response = await self.git.config(top_repo_path, **options)

        if response["code"] != 0:
            self.set_status(500)
        else:
            self.set_status(201)
        self.finish(json.dumps(response))


class GitDiffContentHandler(GitHandler):
    """
    Handler for plain text diffs. Uses git show $REF:$FILE
    Returns `prev_content` and `curr_content` with content of given file.
    """

    @web.authenticated
    async def post(self):
        cm = self.contents_manager
        data = self.get_json_body()
        filename = data["filename"]
        prev_ref = data["prev_ref"]
        curr_ref = data["curr_ref"]
        top_repo_path = os.path.join(cm.root_dir, url2path(data["top_repo_path"]))
        response = await self.git.diff_content(
            filename, prev_ref, curr_ref, top_repo_path
        )
        self.finish(json.dumps(response))


class GitServerRootHandler(GitHandler):
    @web.authenticated
    async def get(self):
        # Similar to https://github.com/jupyter/nbdime/blob/master/nbdime/webapp/nb_server_extension.py#L90-L91
        root_dir = getattr(self.contents_manager, "root_dir", None)
        server_root = None if root_dir is None else Path(root_dir).as_posix()
        self.finish(json.dumps({"server_root": server_root}))


def setup_handlers(web_app):
    """
    Setups all of the git command handlers.
    Every handler is defined here, to be used in git.py file.
    """

    git_handlers = [
        ("/git/add", GitAddHandler),
        ("/git/add_all_unstaged", GitAddAllUnstagedHandler),
        ("/git/add_all_untracked", GitAddAllUntrackedHandler),
        ("/git/all_history", GitAllHistoryHandler),
        ("/git/branch", GitBranchHandler),
        ("/git/changed_files", GitChangedFilesHandler),
        ("/git/checkout", GitCheckoutHandler),
        ("/git/clone", GitCloneHandler),
        ("/git/commit", GitCommitHandler),
        ("/git/config", GitConfigHandler),
        ("/git/delete_commit", GitDeleteCommitHandler),
        ("/git/detailed_log", GitDetailedLogHandler),
        ("/git/diff", GitDiffHandler),
        ("/git/diffcontent", GitDiffContentHandler),
        ("/git/init", GitInitHandler),
        ("/git/log", GitLogHandler),
        ("/git/pull", GitPullHandler),
        ("/git/push", GitPushHandler),
        ("/git/remote/add", GitRemoteAddHandler),
        ("/git/reset", GitResetHandler),
        ("/git/reset_to_commit", GitResetToCommitHandler),
        ("/git/server_root", GitServerRootHandler),
        ("/git/show_prefix", GitShowPrefixHandler),
        ("/git/show_top_level", GitShowTopLevelHandler),
        ("/git/status", GitStatusHandler),
        ("/git/upstream", GitUpstreamHandler),
    ]

    # add the baseurl to our paths
    base_url = web_app.settings["base_url"]
    git_handlers = [(ujoin(base_url, x[0]), x[1]) for x in git_handlers]

    web_app.add_handlers(".*", git_handlers)
