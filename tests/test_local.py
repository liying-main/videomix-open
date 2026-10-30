import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from videomix import mix
from videomix.station import StationError


class LocalModeTests(unittest.TestCase):
    def test_local_mode_never_constructs_cloud_client(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True), \
                patch.object(mix, 'StationClient', side_effect=AssertionError('cloud called')), \
                patch.object(mix, 'build_video', return_value={'output': 'local.mp4'}) as build:
            mix.run_batch('offline', tmp, tmp, local_only=True, voice_ref='missing.wav')
            self.assertIsNone(build.call_args.args[0])
            self.assertFalse(build.call_args.kwargs['use_tts'])

    def test_fixed_script_without_tts_needs_no_key(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True), \
                patch.object(mix, 'StationClient', side_effect=AssertionError('cloud called')), \
                patch.object(mix, 'build_video', return_value={'output': 'local.mp4'}) as build:
            script = Path(tmp) / 'script.json'
            script.write_text(json.dumps({'shots': [{'seconds': 2}]}), encoding='utf-8')
            mix.run_batch('', tmp, tmp, script_file=str(script), use_tts=False)
            self.assertIsNone(build.call_args.args[0])
            self.assertEqual(build.call_args.kwargs['script']['shots'][0]['seconds'], 2)

    def test_cloud_mode_requires_key(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(StationError):
                mix.run_batch('cloud', tmp, tmp)


if __name__ == '__main__':
    unittest.main()
