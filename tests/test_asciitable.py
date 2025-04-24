##########################################################################################
# tests/test_asciitable.py
##########################################################################################

import pathlib
import sys
import unittest

from filecache import FCPath

from pdstemplate import PdsTemplate, TemplateError
from pdstemplate.asciitable import AsciiTable, ANALYZE_TABLE, TABLE_VALUE
from pdstemplate.asciitable import _latest_ascii_table, _reset_ascii_table


class Test_AsciiTable(unittest.TestCase):

    def runTest(self):

        self.assertIn('ANALYZE_TABLE', PdsTemplate._PREDEFINED_FUNCTIONS)
        self.assertNotIn('TABLE_VALUE', PdsTemplate._PREDEFINED_FUNCTIONS)

        root_dir = pathlib.Path(sys.modules['pdstemplate'].__file__).parent.parent
        test_file_dir = root_dir / 'test_files'
        path = test_file_dir / 'COVIMS_0094_index.tab'
        table = AsciiTable(path)
        self.assertIs(_latest_ascii_table(), table)
        self.assertEqual(table.filepath, FCPath(path))

        self.assertIn('TABLE_VALUE', PdsTemplate._PREDEFINED_FUNCTIONS)

        self.assertEqual(TABLE_VALUE('PATH'), str(path).replace('\\', '/'))
        self.assertEqual(TABLE_VALUE('BASENAME'), path.name)
        self.assertEqual(TABLE_VALUE('ROWS'), 1711)
        self.assertEqual(TABLE_VALUE('COLUMNS'), 74)
        self.assertEqual(TABLE_VALUE('ROW_BYTES'), 1089)
        self.assertEqual(TABLE_VALUE('TERMINATORS'), 2)
        self.assertEqual(TABLE_VALUE('WIDTH', 0), 27)

        with self.assertRaisesRegex(TemplateError, r'.*KeyError.*'):
            _ = TABLE_VALUE('ZZZ')

        k = 0
        self.assertEqual(TABLE_VALUE('PDS3_FORMAT', k), 'A25')
        self.assertEqual(TABLE_VALUE('PDS4_FORMAT', k), '%25s')
        self.assertEqual(TABLE_VALUE('PDS3_DATA_TYPE', k), 'CHARACTER')
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', k), 'ASCII_Text_Preserved')
        self.assertEqual(TABLE_VALUE('QUOTES', k), 1)
        self.assertEqual(TABLE_VALUE('START_BYTE', k), 1)
        self.assertEqual(TABLE_VALUE('BYTES', k), 25)
        self.assertEqual(TABLE_VALUE('MINIMUM', k), "v1882439160_1.qub        ")
        self.assertEqual(TABLE_VALUE('MAXIMUM', k), "v1884114114_1.qub        ")
        self.assertEqual(TABLE_VALUE('FIRST', k), "v1882439160_1.qub        ")
        self.assertEqual(TABLE_VALUE('LAST', k), "v1884114114_1.qub        ")
        self.assertEqual(len(TABLE_VALUE('VALUES', k)), 1711)

        k = 4
        self.assertEqual(TABLE_VALUE('PDS3_FORMAT', k), 'A23')
        self.assertEqual(TABLE_VALUE('PDS4_FORMAT', k), '%23s')
        self.assertEqual(TABLE_VALUE('PDS3_DATA_TYPE', k), 'TIME')
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', k), 'ASCII_Date_Time_YMD')
        self.assertEqual(TABLE_VALUE('QUOTES', k), 0)
        self.assertEqual(TABLE_VALUE('START_BYTE', k), 98)
        self.assertEqual(TABLE_VALUE('BYTES', k), 23)
        self.assertEqual(TABLE_VALUE('MINIMUM', k), "2017-08-26T10:42:54.426")
        self.assertEqual(TABLE_VALUE('MAXIMUM', k), "2017-09-14T19:58:37.608")
        self.assertEqual(TABLE_VALUE('FIRST', k), "2017-08-26T10:42:54.426")
        self.assertEqual(TABLE_VALUE('LAST', k), "2017-09-14T19:58:37.608")
        self.assertEqual(len(TABLE_VALUE('VALUES', k)), 1711)

        k = 13
        self.assertEqual(TABLE_VALUE('PDS3_FORMAT', k), 'I2')
        self.assertEqual(TABLE_VALUE('PDS4_FORMAT', k), '%2d')
        self.assertEqual(TABLE_VALUE('PDS3_DATA_TYPE', k), 'ASCII_INTEGER')
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', k), 'ASCII_Integer')
        self.assertEqual(TABLE_VALUE('QUOTES', k), 0)
        self.assertEqual(TABLE_VALUE('START_BYTE', k), 275)
        self.assertEqual(TABLE_VALUE('BYTES', k), 2)
        self.assertEqual(TABLE_VALUE('MINIMUM', k), 1)
        self.assertEqual(TABLE_VALUE('MAXIMUM', k), 64)
        self.assertEqual(TABLE_VALUE('FIRST', k), 64)
        self.assertEqual(TABLE_VALUE('LAST', k), 64)
        self.assertEqual(len(TABLE_VALUE('VALUES', k)), 1711)

        k = 15
        self.assertEqual(TABLE_VALUE('PDS3_FORMAT', k), 'F10.1')
        self.assertEqual(TABLE_VALUE('PDS4_FORMAT', k), '%10.1f')
        self.assertEqual(TABLE_VALUE('PDS3_DATA_TYPE', k), 'ASCII_REAL')
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', k), 'ASCII_Real')
        self.assertEqual(TABLE_VALUE('QUOTES', k), 0)
        self.assertEqual(TABLE_VALUE('START_BYTE', k), 281)
        self.assertEqual(TABLE_VALUE('BYTES', k), 10)
        self.assertEqual(TABLE_VALUE('MINIMUM', k), 20.)
        self.assertEqual(TABLE_VALUE('MAXIMUM', k), 1000.)
        self.assertEqual(TABLE_VALUE('FIRST', k), 90.)
        self.assertEqual(TABLE_VALUE('LAST', k), 90.)
        self.assertEqual(len(TABLE_VALUE('VALUES', k)), 1711)

        k = 73
        self.assertEqual(TABLE_VALUE('PDS3_FORMAT', k), 'E11.0')
        self.assertEqual(TABLE_VALUE('PDS4_FORMAT', k), '%11.0E')
        self.assertEqual(TABLE_VALUE('PDS3_DATA_TYPE', k), 'ASCII_REAL')
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', k), 'ASCII_Real')
        self.assertEqual(TABLE_VALUE('QUOTES', k), 0)
        self.assertEqual(TABLE_VALUE('START_BYTE', k), 1077)
        self.assertEqual(TABLE_VALUE('BYTES', k), 11)
        self.assertEqual(TABLE_VALUE('MINIMUM', k), 1.e32)
        self.assertEqual(TABLE_VALUE('MAXIMUM', k), 1.e32)
        self.assertEqual(TABLE_VALUE('FIRST', k), 1.e32)
        self.assertEqual(TABLE_VALUE('LAST', k), 1.e32)
        self.assertEqual(TABLE_VALUE('VALUES', k), 1711 * [1.e32])

        # Misc errors
        self.assertRaises(ValueError, AsciiTable, path, separator='+')
        self.assertRaises(ValueError, AsciiTable, path, escape='+')

        records = [b'123\n', b'1234\n']
        self.assertRaises(TemplateError, AsciiTable, path, records)

        records = [b'12345\n', b'123,5\n']
        self.assertRaises(TemplateError, AsciiTable, path, records)

        records = [b'12345\r\n', b'23456\n']
        self.assertRaises(TemplateError, AsciiTable, path, records)

        records = [b'12345\r\n', b'234567\n']
        self.assertRaises(TemplateError, AsciiTable, path, records)

        records = [b'12345\r\n', b'234567\n']
        self.assertRaises(TemplateError, AsciiTable, path, records)

        records = [b'1234\r\n', b'2345\r\n']
        self.assertRaises(TemplateError, AsciiTable, path, records, crlf=False)

        records = [b'1234\n', b'2345\n']
        self.assertRaises(TemplateError, AsciiTable, path, records, crlf=True)

        records = [b'1234\n', b'abcd\n']
        self.assertRaises(TemplateError, AsciiTable, path, records)

        # More data types
        table = AsciiTable(path, content=[b'2017-09-14T19:58:37.608Z\n'])
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Date_Time_YMD_UTC')

        table = AsciiTable(path, content=[b'2017-009T19:58:37.608Z\n'])
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Date_Time_DOY_UTC')

        table = AsciiTable(path, content=[b'2017-009T19:58:37.608\n'])
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Date_Time_DOY')

        table = AsciiTable(path, content=[b'2017-009T19:58:37.608Z\n'])
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Date_Time_DOY_UTC')

        table = AsciiTable(path, content=[b'2017-009T19:58:37.608 \n',
                                          b'2017-009T19:58:37.608Z\n'])
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Date_Time_DOY')

        table = AsciiTable(path, content=[b'2017-09-14T19:58:37.608Z\n',
                                          b'2017-09-14T19:58:37.608 \n'])
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Date_Time_YMD')

        table = AsciiTable(path, content=[b'2017-009T19:58:37.608Z  \n',
                                          b'2017-09-14T19:58:37.608Z\n'])
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Date_Time_UTC')

        table = AsciiTable(path, content=[b'2017-009T19:58:37.608   \n',
                                          b'2017-09-14T19:58:37.608Z\n'])
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Date_Time')

        table = AsciiTable(path, content=[b'2017-009T19:58:37.608Z \n',
                                          b'2017-09-14T19:58:37.608\n'])
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Date_Time')

        table = AsciiTable(path, content=[b'2017-09-14\n'])
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Date_YMD')

        table = AsciiTable(path, content=[b'2017-009\n'])
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Date_DOY')

        table = AsciiTable(path, content=[b'123x\n'])
        self.assertEqual(TABLE_VALUE('PDS3_DATA_TYPE', 0), 'CHARACTER')
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Text_Preserved')
        self.assertEqual(TABLE_VALUE('PDS3_FORMAT', 0), 'A4')
        self.assertEqual(TABLE_VALUE('PDS4_FORMAT', 0), '%4s')
        self.assertEqual(TABLE_VALUE('WIDTH', 0), 4)
        self.assertEqual(TABLE_VALUE('START_BYTE', 0), 1)
        self.assertEqual(TABLE_VALUE('QUOTES', 0), 0)

        table = AsciiTable(path, content=[b'abcdef\n', b'"ABCD"\n'])
        self.assertEqual(TABLE_VALUE('PDS3_DATA_TYPE', 0), 'CHARACTER')
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Text_Preserved')
        self.assertEqual(TABLE_VALUE('PDS3_FORMAT', 0), 'A6')
        self.assertEqual(TABLE_VALUE('PDS4_FORMAT', 0), '%6s')
        self.assertEqual(TABLE_VALUE('WIDTH', 0), 6)
        self.assertEqual(TABLE_VALUE('START_BYTE', 0), 1)
        self.assertEqual(TABLE_VALUE('QUOTES', 0), 0)
        self.assertEqual(TABLE_VALUE('LAST', 0), '"ABCD"')

        table = AsciiTable(path, content=[b'   +1.E32\n', b'12345.678\n'])
        self.assertEqual(TABLE_VALUE('PDS3_DATA_TYPE', 0), 'ASCII_REAL')
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Real')
        self.assertEqual(TABLE_VALUE('PDS3_FORMAT', 0), 'F9.3')
        self.assertEqual(TABLE_VALUE('PDS4_FORMAT', 0), '%9.3f')

        table = AsciiTable(path, content=[b'   +1.E32\n', b'12345.678\n'])
        self.assertEqual(TABLE_VALUE('PDS3_DATA_TYPE', 0), 'ASCII_REAL')
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', 0), 'ASCII_Real')
        self.assertEqual(TABLE_VALUE('PDS3_FORMAT', 0), 'F9.3')
        self.assertEqual(TABLE_VALUE('PDS4_FORMAT', 0), '%9.3f')

        # Escaped quotes and quoted commas
        table = AsciiTable(path, content=[b'"123,456",789\n'])
        self.assertEqual(TABLE_VALUE('COLUMNS'), 2)
        self.assertEqual(TABLE_VALUE('PDS3_DATA_TYPE', 0), 'CHARACTER')

        self.assertRaises(TemplateError, AsciiTable, path, content=[b'"abc","def\n'])

        table = AsciiTable(path, content=[b'"123\\",456",789\n'], escape='\\')
        self.assertEqual(TABLE_VALUE('COLUMNS'), 2)
        self.assertEqual(TABLE_VALUE('PDS3_DATA_TYPE', 0), 'CHARACTER')
        self.assertEqual(TABLE_VALUE('PDS3_FORMAT', 0), 'A9')
        self.assertEqual(TABLE_VALUE('QUOTES', 0 ), 1)

        table = AsciiTable(path, content=[b'"123"",456",789\n'], escape='"')
        self.assertEqual(TABLE_VALUE('COLUMNS'), 2)
        self.assertEqual(TABLE_VALUE('PDS3_DATA_TYPE', 0), 'CHARACTER')
        self.assertEqual(TABLE_VALUE('PDS3_FORMAT', 0), 'A9')
        self.assertEqual(TABLE_VALUE('QUOTES', 0), 1)

        table = AsciiTable(path, content=[b'"12345678\\""\n',
                                          b'"12345678  "\n',
                                          b'",,,,,,\\",,"\n'], escape='\\')
        self.assertEqual(TABLE_VALUE('FIRST', 0), '12345678"')
        self.assertEqual(TABLE_VALUE('LAST', 0), ',,,,,,",,')

        table = AsciiTable(path, content=[b'"123"\n',
                                          b'abcde\n'])
        self.assertEqual(TABLE_VALUE('FIRST', 0), '"123"')
        self.assertEqual(TABLE_VALUE('LAST', 0), 'abcde')

        # Alt separators
        table = AsciiTable(path, content=[b'"123|456"|789\n'], separator='|')
        self.assertEqual(TABLE_VALUE('FIRST', 0), '123|456')

        table = AsciiTable(path, content=[b'"123\t456"\t789\n'], separator='\t')
        self.assertEqual(TABLE_VALUE('FIRST', 0), '123\t456')

        table = AsciiTable(path, content=[b'"123;456";789\n'], separator=';')
        self.assertEqual(TABLE_VALUE('FIRST', 0), '123;456')

        # ANALYZE_TABLE
        ANALYZE_TABLE(str(path))
        self.assertEqual(TABLE_VALUE('PATH'), str(path).replace('\\', '/'))
        self.assertEqual(TABLE_VALUE('BASENAME'), path.name)
        self.assertEqual(TABLE_VALUE('ROWS'), 1711)
        self.assertEqual(TABLE_VALUE('COLUMNS'), 74)
        self.assertEqual(TABLE_VALUE('ROW_BYTES'), 1089)
        self.assertEqual(TABLE_VALUE('TERMINATORS'), 2)
        self.assertEqual(TABLE_VALUE('WIDTH', 0), 27)

        k = 0
        self.assertEqual(TABLE_VALUE('PDS3_FORMAT', k), 'A25')
        self.assertEqual(TABLE_VALUE('PDS4_FORMAT', k), '%25s')
        self.assertEqual(TABLE_VALUE('PDS3_DATA_TYPE', k), 'CHARACTER')
        self.assertEqual(TABLE_VALUE('PDS4_DATA_TYPE', k), 'ASCII_Text_Preserved')
        self.assertEqual(TABLE_VALUE('QUOTES', k), 1)
        self.assertEqual(TABLE_VALUE('START_BYTE', k), 1)
        self.assertEqual(TABLE_VALUE('BYTES', k), 25)
        self.assertEqual(TABLE_VALUE('MINIMUM', k), "v1882439160_1.qub        ")
        self.assertEqual(TABLE_VALUE('MAXIMUM', k), "v1884114114_1.qub        ")
        self.assertEqual(TABLE_VALUE('FIRST', k), "v1882439160_1.qub        ")
        self.assertEqual(TABLE_VALUE('LAST', k), "v1884114114_1.qub        ")
        self.assertEqual(len(TABLE_VALUE('VALUES', k)), 1711)

        # Reset to starting point
        del PdsTemplate._PREDEFINED_FUNCTIONS['ANALYZE_TABLE']
        del PdsTemplate._PREDEFINED_FUNCTIONS['TABLE_VALUE']
        _reset_ascii_table()
