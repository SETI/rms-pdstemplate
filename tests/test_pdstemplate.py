##########################################################################################
# UNIT TESTS
##########################################################################################

from pdstemplate import *

import unittest
import tempfile


#===============================================================================
class Test_Substitutions(unittest.TestCase):

    #===========================================================================
    def runTest(self):

        T = PdsTemplate('t.xml', content='<instrument_id>$INSTRUMENT_ID$</instrument_id>\n')
        D = {'INSTRUMENT_ID': 'ISSWA'}
        V = '<instrument_id>ISSWA</instrument_id>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content='<f>$"Narrow" if INST == "ISSNA" else "Wide"$</f>\n')
        D = {'INST': 'ISSWA'}
        V = '<f>Wide</f>\n'
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml',
                        content='<a>$cs=("cruise" if TIME < 2004 else "saturn")$</a>\n'+
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


#===============================================================================
class Test_Predefined(unittest.TestCase):

    LOREM_IPSUM = \
"Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "       +\
"incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "   +\
"exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute "      +\
"irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "   +\
"pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia "  +\
"deserunt mollit anim id est laborum."

    JABBERWOCKY = """\
'Twas brillig, and the slithy toves
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

    #===========================================================================
    def runTest(self):

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

            # FILE_ZULU
            os.utime(filepath, None)
            T = PdsTemplate('t.xml', content='$FILE_ZULU(temp)$::$CURRENT_ZULU()$\n')
            test = T.generate(D).rstrip()
            times = test.split('::')    # very rarely, these times could differ by a second
            self.assertEqual(times[0], times[1])

        finally:
            os.close(fd)
            os.remove(filepath)

        # NOESCAPE
        T = PdsTemplate('t.xml', content='<a>$x$</a>' +
                                         '$NOESCAPE("" if x else "  <!-- x == 0 -->")$\n')
        D = {'x': 0}
        V = '<a>0</a>  <!-- x == 0 -->\n'
        self.assertEqual(T.generate(D), V)

        D = {'x': 1}
        V = '<a>1</a>\n'
        self.assertEqual(T.generate(D), V)

        # RAISE
        T = PdsTemplate('t.xml', content='$RAISE(ValueError,"This is the ValueError")$\n')
        V = '[[[ValueError(This is the ValueError) at line 1]]]\n'
        self.assertEqual(T.generate({}), V)
        self.assertEqual(T.ERROR_COUNT, 1)

        try:
            _ = T.generate({}, raise_exceptions=True)
            self.assertTrue(False, "This should have raised an exception but didn't")
        except ValueError as e:
            self.assertEqual(str(e), V[3:-4])
            self.assertEqual(T.ERROR_COUNT, 1)

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

        # VERSION_ID
        T = PdsTemplate('t.xml', content='<!-- PdsTemplate version $VERSION_ID()$ -->\n')
        V = '<!-- PdsTemplate version ' + PDSTEMPLATE_VERSION_ID + ' -->\n'
        self.assertEqual(T.generate(D), V)

        # WRAP
        T = PdsTemplate('t.xml', content="<a>\n        $WRAP(8,84,lorem_ipsum)$\n</a>\n")
        D = {'lorem_ipsum': Test_Predefined.LOREM_IPSUM}
        V = """<a>
        Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
        tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
        quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
        consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
        cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat
        non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.\n</a>\n"""
        self.assertEqual(T.generate(D), V)

        T = PdsTemplate('t.xml', content="<a>\n            $WRAP(12,84,jabberwocky)$\n</a>\n")
        D = {'jabberwocky': Test_Predefined.JABBERWOCKY}
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
        D = {'lorem_ipsum_jabberwocky_multiline':
             Test_Predefined.LOREM_IPSUM_JABBERWOCKY_MULTILINE}
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
        Beware the Jubjub bird, and shun The frumious Bandersnatch!"
</a>
"""
        self.assertEqual(T.generate(D), V)


#===============================================================================
class Test_Headers(unittest.TestCase):

    #===========================================================================
    def runTest(self):

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
        self.assertEqual(T.generate({'x': [1.], 'y': 2}), '        <x>x is True ([1.0])</x>\n')
        self.assertEqual(T.generate({'x': [],   'y': 2}), '        <x>y is True ([], 2)</x>\n')
        self.assertEqual(T.generate({'x': [],   'y': 0}), '        <x>False ([], 0)</x>\n')

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

        # $NOTE and $END_NOTE
        T = PdsTemplate('t.xml', content="""<a></a>
            $NOTE
            This is arbitrary text!
            $END_NOTE
            <b></b>\n""")
        V = """<a></a>
            <b></b>\n"""
        self.assertEqual(T.generate(D), V)

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


#===============================================================================
class Test_Terminators(unittest.TestCase):

    #===========================================================================
    def runTest(self):

        T = PdsTemplate('t.xml', content='<a>$A$</a>\n<b>$B$</b>\n<c>$C$</c>\n')
        D = {'A': 1, 'B': 2, 'C': 3}
        V = '<a>1</a>\n<b>2</b>\n<c>3</c>\n'
        self.assertEqual(T.generate(D, terminator=None), V)
        self.assertEqual(T.generate(D, terminator='\n'), V)

        V = '<a>1</a>\r\n<b>2</b>\r\n<c>3</c>\r\n'
        self.assertEqual(T.generate(D, terminator='\r\n'), V)

        T = PdsTemplate('t.xml', content='<a>$A$</a>\r\n<b>$B$</b>\r\n<c>$C$</c>\r\n')
        V = '<a>1</a>\r\n<b>2</b>\r\n<c>3</c>\r\n'
        self.assertEqual(T.generate(D, terminator=None), V)
        self.assertEqual(T.generate(D, terminator='\r\n'), V)

        V = '<a>1</a>\n<b>2</b>\n<c>3</c>\n'
        self.assertEqual(T.generate(D, terminator='\n'), V)
