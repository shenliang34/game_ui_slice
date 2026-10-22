import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/package_slices.py'
SPEC = importlib.util.spec_from_file_location('package_slices', SCRIPT)
PACKAGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGER)


class PackageSlicesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        image = Image.new('RGBA', (48, 48))
        ImageDraw.Draw(image).rectangle((8, 8, 39, 39), fill=(50, 150, 240, 200))
        image.save(self.root / 'sprite.png')
        self.plan = {
            'sources': {'art': {'path': 'sprite.png', 'size': [48, 48]}},
            'sprites': [{'path': 'icons/sprite.png', 'source': 'art', 'rect': [0, 0, 48, 48]}],
        }

    def run_plan(self, output='output'):
        path = self.root / 'plan.json'
        path.write_text(json.dumps(self.plan), encoding='utf8')
        with contextlib.redirect_stdout(io.StringIO()):
            PACKAGER.build(path, self.root / output)
        return self.root / output

    def assert_rejected_without_output(self):
        with self.assertRaises(ValueError):
            self.run_plan()
        self.assertFalse((self.root / 'output').exists())
        self.assertFalse((self.root / 'output.zip').exists())

    def test_package_preserves_pixels_and_zip_contents(self):
        output = self.run_plan()
        with Image.open(output / 'icons/sprite.png') as image:
            self.assertEqual(image.size, (48, 48))
            self.assertEqual(image.getpixel((10, 10)), (50, 150, 240, 200))
            self.assertEqual(image.getpixel((0, 0))[3], 0)
        with zipfile.ZipFile(self.root / 'output.zip') as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn('output/icons/sprite.png', archive.namelist())
            self.assertIn('output/slices.json', archive.namelist())

    def test_trim_and_padding_record_offsets(self):
        self.plan['sprites'][0].update(trim=True, padding=[1, 2, 3, 4])
        output = self.run_plan()
        report = json.loads((output / 'slices.json').read_text(encoding='utf8'))
        self.assertEqual(report['sprites'][0]['size'], [36, 38])
        self.assertEqual(report['sprites'][0]['trimOffset'], [8, 8])
        with Image.open(output / 'icons/sprite.png') as image:
            self.assertEqual(image.getpixel((1, 2)), (50, 150, 240, 200))

    def test_mask_multiplies_existing_alpha(self):
        Image.new('L', (48, 48), 128).save(self.root / 'mask.png')
        self.plan['sprites'][0]['mask'] = 'mask.png'
        output = self.run_plan()
        with Image.open(output / 'icons/sprite.png') as image:
            self.assertIn(image.getpixel((10, 10))[3], (100, 101))

    def test_wrong_source_dimensions(self):
        self.plan['sources']['art']['size'] = [47, 48]
        self.assert_rejected_without_output()

    def test_out_of_bounds_crop(self):
        self.plan['sprites'][0]['rect'] = [0, 0, 49, 48]
        self.assert_rejected_without_output()

    def test_output_traversal(self):
        self.plan['sprites'][0]['path'] = '../outside.png'
        self.assert_rejected_without_output()
        self.assertFalse((self.root / 'outside.png').exists())

    def test_case_insensitive_duplicate(self):
        other = dict(self.plan['sprites'][0], path='ICONS/SPRITE.PNG')
        self.plan['sprites'].append(other)
        self.assert_rejected_without_output()

    def test_opaque_sprite_rejected_but_background_allowed(self):
        Image.new('RGBA', (48, 48), 'navy').save(self.root / 'sprite.png')
        self.assert_rejected_without_output()
        self.plan['sprites'][0]['role'] = 'background'
        self.run_plan()

    def test_invalid_border(self):
        self.plan['sprites'][0]['border'] = {'left': 24, 'right': 24}
        self.assert_rejected_without_output()

    def test_existing_output_is_preserved(self):
        output = self.run_plan()
        before = (output / 'slices.json').read_bytes()
        with self.assertRaises(ValueError):
            self.run_plan()
        self.assertEqual((output / 'slices.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
