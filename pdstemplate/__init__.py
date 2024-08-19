##########################################################################################
# pdstemplate/__init__.py
##########################################################################################
"""PDS Ring-Moon Systems Node, SETI Institute

Definition of class PdsTemplate.

This class is used to generate PDS labels based on templates. Although specifically
designed to facilitate data deliveries by PDS data providers, the template system is
generic and could be used to generate files from templates for other purposes.
"""

import datetime
import hashlib
import numbers
import os
import pathlib
import re
import string
import textwrap
import time
from collections import deque, namedtuple
from xml.sax.saxutils import escape

import julian
import pdslogger

try:
    from ._version import __version__
except ImportError:
    __version__ = 'Version unspecified'

PDSTEMPLATE_VERSION_ID = __version__

# namedtuple class definition
#
# This is used to describe any subset of lines in the template containing one header and
# any label text up to the next header:
#   header      the header type, e.g., "$FOR" or "$IF" or $END_IF";
#   arg         any expression following the header, inside parentheses;
#   line        the line number of the template in which the header appears;
#   body        the text immediately following this header and up until the next header.
#
# When the template file is first read, it is described by a deque of _Section objects. If
# there is no header before the first line of the template, it is assigned a header type
# of "$ONCE().
_Section = namedtuple('_Section', ['header', 'arg', 'line', 'body'])

_NOESCAPE_FLAG = '!!NOESCAPE!!:'    # used internally


class TemplateError(ValueError):    # class for all template parsing exceptions
    pass


class PdsTemplate:
    """Class to generate PDS labels based on templates.

    See https://rms-pdstemplate.readthedocs.io/en/latest/module.html for details.
    """

    # This pattern matches a header record;
    #  groups(1) = line number; groups(2) = header; groups(3) = argument in parentheses
    _HEADER_WORDS = ['IF', 'ELSE_IF', 'ELSE', 'END_IF', 'FOR', 'END_FOR', 'ONCE',
                     'NOTE', 'END_NOTE']

    # This regular expression splits up the content of the template at the location of
    # each header. For each match, it returns three groups: a leading line number, the
    # header word ("IF", "FOR", etc.), and text inside the parentheses, if any.
    _HEADER_PATTERN = re.compile(r' *\$(\d+):(' + '|'.join(_HEADER_WORDS) + ')' +
                                 r'(\(.*\)|) *\n')

    _GLOBAL_LOGGER = pdslogger.NullLogger()     # default

    def __init__(self, template, *, content='', logger=None, xml=None):
        """Construct a PdsTemplate object from the contents of a template file.

        Parameters:
            template (str or pathlib.Path):
                Path of the input template file.
            content (str or list[str], optional):
                Alternative source of the template content rather than reading it from a
                file.
            logger (pdslogger.Pdslogger, optional):
                Logger to use. The default is pdslogger.NullLogger, which does no logging.
            xml (bool, optional):
                Use True to indicate that the template is in xml format; False otherwise.
                If not specified, an attempt is made to detect the format from the
                template.
        """

        logger = logger or PdsTemplate._GLOBAL_LOGGER

        self.template_path = pathlib.Path(template)
        try:
            # Read the template (if necessary)
            if not content:
                logger.info('Loading template', str(self.template_path))
                content = self.template_path.read_text()

            if isinstance(content, list):
                content = ''.join(content)

            # Infer terminator
            if content.endswith('\r\n'):
                logger.info('Terminator is <CR><LF>')
                self.terminator = '\r\n'
            elif content.endswith('\n'):
                logger.info('Terminator is <LF>')
                self.terminator = '\n'
            else:
                raise ValueError(f'Invalid terminator in template: {self.template_path}')

            # Convert to a list
            records = content.split(self.terminator)

            # Strip out comments
            records = self._strip_comments(records)

            # Detect XML if not specified
            if xml is None:
                self.xml = self._detect_xml(records)
            else:
                self.xml = xml

            # We need to save the line number in which each expression appears so that
            # error messages can be informative. To handle this, we temporarily write the
            # line number followed by a colon after each "$" found in the template.

            # Insert line numbers after each "$"
            numbered = [rec.rstrip().replace('$', f'${k+1}:')
                        for k, rec in enumerate(records)]

            # Merge back into a single string
            content = '\n'.join(numbered)

            # Split based on headers. The entire template is split into substrings...
            # 0: text before the first header, if any
            # 1: line number of the header
            # 2: header word ("IF", "FOR", etc.)
            # 3: text between parentheses in the header line
            # 4: template text from here to the next header line
            # 5: line number of the next header
            # etc.
            parts = PdsTemplate._HEADER_PATTERN.split(content)

            # parts[0] is '' if the file begins with a header, or else it is the body text
            # before the first header. The first header is always described by parts[1:4];
            # every part indexed 4*N + 1 is a line number.

            # Create a list of (header, arg, line, body) tuples, skipping parts[0]
            sections = [_Section('$'+h, a, int(l), b) for (l, h, a, b)
                        in zip(parts[1::4], parts[2::4], parts[3::4], parts[4::4])]

            # Convert to deque and prepend the leading body text if necessary
            sections = deque(sections)
            if parts[0]:
                sections.appendleft(_Section('$ONCE', '', 0, parts[0]))

            # Convert the sections into a list of execution blocks
            # Each call to _PdsBlock.new_block pops one or more items off top of the
            # deque; the loop repeats until no sections are left.
            self.blocks = deque()
            while sections:
                # Each call to _PdsBlock.new_block takes as many sections off the deque as
                # it needs to in order to be syntactically complete. For example, if the
                # the section at the top is "IF", it will remove the subsequent "ELSE_IF"
                # and "ELSE" sections from the deque. It will return when it encounters
                # the associated "END_IF". Calls are recursive, so this handles nesting
                # correctly.
                self.blocks.append(_PdsBlock.new_block(sections, self))

        except Exception as e:
            logger.exception(e, str(self.template_path))
            raise

        # Used to communicate error conditions during generate() or write()
        self.ERROR_COUNT = 0

    @staticmethod
    def _detect_xml(lines):
        """Determine whether the given content is xml."""

        if lines[0].find('<?xml') != -1:
            return True

        if (len(lines[0].split('<')) == len(lines[0].split('>')) and
                len(lines[0].split('<')) > 1):
            return True

        return False

    @staticmethod
    def _strip_comments(lines):
        """Strip inline comments from the given lines of text."""

        comment = '$NOTE:'
        newlines = []
        for line in lines:
            if line == '':
                newlines.append(line)
            else:
                content = line.partition(comment)
                if content[0] == '':
                    continue
                newlines.append(content[0].rstrip())

        return newlines

    @staticmethod
    def set_logger(logger=None):
        """Define the pdslogger globally for this module.

        Parameters:
            logger (pdslogger.PdsLogger, optional):
                The PdsLogger to use, or None to disable logging.
        """

        if logger:
            PdsTemplate._GLOBAL_LOGGER = logger
        else:
            PdsTemplate._GLOBAL_LOGGER = pdslogger.NullLogger()

    def generate(self, dictionary, label_path='', *,
                 terminator=None, raise_exceptions=False, logger=None, _state=None):
        r"""Generate the content of one label based on the template and dictionary.

        Parameters:
            dictionary (dict):
                The dictionary of parameters to replace in the template.
            label_path (str or pathlib.Path, optional):
                The output label file path.
            terminator (str, optional):
                The line terminator, either "\\n" or "\\r\\n". The default is to retain
                the line terminator used in the template.
            raise_exceptions (bool, optional):
                True to raise any exceptions encountered; False to log them and embed the
                error messages into the label, marked by "[[[" and "]]]".
            logger (pdslogger.PdsLogger, optional):
                The logger to use. The default is to use the global default logger.
            _state (_LabelState, optional):
                A _LabelState object to override the other input parameters, for use
                internally.

        Returns:
            str: The generated content.
        """

        # For recursive calls, _state contains the state of the generation process
        if _state:
            state = _state
            state.terminator = state.terminator or self.terminator
        else:
            state = _LabelState(dictionary, label_path,
                                terminator=(terminator or self.terminator),
                                raise_exceptions=raise_exceptions,
                                logger=(logger or PdsTemplate._GLOBAL_LOGGER))

        # Merge the predefined functions into this dictionary unless it was overridden
        local_dict = {}
        for key, func in PdsTemplate._PREDEFINED_FUNCTIONS.items():
            if key not in dictionary:
                local_dict[key] = func

        # These predefined functions are not static methods
        def TEMPLATE_PATH():
            return str(self.template_path)

        def LABEL_PATH():
            return str(state.label_path)

        local_dict['TEMPLATE_PATH'] = TEMPLATE_PATH
        local_dict['LABEL_PATH'] = LABEL_PATH

        # state.local_dicts contains variable names and definitions that are only
        # applicable at this point in the generation. They will become undefined when
        # a "END_IF" or "END_FOR" is encountered.
        state.local_dicts = [local_dict]

        # Generate the label content recursively
        results = deque()
        for block in self.blocks:
            try:
                results += block.execute(state)
            except Exception as e:  # pragma: no coverage - this is impossible to fake
                state.logger.error('Error generating label', state.label_path)
                if state.raise_exceptions:
                    raise
                state.logger.exception(e, state.label_path)
                break

        content = ''.join(results)

        # Update the terminator if necessary
        if state.terminator != '\n':
            content = content.replace('\n', state.terminator)

        self.ERROR_COUNT = state.error_count
        return content

    def write(self, dictionary, label_path, *,
              terminator=None, raise_exceptions=False, logger=None):
        r"""Write one label based on the template, dictionary, and output filename.

        Parameters:
            dictionary (dict):
                The dictionary of parameters to replace in the template.
            label_path (str or pathlib.Path, optional):
                The output label file path.
            terminator (str, optional):
                The line terminator, either "\\n" or "\\r\\n". The default is to retain
                the line terminator used in the template.
            raise_exceptions (bool, optional):
                True to raise any exceptions encountered; False to log them and embed the
                error messages into the label, marked by "[[[" and "]]]".
            logger (pdslogger.PdsLogger, optional):
                The logger to use. The default is to use the global default logger.
        """

        state = _LabelState(dictionary, label_path,
                            terminator=(terminator or self.terminator),
                            raise_exceptions=raise_exceptions,
                            logger=(logger or PdsTemplate._GLOBAL_LOGGER))

        state.logger.info('Generating label', str(state.label_path))

        content = self.generate(dictionary, _state=state)

        # Summarize the errors if necessary
        if state.error_count >= 1:
            state.logger.error(f'1 error{"s" if state.error_count > 1 else ""} '
                               'generating label', str(state.label_path))

        # Write the label
        label_path = pathlib.Path(state.label_path)
        with label_path.open('wb') as f:
            f.write(content.encode('utf-8'))
            if not content.endswith(state.terminator):
                f.write(state.terminator.encode('utf-8'))

    ######################################################################################
    # Utility functions
    ######################################################################################

    @staticmethod
    def BASENAME(filepath):
        """Return the basename of `filepath`, with the leading directory path removed.

        Parameters:
            filepath (str): The filepath.

        Returns:
            str: The basename of the filepath (the final filename).
        """

        return os.path.basename(filepath)

    @staticmethod
    def BOOL(value, true='true', false='false'):
        """Return `true` if `value` evaluates to Boolean True; otherwise, return `false`.

        Parameters:
            value (truthy): The expression to evaluate for truthy-ness.
            true (str, optional): The value to return for a True expression.
            false (str, optional): The value to return for a False expression.

        Returns:
            str: "true" or "false", or the given values in the `true` and/or `false`
            parameters.
        """

        return (true if value else false)

    _counters = {}

    @staticmethod
    def COUNTER(name, reset=False):
        """Return the value of a counter identified by `name`, starting at 1.

        Parameters:
            name (str): The name of the counter. If the counter has not been used
                before, it will start with a value of 1.
            reset (bool, optional): If True, reset the counter to a value of zero
                and return the value 0. The next time this counter is referenced,
                it will have the value 1.

        Returns:
            int: The value of the counter.
        """

        if name not in PdsTemplate._counters.keys():
            PdsTemplate._counters[name] = 0
        PdsTemplate._counters[name] += 1
        if reset:
            PdsTemplate._counters[name] = 0
        return PdsTemplate._counters[name]

    @staticmethod
    def CURRENT_TIME(date_only=False):
        """Return the current date/time in the local time zone.

        Parameters:
            date_only (bool, optional): Return only the date without the time.

        Returns:
            str: The current date/time in the local time zone as a formatted string of
            the form "yyyy-mm-ddThh:mm:sss" if `date_only=False` or "yyyy-mm-dd" if
            `date_only=True`.
        """

        if date_only:
            return datetime.datetime.now().isoformat()[:10]
        return datetime.datetime.now().isoformat()[:19]

    @staticmethod
    def CURRENT_ZULU(date_only=False):
        """Return the current UTC date/time.

        Parameters:
            date_only (bool, optional): Return only the date without the time.

        Returns:
            str: The current date/time in UTC as a formatted string of the form
            "yyyy-mm-ddThh:mm:sssZ" if `date_only=False` or "yyyy-mm-dd" if
            `date_only=True`.
        """

        if date_only:
            return time.strftime('%Y-%m-%d', time.gmtime())
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    @staticmethod
    def _DATETIME(value, offset=0, digits=None, date_type='YMD'):
        """Convert the given date/time string or time in TDB seconds to a year-month-day
        format with a trailing "Z". The date can be in any format parsable by the Julian
        module. An optional offset in seconds is applied. If the value is "UNK", then
        "UNK" is returned.
        """

        if isinstance(value, numbers.Real):
            if digits is None:
                digits = 3

            tai = julian.tai_from_tdb(value)

            # Convert to ISO format or return seconds
            if date_type in ('YMDT', 'YDT'):
                return julian.format_tai(tai + offset, order=date_type, sep='T',
                                         digits=digits, suffix='Z')
            else:
                (day, sec) = julian.day_sec_from_tai(tai + offset)
                return sec

        if value.strip() == 'UNK':
            return 'UNK'

        # Convert to day and seconds
        (day, sec) = julian.day_sec_from_string(value, timesys=True)[:2]

        # Retain the number of digits precision in the source, if appropriate
        if digits is None and offset % 1 == 0:
            parts = re.split(r'\d\d:\d\d:\d\d', value)
            if len(parts) == 2 and parts[1].startswith('.'):
                digits = len(re.match(r'(\.\d*)', parts[1]).group(1)) - 1

        # Apply offset if necessary
        if offset:
            tai = julian.tai_from_day_sec(day, sec)
            (day, sec) = julian.day_sec_from_tai(tai + offset)

        # Interpret the number of digits if still unknown
        if digits is None:
            if sec % 1 == 0.:
                digits = -1     # no fractional part, no decimal point
            else:
                digits = 3
        elif digits == 0:
            digits = -1         # suppress decimal point

        # Convert to ISO format or return seconds
        if date_type in ('YMDT', 'YDT'):
            return julian.format_day_sec(day, sec, order=date_type, sep='T',
                                         digits=digits, suffix='Z')
        else:
            return sec

    @staticmethod
    def DATETIME(time, offset=0, digits=None):
        """Convert `time` to an ISO date of the form "yyyy-mm-ddThh:mm:ss[.fff]Z".

        Parameters:
            time (str or float): The time as an arbitrary date/time string or TDB seconds.
                If `time` is "UNK", then "UNK" is returned.
            offset (float, optional): The offset, in seconds, to add to the time.
            digits (int, optional): The number of digits after the decimal point in the
                seconds field to return. If not specified, the appropriate number of
                digits for the time is used.

        Returns:
            str: The time in the format "yyyy-mm-ddThh:mm:ss[.fff]Z".
        """

        return PdsTemplate._DATETIME(time, offset, digits, date_type='YMDT')

    @staticmethod
    def DATETIME_DOY(time, offset=0, digits=None):
        """Convert `time` to an ISO date of the form "yyyy-dddThh:mm:ss[.fff]Z".

        Parameters:
            time (str or float): The time as an arbitrary date/time string or TDB seconds.
                If `time` is "UNK", then "UNK" is returned.
            offset (float, optional): The offset, in seconds, to add to the time.
            digits (int, optional): The number of digits after the decimal point in the
                seconds field to return. If not specified, the appropriate number of
                digits for the time is used.

        Returns:
            str: The time in the format "yyyy-dddThh:mm:ss[.fff]Z".
        """

        return PdsTemplate._DATETIME(time, offset, digits, date_type='YDT')

    @staticmethod
    def DAYSECS(time):
        """Return the number of elapsed seconds since the most recent midnight.

        Parameters:
            time (str or float): The time as an arbitrary date/time string or TDB seconds.
                If `time` is "UNK", then "UNK" is returned.

        Returns:
            float: The number of elapsed seconds since the most recent midnight.
        """

        if isinstance(time, numbers.Real):
            return PdsTemplate._DATETIME(time, 0, None, date_type='SEC')

        try:
            return julian.sec_from_string(time)
        except Exception:
            return PdsTemplate._DATETIME(time, 0, None, date_type='SEC')

    @staticmethod
    def FILE_BYTES(filepath):
        """Return the size in bytes of the file specified by `filepath`.

        Parameters:
            filepath (str): The filepath.

        Returns:
            int: The size in bytes of the file.
        """

        return os.path.getsize(filepath)

    # From http://stackoverflow.com/questions/3431825/-
    @staticmethod
    def FILE_MD5(filepath):
        """Return the MD5 checksum of the file specified by `filepath`.

        Parameters:
            filepath (str): The filepath.

        Returns:
            str: The MD5 checksum of the file.
        """

        blocksize = 65536
        with open(filepath, 'rb') as f:
            hasher = hashlib.md5()
            buf = f.read(blocksize)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(blocksize)

        f.close()
        return hasher.hexdigest()

    @staticmethod
    def FILE_RECORDS(filepath):
        """Return the number of records in the the file specified by `filepath`.

        Parameters:
            filepath (str): The filepath.

        Returns:
            int: The number of records in the file if it is ASCII;
            0 if the file is binary.
        """

        # We intentionally open this in non-binary mode so we don't have to
        # content with line terminator issues
        with open(filepath, 'r') as f:
            count = 0
            asciis = 0
            non_asciis = 0
            for line in f:
                for c in line:
                    if c in string.printable:
                        asciis += 1
                    else:
                        non_asciis += 1

                count += 1

        if non_asciis > 0.05 * asciis:
            return 0

        return count

    @staticmethod
    def FILE_TIME(filepath):
        """Return the modification time in the local time zone of a file.

        Parameters:
            filepath (str): The filepath.

        Returns:
            str: The modification time in the local time zone of the file specified by
            `filepath` in the form "yyyy-mm-ddThh:mm:ss".
        """

        timestamp = os.path.getmtime(filepath)
        return datetime.datetime.fromtimestamp(timestamp).isoformat()[:19]

    @staticmethod
    def FILE_ZULU(filepath):
        """Return the UTC modification time of a file.

        Parameters:
            filepath (str): The filepath.

        Returns:
            str: The UTC modification time of the file specified by `filepath` in the
            form "yyyy-mm-ddThh:mm:ssZ".
        """

        timestamp = os.path.getmtime(filepath)
        try:
            utc_dt = datetime.datetime.fromtimestamp(timestamp, datetime.UTC)
        except AttributeError:  # pragma: no cover
            # Python < 3.11
            utc_dt = datetime.datetime.utcfromtimestamp(timestamp)
        return utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    @staticmethod
    def NOESCAPE(text):
        """Prevent the given text from being escaped in the XML.

        If the template is XML, evaluated expressions are "escaped" to ensure that they
        are suitable for embedding in a PDS label. For example, ">" inside a string will
        be replaced by "&gt;". This function prevents `text` from being escaped in the
        label, allowing it to contain literal XML.

        Parameters:
            text (str): The text that should not be escaped.

        Returns:
            str: The text marked so that it won't be escaped.
        """

        return _NOESCAPE_FLAG + text

    @staticmethod
    def RAISE(exception, message):
        """Raise an exception with the given class `exception` and the `message`.

        Parameters:
            exception (Exception): The exception to raise.
            message (str): The message to include in the exception.

        Raises:
            Exception: The specified exception.
        """

        raise (exception)(message)

    @staticmethod
    def REPLACE_NA(value, na_value, flag='N/A'):
        """Return `na_value` if `value` equals "N/A"; otherwise, return `value`.

        Parameters:
            value (str or int or float or bool): The input value.
            flag (str or int or float or bool, optional): The value that means N/A.
                Defaults to the string "N/A".

        Returns:
            str or int or float or bool: The original value if it is not equal to
            `flag`, otherwise `na_value`.
        """

        if isinstance(value, str):
            value = value.strip()

        if value == flag:
            return na_value
        else:
            return value

    @staticmethod
    def REPLACE_UNK(value, unk_value):
        """Return `unk_value` if `value` equals "UNK"; otherwise, return `value`.

        Parameters:
            value (str or int or float or bool): The input value.

        Returns:
            str or int or float or bool: The original value if it is not equal to
            "UNK", otherwise `unk_value`.
        """

        return PdsTemplate.REPLACE_NA(value, unk_value, flag='UNK')

    @staticmethod
    def VERSION_ID():
        """Return the PdsTemplate version ID, e.g., "v0.1.0".

        Returns:
            str: The version ID.
        """

        return PDSTEMPLATE_VERSION_ID

    @staticmethod
    def WRAP(left, right, text, preserve_single_newlines=True):
        """Format `text` to fit between the `left` and `right` column numbers.

        The first line is not indented, so the text will begin in the column where "$WRAP"
        first appears in the template.

        Parameters:
            left (int): The starting column number, numbered from 0.
            right (int): the ending column number, numbered from 0.
            text (str): The text to wrap.
            preserve_single_newlines (bool, optional): If True, single newlines
                are preserved. If False, single newlines are just considered to be
                wrapped text and do not cause a break in the flow.

        Returns:
            str: The wrapped text.
        """

        if not preserve_single_newlines:
            # Remove any newlines between otherwise good text - we do this twice
            #   because sub is non-overlapping and single-character lines won't
            #   get treated properly
            # Remove any single newlines at the beginning or end of the string
            # Remove any pair of newlines after otherwise good text
            # Remove any leading or trailing spaces
            text = re.sub(r'([^\n])\n([^\n])', r'\1 \2', text)
            text = re.sub(r'([^\n])\n([^\n])', r'\1 \2', text)
            text = re.sub(r'([^\n])\n$', r'\1', text)
            text = re.sub(r'^\n([^\n])', r'\1', text)
            text = re.sub(r'([^\n])\n\n', r'\1\n', text)
            text = text.strip(' ')

        old_lines = text.splitlines()

        indent = left * ' '
        new_lines = []
        for line in old_lines:
            if line:
                new_lines += textwrap.wrap(line,
                                           width=right,
                                           initial_indent=indent,
                                           subsequent_indent=indent,
                                           break_long_words=False,
                                           break_on_hyphens=False)
            else:
                new_lines.append('')

        # strip the first left indent; this should be where "$WRAP" appears in the
        # template.
        new_lines[0] = new_lines[0][left:]

        return '\n'.join(new_lines)


PdsTemplate._PREDEFINED_FUNCTIONS = {}
PdsTemplate._PREDEFINED_FUNCTIONS['BASENAME'    ] = PdsTemplate.BASENAME
PdsTemplate._PREDEFINED_FUNCTIONS['BOOL'        ] = PdsTemplate.BOOL
PdsTemplate._PREDEFINED_FUNCTIONS['CURRENT_TIME'] = PdsTemplate.CURRENT_TIME
PdsTemplate._PREDEFINED_FUNCTIONS['CURRENT_ZULU'] = PdsTemplate.CURRENT_ZULU
PdsTemplate._PREDEFINED_FUNCTIONS['COUNTER'     ] = PdsTemplate.COUNTER
PdsTemplate._PREDEFINED_FUNCTIONS['DATETIME'    ] = PdsTemplate.DATETIME
PdsTemplate._PREDEFINED_FUNCTIONS['DATETIME_DOY'] = PdsTemplate.DATETIME_DOY
PdsTemplate._PREDEFINED_FUNCTIONS['DAYSECS'     ] = PdsTemplate.DAYSECS
PdsTemplate._PREDEFINED_FUNCTIONS['FILE_BYTES'  ] = PdsTemplate.FILE_BYTES
PdsTemplate._PREDEFINED_FUNCTIONS['FILE_MD5'    ] = PdsTemplate.FILE_MD5
PdsTemplate._PREDEFINED_FUNCTIONS['FILE_RECORDS'] = PdsTemplate.FILE_RECORDS
PdsTemplate._PREDEFINED_FUNCTIONS['FILE_TIME'   ] = PdsTemplate.FILE_TIME
PdsTemplate._PREDEFINED_FUNCTIONS['FILE_ZULU'   ] = PdsTemplate.FILE_ZULU
PdsTemplate._PREDEFINED_FUNCTIONS['NOESCAPE'    ] = PdsTemplate.NOESCAPE
PdsTemplate._PREDEFINED_FUNCTIONS['RAISE'       ] = PdsTemplate.RAISE
PdsTemplate._PREDEFINED_FUNCTIONS['REPLACE_NA'  ] = PdsTemplate.REPLACE_NA
PdsTemplate._PREDEFINED_FUNCTIONS['REPLACE_UNK' ] = PdsTemplate.REPLACE_UNK
PdsTemplate._PREDEFINED_FUNCTIONS['VERSION_ID'  ] = PdsTemplate.VERSION_ID
PdsTemplate._PREDEFINED_FUNCTIONS['WRAP'        ] = PdsTemplate.WRAP


##########################################################################################
# LabelStatus class
##########################################################################################

class _LabelState(object):
    """Internal class to carry status information about where we are in the template and
    the label generation.
    """

    def __init__(self, dictionary, label_path='', *,
                 terminator=None, raise_exceptions=False, logger=None):

        self.label_path = label_path
        self.terminator = terminator
        self.raise_exceptions = raise_exceptions
        self.logger = logger or PdsTemplate._GLOBAL_LOGGER

        self.global_dict = dictionary
        self.local_dicts = [{}]
        self.error_count = 0

    # def copy(self):
    #     return _LabelState(self.global_dict, self.label_path,
    #                        terminator=self.terminator,
    #                        raise_exceptions=self.raise_exceptions,
    #                        logger=self.logger)


##########################################################################################
# _PdsBlock class and subclasses
##########################################################################################

class _PdsBlock(object):
    """_PdsBlock is an abstract class that describes a hierarchical section of the label
    template, beginning with a header. There are individual subclasses to support these
    different types of headers:
        _PdsForBlock   for $FOR
        _PdsIfBlock    for $IF and $ELSE_IF
        _PdsElseBlock  for $ELSE
        _PdsNoteBlock  for $NOTE
        _PdsOnceBlock  for $END_FOR, $END_IF, $END_NOTE, and any other section of the
                       template for which what follows is included exactly once.

    Each _PdsBlock always represents a logically complete section of the template, from
    one header up to its logical completion. For example, if a template contains this
    sequence of headers:
        $FOR(...)
          $IF(...)
          $ELSE
          $END_IF
        $END_FOR
    then every line of the template from the $FOR header down to (but not including) the
    $END_FOR will be described by one _PdsForBlock. Every _PdsBlock object contains a
    "sub_block" attribute, which is a deque of all the _PdsBlocks embedded within it. In
    this case, the sub_blocks attribute will contain a single _PdsIfBlock, which in turn
    will contain a single _PdsElseBlock.

    Each _PdsBlock also has a "body" attribute, which represents the template text between
    this header and the next header. That text is pre-processed for speedier execution by
    locating all the Python expressions (surrounded by "$") embedded within it.

    The constructor for each _PdsBlock subclass takes a single deque of Sequence objects
    as input. As a side-effect, it removes one or more items from the front of the deque
    until its definition, including any nested _PdsBlocks, is complete. The constructor
    handles any nested _PdsBlocks within it by calling the constructor recursively and
    saving the results of each recursive call in its sub_blocks attribute.

    Each _PdsBlock subclass has its own execute() method. This method contains the logic
    that determines whether (for _PdsIfBlocks and _PdsElseBlocks) or how many times (for
    _PdsForBlocks) its body and sub_blocks are written into the label file. Nesting is
    handled by having each _PdsBlock call the execute method of the _PdsBlocks nested
    within it.
    """

    # This pattern matches an internal assignment within an expression;
    # group(0) = variable name; group(1) = expression
    NAMED_PATTERN = re.compile(r' *([A-Za-z_]\w*) *=([^=].*)')
    ELSE_HEADERS = {'$ELSE_IF', '$ELSE', '$END_IF'}

    @staticmethod
    def new_block(sections, template):
        """Construct an _PdsBlock subclass based on a deque of _Section tuples (header,
        arg, line,  body). Pop as many _Section tuples off the top of the deque as are
        necessary to complete the block and any of its internal blocks, recursively.
        """

        (header, arg, line, body) = sections[0]
        if header.startswith('$ONCE'):
            return _PdsOnceBlock(sections, template)
        if header.startswith('$NOTE'):
            return _PdsNoteBlock(sections, template)
        if header == '$FOR':
            return _PdsForBlock(sections, template)
        if header == '$IF':
            return _PdsIfBlock(sections, template)

        if header == '$END_FOR':
            raise TemplateError(f'$END_FOR without matching $FOR at line {line}')
        if header == '$END_NOTE':
            raise TemplateError(f'$END_NOTE without matching $NOTE at line {line}')
        if header in _PdsBlock.ELSE_HEADERS:  # pragma: no coverage - can't get here
            raise TemplateError(f'{header} without matching $IF at line {line}')

        raise TemplateError(f'unrecognized header at line {line}: {header}({arg})'
                            )  # pragma: no coverage - can't get here

    def preprocess_body(self):
        """Preprocess body text from the template by locating all of the embedded
        Python expressions and returning a list of substrings, where odd-numbered entries
        are the expressions to evaluate, along with the associated line number.
        """

        # Split at the "$"
        parts = self.body.split('$')
        if len(parts) % 2 != 1:
            line = parts[-1].partition(':')[0]
            raise TemplateError(f'mismatched "$" at line {line}')

        # Because we inserted the line number after every "$", every part except the first
        # now begins with a number followed by ":". We need to make the first item
        # consistent with the others
        parts[0] = '0:' + parts[0]

        # new_parts is a deque of values that alternates between label substrings and
        # tuples (expression, name, line)

        new_parts = deque()
        for k, part in enumerate(parts):

            # Strip off the line number that we inserted after every "$"
            (line, _, part) = part.partition(':')

            # Even-numbered items are literal text
            if k % 2 == 0:
                new_parts.append(part)

            # Odd-numbered are expressions, possibly with a name
            else:

                # Look for a name
                match = _PdsBlock.NAMED_PATTERN.fullmatch(part)
                if match:
                    expression = match.group(2)
                    name = match.group(1)
                else:
                    expression = part
                    name = ''

                new_parts.append((expression, name, line))

        self.preprocessed = new_parts

    def evaluate_expression(self, expression, line, state):
        """Evaluate a single expression using the given dictionaries as needed. Identify
        the line number if an error occurs.
        """

        if expression:
            try:
                return eval(expression, state.global_dict, state.local_dicts[-1])
            except Exception as e:
                state.error_count += 1
                message = f'{type(e).__name__}({e}) at line {line}'
                state.logger.error(message, state.label_path)
                raise type(e)(message) from e   # pass the exception forward

        # An empty expression is just a "$" followed by another "$"
        else:
            return '$'      # "$$" maps to "$"

    def execute_body(self, state):
        """Generate the label text defined by this body, using the given dictionaries to
        fill in the blanks. The content is returned as a deque of strings, which are to be
        joined upon completion to create the content of the label.
        """

        results = deque()
        for k, item in enumerate(self.preprocessed):

            # Even-numbered items are literal text
            if k % 2 == 0:
                results.append(item)

            # Odd-numbered items are expressions
            else:
                (expression, name, line) = item
                try:
                    value = self.evaluate_expression(expression, line, state)
                except Exception as e:
                    state.logger.exception(e, state.label_path)
                    if state.raise_exceptions:
                        raise
                    value = f'[[[{e}]]]'        # put the error text into label

                if name:
                    state.local_dicts[-1][name] = value

                # Format a float without unnecessary trailing zeros
                if isinstance(value, float):
                    value = _PdsBlock._pretty_truncate(value)
                else:
                    # Otherwise, just convert to string
                    value = str(value)

                # Escape
                if self.template.xml:
                    if value.startswith(_NOESCAPE_FLAG):
                        value = value[len(_NOESCAPE_FLAG):]
                    else:
                        value = escape(value)

                results.append(value)

        return results

    def execute(self, state):
        """Evaluate this block of label text, using the dictionaries to fill in the
        blanks. The content is returned as a deque of strings, to be joined upon
        completion to create the label content.

        This base class method implements the default procedure, which is to execute the
        body plus any sub-blocks exactly once. It is overridden for $FOR and $IF blocks.
        The execute methods write all of their error messages to the logger rather than
        raising exceptions. Each error also increments the PdsTemplate's ERROR_COUNT.
        """

        results = self.execute_body(state)

        for block in self.sub_blocks:
            results += block.execute(state)

        return results

    ######################################################################################
    # Utility
    ######################################################################################

    # Modify a number if it contains ten 0's or 9's in a row, followed by other digits
    _ZEROS = re.compile(r'(.*[.1-9])0{10,99}[1-9]\d*')
    _NINES = re.compile(r'(.*\.\d+9{10,99})[0-8]\d*')

    def _pretty_truncate(value):
        """Convert a floating-point number to a string, while suppressing any extraneous
        trailing digits by rounding to the nearest value that does not have them.

        This eliminates numbers like "1.0000000000000241" and "0.9999999999999865" in the
        label, by suppressing insignificant digits.
        """

        str_value = str(value)

        (mantissa, e, exponent) = str_value.partition('e')
        if mantissa.endswith('.0'):
            return mantissa[:-1] + e + exponent

        # Handle trailing zeros
        match = _PdsBlock._ZEROS.fullmatch(mantissa)
        if match:
            return match.group(1) + e + exponent

        # Check for trailing nines
        match = _PdsBlock._NINES.fullmatch(mantissa)
        if not match:
            # Value looks OK; return as is
            return str_value

        # Replace every digit in the mantissa with a zero
        # This creates an string expression equal to zero, but using the exact same
        # format, including sign.
        offset_str = match.group(1)
        for c in '123456789':       # replace non-zero digits with zeros
            offset_str = offset_str.replace(c, '0')

        # Now replace the last digit with "1"
        # This is an offset (positive or negative) to zero out the trailing digits
        offset_str = offset_str[:-1] + '1'      # replace the last digit with "1"

        # Apply the offset and return
        value = float(match.group(1)) + float(offset_str)
        return str(value).rstrip('0') + e + exponent


################################################

class _PdsOnceBlock(_PdsBlock):
    """A block of text to be included once. This applies to a literal $ONCE header, and
    also to $END_FOR, $END_IF, and $END_NOTE headers."""

    WORD = r' *([A-Za-z_]\w*) *'
    PATTERN = re.compile(r'\(' + WORD + r'=([^=].*)\)')

    def __init__(self, sections, template):
        """Define a block to be executed once. Pop the associated section off the stack.

        Note that the name of a properly matched $END_IF header is changed internally to
        $ONCE-$END_IF during template initialization. Also, the name of a properly matched
        $END_FOR is changed to $ONCE-$END_FOR during template initialization, and
        $END_NOTE is changed to $ONCE-$END_NOTE. This code must strip away the $ONCE-
        prefix.
        """

        (header, arg, line, body) = sections.popleft()
        self.header = header.replace('$ONCE-', '')
        self.arg = arg
        self.name = ''
        self.line = line
        self.body = body
        self.preprocess_body()
        self.sub_blocks = deque()
        self.template = template

        # Pop one entry off the local dictionary stack at the end of IF and FOR loops
        self.pop_local_dict = header in ('$ONCE-$END_FOR', '$ONCE-$END_IF')

        match = _PdsOnceBlock.PATTERN.fullmatch(arg)
        if match:
            (self.name, self.arg) = match.groups()

        if header == '$ONCE' and arg and not self.name:
            raise TemplateError(f'{self.header} expression does not define a variable ' +
                                f'at line {line}')

        if header.startswith('$ONCE-') and arg:  # pragma: no coverage
            # This can't happen in the current code because IF, FOR, and NOTE all
            # ignore the arg that's present in the template and pass in '' instead
            raise TemplateError(f'extraneous argument for {self.header} at line {line}')

    def execute(self, state):
        """Evaluate this block of label text, using the dictionaries to fill in the
        blanks. The content is returned as a deque of strings, to be joined upon
        completion to create the label content.
        """

        # Pop the local dictionary stack if necessary
        if self.pop_local_dict:
            state.local_dicts.pop()

        # Define the local variable if necessary
        if self.arg:
            try:
                result = self.evaluate_expression(self.arg, self.line, state)
            except Exception as e:
                state.logger.exception(e, state.label_path)
                if state.raise_exceptions:
                    raise
                return deque([f'[[[{e}]]]'])  # include the error message inside the label

            # Write new values into the local dictionary, not a copy
            state.local_dicts[-1][self.name] = result

        # Execute the default procedure, which is to include the body and any sub-blocks
        # exactly once
        return _PdsBlock.execute(self, state)


################################################

class _PdsNoteBlock(_PdsBlock):
    """A block of text between $NOTE and $END_NOTE, not to be included."""

    def __init__(self, sections, template):
        """Define a block to be executed zero times. Pop the associated section off the
        stack.
        """

        (header, arg, line, body) = sections.popleft()
        self.header = header
        self.arg = arg
        self.line = line
        self.body = body
        self.preprocess_body()
        self.sub_blocks = deque()
        self.template = template

        if arg:
            raise TemplateError(f'extraneous argument for {self.header} at line {line}')

        # Save internal sub-blocks until the $END_NOTE is found
        self.sub_blocks = deque()
        while sections and sections[0].header != '$END_NOTE':
            self.sub_blocks.append(_PdsBlock.new_block(sections, template))

        if not sections:
            raise TemplateError(f'unterminated {header} block starting at line {line}')

        # Handle the matching $END_NOTE section as $ONCE
        (header, arg, line, body) = sections[0]
        sections[0] = _Section('$ONCE-' + header, '', line, body)

    def execute(self, state):
        """Evaluate this block of label text, using the dictionaries to fill in the
        blanks. The content is returned as a deque of strings, to be joined upon
        completion to create the label content.
     """

        return deque()


################################################

class _PdsForBlock(_PdsBlock):
    """A block of text preceded by $FOR. It is to be evaluated zero or more times, by
    iterating through the argument.
    """

    # These patterns match one, two, or three variable names, followed by "=", to be used
    # as temporary variables inside this section of the label
    WORD = r' *([A-Za-z_]\w*) *'
    PATTERN1 = re.compile(r'\(' + WORD + r'=([^=].*)\)')
    PATTERN2 = re.compile(r'\(' + WORD + ',' + WORD + r'=([^=].*)\)')
    PATTERN3 = re.compile(r'\(' + WORD + ',' + WORD + ',' + WORD + r'=([^=].*)\)')

    def __init__(self, sections, template):
        (header, arg, line, body) = sections.popleft()
        self.header = header
        self.line = line
        self.body = body
        self.preprocess_body()
        self.template = template

        # Interpret arg as (value=expression), (value,index=expression), etc.
        if not arg:
            raise TemplateError(f'missing argument for {header} at line {line}')

        self.value = 'VALUE'
        self.index = 'INDEX'
        self.length = 'LENGTH'
        self.arg = arg

        for pattern in (_PdsForBlock.PATTERN1, _PdsForBlock.PATTERN2,
                        _PdsForBlock.PATTERN3):
            match = pattern.fullmatch(arg)
            if match:
                groups = match.groups()
                self.arg = groups[-1]
                self.value = groups[0]
                if len(groups) > 2:
                    self.index = groups[1]
                if len(groups) > 3:
                    self.length = groups[2]
                break

        # Save internal sub-blocks until the $END_FOR is found
        self.sub_blocks = deque()
        while sections and sections[0].header != '$END_FOR':
            self.sub_blocks.append(_PdsBlock.new_block(sections, template))

        if not sections:
            raise TemplateError(f'unterminated {header} block starting at line {line}')

        # Handle the matching $END_FOR section as $ONCE
        (header, arg, line, body) = sections[0]
        sections[0] = _Section('$ONCE-' + header, '', line, body)

    def execute(self, state):
        """Evaluate this block of label text, using the dictionaries to fill in the
        blanks. The content is returned as a deque of strings, to be joined upon
        completion.
        """

        try:
            iterator = self.evaluate_expression(self.arg, self.line, state)
        except Exception as e:
            state.logger.exception(e, state.label_path)
            if state.raise_exceptions:
                raise
            return deque([f'[[[{e}]]]'])    # include the error message inside the label

        # Create a new local dictionary
        state.local_dicts.append(state.local_dicts[-1].copy())

        results = deque()
        iterator = list(iterator)
        state.local_dicts[-1][self.length] = len(iterator)
        for k, item in enumerate(iterator):
            state.local_dicts[-1][self.value] = item
            state.local_dicts[-1][self.index] = k
            results += _PdsBlock.execute(self, state)

        return results


################################################

class _PdsIfBlock(_PdsBlock):
    """A block of text to be included if the argument evaluates to True, either $IF or
    $ELSE_IF.
    """

    WORD = r' *([A-Za-z_]\w*) *'
    PATTERN = re.compile(r'\(' + WORD + r'=([^=].*)\)')

    def __init__(self, sections, template):
        (header, arg, line, body) = sections.popleft()
        self.header = header
        self.arg = arg
        self.name = ''
        self.line = line
        self.body = body
        self.preprocess_body()
        self.template = template

        if not arg:
            raise TemplateError(f'missing argument for {header} at line {line}')

        match = _PdsIfBlock.PATTERN.fullmatch(arg)
        if match:
            (self.name, self.arg) = match.groups()

        self.else_if_block = None
        self.else_block = None

        self.sub_blocks = deque()
        while sections and sections[0].header not in _PdsBlock.ELSE_HEADERS:
            self.sub_blocks.append(_PdsBlock.new_block(sections, template))

        if not sections:
            raise TemplateError(f'unterminated {header} block starting at line {line}')

        # Handle the first $ELSE_IF. It will handle more $ELSE_IFs and $ELSEs recursively.
        if sections[0].header == '$ELSE_IF':
            self.else_if_block = _PdsIfBlock(sections, template)
            return

        # Handle $ELSE
        if sections[0].header == '$ELSE':
            self.else_block = _PdsElseBlock(sections, template)
            return

        # Handle the matching $END_IF section as $ONCE
        (header, arg, line, body) = sections[0]
        sections[0] = _Section('$ONCE-' + header, '', line, body)

    def execute(self, state):
        """Evaluate this block of label text, using the dictionaries to fill in the
        blanks. The content is returned as a deque of strings, to be joined upon
        completion to be joined upon completion to create the label content.
        """

        try:
            status = self.evaluate_expression(self.arg, self.line, state)
        except Exception as e:
            if state.raise_exceptions:
                state.logger.exception(e, state.label_path)
                raise
            return deque([f'[[[{e}]]]'])  # include the error message inside the label

        # Create a new local dictionary for IF but not ELSE_IF
        if self.header == '$IF':
            state.local_dicts.append(state.local_dicts[-1].copy())

        if self.name:
            state.local_dicts[-1][self.name] = status

        if status:
            return _PdsBlock.execute(self, state)

        elif self.else_if_block:
            return self.else_if_block.execute(state)

        elif self.else_block:
            return self.else_block.execute(state)

        else:
            return deque()  # empty response


################################################

class _PdsElseBlock(_PdsBlock):

    def __init__(self, sections, template):
        (header, arg, line, body) = sections.popleft()
        self.header = header
        self.arg = arg
        self.line = line
        self.body = body
        self.preprocess_body()
        self.template = template

        # Save internal sub-blocks until the $END_IF is found
        self.sub_blocks = deque()
        while sections and sections[0].header != '$END_IF':
            self.sub_blocks.append(_PdsBlock.new_block(sections, template))

        if not sections:
            raise TemplateError(f'unterminated {header} block starting at line {line}')

        # Handle the matching $END_IF section as $ONCE
        (header, arg, line, body) = sections[0]
        sections[0] = _Section('$ONCE-' + header, '', line, body)

##########################################################################################
