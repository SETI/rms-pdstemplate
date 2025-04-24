##########################################################################################
# tests/test_pds3table.py
##########################################################################################

from contextlib import redirect_stdout
import io
import os
import pathlib
import re
import shutil
import sys
import tempfile
import time
import unittest

import pdslogger

from pdstemplate import PdsTemplate, get_logger, TemplateError
from pdstemplate.pds3table import (Pds3Table, VALIDATE_PDS3_LABEL,
                                   LABEL_VALUE, OLD_LABEL_VALUE, ANALYZE_TABLE,
                                   pds3_table_preprocessor, _latest_pds3_table)
from pdstemplate.asciitable import AsciiTable, _reset_ascii_table


class Test_Pds3Table(unittest.TestCase):

    def runTest(self):
        # Reset to starting point in case test_asciitable failed
        try:
            del PdsTemplate._PREDEFINED_FUNCTIONS['ANALYZE_TABLE']
        except KeyError:
            pass
        try:
            del PdsTemplate._PREDEFINED_FUNCTIONS['TABLE_VALUE']
        except KeyError:
            pass
        _reset_ascii_table()

        # No logging to stdout
        _LOGGER = get_logger()
        _LOGGER.add_handler(pdslogger.NULL_HANDLER)

        root_dir = pathlib.Path(sys.modules['pdstemplate'].__file__).parent.parent
        test_file_dir = root_dir / 'test_files'
        path = test_file_dir / 'COVIMS_0094_index.lbl'
        label = Pds3Table(path)

        self.assertRaisesRegex(TemplateError, r'No ASCII table has been.*',
                               label.assign_to)

        self.assertEqual(OLD_LABEL_VALUE('RECORD_TYPE'), 'FIXED_LENGTH')
        self.assertEqual(OLD_LABEL_VALUE('RECORD_BYTES'), 1089)
        self.assertEqual(OLD_LABEL_VALUE('FILE_RECORDS'), 1711)
        self.assertEqual(OLD_LABEL_VALUE('INTERCHANGE_FORMAT'), 'ASCII')
        self.assertEqual(OLD_LABEL_VALUE('ROWS'), 1711)
        self.assertEqual(OLD_LABEL_VALUE('COLUMNS'), 61)
        self.assertEqual(OLD_LABEL_VALUE('ROW_BYTES'), 1089)

        self.assertEqual(LABEL_VALUE('PATH'), str(path).replace('\\', '/'))
        self.assertEqual(LABEL_VALUE('BASENAME'), path.name)
        self.assertEqual(LABEL_VALUE('RECORD_TYPE'), 'FIXED_LENGTH')
        self.assertEqual(LABEL_VALUE('INTERCHANGE_FORMAT'), 'ASCII')
        self.assertEqual(LABEL_VALUE('TABLE_PATH'),
                         str(test_file_dir / 'COVIMS_0094_index.tab').replace('\\', '/'))
        self.assertEqual(LABEL_VALUE('TABLE_BASENAME'), 'COVIMS_0094_index.tab')

        ANALYZE_TABLE(_latest_pds3_table().get_table_path())

        self.assertEqual(LABEL_VALUE('RECORD_BYTES'), 1089)
        self.assertEqual(LABEL_VALUE('FILE_RECORDS'), 1711)
        self.assertEqual(LABEL_VALUE('ROWS'), 1711)
        self.assertEqual(LABEL_VALUE('COLUMNS'), 61)
        self.assertEqual(LABEL_VALUE('ROW_BYTES'), 1089)

        k = 1
        self.assertEqual(OLD_LABEL_VALUE('NAME', k), 'FILE_NAME')
        self.assertEqual(OLD_LABEL_VALUE('DATA_TYPE', k), 'CHARACTER')
        self.assertEqual(OLD_LABEL_VALUE('START_BYTE', k), 2)
        self.assertEqual(OLD_LABEL_VALUE('BYTES', k), 25)
        self.assertEqual(OLD_LABEL_VALUE('FORMAT', k), None)
        self.assertEqual(OLD_LABEL_VALUE('NOT_APPLICABLE_CONSTANT', k), None)
        self.assertEqual(OLD_LABEL_VALUE('COLUMN_NUMBER', k), None)

        self.assertEqual(LABEL_VALUE('NAME', k), 'FILE_NAME')
        self.assertEqual(LABEL_VALUE('DATA_TYPE', k), 'CHARACTER')
        self.assertEqual(LABEL_VALUE('START_BYTE', k), 2)
        self.assertEqual(LABEL_VALUE('BYTES', k), 25)
        self.assertEqual(LABEL_VALUE('FORMAT', k), 'A25')
        self.assertEqual(LABEL_VALUE('NOT_APPLICABLE_CONSTANT', k), None)
        self.assertEqual(LABEL_VALUE('COLUMN_NUMBER', k), 1)

        k = 'CENTRAL_BODY_DISTANCE'
        self.assertEqual(OLD_LABEL_VALUE('NAME', k), 'CENTRAL_BODY_DISTANCE')
        self.assertEqual(OLD_LABEL_VALUE('DATA_TYPE', k), 'ASCII_REAL')
        self.assertEqual(OLD_LABEL_VALUE('START_BYTE', k), 388)
        self.assertEqual(OLD_LABEL_VALUE('BYTES', k), 14)
        self.assertEqual(OLD_LABEL_VALUE('FORMAT', k), 'E14')
        self.assertEqual(OLD_LABEL_VALUE('NOT_APPLICABLE_CONSTANT', k), -1.e32)
        self.assertEqual(OLD_LABEL_VALUE('NULL_CONSTANT', k), 1.e32)
        self.assertEqual(OLD_LABEL_VALUE('COLUMN_NUMBER', k), None)

        self.assertEqual(LABEL_VALUE('NAME', k), 'CENTRAL_BODY_DISTANCE')
        self.assertEqual(LABEL_VALUE('DATA_TYPE', k), 'ASCII_REAL')
        self.assertEqual(LABEL_VALUE('START_BYTE', k), 388)
        self.assertEqual(LABEL_VALUE('BYTES', k), 14)
        self.assertEqual(LABEL_VALUE('FORMAT', k), 'E14.0')
        self.assertEqual(LABEL_VALUE('NOT_APPLICABLE_CONSTANT', k), -1.e32)
        self.assertEqual(LABEL_VALUE('NULL_CONSTANT', k), 1.e32)
        self.assertEqual(LABEL_VALUE('COLUMN_NUMBER', k), 24)
        self.assertEqual(LABEL_VALUE('MINIMUM_VALUE', k), 1.e32)
        self.assertEqual(LABEL_VALUE('MAXIMUM_VALUE', k), 1e+32)

        # Validation, edits
        warns = label._validation_warnings()
        answer = ['SWATH_WIDTH:DATA_TYPE error: INTEGER -> ASCII_INTEGER',
                  'SWATH_LENGTH:DATA_TYPE error: INTEGER -> ASCII_INTEGER',
                  'IR_EXPOSURE:DATA_TYPE error: REAL -> ASCII_REAL',
                  'VIS_EXPOSURE:DATA_TYPE error: REAL -> ASCII_REAL',
                  'CENTRAL_BODY_DISTANCE:FORMAT error: E14 -> "E14.0"',
                  'MAXIMUM_RING_RADIUS:FORMAT error: E14 -> "E14.0"',
                  'MINIMUM_RING_RADIUS:FORMAT error: E14 -> "E14.0"',
                  'TARGET_DISTANCE:FORMAT error: E14 -> "E14.0"']
        self.assertEqual(warns, answer)

        label = Pds3Table(path, edits=['SC_SUN_POSITION_VECTOR:UNKNOWN_CONSTANT = 0.',
                                       'SC_SUN_VELOCITY_VECTOR:NULL_CONSTANT = 0.'])
        warns = label._validation_warnings()
        for warn in answer:
            self.assertIn(warn, warns)
            warns.remove(warn)
        self.assertEqual(warns,
                    ['SC_SUN_POSITION_VECTOR:UNKNOWN_CONSTANT was inserted: 0.',
                     'SC_SUN_VELOCITY_VECTOR:NULL_CONSTANT was edited: 1.E+32 -> 0.'])

        self.assertEqual(LABEL_VALUE('MINIMUM_VALUE', 'SC_SUN_POSITION_VECTOR'), 0.)
        self.assertEqual(LABEL_VALUE('MAXIMUM_VALUE', 'SC_SUN_POSITION_VECTOR'), 0.)

        before = [_LOGGER.message_count('error'), _LOGGER.message_count('warn')]
        VALIDATE_PDS3_LABEL()
        after = [_LOGGER.message_count('error'), _LOGGER.message_count('warn')]
        self.assertEqual(after[0] - before[0], 0)
        self.assertEqual(after[1] - before[1], 10)

        # More options
        label = Pds3Table(path, numbers=True, formats=True, minmax='float',
                          derived=('SC_SUN_POSITION_VECTOR', 'int'),
                          edits=['SC_SUN_POSITION_VECTOR:UNKNOWN_CONSTANT = 0.',
                                 'SC_SUN_VELOCITY_VECTOR:NULL_CONSTANT = 0.'])
        with (test_file_dir / 'COVIMS_0094_index_template.txt').open('rb') as f:
            answer = f.read().decode('latin-1')
        # print(label.content)
        self.assertEqual(answer, label.content)

        # Preprocessor
        kwargs = {'validate': True, 'numbers': True, 'formats': True, 'minmax': 'float',
                  'derived': ('SC_SUN_POSITION_VECTOR', 'int'),
                  'edits': ['SC_SUN_POSITION_VECTOR:UNKNOWN_CONSTANT = 0.',
                            'SC_SUN_VELOCITY_VECTOR:NULL_CONSTANT = 0.']}
        template = PdsTemplate(path, preprocess=pds3_table_preprocessor, kwargs=kwargs,
                               crlf=True, upper_e=True)

        dirpath = pathlib.Path(tempfile.mkdtemp())
        try:
            outpath = dirpath / 'test.lbl'
            tablepath = dirpath / 'test.tab'
            tablepath.symlink_to(test_file_dir / 'COVIMS_0094_index.tab')

            # Save...
            template.write({}, outpath, mode='save')
            with outpath.open('rb') as f:
                written = f.read().decode('latin-1')
            with (test_file_dir / 'COVIMS_0094_index_test1.txt').open('rb') as f:
                answer = f.read().decode('latin-1')
            # print(written)
            self.assertEqual(written, answer)

            # Repair does nothing
            mtime = os.path.getmtime(outpath)
            time.sleep(1)
            template.write({}, outpath, mode='repair')
            self.assertEqual(mtime, os.path.getmtime(outpath))  # file unchanged

            # Save creates backup
            template.write({}, outpath, mode='save', backup=True)
            all_paths = list(outpath.parent.iterdir())
            paths = list(all_paths)
            paths.remove(outpath)
            paths.remove(tablepath)
            self.assertIsNotNone(re.fullmatch(r'.*/test_20\d\d-\d\d-\d\dT.*\.lbl',
                                              paths[0].as_posix()))
            mtime = os.path.getmtime(outpath)

            # Validate
            F = io.StringIO()           # capture stdout to a string
            with redirect_stdout(F):
                template.write({}, outpath, mode='validate')
            _ = F.getvalue()

            self.assertEqual(mtime, os.path.getmtime(outpath))  # file unchanged

            paths = list(all_paths)
            paths.remove(outpath)

            self.assertRaises(ValueError, template.write, {}, outpath, mode='xxx')

        finally:
            shutil.rmtree(dirpath)

        # Test of sky_summary template
        kwargs = {'validate': False, 'numbers': True, 'formats': True}
        sky_summary = PdsTemplate(test_file_dir / 'sky_summary_template.txt',
                                  preprocess=pds3_table_preprocessor, kwargs=kwargs,
                                  crlf=True, upper_e=True)

        self.maxDiff = None
        with open(test_file_dir/'sky_summary_template_preprocessed.txt', 'r') as f:
            answer = f.read()
        self.assertEqual(sky_summary.content, answer)

        label = sky_summary.generate({}, test_file_dir / 'GO_0023_sky_summary.lbl')
        with open(test_file_dir/'GO_0023_sky_summary.lbl', 'rb') as f:
            answer = f.read()
        answer = answer.decode('utf-8')

        self.assertEqual(label, answer)

        # Missing TABLE
        template_path = test_file_dir / 'sky_summary_template.txt'
        with template_path.open('rb') as f:
            content = f.read()
        content = content.decode('utf-8')
        content = content.replace('TABLE', 'IMAGE')
        self.assertRaisesRegex(TemplateError, r'Template does not contain.*',
                               PdsTemplate, template_path, content,
                               preprocess=pds3_table_preprocessor,
                               crlf=True, upper_e=True)

        # Two tables
        with template_path.open('rb') as f:
            content = f.read()
        content = content.decode('utf-8')
        content = content + content
        self.assertRaisesRegex(TemplateError, r'Template contains multiple.*',
                               PdsTemplate, template_path, content,
                               preprocess=pds3_table_preprocessor,
                               crlf=True, upper_e=True)

        # Repeated column names
        path = test_file_dir / 'repeated_column_names.lbl'
        label = Pds3Table(path, units=False)
        _ = AsciiTable(test_file_dir / 'GO_0023_sky_summary.tab')
        warns = label._validation_warnings()
        self.assertEqual(warns,
                ['ERROR: Name FILE_SPECIFICATION_NAME is duplicated at columns 2 and 3',
                 'ERROR: Name MAXIMUM_DECLINATION is duplicated at columns 4 and 5',
                 'ERROR: Name MAXIMUM_DECLINATION is duplicated at columns 5 and 6'])

        # Reset to starting point
        del PdsTemplate._PREDEFINED_FUNCTIONS['ANALYZE_PDS3_LABEL']
        del PdsTemplate._PREDEFINED_FUNCTIONS['VALIDATE_PDS3_LABEL']
        del PdsTemplate._PREDEFINED_FUNCTIONS['LABEL_VALUE']
        del PdsTemplate._PREDEFINED_FUNCTIONS['ANALYZE_TABLE']
        del PdsTemplate._PREDEFINED_FUNCTIONS['TABLE_VALUE']

        _LOGGER.remove_all_handlers()

class Test_Pds3Table_units(unittest.TestCase):

    def runTest(self):
        self.assertEqual(Pds3Table._get_valid_unit('ERGS/SEC/CM^2/MICROMETER/STER'),
                         'erg/s/cm**2/micron/sr')
        self.assertEqual(Pds3Table._get_valid_unit('METERS/SECOND'), 'm/s')
        self.assertEqual(Pds3Table._get_valid_unit('millisec'), 'ms')
        self.assertEqual(Pds3Table._get_valid_unit('microns'), 'micron')
        self.assertEqual(Pds3Table._get_valid_unit('Micron'), 'micron')
        self.assertEqual(Pds3Table._get_valid_unit('BITS/sec'), 'bit/s')
        self.assertEqual(Pds3Table._get_valid_unit('kbits/sec'), 'kbit/s')
        self.assertEqual(Pds3Table._get_valid_unit('BITS/PIX'), 'bit/pixel')
        self.assertEqual(Pds3Table._get_valid_unit('MB/sec'), 'MB/s')
        self.assertEqual(Pds3Table._get_valid_unit('mb/sec'), '')  # Can't lower-case "MB"
        self.assertEqual(Pds3Table._get_valid_unit('hz'), 'Hz')
        self.assertEqual(Pds3Table._get_valid_unit('HZ'), 'Hz')
        self.assertEqual(Pds3Table._get_valid_unit('J'), 'J')
        self.assertEqual(Pds3Table._get_valid_unit('j'), '')       # Can't lower-case "J"
        self.assertEqual(Pds3Table._get_valid_unit('SR'), 'sr')
        self.assertEqual(Pds3Table._get_valid_unit('N/A'), 'N/A')
        self.assertEqual(Pds3Table._get_valid_unit("'N/A'"), "'N/A'")
        self.assertEqual(Pds3Table._get_valid_unit("'KM/S'"), "km/s")

        self.assertEqual(Pds3Table._unit_is_valid('METERS/SECOND'), True)
        self.assertEqual(Pds3Table._unit_is_valid('mb/sec'), False)

class Test_Pds3Table_format_is_valid(unittest.TestCase):

    def runTest(self):
        self.assertEqual(Pds3Table._format_is_valid('F12.0'), True)
        self.assertEqual(Pds3Table._format_is_valid('F12.10'), True)
        self.assertEqual(Pds3Table._format_is_valid('F12.11'), False)
        self.assertEqual(Pds3Table._format_is_valid('E12.0'), True)
        self.assertEqual(Pds3Table._format_is_valid('E12.6'), True)
        self.assertEqual(Pds3Table._format_is_valid('E12.7'), False)
        self.assertEqual(Pds3Table._format_is_valid('e12.4'), False)
        self.assertEqual(Pds3Table._format_is_valid('I1'), True)
        self.assertEqual(Pds3Table._format_is_valid('I0'), False)
        self.assertEqual(Pds3Table._format_is_valid('A1'), True)
        self.assertEqual(Pds3Table._format_is_valid('A0'), False)
