##########################################################################################
# tests/test_utils.py
##########################################################################################

import unittest

from pdstemplate import TemplateError
from pdstemplate.utils import _check_terminators


class Test_Utils(unittest.TestCase):

    def test_check_terminators(self):

        text = 'line 1\nline 2\nline 3\n'
        self.assertEqual(_check_terminators('foo.txt', text, crlf=None), False)
        self.assertEqual(_check_terminators('foo.txt', text, crlf=False), False)
        self.assertRaises(TemplateError, _check_terminators, 'foo.txt', text, crlf=True)

        text = 'line 1\r\nline 2\r\nline 3\r\n'
        self.assertEqual(_check_terminators('foo.txt', text, crlf=None), True)
        self.assertEqual(_check_terminators('foo.txt', text, crlf=True), True)
        self.assertRaises(TemplateError, _check_terminators, 'foo.txt', text, crlf=False)

        text = ['line 1\n', 'line 2\n', 'line 3\n']
        self.assertEqual(_check_terminators('foo.txt', text, crlf=None), False)
        self.assertEqual(_check_terminators('foo.txt', text, crlf=False), False)
        self.assertRaises(TemplateError, _check_terminators, 'foo.txt', text, crlf=True)

        text = ['line 1\r\n', 'line 2\r\n', 'line 3\r\n']
        self.assertEqual(_check_terminators('foo.txt', text, crlf=None), True)
        self.assertEqual(_check_terminators('foo.txt', text, crlf=True), True)
        self.assertRaises(TemplateError, _check_terminators, 'foo.txt', text, crlf=False)

        text = b'line 1\nline 2\nline 3\n'
        self.assertEqual(_check_terminators('foo.txt', text, crlf=None), False)
        self.assertEqual(_check_terminators('foo.txt', text, crlf=False), False)
        self.assertRaises(TemplateError, _check_terminators, 'foo.txt', text, crlf=True)

        text = b'line 1\r\nline 2\r\nline 3\r\n'
        self.assertEqual(_check_terminators('foo.txt', text, crlf=None), True)
        self.assertEqual(_check_terminators('foo.txt', text, crlf=True), True)
        self.assertRaises(TemplateError, _check_terminators, 'foo.txt', text, crlf=False)

        text = [b'line 1\n', b'line 2\n', b'line 3\n']
        self.assertEqual(_check_terminators('foo.txt', text, crlf=None), False)
        self.assertEqual(_check_terminators('foo.txt', text, crlf=False), False)
        self.assertRaises(TemplateError, _check_terminators, 'foo.txt', text, crlf=True)

        text = [b'line 1\r\n', b'line 2\r\n', b'line 3\r\n']
        self.assertEqual(_check_terminators('foo.txt', text, crlf=None), True)
        self.assertEqual(_check_terminators('foo.txt', text, crlf=True), True)
        self.assertRaises(TemplateError, _check_terminators, 'foo.txt', text, crlf=False)

        # Missing final terminator
        for text in ('line 1\nline 2\nline 3', b'line 1\nline 2\nline 3',
                     'line 1\r\nline 2\r\nline 3', b'line 1\r\nline 2\r\nline 3'):
            for crlf in (False, True, None):
                self.assertRaises(TemplateError, _check_terminators, 'foo.txt', text,
                                  crlf=crlf)

        # Mixed terminators
        for text in ('line 1\nline 2\nline 3\r\n', b'line 1\nline 2\nline 3\r\n',
                     'line 1\r\nline 2\r\nline 3\n', b'line 1\r\nline 2\n\nline 3\n'):
            for crlf in (False, True, None):
                self.assertRaises(TemplateError, _check_terminators, 'foo.txt', text,
                                  crlf=crlf)
