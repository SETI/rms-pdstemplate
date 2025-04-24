##########################################################################################
# tests/test_pdstemplate.py
##########################################################################################

import os
import pathlib
import platform
import re
import sys
import tempfile
import unittest

import pdslogger
from filecache import FCPath

from pdstemplate import PdsTemplate, TemplateError


class Test_Substitutions(unittest.TestCase):

    def runTest(self):

        # No logging to stdout
        PdsTemplate.get_logger().add_handler(pdslogger.NULL_HANDLER)

        T = PdsTemplate('t.xml',
                        content='<instrument_id>$INSTRUMENT_ID$</instrument_id>\n')
        D = {'INSTRUMENT_ID': 'ISSWA'}
        V = '<instrument_id>ISSWA</instrument_id>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml',
                        content='<f>$"Narrow" if INST == "ISSNA" else "Wide"$</f>\n')
        D = {'INST': 'ISSWA'}
        V = '<f>Wide</f>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml',
                        content='<a>$cs=("cruise" if TIME < 2004 else "saturn")$</a>\n'
                                '<b>$cs.upper()$<b>\n')
        D = {'TIME': 2004}
        V = '<a>saturn</a>\n<b>SATURN<b>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<dollar>$$</dollar>\n')
        V = '<dollar>$</dollar>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<gt>$greater_than$</gt>\n')
        D = {'greater_than': '>'}
        V = '<gt>&gt;</gt>\n'
        self.assertEqual(T.generate(D), V)

        PdsTemplate.get_logger().remove_all_handlers()

LOREM_IPSUM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "
    "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
    "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute "
    "irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
    "pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia "
    "deserunt mollit anim id est laborum.")

JABBERWOCKY = """'Twas brillig, and the slithy toves
Did gyre and gimble in the wabe:
All mimsy were the borogoves,
And the mome raths outgrabe.

"Beware the Jabberwock, my son!
The jaws that bite, the claws that catch!
Beware the Jubjub bird, and shun
The frumious Bandersnatch!"

"""

LOREM_IPSUM_JABBERWOCKY_MULTILINE = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor
incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud
exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute
irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla
pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia
deserunt mollit anim id est laborum.


'Twas brillig, and the slithy toves
Did gyre and gimble in the wabe:
All mimsy were the borogoves,
And the mome raths outgrabe.

"Beware the Jabberwock, my son!
The jaws that bite, the claws that catch!
Beware the Jubjub bird, and shun
The frumious Bandersnatch!"
"""


class Test_Predefined(unittest.TestCase):

    def runTest(self):

        # No logging to stdout
        PdsTemplate.get_logger().add_handler(pdslogger.NULL_HANDLER)

        # BASENAME
        T = PdsTemplate('t.xml', content='<a>$BASENAME(path)$</a>\n')
        D = {'path': 'a/b/c.txt'}
        V = '<a>c.txt</a>\n'
        self.assertEqual(T.generate(D), V)

        # BOOL
        T = PdsTemplate('t.xml', content='<a>$BOOL(test)$</a>\n')
        D = {'test': 'whatever'}
        V = '<a>true</a>\n'
        self.assertEqual(T.generate(D), V)

        D = {'test': ''}
        V = '<a>false</a>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<a>$BOOL(test, true="YES")$</a>\n')
        D = {'test': 'whatever'}
        V = '<a>YES</a>\n'
        self.assertEqual(T.generate(D), V)

        D = {'test': ''}
        V = '<a>false</a>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<a>$BOOL(test, true="YES", false="NO")$</a>\n')
        D = {'test': ''}
        V = '<a>NO</a>\n'
        self.assertEqual(T.generate(D), V)

        # COUNTER
        T = PdsTemplate('t.xml', content='$COUNTER("test")$\n')
        self.assertEqual(T.generate({}), '1\n')
        self.assertEqual(T.generate({}), '2\n')
        self.assertEqual(T.generate({}), '3\n')
        self.assertEqual(T.generate({}), '4\n')

        # CURRENT_TIME
        T = PdsTemplate('t.xml', content='<a>today=$CURRENT_TIME()$</a>\n')
        D = {'path': 'a/b/c.txt'}
        V = re.compile(r'<a>today=202\d-\d\d-\d\dT\d\d:\d\d:\d\d</a>\n')
        self.assertTrue(V.fullmatch(T.generate(D)))

        T = PdsTemplate('t.xml', content='<a>today=$CURRENT_TIME(date_only=True)$</a>\n')
        D = {'path': 'a/b/c.txt'}
        V = re.compile(r'<a>today=202\d-\d\d-\d\d</a>\n')
        self.assertTrue(V.fullmatch(T.generate(D)))

        # CURRENT_ZULU
        T = PdsTemplate('t.xml', content='<a>today=$CURRENT_ZULU()$</a>\n')
        D = {'path': 'a/b/c.txt'}
        V = re.compile(r'<a>today=202\d-\d\d-\d\dT\d\d:\d\d:\d\dZ</a>\n')
        self.assertTrue(V.fullmatch(T.generate(D)))

        T = PdsTemplate('t.xml', content='<a>today=$CURRENT_ZULU(date_only=True)$</a>\n')
        D = {'path': 'a/b/c.txt'}
        V = re.compile(r'<a>today=202\d-\d\d-\d\d</a>\n')
        self.assertTrue(V.fullmatch(T.generate(D)))

        # DATETIME
        T = PdsTemplate('t.xml', content='<a>$DATETIME(date)$</a>\n')
        D = {'date': '2000-001T12:34:56'}
        V = '<a>2000-01-01T12:34:56Z</a>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<a>$DATETIME(date)$</a>\n')
        D = {'date': 'January 1, 2000'}
        V = '<a>2000-01-01T00:00:00Z</a>\n'
        self.assertEqual(T.generate(D), V)

        D = {'date': 'UNK'}
        V = '<a>UNK</a>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<a>$DATETIME(date,-43200)$</a>\n')
        D = {'date': '2000-001T12:34:56'}
        V = '<a>2000-01-01T00:34:56Z</a>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<a>$DATETIME(date,-43200,digits=0)$</a>\n')
        D = {'date': '2000-001T12:34:56'}
        V = '<a>2000-01-01T00:34:56Z</a>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<a>$DATETIME(date,-43200,digits=1)$</a>\n')
        D = {'date': '2000-001T12:34:56'}
        V = '<a>2000-01-01T00:34:56.0Z</a>\n'
        self.assertEqual(T.generate(D), V)

        # DATETIME_DOY
        T = PdsTemplate('t.xml', content='<a>$DATETIME_DOY(date)$</a>\n')
        D = {'date': '2000-001T12:34:56'}
        V = '<a>2000-001T12:34:56Z</a>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<a>$DATETIME_DOY(date)$</a>\n')
        D = {'date': 'January 1, 2000'}
        V = '<a>2000-001T00:00:00Z</a>\n'
        self.assertEqual(T.generate(D), V)

        D = {'date': 'UNK'}
        V = '<a>UNK</a>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<a>$DATETIME_DOY(date,-43200)$</a>\n')
        D = {'date': '2000-001T12:34:56'}
        V = '<a>2000-001T00:34:56Z</a>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<a>$DATETIME_DOY(date,-43200,digits=0)$</a>\n')
        D = {'date': '2000-001T12:34:56'}
        V = '<a>2000-001T00:34:56Z</a>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<a>$DATETIME_DOY(date,-43200,digits=2)$</a>\n')
        D = {'date': '2000-001T12:34:56'}
        V = '<a>2000-001T00:34:56.00Z</a>\n'
        self.assertEqual(T.generate(D), V)

        # DAYSECS
        T = PdsTemplate('t.xml', content='<a>$DAYSECS(date)$</a>\n')
        D = {'date': '2000-001T12:34:56'}
        V = '<a>45296</a>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<a>$DAYSECS(date)$</a>\n')
        D = {'date': '2099-001T12:34:56'}
        V = '<a>45296</a>\n'
        self.assertEqual(T.generate(D), V)

        # Create a temporary file in the user's root directory
        (fd, filepath) = tempfile.mkstemp(prefix='delete-me-', suffix='.tmp',
                                          dir=os.path.expanduser('~'))
        try:
            for k in range(10):
                os.write(fd, b'1234567\n')

            # FILE_BYTES
            T = PdsTemplate('t.xml', content='<bytes>$FILE_BYTES(temp)$</bytes>\n')
            D = {'temp': filepath}
            V = '<bytes>80</bytes>\n'
            self.assertEqual(T.generate(D), V)

            # FILE_MD5
            T = PdsTemplate('t.xml', content='<md5>$FILE_MD5(temp)$</md5>\n')
            V = '<md5>8258601701b61fe08312bac0be88ae48</md5>\n'
            self.assertEqual(T.generate(D), V)

            # FILE_RECORDS
            T = PdsTemplate('t.xml', content='<records>$FILE_RECORDS(temp)$</records>\n')
            V = '<records>10</records>\n'
            self.assertEqual(T.generate(D), V)

            # FILE_TIME, CURRENT_TIME
            os.utime(filepath, None)
            T = PdsTemplate('t.xml', content='$FILE_TIME(temp)$::$CURRENT_TIME()$\n')
            test = T.generate(D).rstrip()
            times = test.split('::')   # very rarely, these times could differ by a second
            self.assertEqual(times[0], times[1])

            # FILE_ZULU, CURRENT_ZULU
            os.utime(filepath, None)
            T = PdsTemplate('t.xml', content='$FILE_ZULU(temp)$::$CURRENT_ZULU()$\n')
            test = T.generate(D).rstrip()
            times = test.split('::')   # very rarely, these times could differ by a second
            self.assertEqual(times[0], times[1])

            # RECORD_BYTES
            self.assertEqual(PdsTemplate.RECORD_BYTES(filepath), 8)
        finally:
            os.close(fd)
            os.remove(filepath)

        # GETENV
        T = PdsTemplate('t.xml', content='<env>$GETENV("HOME")$</env>')
        self.assertNotEqual(T.generate({}), '<env>None</env>\n')

        T = PdsTemplate('t.xml', content='<env>$GETENV("abcdefghijk", "Missing!")$</env>')
        self.assertEqual(T.generate({}), '<env>Missing!</env>\n')

        # LABEL_PATH
        T = PdsTemplate('t.xml', content='<path>$LABEL_PATH()$</path>\n')
        label_path = 'path/to/label.xml'
        if platform.system() == 'Windows':
            label_path = r'path\to\label.xml'

        V = f'<path>{label_path}</path>\n'
        self.assertEqual(T.generate({}, label_path), V)

        # NOESCAPE
        T = PdsTemplate('t.xml', content='<a>$x$</a>' +
                                         '$NOESCAPE("" if x else "  <!-- x == 0 -->")$\n')
        D = {'x': 0}
        V = '<a>0</a>  <!-- x == 0 -->\n'
        self.assertEqual(T.generate(D), V)

        D = {'x': 1}
        V = '<a>1</a>\n'
        self.assertEqual(T.generate(D), V)

        # QUOTE_IF
        self.assertEqual(PdsTemplate.QUOTE_IF('ABC'), 'ABC')
        self.assertEqual(PdsTemplate.QUOTE_IF('F13.4'), '"F13.4"')
        self.assertEqual(PdsTemplate.QUOTE_IF('km'), '"km"')
        self.assertEqual(PdsTemplate.QUOTE_IF('N/A'), "'N/A'")
        self.assertEqual(PdsTemplate.QUOTE_IF("'N/A'"), "'N/A'")
        self.assertEqual(PdsTemplate.QUOTE_IF("N/A"), "'N/A'")

        # RAISE
        T = PdsTemplate('t.xml', content='$RAISE(ValueError,"This is the ValueError")$\n')
        V = '[[[ValueError(This is the ValueError) at t.xml:1]]]\n'
        self.assertEqual(T.generate({}), V)
        self.assertEqual(T.error_count, 1)

        V = 'This is the ValueError at t.xml:1'
        try:
            _ = T.generate({}, raise_exceptions=True)
            self.assertTrue(False, "This should have raised an exception but didn't")
        except ValueError as e:
            self.assertEqual(str(e), V)
            self.assertEqual(T.error_count, 1)

        # REPLACE_NA
        T = PdsTemplate('t.xml', content='<q>$REPLACE_NA(test,"Not applicable")$</q>\n')
        D = {'test': 111}
        V = '<q>111</q>\n'
        self.assertEqual(T.generate(D), V)

        D = {'test': 'N/A'}
        V = '<q>Not applicable</q>\n'
        self.assertEqual(T.generate(D), V)

        # REPLACE_UNK
        T = PdsTemplate('t.xml', content='<q>$REPLACE_UNK(test,"Unknown")$</q>\n')
        D = {'test': 111}
        V = '<q>111</q>\n'
        self.assertEqual(T.generate(D), V)

        D = {'test': 'UNK'}
        V = '<q>Unknown</q>\n'
        self.assertEqual(T.generate(D), V)

        # TEMPLATE_PATH
        T = PdsTemplate('t.xml', content='<path>$TEMPLATE_PATH()$</path>\n')
        V = '<path>t.xml</path>\n'
        self.assertEqual(T.generate({}), V)

        # VERSION_ID
        T = PdsTemplate('t.xml', content='<!-- PdsTemplate version $VERSION_ID()$ -->\n')
        V = r'<!-- PdsTemplate version \d\.\d -->\n'
        self.assertIsNotNone(re.fullmatch(V, T.generate(D)))

        # WRAP
        T = PdsTemplate('t.xml', content="<a>\n        $WRAP(8,84,lorem_ipsum)$\n</a>\n")
        D = {'lorem_ipsum': LOREM_IPSUM}
        V = """<a>
        Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
        tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
        quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
        consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
        cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat
        non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.\n</a>\n"""
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml',
                        content="<a>\n            $WRAP(12,84,jabberwocky)$\n</a>\n")
        D = {'jabberwocky': JABBERWOCKY}
        V = """<a>
            'Twas brillig, and the slithy toves
            Did gyre and gimble in the wabe:
            All mimsy were the borogoves,
            And the mome raths outgrabe.

            "Beware the Jabberwock, my son!
            The jaws that bite, the claws that catch!
            Beware the Jubjub bird, and shun
            The frumious Bandersnatch!"\n\n</a>\n"""
        self.assertEqual(T.generate(D), V)

        # WRAP removing single newlines
        T = PdsTemplate('t.xml',
                        content="<a>\n        $WRAP(8,84,lorem_ipsum_jabberwocky_multiline,"
                                "preserve_single_newlines=False)$\n</a>\n")
        D = {'lorem_ipsum_jabberwocky_multiline': LOREM_IPSUM_JABBERWOCKY_MULTILINE}
        V = """<a>
        Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
        tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
        quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
        consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
        cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat
        non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

        'Twas brillig, and the slithy toves Did gyre and gimble in the wabe: All
        mimsy were the borogoves, And the mome raths outgrabe.
        "Beware the Jabberwock, my son! The jaws that bite, the claws that catch!
        Beware the Jubjub bird, and shun The frumious Bandersnatch!"\n</a>\n"""
        self.assertEqual(T.generate(D), V)

        # Insert a new function
        PdsTemplate.define_global('LENGTH', len)
        T = PdsTemplate('t.xml', content='<length>$LENGTH("abc")$</length>\n')
        self.assertEqual(T.generate({}), '<length>3</length>\n')

        # Temporarily override a predefined function
        T = PdsTemplate('t.xml', content='<a>$BASENAME+7$</a>\n')
        D = {'BASENAME': 2}
        V = '<a>9</a>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<a>$BASENAME(path)$</a>\n')
        D = {'path': 'a/b/c.txt'}
        V = '<a>c.txt</a>\n'
        self.assertEqual(T.generate(D), V)

        PdsTemplate.get_logger().remove_all_handlers()


class Test_Headers(unittest.TestCase):

    def runTest(self):

        # No logging to stdout
        PdsTemplate.get_logger().add_handler(pdslogger.NULL_HANDLER)

        # $FOR and $END_FOR
        T = PdsTemplate('t.xml', content="""<a></a>
            $FOR(targets)
            <target_name>$VALUE$ ($naif_ids[INDEX]$)</target_name>
            $END_FOR
            <b></b>\n""")
        D = {'targets': ["Jupiter", "Io", "Europa"], 'naif_ids': [599, 501, 502]}
        V = """<a></a>
            <target_name>Jupiter (599)</target_name>
            <target_name>Io (501)</target_name>
            <target_name>Europa (502)</target_name>
            <b></b>\n"""
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content="""
            $FOR(targets)
            <length>$LENGTH$</length>
            $END_FOR\n""")
        D = {'targets': ["Jupiter", "Io", "Europa"], 'naif_ids': [599, 501, 502]}
        V = """
            <length>3</length>
            <length>3</length>
            <length>3</length>\n"""
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content="""<a></a>
            $FOR(name,k=targets)
            <target_name>$name$ ($naif_ids[k]$)</target_name>
            $END_FOR
            <b></b>\n""")
        D = {'targets': ["Jupiter", "Io", "Europa"], 'naif_ids': [599, 501, 502]}
        V = """<a></a>
            <target_name>Jupiter (599)</target_name>
            <target_name>Io (501)</target_name>
            <target_name>Europa (502)</target_name>
            <b></b>\n"""
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content="""<a></a>
            $FOR(name,k,length=targets)
            <target_name>$name$ ($naif_ids[k]$/$length$)</target_name>
            $END_FOR
            <b></b>\n""")
        D = {'targets': ["Jupiter", "Io", "Europa"], 'naif_ids': [599, 501, 502]}
        V = """<a></a>
            <target_name>Jupiter (599/3)</target_name>
            <target_name>Io (501/3)</target_name>
            <target_name>Europa (502/3)</target_name>
            <b></b>\n"""
        self.assertEqual(T.generate(D), V)

        with self.assertRaises(TemplateError) as context:
            T = PdsTemplate('t.xml', content="""<a></a>
                $END_FOR
                <b></b>\n""")
        self.assertEqual(str(context.exception),
                         '$END_FOR without matching $FOR at t.xml:2')

        with self.assertRaises(TemplateError) as context:
            T = PdsTemplate('t.xml', content="""<a></a>
                $FOR
                $END_FOR
                <b></b>\n""")
        self.assertEqual(str(context.exception),
                         'Missing argument for $FOR at t.xml:2')

        with self.assertRaises(TemplateError) as context:
            T = PdsTemplate('t.xml', content="""<a></a>
                $FOR(5)
                <b></b>\n""")
        self.assertEqual(str(context.exception),
                         'Unterminated $FOR block starting at t.xml:2')

        # $IF, $ELSE_IF, $ELSE, $END_IF
        T = PdsTemplate('t.xml', content="""\
        $IF(x==0)
        <x>zero</x>
        $ELSE_IF(x==1)
        <x>one</x>
        $ELSE_IF(x==1)
        <x>one again</x>
        $ELSE
        <x>$x$</x>
        $END_IF\n""")
        self.assertEqual(T.generate({'x': 0 }), '        <x>zero</x>\n')
        self.assertEqual(T.generate({'x': 1.}), '        <x>one</x>\n')
        self.assertEqual(T.generate({'x': 3 }), '        <x>3</x>\n')
        self.assertEqual(T.generate({'x': 3.}), '        <x>3.</x>\n')

        # $IF, $ELSE_IF, $ELSE, $END_IF with definitions
        T = PdsTemplate('t.xml', content="""\
        $IF(a=x)
        <x>x is True ($a$)</x>
        $ELSE_IF(b=y)
        <x>y is True ($a$, $b$)</x>
        $ELSE
        <x>False ($a$, $b$)</x>
        $END_IF\n""")
        self.assertEqual(T.generate({'x': [1.], 'y': 2}),
                         '        <x>x is True ([1.0])</x>\n')
        self.assertEqual(T.generate({'x': [],   'y': 2}),
                         '        <x>y is True ([], 2)</x>\n')
        self.assertEqual(T.generate({'x': [],   'y': 0}),
                         '        <x>False ([], 0)</x>\n')

        with self.assertRaises(TemplateError) as context:
            T = PdsTemplate('t.xml', content="""<a></a>
                $END_IF
                <b></b>\n""")
        self.assertEqual(str(context.exception),
                         '$END_IF without matching $IF at t.xml:2')

        with self.assertRaises(TemplateError) as context:
            T = PdsTemplate('t.xml', content="""<a></a>
                $IF
                $END_IF
                <b></b>\n""")
        self.assertEqual(str(context.exception),
                         'Missing argument for $IF at t.xml:2')

        with self.assertRaises(TemplateError) as context:
            T = PdsTemplate('t.xml', content="""<a></a>
                $IF(5)
                <b></b>\n""")
        self.assertEqual(str(context.exception),
                         'Unterminated $IF block starting at t.xml:2')

        with self.assertRaises(TemplateError) as context:
            T = PdsTemplate('t.xml', content="""<a></a>
                $IF(5)
                $ELSE
                <b></b>\n""")
        self.assertEqual(str(context.exception),
                         'Unterminated $ELSE block starting at t.xml:3')

        # $ONCE
        T = PdsTemplate('t.xml', content="""<a></a>
            $ONCE
            <target_name>JUPITER</target_name>
            <b></b>\n""")
        D = {'targets': ["Jupiter", "Io", "Europa"], 'naif_ids': [599, 501, 502]}
        V = """<a></a>
            <target_name>JUPITER</target_name>
            <b></b>\n"""
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content="""<a></a>
            $ONCE(planet='JUPITER')
            <target_name>$planet$</target_name>
            <b></b>\n""")
        D = {}
        V = """<a></a>
            <target_name>JUPITER</target_name>
            <b></b>\n"""
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml',
                        content='$ONCE(cs=("cruise" if TIME < 2004 else "saturn"))\n' +
                                '<b>$cs.upper()$<b>\n')
        D = {'TIME': 2004}
        V = '<b>SATURN<b>\n'
        self.assertEqual(T.generate(D), V)

# Test is no longer correct
#         with self.assertRaises(TemplateError) as context:
#             T = PdsTemplate('t.xml', content='$ONCE(5)\n')
#         self.assertEqual(str(context.exception),
#                          '$ONCE expression does not define a variable at t.xml:1')

        T = PdsTemplate('t.xml', content='$ONCE(a=5/0)\n')
        V = """[[[ZeroDivisionError(division by zero) in 5/0 at t.xml:1]]]"""
        with self.assertRaises(ZeroDivisionError) as context:
            T.generate({}, raise_exceptions=True)
        self.assertEqual(str(context.exception), 'division by zero in 5/0 at t.xml:1')
        self.assertEqual(T.generate({}), V)

        # $NOTE and $END_NOTE
        T = PdsTemplate('t.xml', content="""<a></a>
            $NOTE
            This is arbitrary text!
            $END_NOTE
            <b></b>\n""")
        V = """<a></a>
            <b></b>\n"""
        self.assertEqual(T.generate(D), V)

        with self.assertRaises(TemplateError) as context:
            T = PdsTemplate('t.xml', content="""<a></a>
                $END_NOTE
                <b></b>\n""")
        self.assertEqual(str(context.exception),
                         '$END_NOTE without matching $NOTE at t.xml:2')

        with self.assertRaises(TemplateError) as context:
            T = PdsTemplate('t.xml', content="""<a></a>
                $NOTE(a=5)
                <b></b>\n""")
        self.assertEqual(str(context.exception),
                         'Extraneous argument for $NOTE at t.xml:2')

        with self.assertRaises(TemplateError) as context:
            T = PdsTemplate('t.xml', content="""<a></a>
                $NOTE
                <b></b>\n""")
        self.assertEqual(str(context.exception),
                         'Unterminated $NOTE block starting at t.xml:2')

        # Nesting...

        T = PdsTemplate('t.xml', content="""<a></a>
            $FOR(targets)
            $IF(naif_ids[INDEX] == 501)
            <target_name>$VALUE$ (This is 501)</target_name>
            $ELSE
            <target_name>$VALUE$ ($naif_ids[INDEX]$)</target_name>
            $END_IF
            $END_FOR
            <b></b>\n""")
        D = {'targets': ["Jupiter", "Io", "Europa"], 'naif_ids': [599, 501, 502]}
        V = """<a></a>
            <target_name>Jupiter (599)</target_name>
            <target_name>Io (This is 501)</target_name>
            <target_name>Europa (502)</target_name>
            <b></b>\n"""
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content="""
            <a></a>
            $FOR(targets)
            $IF(naif_ids[INDEX] == 501)
            $FOR(x=range(3))
            <target_name>$VALUE$ (This is 501)</target_name>
            $END_FOR
            $ELSE
            <target_name>$VALUE$ ($naif_ids[INDEX]$)</target_name>
            $END_IF
            $END_FOR
            <b></b>\n""")
        D = {'targets': ["Jupiter", "Io", "Europa"], 'naif_ids': [599, 501, 502]}
        V = """
            <a></a>
            <target_name>Jupiter (599)</target_name>
            <target_name>Io (This is 501)</target_name>
            <target_name>Io (This is 501)</target_name>
            <target_name>Io (This is 501)</target_name>
            <target_name>Europa (502)</target_name>
            <b></b>\n"""
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content="""\
            $FOR(I=range(ICOUNT))
            $FOR(J=range(JCOUNT))
            <indices>$I$, $J$</indices>
            $END_FOR
            $END_FOR\n""")
        D = {'ICOUNT': 10, 'JCOUNT': 12}
        self.assertEqual(len(T.generate(D).split('\n')), D['ICOUNT'] * D['JCOUNT'] + 1)

        T = PdsTemplate('t.xml', content="""\
            $FOR(I=range(ICOUNT))
            $FOR(J=range(JCOUNT))
            $NOTE
                whatever
            $END_NOTE
            <indices>$I$, $J$</indices>
            $END_FOR
            $END_FOR\n""")
        D = {'ICOUNT': 10, 'JCOUNT': 12}
        self.assertEqual(len(T.generate(D).split('\n')), D['ICOUNT'] * D['JCOUNT'] + 1)

        T = PdsTemplate('t.xml', content="""
            $FOR(I=range(ICOUNT))
            $NOTE
            inner loop should not be executed!
            $FOR(J=range(JCOUNT))
            <indices>$I$, $J$</indices>
            $END_FOR
            $END_NOTE
            <index>$I$</index>
            $END_FOR\n""")
        D = {'ICOUNT': 4, 'JCOUNT': 12}
        V = """
            <index>0</index>
            <index>1</index>
            <index>2</index>
            <index>3</index>\n"""
        self.assertEqual(T.generate(D), V)

        PdsTemplate.get_logger().remove_all_handlers()


class Test_Terminators(unittest.TestCase):

    def runTest(self):

        # No logging to stdout
        PdsTemplate.get_logger().add_handler(pdslogger.NULL_HANDLER)

        D = {'A': 1, 'B': 2, 'C': 3}

        content_lf = '<a>$A$</a>\n<b>$B$</b>\n<c>$C$</c>\n'
        content_crlf = content_lf.replace('\n', '\r\n')
        value_lf = '<a>1</a>\n<b>2</b>\n<c>3</c>\n'
        value_crlf = value_lf.replace('\n', '\r\n')

        T = PdsTemplate('t.xml', content=content_lf, crlf=None)
        self.assertEqual(T.generate(D), value_lf)

        T = PdsTemplate('t.xml', content=content_crlf, crlf=None)
        self.assertEqual(T.generate(D), value_crlf)

        for content in (content_lf, content_crlf):
            T = PdsTemplate('t.xml', content=content, crlf=False)
            self.assertEqual(T.generate(D), value_lf)

            T = PdsTemplate('t.xml', content=content, crlf=True)
            self.assertEqual(T.generate(D), value_crlf)

        PdsTemplate.get_logger().remove_all_handlers()


class Test_Misc(unittest.TestCase):

    def runTest(self):

        # No logging to stdout
        PdsTemplate.get_logger().add_handler(pdslogger.NULL_HANDLER)

        # Supplying content as a list
        T = PdsTemplate('t.xml', content=[
            '$FOR(I=range(ICOUNT))\n',
            '$NOTE\n',
            'inner loop should not be executed!\n',
            '$FOR(J=range(JCOUNT))\n',
            '<indices>$I$, $J$</indices>\n',
            '$END_FOR\n',
            '$END_NOTE\n',
            '<index>$I$</index>\n',
            '$END_FOR\n'
        ])
        D = {'ICOUNT': 4, 'JCOUNT': 12}
        V = """<index>0</index>
<index>1</index>
<index>2</index>
<index>3</index>\n"""
        self.assertEqual(T.generate(D), V)

        # Disabling auto-detection of XML
        T = PdsTemplate('t.xml', content='$val$\n')
        D = {'val': '&'}
        V = '&\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<?xml\n$val$\n')
        V = '<?xml\n&amp;\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<?xml $val$\n', xml=False)
        V = '<?xml &\n'
        self.assertEqual(T.generate(D), V)

        # Raised exceptions
        T = PdsTemplate('t.xml', content='$1/0$\n', xml=False)
        D = {}
        V = '[[[ZeroDivisionError(division by zero) in 1/0 at t.xml:1]]]\n'
        self.assertEqual(T.generate(D), V)
        self.assertEqual(T.generate(D, raise_exceptions=False), V)

        with self.assertRaises(ZeroDivisionError):
            T.generate(D, raise_exceptions=True)

        T = PdsTemplate('t.xml', content="""
            $IF(1/0)
                SOMETHING
            $END_IF\n""")
        D = {}
        V = '\n[[[ZeroDivisionError(division by zero) in (1/0) at t.xml:2]]]'
        self.assertEqual(T.generate(D), V)

        with self.assertRaises(ZeroDivisionError):
            T.generate(D, raise_exceptions=True)

        T = PdsTemplate('t.xml', content="""
            $FOR(1/0)
                SOMETHING
            $END_FOR\n""")
        D = {}
        V = '\n[[[ZeroDivisionError(division by zero) in (1/0) at t.xml:2]]]'
        self.assertEqual(T.generate(D), V)

        with self.assertRaises(ZeroDivisionError):
            T.generate(D, raise_exceptions=True)

        # Mismatched $
        with self.assertRaises(TemplateError) as context:
            T = PdsTemplate('t.xml', content='$\n')
        self.assertEqual(str(context.exception), 'Mismatched "$" at t.xml:1')

        # Float pretty-printing
        T = PdsTemplate('t.xml', content='$0.1+0.2$\n', xml=False)
        D = {}
        V = '0.3\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='$1.0000000000000241$\n', xml=False)
        D = {}
        V = '1.\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='$0.9999999999999865$\n', xml=False)
        D = {}
        V = '1.\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='$-1.0000000000000241$\n', xml=False)
        D = {}
        V = '-1.\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='$-0.9999999999999865$\n', xml=False)
        D = {}
        V = '-1.\n'
        self.assertEqual(T.generate(D), V)

        # Logging - Feature disabled in favor of set_log_format()
#         PdsTemplate.set_logger(pdslogger.EasyLogger())
#         self.assertIsInstance(PdsTemplate._GLOBAL_LOGGER, pdslogger.EasyLogger)
#         self.assertIs(T.logger, PdsTemplate._GLOBAL_LOGGER)
#         PdsTemplate.set_logger(None)
#         self.assertIs(PdsTemplate._GLOBAL_LOGGER, PdsTemplate._DEFAULT_LOGGER)
#         self.assertIs(T.logger, PdsTemplate._DEFAULT_LOGGER)
#
#         PdsTemplate.set_logger(pdslogger.EasyLogger(), default=False)
#         self.assertIs(PdsTemplate._GLOBAL_LOGGER, PdsTemplate._DEFAULT_LOGGER)
#         self.assertIsInstance(T.logger, pdslogger.EasyLogger)
#         PdsTemplate.set_logger(None, default=False)
#         self.assertIs(PdsTemplate._GLOBAL_LOGGER, PdsTemplate._DEFAULT_LOGGER)
#         self.assertIs(T.logger, PdsTemplate._GLOBAL_LOGGER)

        # Overriding predefined function
        # Why someone would do this I have no idea...but we support it
        T = PdsTemplate('t.xml', content='$FILE_BYTES(1)$\n')
        D = {'FILE_BYTES': lambda x: x+1}
        V = '2\n'
        self.assertEqual(T.generate(D), V)

        PdsTemplate.get_logger().remove_all_handlers()


class Test_Files(unittest.TestCase):

    def runTest(self):

        # No logging to stdout
        PdsTemplate.get_logger().add_handler(pdslogger.NULL_HANDLER)

        update_expected = False

        self.maxDiff = 100000

        root_dir = pathlib.Path(sys.modules['pdstemplate'].__file__).parent.parent
        test_file_dir = root_dir / 'test_files'

        # Test predefined functions

        test_template_file = test_file_dir / 'functions_template.txt'
        test_expected_file = test_file_dir / 'functions_expected.txt'
        bin_data_file = test_file_dir / 'data_file.bin'

        if not update_expected:
            with open(test_expected_file, 'r') as fp:
                expected = fp.read()

        for_list = ['a', 'b', 'c']
        template = PdsTemplate(test_template_file)

        with tempfile.TemporaryDirectory() as temp_dir:
            contents = """Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do \
eiusmod tempor incididunt
ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation
ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in
reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur
sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id
est laborum.
"""
            # We have to write this here in binary mode because if we check it
            # into git, when we check it out on Linux/Mac vs Windows we get
            # different line terminators, and thus different numbers of bytes
            # and MD5 checksums
            text_data_file = f'{temp_dir}/data_file.txt'
            with open(text_data_file, 'wb') as fp:
                fp.write(contents.encode('utf-8'))
            dictionary = {'bin_data_file': str(bin_data_file),
                          'text_data_file': str(text_data_file),
                          'for_list': for_list}
            test_output_file = f'{temp_dir}/functions_output.txt'
            answer = template.write(dictionary, test_output_file)
            self.assertEqual(answer, (0, 0))
            with open(test_output_file, 'r') as fp:
                result = fp.read()

        if update_expected:
            # print(result)
            with open(test_expected_file, 'w') as fp:
                fp.write(result)
        else:
            # print(result)
            self.assertEqual(expected, result)

        # Test XML escaping

        test_template_file = test_file_dir / 'xml_template.xml'
        test_expected_file = test_file_dir / 'xml_expected.txt'

        if not update_expected:
            with open(test_expected_file, 'r') as fp:
                expected = fp.read()

        template = PdsTemplate(test_template_file)
        dictionary = {'escape_text': '<&>'}

        with tempfile.TemporaryDirectory() as temp_dir:
            test_output_file = f'{temp_dir}/xml_output.txt'
            answer = template.write(dictionary, test_output_file)
            self.assertEqual(answer, (0, 0))
            with open(test_output_file, 'r') as fp:
                result = fp.read()

        if update_expected:
            # print(result)
            with open(test_expected_file, 'w') as fp:
                fp.write(result)
        else:
            # print(result)
            self.assertEqual(expected, result)

        # Test writing files with template errors

        test_template_file = test_file_dir / 'raises_template.txt'
        test_expected_file = test_file_dir / 'raises_expected.txt'

        if not update_expected:
            with open(test_expected_file, 'r') as fp:
                expected = fp.read()

        with tempfile.TemporaryDirectory() as temp_dir:
            test_output_file = f'{temp_dir}/raises_output.txt'

            T = PdsTemplate(test_template_file)
            answer = T.write({}, test_output_file)
            self.assertEqual(answer, (1, 0))
            self.assertEqual(T.error_count, 1)
            with open(test_output_file, 'r') as fp:
                result = fp.read()

            if update_expected:
                # print(result)
                with open(test_expected_file, 'w') as fp:
                    fp.write(result)
            else:
                # print(result)
                self.assertEqual(expected, result)

            try:
                answer = T.write({}, test_output_file, raise_exceptions=True)
                self.assertEqual(answer, (0, 0))
                self.assertTrue(False, "This should have raised an exception but didn't")
            except ValueError as e:
                self.assertEqual(str(e), 'This is the ValueError at raises_template.txt:1')
                self.assertEqual(T.error_count, 1)

        # Test writing files with different terminators

        with tempfile.TemporaryDirectory() as temp_dir:
            test_output_file = f'{temp_dir}/terminator_output.txt'

            T = PdsTemplate('t.xml', content='value1\nvalue2\n', crlf=True)
            answer = T.write({}, test_output_file)
            self.assertEqual(answer, (0, 0))

            with open(test_output_file, 'rb') as fp:
                result = fp.read()
            result = result.decode('utf-8')
            self.assertEqual(result, 'value1\r\nvalue2\r\n')

            T = PdsTemplate('t.xml', content='value1\r\nvalue2\r\n', crlf=True)
            answer = T.write({}, test_output_file)
            self.assertEqual(answer, (0, 0))

            with open(test_output_file, 'rb') as fp:
                result = fp.read()
            result = result.decode('utf-8')
            self.assertEqual(result, 'value1\r\nvalue2\r\n')

            T = PdsTemplate('t.xml', content='value1\r\nvalue2\r\n', crlf=False)
            answer = T.write({}, test_output_file)
            self.assertEqual(answer, (0, 0))
            with open(test_output_file, 'rb') as fp:
                result = fp.read()
            result = result.decode('utf-8')
            self.assertEqual(result, 'value1\nvalue2\n')

            # Missing end terminator
            T = PdsTemplate('t.xml', content='test', crlf=True)
            T.write({}, test_output_file)

            with open(test_output_file, 'rb') as fp:
                result = fp.read()
            result = result.decode('utf-8')
            self.assertEqual(result, 'test\r\n')

        PdsTemplate.get_logger().remove_all_handlers()


class Test_Preprocessor(unittest.TestCase):

    def runTest(self):

        # No logging to stdout
        PdsTemplate.get_logger().add_handler(pdslogger.NULL_HANDLER)

        def hello(filepath, content, name=''):
            return 'Hello' + (' ' if name else '') + name.capitalize() + '!\n' + content

        def uppercase(filepath, content):
            return content.upper()

        T = PdsTemplate('t.xml', content='text\n', preprocess=hello)
        self.assertEqual(T.generate({}), 'Hello!\ntext\n')

        T = PdsTemplate('t.xml', content='text\n', preprocess=hello, args=('rob',))
        self.assertEqual(T.generate({}), 'Hello Rob!\ntext\n')

        T = PdsTemplate('t.xml', content='text\n', preprocess=hello, kwargs={'name': 'rob'})
        self.assertEqual(T.generate({}), 'Hello Rob!\ntext\n')

        T = PdsTemplate('t.xml', content='text\n', preprocess=uppercase)
        self.assertEqual(T.generate({}), 'TEXT\n')

        T = PdsTemplate('t.xml', content='text\n', preprocess=[hello, uppercase],
                        args=('rob',))
        self.assertEqual(T.generate({}), 'HELLO ROB!\nTEXT\n')

        T = PdsTemplate('t.xml', content='text\n', preprocess=[hello, uppercase],
                        kwargs={'name': 'rob'})
        self.assertEqual(T.generate({}), 'HELLO ROB!\nTEXT\n')

        T = PdsTemplate('t.xml', content='text\n', preprocess=[uppercase, hello])
        self.assertEqual(T.generate({}), 'Hello!\nTEXT\n')

        def h2(filepath, content):
            return hello(filepath, content, name='rob')
        T = PdsTemplate('t.xml', content='text\n', preprocess=[uppercase, h2])
        self.assertEqual(T.generate({}), 'Hello Rob!\nTEXT\n')

        # No logging to stdout
        PdsTemplate.get_logger().remove_all_handlers()


class Test_include_dirs(unittest.TestCase):

    def runTest(self):

        # No logging to stdout
        PdsTemplate.get_logger().add_handler(pdslogger.NULL_HANDLER)

        try:
            PdsTemplate._GETENV_INCLUDE_DIRS = None
            original = os.getenv('PDSTEMPLATE_INCLUDES')
            os.environ['PDSTEMPLATE_INCLUDES'] = '.:foo:bar'

            T = PdsTemplate('prefix/t.xml', content='ignored\n', includes='whatever')
            dirs = [str(d) for d in T._include_dirs()]
            self.assertEqual(dirs, ['prefix', 'whatever', '.', 'foo', 'bar'])

            T = PdsTemplate('prefix/t.xml', content='ignored\n', includes=['what', 'ever'])
            dirs = [str(d) for d in T._include_dirs()]
            self.assertEqual(dirs, ['prefix', 'what', 'ever', '.', 'foo', 'bar'])

        finally:
            PdsTemplate._GETENV_INCLUDE_DIRS = None
            if original is not None:
                os.environ['PDSTEMPLATE_INCLUDES'] = original

        PdsTemplate.get_logger().remove_all_handlers()


class Test_Includes(unittest.TestCase):

    def runTest(self):

        # No logging to stdout
        PdsTemplate.get_logger().add_handler(pdslogger.NULL_HANDLER)

        root_dir = pathlib.Path(sys.modules['pdstemplate'].__file__).parent.parent
        test_file_dir = root_dir / 'test_files'

        T = PdsTemplate(test_file_dir / 'include_test.lbl')
        answer = (test_file_dir / 'include_test_content.txt').read_text()
        self.assertEqual(T.content, answer)

        label = T.generate({'isvis': True}, 'temp.lbl')
        answer = (test_file_dir / 'include_test_label_vis.txt').read_bytes().decode('utf-8')
        self.assertEqual(label, answer)

        label = T.generate({'isvis': False}, 'temp.lbl')
        answer = (test_file_dir / 'include_test_label_ir.txt').read_bytes().decode('utf-8')
        self.assertEqual(label, answer)

        PdsTemplate.get_logger().remove_all_handlers()

        try:
            PdsTemplate._GETENV_INCLUDE_DIRS = None
            original = os.getenv('PDSTEMPLATE_INCLUDES')
            os.environ['PDSTEMPLATE_INCLUDES'] = '.:foo:bar'
            self.assertIsNone(PdsTemplate._GETENV_INCLUDE_DIRS)
            dirs = [str(d).replace('\\', '/') for d in T._include_dirs()]
            self.assertEqual(dirs, [str(test_file_dir).replace('\\', '/'), '.',
                                    'foo', 'bar'])

            PdsTemplate._GETENV_INCLUDE_DIRS = None
            del os.environ['PDSTEMPLATE_INCLUDES']
            self.assertEqual(T._include_dirs(), [FCPath(test_file_dir)])

        finally:
            PdsTemplate._GETENV_INCLUDE_DIRS = None
            if original is not None:
                os.environ['PDSTEMPLATE_INCLUDES'] = original
