##########################################################################################
# pdstemplate/__init__.py
##########################################################################################
"""PDS Ring-Moon Systems Node, SETI Institute

``pdstemplate`` is a Python module that defines the :class:`PdsTemplate` class, which is
used to generate PDS labels based on template files. Both PDS3 and PDS4 (xml) labels are
supported. Although specifically designed to facilitate data deliveries by PDS data
providers, the template system is generic and can be used to generate files from templates
for other purposes.

###############
Getting Started
###############

The general procedure is as follows:

1. Create a template object by calling the :meth:`PdsTemplate` constructor to read a
template file::

    from pdstemplate import PdsTemplate
    template = PdsTemplate(template_file_path)

2. Create a dictionary that contains the parameter values to use inside the label.

3. Construct the label using method :meth:`~PdsTemplate.write` as follows::

    template.write(dictionary, label_file)

This will create a new label of the given name, using the values in the given dictionary.
Once the template has been constructed, steps 2 and 3 can be repeated any number of times.

Alternatively, you can obtain the content of a label without writing it to a file using
method :meth:`~PdsTemplate.generate`.

``pdstemplate`` employs the RMS Node's `rms-filecache
<https://pypi.org/project/rms-filecache>`_ module and its `FCPath
<https://rms-filecache.readthedocs.io/en/latest/module.html#filecache.file_cache_path.FCPath>`_
class to support the handling of files at a website or in the cloud. You can refer to a
remote file by URL and the :class:`PdsTemplate` will treat it as if it were a local file.
See `filecache's documentation
<https://rms-filecache.readthedocs.io/en/latest/index.html>`_ for further details.

###############
Template Syntax
###############

A template file will look generally like a label file, except for certain embedded
expressions that will be replaced when the template's :meth:`~PdsTemplate.write` or
:meth:`~PdsTemplate.generate` method is called.

*************
Substitutions
*************

In general, everything between dollar signs "$" in the template is interpreted as a
Python expression to be evaluated. The result of this expression then replaces it
inside the label. For example, if ``dictionary['INSTRUMENT_ID'] == 'ISSWA'``, then::

    <instrument_id>$INSTRUMENT_ID$</instrument_id>

in the template will become::

    <instrument_id>ISSWA</instrument_id>

in the label. The expression between "$" in the template can include indexes, function
calls, or just about any other Python expression. As another example, using the same
dictionary above::

    <camera_fov>$"Narrow" if INSTRUMENT_ID == "ISSNA" else "Wide"$</camera_fov>

in the template will become this in the label::

    <camera_fov>Wide</camera_fov>

An expression in the template of the form ``$name=expression$``, where the `name` is a
valid Python variable name, will also also have the side-effect of defining this
variable so that it can be re-used later in the template. For example, if this appears
as an expression::

    $cruise_or_saturn=('cruise' if START_TIME < 2004 else 'saturn')$

then later in the template, one can write::

    <lid_reference>
    urn:nasa:pds:cassini_iss_$cruise_or_saturn$:data_raw:cum-index
    </lid_reference>

To embed a literal "$" inside a label, enter "$$" into the template.

*******
Headers
*******

Headers provide even more sophisticaed control over the content of a label. A header
appears alone on a line of the template and begins with "$" as the first non-blank
character. It determines whether or how subsequent text of the template will appear in the
file, from here up to the next header line.

===============
FOR and END_FOR
===============

You can include one or more repetitions of the same text using ``FOR`` and ``END_FOR``.
The format is::

    $FOR(expression)
        <template text>
    $END_FOR

where `expression` evaluates to a Python iterable. Within the `template text`, these new
variable names are assigned:

- `VALUE` = the current value of the iterator;
- `INDEX` = the index of this iteration, starting from zero;
- `LENGTH` = the total number of iterations.

For example, if::

    dictionary["targets"] = ["Jupiter", "Io", "Europa"]
    dictionary["naif_ids"] = [599, 501, 502]

then::

    $FOR(targets)
        <target_name>$VALUE (naif_ids[INDEX])$</target_name>
    $END_FOR

in the template will become this in the label::

    <target_name>Jupiter (599)</target_name>
    <target_name>Io (501)</target_name>
    <target_name>Europa (502)</target_name>

Instead of using the names `VALUE`, `INDEX`, and `LENGTH`, you can customize the variable
names by listing up to three comma-separated names and an equal sign "=" before the
iterable expression. For example, this will produce the same results as the example
above::

    $FOR(name, k=targets)
        <target_name>$name (naif_ids[k])$</target_name>
    $END_FOR

=============================
IF, ELSE_IF, ELSE, and END_IF
=============================

You can use ``IF``, ``ELSE_IF``, ``ELSE``, and ``END_IF`` to select among alternative
blocks of text in the template:

- ``IF(expression)``: Evaluate `expression` and include the next lines of the template if
  it is logically True (e.g., boolean True, a nonzero number, a non-empty list or string,
  etc.).

- ``ELSE_IF(expression)``: Include the next lines of the template if `expression` is
  logically True and every previous expression was logically false.

- ``ELSE``: Include the next lines of the template only if all prior expressions were
  logically False.

- ``END_IF``:  This marks the end of the set of if/else alternatives.

As with other substitutions, you can define a new variable of a specified name by using
`name=expression` inside the parentheses of ``IF()`` and ``ELSE_IF()``.

Note that headers can be nested arbitrarily inside the template.

.. _ONCE:

====
ONCE
====

``ONCE`` is a header that simply includes the content that follows it one time. However,
it is useful for its side-effect, which is that ``ONCE(expression)`` allows the embedded
`expression` to be evaluated without writing new text into the label. You can use this
capability to define variables internally without affecting the content of the label
produced. For example::

    $ONCE(date = big_dictionary["key"]["date"])

will assign the value of the variable named `date` for subsequent use within the template.

=======
INCLUDE
=======

This header will read the content of another file and insert its content into the template
here::

    $INCLUDE(filename)

Using the environment variable ``PDSTEMPLATE_INCLUDES``, you can define one or more
directories that will be searched for a file to be included. If multiple directories are
to be searched, they should be separated by colons. You can also specify one or more
directories to search in the :meth:`PdsTemplate` constructor using the `includes` input
parameter.

Include files are handled somewhat differently from other headers. When ``INCLUDE``
references a file as a literal string rather than as an expression to evaluate, it is
processed at the time that the :class:`PdsTemplate` is constructed. However, if the
filename is given as an expression, it is not evaluated until :meth:`~PdsTemplate.write``
or :meth:`~PdsTemplate.generate`` is called for each label.

=================
NOTE and END_NOTE
=================

You can use ``NOTE`` and ``END_NOTE`` to embed any arbitrary comment block into the
template. Any text between these headers does not appear in the label::

    $NOTE
    Here is an extended comment about the templae
    $END_NOTE

You can also use ``$NOTE:`` for an in-line comment. This text, and any blanks before it,
are not included in the label::

    <filter>$FILTER$</filter>   $NOTE: This is where we identify the filter

*********************
Pre-defined Functions
*********************

The following pre-defined functions can be used inside any expression in the template.

- :meth:`~.PdsTemplate.BASENAME`:
  The basename of a filepath, with leading directory path removed.

- :meth:`~.PdsTemplate.BOOL`
  Return one of two strings based on a boolean input.

- :meth:`~.PdsTemplate.COUNTER`
  The current value of a counter.

- :meth:`~.PdsTemplate.CURRENT_TIME`
  The current date or time in the local time zone as a string of the form "yyyy-mm-dd" or
  "yyyy-mm-ddThh:mm:sss".

- :meth:`~.PdsTemplate.CURRENT_ZULU`
  The current UTC date or time as a string of the form "yyyy-mm-dd" or
  "yyyy-mm-ddThh:mm:sssZ".

- :meth:`~.PdsTemplate.DATETIME`
  Convert a time to an ISO time string with the date expressed as "yyyy-mm-dd".

- :meth:`~.PdsTemplate.DATETIME_DOY`
  Convert a time to an ISO time string with the date expressed as "yyyy-ddd".

- :meth:`~.PdsTemplate.DAYSECS`
  Convert a time to the number of elapsed seconds since the most recent midnight.

- :meth:`~.PdsTemplate.FILE_BYTES`
  The size in bytes of a specified file.

- :meth:`~.PdsTemplate.FILE_MD5`
  The MD5 checksum of a specified file.

- :meth:`~.PdsTemplate.FILE_RECORDS`
  The number of records in a specified file.

- :meth:`~.PdsTemplate.FILE_TIME`
  The modification time in the local time zone of the specified file.

- :meth:`~.PdsTemplate.FILE_ZULU`
  The UTC modification time of a specified by file.

- :meth:`~.PdsTemplate.GETENV`
  The value of any environment variable.

- :meth:`~.PdsTemplate.LABEL_PATH`
  The file path of the label being written.

- :meth:`~.PdsTemplate.LOG`
  Write a message to the current log.

- :meth:`~.PdsTemplate.NOESCAPE`
  If the template is XML, evaluated expressions are "escaped" to ensure that they are
  suitable for embedding in a PDS4 label. For example, ">" inside a string will be
  replaced by "&gt;". This function prevents text from being escaped in the label,
  allowing it to contain literal XML.

- :meth:`~.PdsTemplate.QUOTE_IF`
  Quote the given text if it requires quotes within a PDS3 label.

- :meth:`~.PdsTemplate.RAISE`
  Raise an exception with a given class and text message.

- :meth:`~.PdsTemplate.RECORD_BYTES`
  The maximum number of bytes in any record of a specified file, including line
  terminators.

- :meth:`~.PdsTemplate.REPLACE_NA`
  Return either a given string or an indication that it is "not applicable".

- :meth:`~.PdsTemplate.REPLACE_UNK`
  Return either a given string or an indication that it is "unknown".

- :meth:`~.PdsTemplate.TEMPLATE_PATH`
  The directory path to the template file.

- :meth:`~.PdsTemplate.VERSION_ID`
  Version ID of this module using two digits, e.g., "v1.0".

- :meth:`~.PdsTemplate.WRAP`
  Wrap the given text to a specified indentation and width.

These functions can also be used directly by the programmer within a template; they are
static functions of class :class:`PdsTemplate`.

##############################
Logging and Exception Handling
##############################

``pdstemplate`` employs the RMS Node's `rms-pdslogger
<https://pypi.org/project/rms-pdslogger>`_ module to handle logging. By default, the
logger is a `PdsLogger
<https://rms-pdslogger.readthedocs.io/en/latest/module.html#pdslogger.PdsLogger>`_ object,
although any ``logging.Logger`` object will work. See `pdslogger's documentation
<https://rms-pdslogger.readthedocs.io>`_ for further details.

You can override the default Logger using static method :meth:`~utils.set_logger`. You can
also set the logging level ("info", "warning", "error", etc.) using
:meth:`~utils.set_log_level` and can select among many log formatting options using
:meth:`~set_log_format`. Use :meth:`~utils.get_logger` to obtain the current Logger.

By default, exceptions during a call to :meth:`~PdsTemplate.write` or
:meth:`~PdsTemplate.generate` are handled as follows:

1. They are written to the log.
2. The expression that triggered the exception is replaced by the error text in the label,
   surrounded by "[[[" and "]]]" to make it easier to find.
3. The attributes ``fatal_count``, ``error_count``, and ``warning_count`` of the
   :class:`PdsTemplate` contain the number of messages logged by each category.
4. The exception is otherwise suppressed.

This behavior can be modified using ``raise_exceptions=True`` in the call to
:meth:`~PdsTemplate.write` or :meth:`~PdsTemplate.generate`; in this case, the exception
will be raised, label generation will stop, and the label will not be written.

##############
Pre-processors
##############

A pre-processor is a function that takes the text of a template file as input and returns
a new template as output. As described above, ``INCLUDE`` headers that contain an explicit
file name (rather than an expression to be evaluated) are handled by a pre-processor.

You may define your own functions to pre-process the content of a template. They must have
this call signature::

    func(path: str | Path | FCPath, content: str, *args, **kwargs) -> str

where

* `path` is the path to the template file (used here just for error logging).
* `content` is the content of a template represented by a single string with <LF> line
  terminators.
* `*args` is for any additional positional arguments to `func`.
* `**kwargs` is for any additional keyword arguments to `func`.

When you invoke the :meth:`PdsTemplate` constructor, one of the optional inputs is
`preprocess`, which takes either a single function or a list of functions to apply after
the INCLUDE pre-processor. For the first of these, the `args` and `kwargs` inputs can be
provided as additional inputs to the constructor. Subsequent pre-processors cannot take
additional arguments; define them using lambda notation instead.

Note that a :class:`PdsTemplate` object has an attribute `content`, which contains the
full content of the template after all pre-processing has been performed. You can examine
this attribute to see the final result of all processing. Note also that when line numbers
appear in an error message, they refer to the line number of the template after
pre-processing, not before.
"""

import datetime
import hashlib
import numbers
import os
import re
import string
import textwrap
import time
from collections import deque

from filecache import FCPath
import julian
import pdslogger

try:
    from ._version import __version__
except ImportError:                                                 # pragma: no cover
    __version__ = 'Version unspecified'

from .utils import TemplateError, TemplateAbort                     # noqa: F401
    # Unused here but included to support "from pdstemplate import TemplateError", etc.

from .utils import _RaisedException, _NOESCAPE_FLAG
from .utils import set_logger, get_logger, set_log_level, set_log_format
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

    _GETENV_INCLUDE_DIRS = None

    def __init__(self, template, content='', *, xml=None, crlf=None, upper_e=False,
                 includes=[], preprocess=None, args=(), kwargs={}, postprocess=None):
        """Construct a PdsTemplate object from the contents of a template file.

        Parameters:
            template (str, Path, or FCPath):
                Path of the input template file.
            content (str or list[str], optional):
                Alternative source of the template content rather than reading it from a
                file.
            xml (bool, optional):
                Use True to indicate that the template is in xml format; False otherwise.
                If not specified, an attempt is made to detect the format from the
                template.
            upper_e (bool, optional):
                True to force the "E" in the exponents of floating-point numbers to be
                upper case.
            crlf (bool, optional):
                True to indicate that the line termination should be <CR><LF>; False for
                <LF> only. If not specified, the line termination is inferred from the
                template.
            includes (str, Path, FCPath, or list):
                One or more directory paths where template include files can be found. The
                directory containing `template` is always searched first. Note that
                include paths can also be specified using the environment variable
                PDSTEMPLATE_INCLUDES, which should contain one or more directory paths
                separated by colons. Any directories specified here are searched before
                those defined by PDSTEMPLATE_INCLUDES.
            preprocess (function or list[function], optional):
                An optional function or list of functions that transform the content of a
                template into a new template. The call signature is::

                    func(path, content, *args, **kwargs) -> str

                where `path` is the path of the template file (used here just for error
                reporting), `content` is the template's content, provided as a single
                string with <LF> line terminators, and `args` and `kwargs` are additional
                inputs. Note that any pre-processor after the first cannot have `args` or
                `kwargs` as inputs; use lambda notation if later functions require inputs.
            args (tuple or list):
                Any arguments to be passed to the first preprocess function after the
                template's content.
            kwargs (dict):
                Any keywords=value arguments to be passed to the first preprocess
                function.
            postprocess (function, optional):
                An optional function to apply after label content has been generated. This
                could be used to transform the content or to apply further validation. The
                call signature is::

                    func(content: str) -> str

                For example, use `postprocess=ps3_syntax_checker` to ensure a generated
                label strictly conforms to the PDS3 standard.
        """

        self.template_path = FCPath(template)
        PdsTemplate._CURRENT_TEMPLATE = self
        PdsTemplate._CURRENT_LABEL_PATH = ''
        PdsTemplate._CURRENT_GLOBAL_DICT = {}

        includes = includes if isinstance(includes, (list, tuple)) else [includes]
        self._includes = [FCPath(dir) for dir in includes]

        self.upper_e = bool(upper_e)
        self.postprocess = postprocess

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
        self.fatal_count = 0
        self.error_count = 0
        self.warning_count = 0

    def _include_dirs(self):
        """Ordered list of all include directories to search."""

        if PdsTemplate._GETENV_INCLUDE_DIRS is None:
            value = os.getenv('PDSTEMPLATE_INCLUDES')
            dirs = value.split(':') if value else []
            PdsTemplate._GETENV_INCLUDE_DIRS = [FCPath(d) for d in dirs]

        return ([self.template_path.parent] + self._includes
                + PdsTemplate._GETENV_INCLUDE_DIRS)

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
            label_path (str, Path, or FCPath, optional):
                The output label file path. Although a file is not written, this path is
                used in error messages.
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

        label_path = str(label_path) if label_path else ''

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
            content = ''.join(results)
            if self.postprocess:            # postprocess if necessary
                content = self.postprocess(content)
        except TemplateAbort as err:
            logger.fatal('**** ' + err.message, label_path)
        except Exception as err:
            logger.exception(err, label_path)
            raise err
        finally:
            (fatals, errors, warns, total) = logger.close()

        content = ''.join(results)
        self.fatal_count = fatals
        self.error_count = errors
        self.warning_count = warns

        # Update the terminator if necessary
        if self.terminator != '\n':
            content = content.replace('\n', self.terminator)

        # Reset global symbols
        PdsTemplate._CURRENT_LABEL_PATH = ''
        PdsTemplate._CURRENT_GLOBAL_DICT = {}

        return content

    def write(self, dictionary, label_path, *, mode='save', backup=False,
              raise_exceptions=False, handler=None):
        """Write one label based on the template, dictionary, and output filename.

        Parameters:
            dictionary (dict):
                The dictionary of parameters to replace in the template.
            label_path (str, Path, or FCPath, optional):
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
            handler (str, Path, FCPath, or logger.Handler, optional):
                Define a handler to use exclusively during the generation of this label.
                If it is a string, Path, or FCPath, a logger.FileHandler using this path
                is constructed. However, if the string begins with "." is instead
                interpreted as the file extension to use, where the path up to the
                extension is defined by `label_path`; for example, if handler=".log", then
                when writing "path/to/123.lbl", the log created will be "path/to/123.log".
                This log is automatically closed once the label is written.

        Returns:
            int: Number of errors issued.
            int: Number of warnings issued.
        """

        if mode not in {'save', 'repair', 'validate'}:
            raise ValueError('invalid mode value: ' + repr(mode))

        label_path = FCPath(label_path)

        logger = get_logger()
        if handler:
            # Convert any string to an FCPath
            if isinstance(handler, str):
                if handler.startswith('.'):
                    handler = label_path.with_suffix(handler)
                else:
                    handler = FCPath(handler)
            # Convert any FCPath to a FileHandler
            if isinstance(handler, FCPath):
                handler = pdslogger.file_handler(handler)
            logger.add_handler(handler)

        try:
            content = self.generate(dictionary, label_path,
                                    raise_exceptions=raise_exceptions,
                                    hide_warnings=(mode == 'save'),
                                    abort_on_error=(mode != 'save'))
            fatals = self.fatal_count
            errors = self.error_count
            warns = self.warning_count

            if fatals and not errors:
                errors = fatals

            # Validation case
            if mode == 'validate':
                if errors:
                    plural = 's' if errors > 1 else ''
                    logger.error(f'Validation failed with {errors} error{plural}',
                                 label_path, force=True)
                elif warns:
                    plural = 's' if warns > 1 else ''
                    logger.warning(f'Validation failed with {warns} warning{plural}',
                                   label_path, force=True)
                else:
                    logger.info('Validation successful', label_path, force=True)

            # Repair case
            elif mode == 'repair':
                if errors:
                    plural = 's' if errors > 1 else ''
                    logger.warning(f'Repair failed with {errors} error{plural}',
                                   label_path)
                elif label_path.exists():
                    old_content = label_path.read_bytes().decode('utf-8')
                    if old_content == content:
                        logger.info('Repair unnecessary; content is unchanged',
                                    label_path)
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
                timestamp = os.path.getmtime(label_path.get_local_path())
                date = datetime.datetime.fromtimestamp(timestamp)   # wrong if remote
                datestr = date.isoformat(timespec='seconds').replace(':', '-')
                backup_path = label_path.parent / (label_path.stem + '_' + datestr +
                                                   label_path.suffix)
                label_path.rename(backup_path)
                logger.info('Existing label renamed to', backup_path)
                exists = False

            # Write label
            if content and not content.endswith(self.terminator):
                content += self.terminator
            label_path.write_bytes(content.encode('utf-8'))

            # Log event
            if exists:
                logger.info('Label re-written', label_path)
            else:
                logger.info('Label written', label_path)

        finally:
            logger.remove_handler(handler)      # OK if handler is None

        return (errors, warns)

    @staticmethod
    def log(level, message, filepath='', *, force=False):
        """Send a message to the current logger.

        This allows external modules to issue warnings and other messages.

        Parameters:
            level (int or str): Level of the message: 'info', 'error', 'warn', etc.
            message (str): Text of the warning message.
            filepath (str, Path, or FCPath, optional): File path to include in the
                message.
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

        # We intentionally open this in non-binary mode so we don't have to contend with
        # line terminator issues.
        printable = string.printable.encode('latin8')
        with open(filepath, 'rb') as f:
            count = 0
            asciis = 0
            non_asciis = 0
            for line in f:
                for c in line:
                    if c in printable:
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
            utc_dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
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
            filepath (str, Path, or FCPath, optional): File path to include in the
                message.
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
        """Place the given text in quotes if it is not a valid upper-case identifier.

        An empty string and a string starting with a digit is also quoted. A string that
        is already enclosed in quotes or apostrophes is not quoted (but quote balancing is
        not checked). Other values are returned unchanged.

        Parameters:
            text (str): Text to possibly quote.

        Returns:
            str: The text with quotes if necessary.
        """

        if text == text.upper() and text.isidentifier():
            return text

        if text.startswith('"') and text.endswith('"'):
            return text

        if text.startswith("'") and text.endswith("'"):
            return text

        if text == 'N/A':
            return "'N/A'"

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
    def RECORD_BYTES(filepath):
        """The maximum number of bytes in any record of the specified file, including line
        terminators.

        Parameters:
            filepath (str): The filepath.
        """

        # We intentionally open this in non-binary mode so we don't have to contend with
        # line terminator issues.
        max_bytes = 0
        with open(filepath, 'rb') as f:
            for line in f:
                max_bytes = max(max_bytes, len(line))

        return max_bytes

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
        """The PdsTemplate version ID using two digits, e.g., "v1.0".

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
PdsTemplate._PREDEFINED_FUNCTIONS['RECORD_BYTES' ] = PdsTemplate.RECORD_BYTES
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
        label_path (str, path, or FCPath): The path to the file being generated.
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
