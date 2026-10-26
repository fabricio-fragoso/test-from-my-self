import tempfile
import unittest
from unittest.mock import patch
from datetime import date
from pathlib import Path

from app import report_date, selected_period, rename_safely
from shop9 import Cancelled, STEPS, extract_period, validate_config


class Driver:
    def __init__(self, on_export=None):
        self.actions = []
        self.on_export = on_export

    def check_stop(self):
        pass

    def pause(self, seconds):
        pass

    def click(self, point):
        self.actions.append(('click', point))
        if point == 'exportar' and self.on_export:
            self.on_export(self.path)

    def fill(self, point, text):
        self.actions.append(('fill', point, text))
        if point == 'salvar':
            self.path = Path(text)


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.points = {key: key for key, _ in STEPS}
        self.logs = []

    def run_extraction(self, start, end, driver, reader):
        return extract_period(start, end, self.folder, self.points, driver,
                              reader, rename_safely, self.logs.append)

    def test_inclusive_period_exports_each_date_and_closes_windows(self):
        driver = Driver(lambda path: path.write_bytes(b'pdf-content'))
        def reader(path):
            self.assertEqual(path.read_bytes(), b'pdf-content')
            value = next(action[2] for action in reversed(driver.actions)
                         if action[:2] == ('fill', 'data'))
            return date(int(value[4:]), int(value[2:4]), int(value[:2]))
        self.assertEqual(self.run_extraction(date(2026, 8, 1), date(2026, 8, 2), driver, reader), (2, 0))
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()),
                         ['FECHAMENTO 01-08.pdf', 'FECHAMENTO 02-08.pdf'])
        self.assertEqual(driver.actions.count(('fill', 'caixa', '01')), 2)
        self.assertEqual(driver.actions.count(('click', 'fechar_exportacao')), 2)
        self.assertEqual(driver.actions.count(('click', 'fechar_previa')), 2)
        self.assertEqual(driver.actions.count(('click', 'financeiro')), 1)

    def test_existing_pdf_is_preserved_without_any_clicks(self):
        existing = self.folder / 'FECHAMENTO 01-08.pdf'
        existing.write_bytes(b'original')
        driver = Driver()
        self.assertEqual(self.run_extraction(date(2026, 8, 1), date(2026, 8, 1), driver, report_date), (0, 1))
        self.assertEqual(existing.read_bytes(), b'original')
        self.assertEqual(driver.actions, [])

    def test_wrong_year_stops_and_retains_temporary_pdf_for_review(self):
        driver = Driver(lambda path: path.write_bytes(b'wrong-date'))
        with self.assertRaisesRegex(RuntimeError, 'contém a data'):
            self.run_extraction(date(2026, 8, 1), date(2026, 8, 2), driver, lambda _: date(2025, 8, 1))
        self.assertFalse((self.folder / 'FECHAMENTO 01-08.pdf').exists())
        self.assertEqual(len(list(self.folder.glob('_shop9_*.pdf'))), 1)
        self.assertEqual(driver.actions.count(('click', 'imprimir')), 1)

    def test_export_dialog_may_close_itself(self):
        self.points['fechar_exportacao'] = None
        driver = Driver(lambda path: path.write_bytes(b'pdf-content'))
        self.run_extraction(date(2026, 8, 1), date(2026, 8, 1), driver, lambda _: date(2026, 8, 1))
        self.assertNotIn(('click', None), driver.actions)
        self.assertIn(('click', 'fechar_previa'), driver.actions)

    def test_cancel_prevents_navigation(self):
        class StoppedDriver(Driver):
            def pause(self, seconds):
                raise Cancelled('Parado')
        driver = StoppedDriver()
        with self.assertRaises(Cancelled):
            self.run_extraction(date(2026, 8, 1), date(2026, 8, 1), driver, report_date)
        self.assertEqual(driver.actions, [])

    def test_no_overwrite_if_destination_appears_during_export(self):
        destination = self.folder / 'FECHAMENTO 01-08.pdf'
        def export(path):
            path.write_bytes(b'new')
            destination.write_bytes(b'other')
        driver = Driver(export)
        with self.assertRaises(FileExistsError):
            self.run_extraction(date(2026, 8, 1), date(2026, 8, 1), driver, lambda _: date(2026, 8, 1))
        self.assertEqual(destination.read_bytes(), b'other')

    def test_invalid_periods_are_rejected(self):
        with self.assertRaises(ValueError):
            selected_period('29/02/2026', '01/03/2026')
        with self.assertRaises(ValueError):
            selected_period('02/08/2026', '01/08/2026')
        with self.assertRaises(ValueError):
            self.run_extraction(date(2025, 1, 1), date(2026, 1, 1), Driver(), report_date)

    def test_incomplete_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_config({'version': 1, 'points': {}})

    def test_missing_export_times_out_without_publishing(self):
        driver = Driver()
        with patch('shop9.time.monotonic', side_effect=[0, 61]):
            with self.assertRaisesRegex(RuntimeError, 'PDF não confirmado'):
                self.run_extraction(date(2026, 8, 1), date(2026, 8, 1), driver, report_date)
        self.assertFalse(list(self.folder.iterdir()))


if __name__ == '__main__':
    unittest.main()
