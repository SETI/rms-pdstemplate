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
from collections import deque

import julian

try:
    from ._version import __version__
except ImportError:                                                 # pragma: no cover
    __version__ = 'Version unspecified'

from ._utils import TemplateError, TemplateAbort                    # noqa: F401
    # Unused here but included to support "from pdstemplate import TemplateError", etc.

from ._utils import _RaisedException, _NOESCAPE_FLAG, getenv_include_dirs
from ._utils import set_logger, get_logger, set_log_level, set_log_format
from ._pdsblock import _PdsBlock, _PdsIncludeBlock


class PdsTemplate:
    """Class to generate PDS labels based on a template.

    See https://rms-pdstemplate.readthedocs.io/en/latest/module.html for details.
    """

    # We need to handle certain attributes as class variables because we need to support
    # the various default functions such as LABEL_PATH(), etc., and these function execute
    # within a template without any associated context. Therefore, the PdsTemplate module
    # cannot operate in a multi-threaded environment!
    _CURRENT_TEMPLATE = None
    _CURRENT_LABEL_PATH = ''
    _CURRENT_GLOBAL_DICT = {}

    def __init__(self, template, content='', *, xml=None, crlf=None, preprocess=None,
                 args=(), kwargs={}, includes=[], upper_e=False):
        """Construct a PdsTemplate object from the contents of a template file.

        Parameters:
            template (str or pathlib.Path):
                Path of the input template file.
            content (str or list[str], optional):
                Alternative source of the template content rather than reading it from a
                file.
            xml (bool, optional):
                Use True to indicate that the template is in xml format; False otherwise.
                If not specified, an attempt is made to detect the format from the
                template.
            crlf (bool, optional):
                True to indicate that the line termination should be <CR><LF>; False for
                <LF> only. If not specified, the line termination is inferred from the
                template.
            preprocess (function or list[function], optional):
                An optional function or list of functions that receive the path of a
                template plus the template's content and return revised content. The
                template's content is provided as a single string with <LF> line
                terminators.
            args (tuple or list):
                Any arguments to be passed to the first preprocess function after the
                template's content.
            kwargs (dict):
                Any keywords=value arguments to be passed to the first preprocess
                function.
            includes (str, pathlib.Path, or list):
                One or more directory paths where template include files can be found. The
                directory containing `template` is always searched first. Note that
                include paths can also be specified using the environment variable
                PDSTEMPLATE_INCLUDES, which should contain one or more directory paths
                separated by colons. Any directories specified here are searched before
                those defined by PDSTEMPLATE_INCLUDES.
            upper_e (bool, optional):
                True to force the "E" in the exponents of floating-point numbers to be
                upper case.
        """

        self.template_path = pathlib.Path(template)
        PdsTemplate._CURRENT_TEMPLATE = self
        PdsTemplate._CURRENT_LABEL_PATH = ''
        PdsTemplate._CURRENT_GLOBAL_DICT = {}

        includes = [includes] if isinstance(includes, (str, pathlib.Path)) else includes
        self._includes = [pathlib.Path(dir) for dir in includes]

        self.upper_e = bool(upper_e)

        logger = get_logger()
        logger.info('New PdsTemplate', self.template_path)
        try:
            # Read the template if necessary; use binary to preserve line terminators
            if not content:
                logger.debug('Reading template', self.template_path)
                content = self.template_path.read_bytes().decode('utf-8')

            # Check the line terminators
            if crlf is None:
                if isinstance(content, list):
                    crlf = content[0].endswith('\r\n')
                else:
                    crlf = content.endswith('\r\n')
                logger.debug(f'Inferred terminator is {"<CR><LF>" if crlf else "<LF>"}')
            self.crlf = crlf
            self.terminator = '\r\n' if self.crlf else '\n'

            # Convert to a single string with <LF> line terminators
            if not isinstance(content, list):
                content = content.split('\n')
                if not content[-1]:         # strip extraneous empty string at end
                    content = content[:-1]

            content = [c.rstrip('\r\n') for c in content] + ['']
            content = '\n'.join(content)

            # Preprocess the explicit $INCLUDES
            content = self._preprocess_includes(content)

            # Apply any additional preprocessor
            if preprocess:
                if not isinstance(preprocess, list):
                    preprocess = [preprocess]

                for k, func in enumerate(preprocess):
                    logger.info('Preprocessing with ' + func.__name__)
                    if k == 0:
                        content = func(self.template_path, content, *args, **kwargs)
                    else:
                        content = func(self.template_path, content)

            self.content = content

            # If the template has been pre-processed, line numbers in the error messages
            # will no longer be correct (because they are the line numbers _after_
            # pre-processing. Inside _pdsblock.py, this flag tells the logger to print the
            # actual content of the line causing the error, for simpler diagnosis of the
            # problem. DISABLED for now.
            # self._include_more_error_info = (content != before)
            self._include_more_error_info = False

            # Detect XML if not specified
            if xml is None:
                self.xml = self._detect_xml(content)
            else:
                self.xml = xml

            # Compile into a deque of _PdsBlock objects
            self._blocks = _PdsBlock.process_headers(content, self)

        except Exception as err:
            logger.exception(err, self.template_path)
            raise

        # For managing errors and warnings raised during generate()
        self._fatal_count = 0
        self._error_count = 0
        self._warning_count = 0

    def _include_dirs(self):
        """Ordered list of all include directories to search."""

        return [self.template_path.parent] + self._includes + getenv_include_dirs()

    _INCLUDE_REGEX = re.compile(r'(?<![^\n]) *\$INCLUDE\( *(\'[^\']+\'|"[^"]+") *\) *\n')

    def _preprocess_includes(self, content):
        """Pre-process the template content for $INCLUDE directives with explicit paths.

        Paths containing expressions of any sort are left alone.
        """

        # Split based on $INCLUDE headers. The entire template is split into substrings:
        # - Even indices contain text between the $INCLUDES
        # - Odd indices contain the file name surrounded by quotes
        parts = PdsTemplate._INCLUDE_REGEX.split(content)
        for k, part in enumerate(parts):
            if k % 2 == 1:
                part = _PdsIncludeBlock.get_content(part[1:-1], self._include_dirs())
                part = self._preprocess_includes(part)      # process recursively
                parts[k] = part

        return ''.join(parts)

    @staticmethod
    def _detect_xml(content):
        """Determine whether the given content is xml."""

        first_line = content.partition('\n')[0]

        if '<?xml' in first_line:
            return True

        count = len(first_line.split('<'))
        if count > 1 and count == len(first_line.split('>')):
            return True

        return False

    def generate(self, dictionary, label_path='', *, raise_exceptions=False,
                 hide_warnings=False, abort_on_error=False):
        """Generate the content of one label based on the template and dictionary.

        Parameters:
            dictionary (dict):
                The dictionary of parameters to replace in the template.
            label_path (str or pathlib.Path, optional):
                The output label file path, used for error messages.
            raise_exceptions (bool, optional):
                True to raise any exceptions encountered; False to log them and embed the
                error message into the label surrounded by "[[[" and "]]]".
            hide_warnings (bool, optional):
                True to hide warning messages.
            abort_on_error (bool, optional):
                True to abort the generation process if a validation error is encountered.
                If `raise_exceptions` is True, an exception will be raised; otherwise, the
                error will logged and an empty string will be returned.

        Returns:
            str: The generated content.
        """

        label_path = pathlib.Path(label_path) if label_path else ''

        # Initialize
        PdsTemplate._CURRENT_TEMPLATE = self
        PdsTemplate._CURRENT_LABEL_PATH = label_path

        # Add predefined functions to the dictionary
        global_dict = dictionary.copy()
        for name, value in PdsTemplate._PREDEFINED_FUNCTIONS.items():
            if name not in global_dict:
                global_dict[name] = value
        global_dict['hide_warnings'] = bool(hide_warnings)
        global_dict['abort_on_error'] = bool(abort_on_error)
        PdsTemplate._CURRENT_GLOBAL_DICT = global_dict

        state = _LabelState(self, global_dict, label_path,
                            raise_exceptions=raise_exceptions)

        # Generate the label content recursively
        results = deque()
        logger = get_logger()
        logger.open('Generating label', label_path)
        try:
            for block in self._blocks:
                results += block.execute(state)
        except TemplateAbort as err:
            logger.fatal('**** ' + err.message, label_path)
        finally:
            (fatals, errors, warns, total) = logger.close()

        content = ''.join(results)
        self._fatal_count = fatals
        self._error_count = errors
        self._warning_count = warns

        # Update the terminator if necessary
        if self.terminator != '\n':
            content = content.replace('\n', self.terminator)

        # Reset global symbols
        PdsTemplate._CURRENT_LABEL_PATH = ''
        PdsTemplate._CURRENT_GLOBAL_DICT = {}

        return content

    def write(self, dictionary, label_path, *, mode='save', backup=False,
              raise_exceptions=False):
        """Write one label based on the template, dictionary, and output filename.

        Parameters:
            dictionary (dict):
                The dictionary of parameters to replace in the template.
            label_path (str or pathlib.Path, optional):
                The output label file path.
            mode (str, optional):
                "save" to save the new label content regardless of any warnings or errors;
                "repair" to save the new label if warnings occurred but no errors;
                "validate" to log errors and warnings but never save the new label file.
            backup (bool, optional):
                If True and an existing file of the same name as label_path already
                exists, that file is renamed with a suffix indicating its original
                modification date. The format is "_yyyy-mm-ddThh-mm-ss" and it appears
                after the file stem, before the extension.
            raise_exceptions (bool, optional):
                True to raise any exceptions encountered; False to log them and embed the
                error message into the label surrounded by "[[[" and "]]]".

        Returns:
            int: Number of errors issued.
            int: Number of warnings issued.
        """

        if mode not in {'save', 'repair', 'validate'}:
            raise ValueError('invalid mode value: ' + repr(mode))

        label_path = pathlib.Path(label_path)
        content = self.generate(dictionary, label_path, raise_exceptions=raise_exceptions,
                                hide_warnings=(mode == 'save'),
                                abort_on_error=(mode != 'save'))
        fatals = self._fatal_count
        errors = self._error_count
        warns = self._warning_count
        logger = get_logger()

        if fatals and not errors:
            errors = fatals

        # Validation case
        if mode == 'validate':
            if errors:
                plural = 's' if errors > 1 else ''
                logger.error(f'Validation failed with {errors} error{plural}', label_path,
                             force=True)
            elif warns:
                plural = 's' if warns > 1 else ''
                logger.warn(f'Validation failed with {warns} warning{plural}', label_path,
                            force=True)
            else:
                logger.info('Validation successful', label_path, force=True)

        # Repair case
        elif mode == 'repair':
            if errors:
                plural = 's' if errors > 1 else ''
                logger.warn(f'Repair failed with {errors} error{plural}', label_path)
            elif label_path.exists():
                old_content = label_path.read_bytes().decode('utf-8')
                if old_content == content:
                    logger.info('Repair unnecessary; content is unchanged', label_path)
                else:
                    mode = 'save'       # re-save the file
            else:
                plural = 's' if warns > 1 else ''
                logger.info(f'Repairing {warns} warning{plural}', label_path,
                            force=True)
                mode = 'save'           # proceed with saving the file

        # Otherwise, save
        if mode != 'save':
            return (errors, warns)

        # Don't save a file after a fatal error
        if fatals:
            logger.error('File save aborted due to prior errors')
            return (errors, warns)

        # Backup existing label if necessary
        exists = label_path.exists()
        if exists and backup:
            date = datetime.datetime.fromtimestamp(os.path.getmtime(label_path))
            datestr = date.isoformat(timespec='seconds').replace(':', '-')
            backup_path = label_path.parent / (label_path.stem + '_' + datestr +
                                               label_path.suffix)
            label_path.rename(backup_path)
            logger.info('Existing label renamed to', backup_path)
            exists = False

        # Write label
        with label_path.open('wb') as f:
            f.write(content.encode('utf-8'))
            if content and not content.endswith(self.terminator):
                f.write(self.terminator.encode('utf-8'))

        # Log event
        if exists:
            logger.info('Label re-written', label_path)
        else:
            logger.info('Label written', label_path)

        return (errors, warns)

    @staticmethod
    def log(level, message, filepath='', *, force=False):
        """Send a message to the current logger.

        This allows external modules to issue warnings and other messages.

        Parameters:
            level (int or str): Level of the message: 'info', 'error', 'warn', etc.
            message (str): Text of the warning message.
            filepath (str or pathlib.Path, optional): File path to include in the message.
            force (bool, optional): True to force the logging of the message regardless
                of the level.
        """

        get_logger().log(level, message, filepath, force=force)

    @staticmethod
    def define_global(name, value):
        """Define a new global symbol.

        This allows external modules to define new symbols during template generation.

        Parameters:
            name (str): Name of global symbol as it will appear inside the template.
            value (any): Value of the symbol.
        """

        # Add the new value to the permanent set (even if it's not really a function)
        PdsTemplate._PREDEFINED_FUNCTIONS[name] = value

        # If generate() is currently active, add it to the active dictionary too
        if PdsTemplate._CURRENT_LABEL_PATH:     # hard to get here  # pragma: no cover
            PdsTemplate._CURRENT_GLOBAL_DICT[name] = value

    ######################################################################################
    # Utility functions
    ######################################################################################

    @staticmethod
    def BASENAME(filepath):
        """The basename of `filepath`, with the leading directory path removed.

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
        """The value of a counter identified by `name`, starting at 1.

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
        """The current date/time in the local time zone.

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
        """The current UTC date/time.

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
        """The number of elapsed seconds since the most recent midnight.

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
        """The size in bytes of the file specified by `filepath`.

        Parameters:
            filepath (str): The filepath.

        Returns:
            int: The size in bytes of the file.
        """

        return os.path.getsize(filepath)

    # From http://stackoverflow.com/questions/3431825/-
    @staticmethod
    def FILE_MD5(filepath):
        """The MD5 checksum of the file specified by `filepath`.

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
        """The number of records in the the file specified by `filepath`.

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
        """The modification time in the local time zone of a file.

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
        """The UTC modification time of a file.

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
    def GETENV(name, default=''):
        """The value of the specified environment variable.

        Parameters:
            name (str): Name of the environment variable.
            default (str): Value to return if the environment variable is undefined.

        Returns:
            str: The value of the variable or else the default.
        """

        return os.getenv(name, default=default)

    @staticmethod
    def LABEL_PATH():
        """The path to the current label file being generated.

        Returns:
            str: Path string to the label file.
        """

        return str(PdsTemplate._CURRENT_LABEL_PATH)

    @staticmethod
    def LOG(level, message, filepath='', *, force=False):
        """Send a message to the logger; nothing is returned.

        This allows a template to issue warnings and other messages.

        Parameters:
            level (int or str): Level of the message: 'info', 'error', 'warn', etc.
            message (str): Text of the warning message.
            filepath (str or pathlib.Path, optional): File path to include in the message.
            force (bool, optional): True to force the logging of the message regardless
                of the level.
        """

        get_logger().log(level, message, filepath, force=force)

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
    def QUOTE_IF(text):
        """Place the given text in quotes if it contains any character other than letters,
        digits, and an underscore.

        An empty string is also quoted. A string that is already enclosed in quotes is
        not quoted (but quote balancing is not checked). Other values are returned
        unchanged.

        Parameters:
            text (str): Text to possibly quote.

        Returns:
            str: The text with quotes if necessary.
        """

        if text.isidentifier():
            return text

        if text.startswith('"') and text.endswith('"'):
            return text

        return '"' + text + '"'

    @staticmethod
    def RAISE(exception, message):
        """Raise an exception with the given class `exception` and the `message`.

        Parameters:
            exception (type): The class of the exception to raise, e.g., ValueError.
            message (str): The message to include in the exception.

        Raises:
            Exception: The specified exception.
        """

        raise _RaisedException(exception, message)  # wrapper used to handle formatting

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
    def TEMPLATE_PATH():
        """The path to this template file.

        Returns:
            str: Path string to this template file.
        """

        return str(PdsTemplate._CURRENT_TEMPLATE.template_path)

    @staticmethod
    def VERSION_ID():
        """The PdsTemplate version ID, e.g., "v1.0".

        Returns:
            str: The version ID.
        """

        parts = __version__.split('.')
        if len(parts) >= 2:                                         # pragma: no cover
            return '.'.join(parts[:2])

        return '0.0'        # version unspecified                   # pragma: no cover

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
PdsTemplate._PREDEFINED_FUNCTIONS['BASENAME'     ] = PdsTemplate.BASENAME
PdsTemplate._PREDEFINED_FUNCTIONS['BOOL'         ] = PdsTemplate.BOOL
PdsTemplate._PREDEFINED_FUNCTIONS['COUNTER'      ] = PdsTemplate.COUNTER
PdsTemplate._PREDEFINED_FUNCTIONS['CURRENT_TIME' ] = PdsTemplate.CURRENT_TIME
PdsTemplate._PREDEFINED_FUNCTIONS['CURRENT_ZULU' ] = PdsTemplate.CURRENT_ZULU
PdsTemplate._PREDEFINED_FUNCTIONS['DATETIME'     ] = PdsTemplate.DATETIME
PdsTemplate._PREDEFINED_FUNCTIONS['DATETIME_DOY' ] = PdsTemplate.DATETIME_DOY
PdsTemplate._PREDEFINED_FUNCTIONS['DAYSECS'      ] = PdsTemplate.DAYSECS
PdsTemplate._PREDEFINED_FUNCTIONS['FILE_BYTES'   ] = PdsTemplate.FILE_BYTES
PdsTemplate._PREDEFINED_FUNCTIONS['FILE_MD5'     ] = PdsTemplate.FILE_MD5
PdsTemplate._PREDEFINED_FUNCTIONS['FILE_RECORDS' ] = PdsTemplate.FILE_RECORDS
PdsTemplate._PREDEFINED_FUNCTIONS['FILE_TIME'    ] = PdsTemplate.FILE_TIME
PdsTemplate._PREDEFINED_FUNCTIONS['FILE_ZULU'    ] = PdsTemplate.FILE_ZULU
PdsTemplate._PREDEFINED_FUNCTIONS['GETENV'       ] = PdsTemplate.GETENV
PdsTemplate._PREDEFINED_FUNCTIONS['LABEL_PATH'   ] = PdsTemplate.LABEL_PATH
PdsTemplate._PREDEFINED_FUNCTIONS['LOG'          ] = PdsTemplate.LOG
PdsTemplate._PREDEFINED_FUNCTIONS['NOESCAPE'     ] = PdsTemplate.NOESCAPE
PdsTemplate._PREDEFINED_FUNCTIONS['QUOTE_IF'     ] = PdsTemplate.QUOTE_IF
PdsTemplate._PREDEFINED_FUNCTIONS['RAISE'        ] = PdsTemplate.RAISE
PdsTemplate._PREDEFINED_FUNCTIONS['REPLACE_NA'   ] = PdsTemplate.REPLACE_NA
PdsTemplate._PREDEFINED_FUNCTIONS['REPLACE_UNK'  ] = PdsTemplate.REPLACE_UNK
PdsTemplate._PREDEFINED_FUNCTIONS['TEMPLATE_PATH'] = PdsTemplate.TEMPLATE_PATH
PdsTemplate._PREDEFINED_FUNCTIONS['VERSION_ID'   ] = PdsTemplate.VERSION_ID
PdsTemplate._PREDEFINED_FUNCTIONS['WRAP'         ] = PdsTemplate.WRAP

##########################################################################################
# LabelStatus class
##########################################################################################

class _LabelState(object):
    """Internal class to carry status information about where we are in the template and
    the label generation.

    Parameters:
        template (PdsTemplate): The template being processed into a label file.
        dictionary (dict): The dictionary of values used for substitutions.
        label_path (str): The path to the file being generated.
        terminator (str, optional):
            The line terminator, either "\\n" or "\\r\\n". The default is to retain the
            line terminator used in the template.
        raise_exceptions (bool, optional):
            True to raise any exceptions encountered; False to log them and embed the
            error messages into the label, marked by "[[[" and "]]]".
    """

    def __init__(self, template, dictionary, label_path='', *, terminator=None,
                 raise_exceptions=False):

        self.template = template
        self.label_path = label_path
        self.terminator = terminator
        self.raise_exceptions = raise_exceptions

        self.local_dicts = [{}]

        # Merge the predefined functions into a copy of the global dictionary
        self.global_dict = dictionary.copy()
        for key, func in PdsTemplate._PREDEFINED_FUNCTIONS.items():
            if key not in self.global_dict:
                self.global_dict[key] = func

    def define_global(self, name, value):
        """Add this definition to this state's global dictionary."""

        self.global_dict[name] = value

##########################################################################################
# Allow access of key functions a static methods of PdsTemplate
##########################################################################################

PdsTemplate.set_logger = set_logger
PdsTemplate.get_logger = get_logger
PdsTemplate.set_log_level = set_log_level
PdsTemplate.set_log_format = set_log_format

##########################################################################################
