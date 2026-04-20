"""Unit tests for sandbox_filesystem module."""

import tempfile
from pathlib import Path

import pytest
from genesis_core.sandbox_filesystem.sandbox_filesystem import LocalSandboxFilesystem
from genesis_core.schemas import SandboxFileInfo


class TestLocalSandboxFilesystem:
    """Tests for LocalSandboxFilesystem implementation."""

    @pytest.fixture
    def temp_sandbox(self):
        """Create a temporary sandbox directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def fs(self, temp_sandbox):
        """Create a LocalSandboxFilesystem instance."""
        return LocalSandboxFilesystem(temp_sandbox)

    # --- resolve_path tests ---

    def test_resolve_path_returns_absolute_path(self, fs, temp_sandbox):
        result = fs.resolve_path("some/file.txt")
        assert result.is_absolute()
        assert str(result).startswith(str(temp_sandbox))

    def test_resolve_path_handles_nested_paths(self, fs, temp_sandbox):
        result = fs.resolve_path("docs/papers/notes.txt")
        assert result == temp_sandbox / "docs/papers/notes.txt"

    def test_resolve_path_handles_root(self, fs, temp_sandbox):
        result = fs.resolve_path(".")
        assert result == temp_sandbox

    def test_resolve_path_prevents_traversal_attack(self, fs, temp_sandbox):
        with pytest.raises(ValueError, match="Traversal attempt detected"):
            fs.resolve_path("../../../etc/passwd")

    def test_resolve_path_prevents_absolute_path_escape(self, fs, temp_sandbox):
        with pytest.raises(ValueError, match="Traversal attempt detected"):
            fs.resolve_path("/etc/passwd")

    # --- write_file and read_file tests ---

    def test_write_file_creates_file(self, fs, temp_sandbox):
        content = b"Hello, World!"
        info = fs.write_file("test.txt", content)

        assert info.name == "test.txt"
        assert info.relative_path == "test.txt"
        assert info.is_dir is False
        assert info.size == len(content)
        assert info.mime_type == "text/plain"

    def test_write_file_creates_parent_directories(self, fs, temp_sandbox):
        fs.write_file("deep/nested/path/file.txt", b"content")

        assert (temp_sandbox / "deep/nested/path/file.txt").exists()

    def test_write_file_overwrites_existing(self, fs, temp_sandbox):
        fs.write_file("test.txt", b"original")
        info = fs.write_file("test.txt", b"updated")

        assert info.size == 7  # len("updated")
        content = fs.read_file("test.txt")
        assert content == b"updated"

    def test_read_file_returns_bytes(self, fs, temp_sandbox):
        fs.write_file("test.txt", b"Hello, World!")
        content = fs.read_file("test.txt")

        assert content == b"Hello, World!"

    def test_read_file_raises_on_nonexistent(self, fs, temp_sandbox):
        with pytest.raises(FileNotFoundError):
            fs.read_file("nonexistent.txt")

    def test_read_file_raises_on_directory(self, fs, temp_sandbox):
        fs.create_directory("mydir")
        with pytest.raises((FileNotFoundError, ValueError)):
            fs.read_file("mydir")

    # --- create_directory tests ---

    def test_create_directory_creates_dir(self, fs, temp_sandbox):
        info = fs.create_directory("mydir")

        assert info.name == "mydir"
        assert info.relative_path == "mydir"
        assert info.is_dir is True
        assert (temp_sandbox / "mydir").is_dir()

    def test_create_directory_creates_parent_dirs(self, fs, temp_sandbox):
        fs.create_directory("parent/child/grandchild")

        assert (temp_sandbox / "parent/child/grandchild").is_dir()

    def test_create_directory_can_overwrite_same_path(self, fs, temp_sandbox):
        # Should not raise since mkdir with exist_ok=True
        fs.create_directory("mydir")
        fs.create_directory("mydir")  # no-op, no exception

    # --- list_directory tests ---

    def test_list_directory_empty_at_root(self, fs, temp_sandbox):
        entries = fs.list_directory(".")
        assert entries == []

    def test_list_directory_lists_files_and_dirs(self, fs, temp_sandbox):
        fs.write_file("file1.txt", b"content1")
        fs.write_file("file2.txt", b"content2")
        fs.create_directory("subdir")

        entries = fs.list_directory(".")

        names = {e.name for e in entries}
        assert names == {"file1.txt", "file2.txt", "subdir"}

    def test_list_directory_includes_dir_flag(self, fs, temp_sandbox):
        fs.write_file("myfile.txt", b"content")
        fs.create_directory("mydir")

        entries = {e.name: e.is_dir for e in fs.list_directory(".")}
        assert entries["myfile.txt"] is False
        assert entries["mydir"] is True

    def test_list_directory_in_nested_folder(self, fs, temp_sandbox):
        fs.create_directory("docs")
        fs.write_file("docs/notes.txt", b"content")

        entries = fs.list_directory("docs")
        assert len(entries) == 1
        assert entries[0].name == "notes.txt"
        assert entries[0].relative_path == "docs/notes.txt"

    def test_list_directory_returns_empty_for_nonexistent(self, fs, temp_sandbox):
        entries = fs.list_directory("nonexistent")
        assert entries == []

    def test_list_directory_returns_empty_for_file(self, fs, temp_sandbox):
        fs.write_file("myfile.txt", b"content")
        entries = fs.list_directory("myfile.txt")
        assert entries == []

    # --- file_exists tests ---

    def test_file_exists_true_for_file(self, fs, temp_sandbox):
        fs.write_file("myfile.txt", b"content")
        assert fs.file_exists("myfile.txt") is True

    def test_file_exists_true_for_directory(self, fs, temp_sandbox):
        fs.create_directory("mydir")
        assert fs.file_exists("mydir") is True

    def test_file_exists_false_for_nonexistent(self, fs, temp_sandbox):
        assert fs.file_exists("nonexistent") is False

    def test_file_exists_false_for_traversal_attempt(self, fs, temp_sandbox):
        assert fs.file_exists("../etc/passwd") is False

    # --- get_file_info tests ---

    def test_get_file_info_returns_file_info(self, fs, temp_sandbox):
        fs.write_file("myfile.txt", b"Hello")
        info = fs.get_file_info("myfile.txt")

        assert info.name == "myfile.txt"
        assert info.relative_path == "myfile.txt"
        assert info.is_dir is False
        assert info.size == 5

    def test_get_file_info_returns_dir_info(self, fs, temp_sandbox):
        fs.create_directory("mydir")
        info = fs.get_file_info("mydir")

        assert info.name == "mydir"
        assert info.is_dir is True

    def test_get_file_info_raises_on_nonexistent(self, fs, temp_sandbox):
        with pytest.raises(FileNotFoundError):
            fs.get_file_info("nonexistent")

    # --- delete_file tests ---

    def test_delete_file_removes_file(self, fs, temp_sandbox):
        fs.write_file("myfile.txt", b"content")
        fs.delete_file("myfile.txt")

        assert not (temp_sandbox / "myfile.txt").exists()
        assert fs.file_exists("myfile.txt") is False

    def test_delete_file_raises_on_nonexistent(self, fs, temp_sandbox):
        with pytest.raises(FileNotFoundError):
            fs.delete_file("nonexistent.txt")

    def test_delete_file_raises_on_directory(self, fs, temp_sandbox):
        fs.create_directory("mydir")
        with pytest.raises(ValueError, match="directory"):
            fs.delete_file("mydir")

    # --- delete_directory tests ---

    def test_delete_directory_removes_empty_dir(self, fs, temp_sandbox):
        fs.create_directory("mydir")
        fs.delete_directory("mydir")

        assert not (temp_sandbox / "mydir").exists()

    def test_delete_directory_raises_on_nonexistent(self, fs, temp_sandbox):
        with pytest.raises(FileNotFoundError):
            fs.delete_directory("nonexistent")

    def test_delete_directory_raises_on_file(self, fs, temp_sandbox):
        fs.write_file("myfile.txt", b"content")
        with pytest.raises(ValueError, match="file"):
            fs.delete_directory("myfile.txt")

    def test_delete_directory_raises_on_nonempty_dir(self, fs, temp_sandbox):
        fs.create_directory("mydir")
        fs.write_file("mydir/file.txt", b"content")

        with pytest.raises(OSError):
            fs.delete_directory("mydir")

    # --- move_file tests ---

    def test_move_file_moves_file(self, fs, temp_sandbox):
        fs.write_file("source.txt", b"content")
        info = fs.move_file("source.txt", "dest.txt")

        assert not (temp_sandbox / "source.txt").exists()
        assert (temp_sandbox / "dest.txt").exists()
        assert info.relative_path == "dest.txt"
        assert info.name == "dest.txt"

    def test_move_file_to_subfolder(self, fs, temp_sandbox):
        fs.write_file("file.txt", b"content")
        fs.create_directory("subdir")
        info = fs.move_file("file.txt", "subdir/file.txt")

        assert not (temp_sandbox / "file.txt").exists()
        assert (temp_sandbox / "subdir" / "file.txt").exists()
        assert info.relative_path == "subdir/file.txt"

    def test_move_file_raises_on_nonexistent(self, fs, temp_sandbox):
        with pytest.raises(FileNotFoundError):
            fs.move_file("nonexistent.txt", "dest.txt")

    def test_move_file_prevents_traversal(self, fs, temp_sandbox):
        fs.write_file("file.txt", b"content")
        with pytest.raises(ValueError, match="Traversal attempt"):
            fs.move_file("file.txt", "../escape.txt")

    def test_move_file_rejects_directory(self, fs, temp_sandbox):
        fs.create_directory("mydir")
        with pytest.raises(ValueError, match="Directory move is not supported"):
            fs.move_file("mydir", "dest_dir")

    def test_move_file_raises_on_name_collision(self, fs, temp_sandbox):
        fs.write_file("file1.txt", b"content1")
        fs.write_file("file2.txt", b"content2")
        with pytest.raises(ValueError, match="Destination already exists"):
            fs.move_file("file1.txt", "file2.txt")

    # --- get_subdirectories tests ---

    def test_get_subdirectories_returns_immediate_children(self, fs, temp_sandbox):
        fs.create_directory("docs")
        fs.create_directory("data")
        fs.create_directory("deep/nested")

        subs = fs.get_subdirectories(".")
        assert set(subs) == {"docs", "data", "deep"}

    def test_get_subdirectories_for_nested_parent(self, fs, temp_sandbox):
        fs.create_directory("deep/nested/dir")

        subs = fs.get_subdirectories("deep")
        assert subs == ["deep/nested"]

    def test_get_subdirectories_empty_when_none_exist(self, fs, temp_sandbox):
        fs.write_file("myfile.txt", b"content")
        subs = fs.get_subdirectories(".")
        assert subs == []

    def test_get_subdirectories_returns_sorted(self, fs, temp_sandbox):
        fs.create_directory("zebra")
        fs.create_directory("alpha")
        fs.create_directory("middle")

        subs = fs.get_subdirectories(".")
        assert subs == ["alpha", "middle", "zebra"]

    def test_get_subdirectories_returns_empty_for_nonexistent_parent(self, fs, temp_sandbox):
        subs = fs.get_subdirectories("nonexistent")
        assert subs == []

    # --- mime_type tests ---

    def test_write_file_guesses_mime_type(self, fs, temp_sandbox):
        fs.write_file("document.pdf", b"%PDF-1.4 content")
        info = fs.get_file_info("document.pdf")
        assert info.mime_type == "application/pdf"

    def test_write_file_mime_type_for_markdown(self, fs, temp_sandbox):
        fs.write_file("readme.md", b"# Title")
        info = fs.get_file_info("readme.md")
        assert info.mime_type == "text/markdown"

    def test_write_file_mime_type_unknown_for_no_extension(self, fs, temp_sandbox):
        fs.write_file("README", b"content")
        info = fs.get_file_info("README")
        # mimetypes.guess_type returns None for files without extension
        assert info.mime_type is None

    def test_create_directory_mime_type_is_none(self, fs, temp_sandbox):
        fs.create_directory("mydir")
        info = fs.get_file_info("mydir")
        assert info.mime_type is None

    # --- path with special characters ---

    def test_handles_unicode_filename(self, fs, temp_sandbox):
        fs.write_file("文档.txt", b"chinese content")
        info = fs.get_file_info("文档.txt")

        assert info.name == "文档.txt"
        assert info.relative_path == "文档.txt"

    def test_handles_spaces_in_filename(self, fs, temp_sandbox):
        fs.write_file("my file.txt", b"content with spaces")
        info = fs.get_file_info("my file.txt")

        assert info.name == "my file.txt"
        assert info.relative_path == "my file.txt"

    def test_handles_directory_with_spaces(self, fs, temp_sandbox):
        fs.create_directory("my documents")
        fs.write_file("my documents/file.txt", b"content")

        entries = fs.list_directory("my documents")
        assert len(entries) == 1
        assert entries[0].name == "file.txt"


class TestSymlinkBehavior:
    """Tests for symlink handling in _resolve."""

    @pytest.fixture
    def temp_sandbox(self):
        """Create a temporary sandbox directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def fs(self, temp_sandbox):
        """Create a LocalSandboxFilesystem instance with symlinks allowed."""
        return LocalSandboxFilesystem(temp_sandbox, allow_symlinks_outside=True)

    @pytest.fixture
    def fs_no_symlinks_outside(self, temp_sandbox):
        """Create a LocalSandboxFilesystem instance with symlinks restricted."""
        return LocalSandboxFilesystem(temp_sandbox, allow_symlinks_outside=False)

    def test_resolve_does_not_follow_symlinks_within_sandbox(self, fs, temp_sandbox):
        """When a symlink is inside sandbox, _resolve returns the symlink path, not resolved target."""
        # Create a symlink inside sandbox pointing to a file inside sandbox
        target = temp_sandbox / "actual_dir" / "actual_file.txt"
        target.parent.mkdir(parents=True)
        target.write_text("content")

        symlink_path = temp_sandbox / "mylink"
        symlink_path.symlink_to(target, target_is_directory=False)

        result = fs.resolve_path("mylink")

        # Result should be the symlink itself (not resolved), so it starts with sandbox
        assert str(result).startswith(str(temp_sandbox))
        # And it should NOT be the resolved external path
        assert result != target

    def test_resolve_preserves_symlink_for_external_targets(self, fs, temp_sandbox):
        """When a symlink points outside sandbox, _resolve still returns symlink path when it's within sandbox."""
        # Create an external directory (outside sandbox)
        with tempfile.TemporaryDirectory() as external_dir:
            external_target = Path(external_dir) / "external_file.txt"
            external_target.write_text("external content")

            # Create symlink inside sandbox pointing to external file
            symlink_path = temp_sandbox / "external_link"
            symlink_path.symlink_to(external_target, target_is_directory=False)

            result = fs.resolve_path("external_link")

            # Result should be the symlink path (not the resolved external path)
            assert str(result).startswith(str(temp_sandbox))
            # The external path should not appear in result
            assert str(external_target) not in str(result)

    def test_resolve_allow_symlinks_outside_returns_resolved_external(self, fs, temp_sandbox):
        """When allow_symlinks_outside=True, resolve_path exposes the real external path for reading."""
        with tempfile.TemporaryDirectory() as external_dir:
            external_file = Path(external_dir) / "secret.txt"
            external_file.write_text("secret content")

            symlink_path = temp_sandbox / "secret_link"
            symlink_path.symlink_to(external_file, target_is_directory=False)

            # resolve_path should still return the symlink path (not resolved)
            result = fs.resolve_path("secret_link")
            assert result == symlink_path

            # But we should be able to read the file through the symlink
            content = fs.read_file("secret_link")
            assert content == b"secret content"

    def test_resolve_rejects_symlinks_outside_when_disabled(self, fs_no_symlinks_outside, temp_sandbox):
        """When allow_symlinks_outside=False, symlinks pointing outside sandbox raise ValueError."""
        with tempfile.TemporaryDirectory() as external_dir:
            external_file = Path(external_dir) / "secret.txt"
            external_file.write_text("content")

            symlink_path = temp_sandbox / "secret_link"
            symlink_path.symlink_to(external_file, target_is_directory=False)

            with pytest.raises(ValueError, match="Traversal attempt detected"):
                fs_no_symlinks_outside.resolve_path("secret_link")

    def test_get_subdirectories_works_with_symlinked_dir(self, fs, temp_sandbox):
        """get_subdirectories returns correct relative paths when inside a symlinked directory."""
        # Create external directory with subdirectories
        with tempfile.TemporaryDirectory() as external_dir:
            ext_docs = Path(external_dir) / "docs"
            ext_notes = Path(external_dir) / "notes"
            ext_docs.mkdir()
            ext_notes.mkdir()

            # Symlink external dir into sandbox
            symlink_path = temp_sandbox / "knowledge-base"
            symlink_path.symlink_to(external_dir, target_is_directory=True)

            # Get subdirectories of the symlinked directory
            subs = fs.get_subdirectories("knowledge-base")

            # Should return subdirectory names relative to sandbox root
            assert set(subs) == {"knowledge-base/docs", "knowledge-base/notes"}

    def test_list_directory_works_with_symlinked_dir(self, fs, temp_sandbox):
        """list_directory returns correct relative paths when listing a symlinked directory."""
        with tempfile.TemporaryDirectory() as external_dir:
            (Path(external_dir) / "file1.txt").write_text("content1")
            (Path(external_dir) / "file2.txt").write_text("content2")

            symlink_path = temp_sandbox / "data"
            symlink_path.symlink_to(external_dir, target_is_directory=True)

            entries = fs.list_directory("data")

            names = {e.name for e in entries}
            assert names == {"file1.txt", "file2.txt"}
            # Relative paths should be under the symlink name, not external path
            for e in entries:
                assert str(e.relative_path).startswith("data/")


class TestSandboxFileInfo:
    """Tests for the SandboxFileInfo dataclass."""

    def test_sandbox_file_info_creation(self):
        info = SandboxFileInfo(
            relative_path="docs/notes.txt",
            name="notes.txt",
            is_dir=False,
            size=1024,
            mime_type="text/plain",
        )

        assert info.relative_path == "docs/notes.txt"
        assert info.name == "notes.txt"
        assert info.is_dir is False
        assert info.size == 1024
        assert info.mime_type == "text/plain"
        assert info.mtime is None
        assert info.created_at is None

    def test_sandbox_file_info_dir_default(self):
        info = SandboxFileInfo(relative_path="mydir", name="mydir")
        # Default is_dir is False
        assert info.is_dir is False
        assert info.size is None
