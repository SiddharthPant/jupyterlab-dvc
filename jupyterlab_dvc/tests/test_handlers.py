import json
import os
from unittest.mock import ANY, Mock, call, patch

import tornado

from jupyterlab_dvc.handlers import (
    GitAllHistoryHandler,
    GitBranchHandler,
    GitLogHandler,
    GitPushHandler,
    GitUpstreamHandler,
    setup_handlers,
)

from .testutils import ServerTest, assert_http_error


def test_mapping_added():
    mock_web_app = Mock()
    mock_web_app.settings = {"base_url": "nb_base_url"}
    setup_handlers(mock_web_app)

    mock_web_app.add_handlers.assert_called_once_with(".*", ANY)


class TestAllHistory(ServerTest):
    @patch("jupyterlab_dvc.handlers.GitAllHistoryHandler.git")
    def test_all_history_handler_localbranch(self, mock_git):
        # Given
        show_top_level = {"code": 0, "foo": "top_level"}
        branch = "branch_foo"
        log = "log_foo"
        status = "status_foo"

        mock_git.show_top_level.return_value = tornado.gen.maybe_future(show_top_level)
        mock_git.branch.return_value = tornado.gen.maybe_future(branch)
        mock_git.log.return_value = tornado.gen.maybe_future(log)
        mock_git.status.return_value = tornado.gen.maybe_future(status)

        # When
        body = {"current_path": "test_path", "history_count": 25}
        response = self.tester.post(["all_history"], body=body)

        # Then
        mock_git.show_top_level.assert_called_with("test_path")
        mock_git.branch.assert_called_with("test_path")
        mock_git.log.assert_called_with("test_path", 25)
        mock_git.status.assert_called_with("test_path")

        assert response.status_code == 200
        payload = response.json()
        assert payload == {
            "code": show_top_level["code"],
            "data": {
                "show_top_level": show_top_level,
                "branch": branch,
                "log": log,
                "status": status,
            },
        }


class TestBranch(ServerTest):
    @patch("jupyterlab_dvc.handlers.GitBranchHandler.git")
    def test_branch_handler_localbranch(self, mock_git):
        # Given
        branch = {
            "code": 0,
            "branches": [
                {
                    "is_current_branch": True,
                    "is_remote_branch": False,
                    "name": "feature-foo",
                    "upstream": "origin/feature-foo",
                    "top_commit": "abcdefghijklmnopqrstuvwxyz01234567890123",
                    "tag": None,
                },
                {
                    "is_current_branch": False,
                    "is_remote_branch": False,
                    "name": "master",
                    "upstream": "origin/master",
                    "top_commit": "abcdefghijklmnopqrstuvwxyz01234567890123",
                    "tag": None,
                },
                {
                    "is_current_branch": False,
                    "is_remote_branch": False,
                    "name": "feature-bar",
                    "upstream": None,
                    "top_commit": "01234567899999abcdefghijklmnopqrstuvwxyz",
                    "tag": None,
                },
                {
                    "is_current_branch": False,
                    "is_remote_branch": True,
                    "name": "origin/feature-foo",
                    "upstream": None,
                    "top_commit": "abcdefghijklmnopqrstuvwxyz01234567890123",
                    "tag": None,
                },
                {
                    "is_current_branch": False,
                    "is_remote_branch": True,
                    "name": "origin/master",
                    "upstream": None,
                    "top_commit": "abcdefghijklmnopqrstuvwxyz01234567890123",
                    "tag": None,
                },
            ],
        }

        mock_git.branch.return_value = tornado.gen.maybe_future(branch)

        # When
        body = {"current_path": "test_path"}
        response = self.tester.post(["branch"], body=body)

        # Then
        mock_git.branch.assert_called_with("test_path")

        assert response.status_code == 200
        payload = response.json()
        assert payload == {"code": 0, "branches": branch["branches"]}


class TestLog(ServerTest):
    @patch("jupyterlab_dvc.handlers.GitLogHandler.git")
    def test_log_handler(self, mock_git):
        # Given
        log = {"code": 0, "commits": []}
        mock_git.log.return_value = tornado.gen.maybe_future(log)

        # When
        body = {"current_path": "test_path", "history_count": 20}
        response = self.tester.post(["log"], body=body)

        # Then
        mock_git.log.assert_called_with("test_path", 20)

        assert response.status_code == 200
        payload = response.json()
        assert payload == log

    @patch("jupyterlab_dvc.handlers.GitLogHandler.git")
    def test_log_handler_no_history_count(self, mock_git):
        # Given
        log = {"code": 0, "commits": []}
        mock_git.log.return_value = tornado.gen.maybe_future(log)

        # When
        body = {"current_path": "test_path"}
        response = self.tester.post(["log"], body=body)

        # Then
        mock_git.log.assert_called_with("test_path", 25)

        assert response.status_code == 200
        payload = response.json()
        assert payload == log


class TestPush(ServerTest):
    @patch("jupyterlab_dvc.handlers.GitPushHandler.git")
    def test_push_handler_localbranch(self, mock_git):
        # Given
        mock_git.get_current_branch.return_value = tornado.gen.maybe_future("foo")
        mock_git.get_upstream_branch.return_value = tornado.gen.maybe_future(
            "localbranch"
        )
        mock_git.push.return_value = tornado.gen.maybe_future({"code": 0})

        # When
        body = {"current_path": "test_path"}
        response = self.tester.post(["push"], body=body)

        # Then
        mock_git.get_current_branch.assert_called_with("test_path")
        mock_git.get_upstream_branch.assert_called_with("test_path", "foo")
        mock_git.push.assert_called_with(".", "HEAD:localbranch", "test_path", None)

        assert response.status_code == 200
        payload = response.json()
        assert payload == {"code": 0}

    @patch("jupyterlab_dvc.handlers.GitPushHandler.git")
    def test_push_handler_remotebranch(self, mock_git):
        # Given
        mock_git.get_current_branch.return_value = tornado.gen.maybe_future("foo")
        mock_git.get_upstream_branch.return_value = tornado.gen.maybe_future(
            "origin/remotebranch"
        )
        mock_git.push.return_value = tornado.gen.maybe_future({"code": 0})

        # When
        body = {"current_path": "test_path"}
        response = self.tester.post(["push"], body=body)

        # Then
        mock_git.get_current_branch.assert_called_with("test_path")
        mock_git.get_upstream_branch.assert_called_with("test_path", "foo")
        mock_git.push.assert_called_with(
            "origin", "HEAD:remotebranch", "test_path", None
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload == {"code": 0}

    @patch("jupyterlab_dvc.handlers.GitPushHandler.git")
    def test_push_handler_noupstream(self, mock_git):
        # Given
        mock_git.get_current_branch.return_value = tornado.gen.maybe_future("foo")
        mock_git.get_upstream_branch.return_value = tornado.gen.maybe_future("")
        mock_git.push.return_value = tornado.gen.maybe_future({"code": 0})

        # When
        body = {"current_path": "test_path"}
        response = self.tester.post(["push"], body=body)

        # Then
        mock_git.get_current_branch.assert_called_with("test_path")
        mock_git.get_upstream_branch.assert_called_with("test_path", "foo")
        mock_git.push.assert_not_called()

        assert response.status_code == 200
        payload = response.json()
        assert payload == {
            "code": 128,
            "message": "fatal: The current branch foo has no upstream branch.",
        }


class TestUpstream(ServerTest):
    @patch("jupyterlab_dvc.handlers.GitUpstreamHandler.git")
    def test_upstream_handler_localbranch(self, mock_git):
        # Given
        mock_git.get_current_branch.return_value = tornado.gen.maybe_future("foo")
        mock_git.get_upstream_branch.return_value = tornado.gen.maybe_future("bar")

        # When
        body = {"current_path": "test_path"}
        response = self.tester.post(["upstream"], body=body)

        # Then
        mock_git.get_current_branch.assert_called_with("test_path")
        mock_git.get_upstream_branch.assert_called_with("test_path", "foo")

        assert response.status_code == 200
        payload = response.json()
        assert payload == {"upstream": "bar"}


class TestDiffContent(ServerTest):
    @patch("jupyterlab_dvc.git.execute")
    def test_diffcontent(self, mock_execute):
        # Given
        top_repo_path = "path/to/repo"
        filename = "my/file"
        content = "dummy content file\nwith multiple lines"

        mock_execute.side_effect = [
            tornado.gen.maybe_future((0, "1\t1\t{}".format(filename), "")),
            tornado.gen.maybe_future((0, content, "")),
            tornado.gen.maybe_future((0, "1\t1\t{}".format(filename), "")),
            tornado.gen.maybe_future((0, content, ""))
        ]

        # When
        body = {
            "filename": filename,
            "prev_ref": {"git": "previous"},
            "curr_ref": {"git": "current"},
            "top_repo_path": top_repo_path,
        }
        response = self.tester.post(["diffcontent"], body=body)

        # Then
        assert response.status_code == 200
        payload = response.json()
        assert payload["prev_content"] == content
        assert payload["curr_content"] == content
        mock_execute.assert_has_calls(
            [
                call(
                    ["git", "show", "{}:{}".format("previous", filename)],
                    cwd=os.path.join(self.notebook_dir, top_repo_path),
                ),
                call(
                    ["git", "show", "{}:{}".format("current", filename)],
                    cwd=os.path.join(self.notebook_dir, top_repo_path),
                )
            ],
            any_order=True
        )

    @patch("jupyterlab_dvc.git.execute")
    def test_diffcontent_working(self, mock_execute):
        # Given
        top_repo_path = "path/to/repo"
        filename = "my/file"
        content = "dummy content file\nwith multiple lines"

        mock_execute.side_effect = [
            tornado.gen.maybe_future((0, "1\t1\t{}".format(filename), "")),
            tornado.gen.maybe_future((0, content, "")),
            tornado.gen.maybe_future((0, content, ""))
        ]

        dummy_file = os.path.join(self.notebook_dir, top_repo_path, filename)
        os.makedirs(os.path.dirname(dummy_file))
        with open(dummy_file, "w") as f:
            f.write(content)

        # When
        body = {
            "filename": filename,
            "prev_ref": {"git": "previous"},
            "curr_ref": {"special": "WORKING"},
            "top_repo_path": top_repo_path,
        }
        response = self.tester.post(["diffcontent"], body=body)

        # Then
        assert response.status_code == 200
        payload = response.json()
        assert payload["prev_content"] == content
        assert payload["curr_content"] == content
        mock_execute.assert_has_calls(
            [
                call(
                    ["git", "show", "{}:{}".format("previous", filename)],
                    cwd=os.path.join(self.notebook_dir, top_repo_path),
                )
            ]
        )

    @patch("jupyterlab_dvc.git.execute")
    def test_diffcontent_index(self, mock_execute):
        # Given
        top_repo_path = "path/to/repo"
        filename = "my/file"
        content = "dummy content file\nwith multiple lines"

        mock_execute.side_effect = [
            tornado.gen.maybe_future((0, "1\t1\t{}".format(filename), "")),
            tornado.gen.maybe_future((0, content, "")),
            tornado.gen.maybe_future((0, "1\t1\t{}".format(filename), "")),
            tornado.gen.maybe_future((0, content, ""))
        ]

        # When
        body = {
            "filename": filename,
            "prev_ref": {"git": "previous"},
            "curr_ref": {"special": "INDEX"},
            "top_repo_path": top_repo_path,
        }
        response = self.tester.post(["diffcontent"], body=body)

        # Then
        assert response.status_code == 200
        payload = response.json()
        assert payload["prev_content"] == content
        assert payload["curr_content"] == content
        mock_execute.assert_has_calls(
            [
                call(
                    ["git", "show", "{}:{}".format("previous", filename)],
                    cwd=os.path.join(self.notebook_dir, top_repo_path),
                ),
                call(
                    ["git", "show", "{}:{}".format("", filename)],
                    cwd=os.path.join(self.notebook_dir, top_repo_path),
                )
            ],
            any_order=True
        )

    @patch("jupyterlab_dvc.git.execute")
    def test_diffcontent_unknown_special(self, mock_execute):
        # Given
        top_repo_path = "path/to/repo"
        filename = "my/file"
        content = "dummy content file\nwith multiple lines"

        mock_execute.side_effect = [
            tornado.gen.maybe_future((0, "1\t1\t{}".format(filename), "")),
            tornado.gen.maybe_future((0, content, "")),
            tornado.gen.maybe_future((0, "1\t1\t{}".format(filename), "")),
            tornado.gen.maybe_future((0, content, ""))
        ]

        # When
        body = {
            "filename": filename,
            "prev_ref": {"git": "previous"},
            "curr_ref": {"special": "unknown"},
            "top_repo_path": top_repo_path,
        }

        with assert_http_error(500, msg="unknown special ref"):
            self.tester.post(["diffcontent"], body=body)

    @patch("jupyterlab_dvc.git.execute")
    def test_diffcontent_show_handled_error(self, mock_execute):
        # Given
        top_repo_path = "path/to/repo"
        filename = "my/file"

        mock_execute.return_value = tornado.gen.maybe_future(
            (
                -1,
                "",
                "fatal: Path '{}' does not exist (neither on disk nor in the index)".format(
                    filename
                ),
            )
        )

        # When
        body = {
            "filename": filename,
            "prev_ref": {"git": "previous"},
            "curr_ref": {"git": "current"},
            "top_repo_path": top_repo_path,
        }
        response = self.tester.post(["diffcontent"], body=body)

        # Then
        assert response.status_code == 200
        payload = response.json()
        assert payload["prev_content"] == ""
        assert payload["curr_content"] == ""

    @patch("jupyterlab_dvc.git.execute")
    def test_diffcontent_binary(self, mock_execute):
        # Given
        top_repo_path = "path/to/repo"
        filename = "my/file"

        mock_execute.return_value = tornado.gen.maybe_future((0, "-\t-\t{}".format(filename), ""))

        # When
        body = {
            "filename": filename,
            "prev_ref": {"git": "previous"},
            "curr_ref": {"git": "current"},
            "top_repo_path": top_repo_path,
        }
        
        # Then
        with assert_http_error(500, msg="file is not UTF-8"):
            self.tester.post(["diffcontent"], body=body)

    @patch("jupyterlab_dvc.git.execute")
    def test_diffcontent_show_unhandled_error(self, mock_execute):
        # Given
        top_repo_path = "path/to/repo"
        filename = "my/file"

        mock_execute.return_value = tornado.gen.maybe_future((-1, "", "Dummy error"))

        # When
        body = {
            "filename": filename,
            "prev_ref": {"git": "previous"},
            "curr_ref": {"git": "current"},
            "top_repo_path": top_repo_path,
        }

        # Then
        with assert_http_error(500, msg="Dummy error"):
            self.tester.post(["diffcontent"], body=body)

    @patch("jupyterlab_dvc.git.execute")
    def test_diffcontent_getcontent_error(self, mock_execute):
        # Given
        top_repo_path = "path/to/repo"
        filename = "my/absent_file"
        content = "dummy content file\nwith multiple lines"

        mock_execute.side_effect = [
            tornado.gen.maybe_future((0, "1\t1\t{}".format(filename), "")),
            tornado.gen.maybe_future((0, content, "")),
            tornado.gen.maybe_future((0, content, ""))
        ]

        # When
        body = {
            "filename": filename,
            "prev_ref": {"git": "previous"},
            "curr_ref": {"special": "WORKING"},
            "top_repo_path": top_repo_path,
        }
        # Then
        with assert_http_error(404, msg="No such file or directory"):
            self.tester.post(["diffcontent"], body=body)
