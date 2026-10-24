"""Preview server path boundary tests; no sockets or browser launch."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('orbit_serve',Path(__file__).resolve().parents[1]/'design/prototype/serve.py')
serve=importlib.util.module_from_spec(spec)
spec.loader.exec_module(serve)


class PreviewTests(unittest.TestCase):
    def test_scoped_design_files_and_queries(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve()
            self.assertTrue(serve.allowed_path(root,'/prototype/index.html?demo=1'))
            self.assertTrue(serve.allowed_path(root,'/assets/orbit-mark.svg'))

    def test_encoded_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve()
            self.assertFalse(serve.allowed_path(root,'/%2e%2e/private.txt'))
            self.assertFalse(serve.allowed_path(root,'/prototype/../../private.txt'))

    def test_symlink_rejected_even_within_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();(root/'file').touch();(root/'link').symlink_to(root/'file')
            self.assertFalse(serve.allowed_path(root,'/link'))
