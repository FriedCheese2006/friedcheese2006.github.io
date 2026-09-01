import stat
import tempfile
import unittest
from pathlib import Path

from scripts.scan_assets import PUBLIC_FILE_MODE, copy_file


class ScanAssetsTestCase(unittest.TestCase):
    def test_copy_file_sets_owner_only_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.png"
            destination = Path(temp_dir) / "nested" / "destination.png"
            source.write_bytes(b"asset")

            copy_file(source, destination, existed=False)

            self.assertEqual(destination.read_bytes(), b"asset")
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), PUBLIC_FILE_MODE)


if __name__ == "__main__":
    unittest.main()