##########################################################################################
# pdstemplate/_utils.py
##########################################################################################

import os
import pathlib

from pdslogger import PdsLogger, LoggerError

class TemplateError(LoggerError):
    """Class for all template parsing exceptions."""
    pass

class TemplateAbort(TemplateError):
    """Raise this class to abort processing a template if the situation is hopeless.

    When raising an AbortTemplate exception, pass it the exact text to appear in the log.
    It will appear as a FATAL message with "**** " followed by this text and then a colon
    and the file name.
    """
    pass

class _RaisedException(Exception):
    """Internal; used to manage error messages from $RAISE()$."""

    def __init__(self, exception, message):
        self.exception = exception
        self.message = message

_NOESCAPE_FLAG = '!!NOESCAPE!!:'    # used internally

##########################################################################################
# $INCLUDE directory management
##########################################################################################

_INCLUDE_DIRS = None

def getenv_include_dirs():
    """The list of directories to search for $INCLUDE files."""

    global _INCLUDE_DIRS

    if _INCLUDE_DIRS is None:
        value = os.getenv('PDSTEMPLATE_INCLUDES')
        dirs = value.split(':') if value else []
        _INCLUDE_DIRS = [pathlib.Path(d) for d in dirs]

    return _INCLUDE_DIRS

##########################################################################################
# Logger management
##########################################################################################

# Define the global logger with streamlined output, no handlers so printing to stdout
_LOGGER = PdsLogger.get_logger('pds.template', timestamps=False, digits=0, lognames=False,
                               pid=False, indent=True, blanklines=False, level='info')

def set_logger(logger):
    """Define the global PdsLogger for PdsTemplate and associated tools.

    Parameters:
        logger (PdsLogger): Logger to use, replacing the default.

    Returns:
        PdsLogger: The new PdsLogger.
    """

    global _LOGGER

    _LOGGER = logger
    return _LOGGER


def get_logger():
    """The global PdsLogger for PdsTemplate and associated tools."""

    return _LOGGER


def set_log_level(level):
    """Set the minimum level for messages to be logged.

    Parameters:
        level (int or str, optional):
            The minimum level of level name for a record to enter the log.
    """

    _LOGGER.set_level(level)

def set_log_format(**kwargs):
    """Set the formatting and other properties of the logger.

    Parameters:
        level (int or str, optional):
            The minimum level of level name for a record to enter the log.
        timestamps (bool, optional):
            True or False, defining whether to include a timestamp in each log record.
        digits (int, optional):
            Number of fractional digits in the seconds field of the timestamp.
        lognames (bool, optional):
            True or False, defining whether to include the name of the logger in each log
            record.
        pid (bool, optional):
            True or False, defining whether to include the process ID in each log record.
        indent (bool, optional):
            True or False, defining whether to include a sequence of dashes in each log
            record to provide a visual indication of the tier in a logging hierarchy.
        blanklines (bool, optional):
            True or False, defining whether to include a blank line in log files when a
            tier in the hierarchy is closed.
        colors (bool, optional):
            True or False, defining whether to color-code the log files generated, for
            Macintosh only.
        maxdepth (int, optional):
            Maximum depth of the logging hierarchy, needed to prevent unlimited recursion.
    """

    _LOGGER.set_format(**kwargs)

##########################################################################################
# Line terminator utility
##########################################################################################

def _check_terminators(filepath, content='', crlf=None):
    """Raise an exception if the given file content is not consistent with the intended
    line terminator.

    Parameters:
        filepath (str or pathlib.Path):
            Path to the file, used for error messages.
        content (str, bytes, list[str], or list[bytes]):
            Content of the file as a single string or byte string or else as a list of
            records such as provided by file.readlines().
        crlf (bool, optional):
            True to indicate that the line termination should be <CR><LF>; False for
            <LF> only. If not specified, the line termination is inferred from the
            template.

    Returns:
        bool: True if the terminators are <CR><LF>, False otherwise.

    Raises:
        TemplateError: If an incorrect line terminator was found.
    """

    filepath = pathlib.Path(filepath)
    if not content:
        content = filepath.read_bytes()

    # Define <CR><LF> terminator depending on types; split content into a list
    if isinstance(content, list):
        crlf_chars = b'\r\n' if isinstance(content[0], bytes) else '\r\n'
    else:
        lf_char = b'\n' if isinstance(content, bytes) else '\n'
        content = content.split(lf_char)
        if content[-1]:
            raise TemplateError('missing line terminator at end of file', filepath)
        content = content[:-1]
        crlf_chars = b'\r' if isinstance(content[0], bytes) else '\r'
            # Because the split was on the <LF>, we do not expect <LF>'s in records

    # Define `crlf` if it was not provided
    if crlf is None:
        crlf = content[0].endswith(crlf_chars)

    # Validate line terminator in first record
    crlf = bool(crlf)   # make sure it's really boolean
    if crlf != content[0].endswith(crlf_chars):
        name = '<CR><LF>' if crlf else '<LF>'
        raise TemplateError(f'Line terminator is not {name}', filepath)

    # Validate the line terminator in every record
    for recno, record in enumerate(content):
        if crlf != record.endswith(crlf_chars):
            raise TemplateError(f'Inconsistent line terminator at line {recno+1}',
                                filepath)

    return crlf

##########################################################################################
