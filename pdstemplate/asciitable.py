##########################################################################################
# pdstemplate/asciitable.py
##########################################################################################
"""
.. _asciitable:

######################
pdstemplate.asciitable
######################

``asciitable`` is a plug-in module to assist with the labeling of ASCII tables in PDS3 and
PDS4. It supports the :ref:`pds3table` module and the ``tablelabel`` tool, and will also
be used by a future ``pds4table`` tool. To import::

    import pdstemplate.asciitable

This import creates two new pds-defined functions, which can be accessed within any
template.

* :meth:`ANALYZE_TABLE` takes the path to an existing ASCII table and analyzes its
  content, inferring details about the content and formats of all the columns.
* :meth:`TABLE_VALUE` returns information about the content of the table for use within
  the label to be generated.

For example, consider a template that contains this content::

    $ONCE(ANALYZE_TABLE(LABEL_PATH().replace('.lbl', '.tab')))
    ...
    OBJECT              = TABLE
      ...
      ROWS              = $TABLE_VALUE('ROWS')$
      COLUMNS           = $TABLE_VALUE('COLUMNS')$

      OBJECT            = COLUMN
        NAME            = FILE_NAME
        DATA_TYPE       = $TABLE_VALUE("PDS3_DATA_TYPE", 1)$
        START_BYTE      = $TABLE_VALUE("START_BYTE", 1)$
        BYTES           = $TABLE_VALUE("BYTES", 1)$
        FORMAT          = $TABLE_VALUE("PDS3_FORMAT", 1))$
        MINIMUM_VALUE   = $TABLE_VALUE("MINIMUM", 1))$
        MAXIMUM_VALUE   = $TABLE_VALUE("MAXIMUM", 1))$
        DESCRIPTION     = "Name of file in the directory"
      END_OBJECT        = COLUMN
    ...


The initial call to :meth:`ANALYZE_TABLE` is embedded inside a :ref:`ONCE` directive
because it returns no content. However, it reads the table file and assembles a database
of what it has found. The subsequent calls to it can be used for multiple labels and each
label will always contain the correct numbers of ROWS and COLUMNS. :meth:`TABLE_VALUE` can
also retrieve information about the content and format about each of the table's columns.
"""

import re

from filecache import FCPath

from . import PdsTemplate
from .utils import get_logger, TemplateError, TemplateAbort, _check_terminators

##########################################################################################
# Pre-defined template functions
##########################################################################################

# For global access to the latest table
_LATEST_ASCII_TABLE = None


def ANALYZE_TABLE(filepath, *, separator=',', crlf=None, escape=''):
    """Analyze the given table and define it as the default table for subsequent calls to
    :meth:`TABLE_VALUE` inside a template.

    Parameters:
        filepath (str, Path, or FCPath):
            The path to an ASCII table file.
        separator (str, optional):
            The column separator character, typically a comma. Other options are
            semicolon, tab, and vertical bar ("|").
        crlf (bool, optional):
            True to raise an error if the line terminators are not <CR><LF>; False to
            raise an error if the line terminator is not <LF> alone; None to accept either
            line terminator.
        escape (str, optional):
            The character to appear before a quote ('"') if the quote is to be taken as a
            literal part of the string. Options are '"' for a doubled quote and '\\' for a
            backslash. If not specified, quote characters inside quoted strings are
            disallowed.
    """

    global _LATEST_ASCII_TABLE
    _LATEST_ASCII_TABLE = None

    logger = get_logger()
    logger.debug('Analyzing ASCII table', filepath)
    try:
        _LATEST_ASCII_TABLE = AsciiTable(filepath, separator=separator, crlf=crlf,
                                         escape=escape)
    except Exception as err:
        logger.exception(err)


def TABLE_VALUE(name, column=0):
    """Lookup function for information about the table analyzed in the most recent call to
    :meth:`ANALYZE_TABLE`.

    These are all the options; a column is indicated by an integer starting from zero:

    * `TABLE_VALUE("PATH")` = full path to the table file.
    * `TABLE_VALUE("BASENAME")` = basename of the table file.
    * `TABLE_VALUE("ROWS")` = number of rows.
    * `TABLE_VALUE("ROW_BYTES")` = bytes per row.
    * `TABLE_VALUE("COLUMNS")` = number of columns.
    * `TABLE_VALUE["TERMINATORS"]` = length of terminator: 1 for <LF>, 2 for <CR><LF>.
    * `TABLE_VALUE("WIDTH", <column>)` = width of the column in bytes.
    * `TABLE_VALUE("PDS3_FORMAT", <column>)` = a string containing the format for PDS3,
      e.g.,"I7", "A23", or "F12.4".
    * `TABLE_VALUE("PDS4_FORMAT", <column>)` = a string containing the format for PDS4,
      e.g., "%7d", "%23s", or "%12.4f".
    * 'TABLE_VALUE("PDS3_DATA_TYPE", <column>)` = PDS3 data type, one of `CHARACTER`,
      "ASCII_REAL", "ASCII_INTEGER", or "TIME".
    * 'TABLE_VALUE("PDS4_DATA_TYPE", <column>)` = PDS3 data type, e.g.,
      "ASCII_Text_Preserved", "ASCII_Real", or "ASCII_Date_YMD".
    * 'TABLE_VALUE("QUOTES", <column>)` = number of quotes before field value, 0 or 1.
    * 'TABLE_VALUE("START_BYTE", <column>)` = start byte of column, starting from 1.
    * 'TABLE_VALUE("BYTES", <column>)` = number of bytes in column, excluding quotes.
    * 'TABLE_VALUE("VALUES", <column>)` = a list of all the values found in the column.
    * 'TABLE_VALUE("MINIMUM", <column>)` = the minimum value in the column.
    * 'TABLE_VALUE("MAXIMUM", <column>)` = the maximum value in the column.
    * 'TABLE_VALUE("FIRST", <column>)` = the first value in the column.
    * 'TABLE_VALUE("LAST", <column>)` = the last value in the column.

    Parameters:
        name (str): Name of a parameter.
        column (int, optional): The index of the column, starting from zero.

    Returns:
        str, int, float, or bool: The value of the specified parameter as inferred from
        the ASCII table.

    Raises:
        TemplateAbort: If no ASCII Table was successfully analyzed.
        TemplateError: A wrapper for any other exception.
    """

    if not _LATEST_ASCII_TABLE:
        raise TemplateAbort('No ASCII table has been analyzed')

    try:
        return _LATEST_ASCII_TABLE.lookup(name, column)
    except Exception as err:
        raise TemplateError(err) from err


def _latest_ascii_table():
    """The most recently defined AsciiTable object. Provided for global access."""

    return _LATEST_ASCII_TABLE


def _reset_ascii_table():
    """Reset the most recently defined AsciiTable object to None, for debugging."""

    global _LATEST_ASCII_TABLE
    _LATEST_ASCII_TABLE = None


PdsTemplate.define_global('ANALYZE_TABLE', ANALYZE_TABLE)

##########################################################################################
# AsciiTable class definition and API
##########################################################################################

class AsciiTable():

    # This will match any valid fields between un-quoted commas
    _COMMA_REGEX = rb'([^",]*| *"[^"]*" *)(?:,|$)'

    _COLUMN_REGEX = {
        b',' : re.compile(_COMMA_REGEX),
        b'|' : re.compile(_COMMA_REGEX.replace(b',', rb'\|')),
        b';' : re.compile(_COMMA_REGEX.replace(b',', b';')),
        b'\t': re.compile(_COMMA_REGEX.replace(b',', b'\t')),
    }

    def __init__(self, filepath, content=[], *, separator=',', crlf=None, escape=''):
        """Constructor for an AsciiTable.

        Parameters:
            filepath (str, Path, or FCPath):
                The path to an ASCII table file.
            content (bytes or list[bytes], optional):
                The table file content as a byte string or sequence of byte strings. If
                this input is empty, the file will be read; otherwise, this content is
                used without reading the file. Line terminators must be included.
            separator (str, optional):
                The column separator character, typically a comma. Other options are
                semicolon, tab, and vertical bar ("|").
            crlf (bool, optional):
                True to raise an error if the line terminators are not <CR><LF>; False to
                raise an error if the line terminator is not <LF> alone; None to accept
                either line terminator.
            escape (str, optional):
                The character to appear before a quote ('"') if the quote is to be taken
                as a literal part of the string. Options are '"' for a doubled quote and
                '\\' for a backslash. If not specified, quote characters inside quoted
                strings are disallowed.
        """

        global _LATEST_ASCII_TABLE

        self.filepath = FCPath(filepath)

        if separator not in ',;|\t':
            raise ValueError('Disallowed separator: ' + repr(separator))
        self.separator = separator.encode('latin-1')

        if escape not in ('"', '\\', ''):
            raise ValueError('Disallowed escape character: ' + repr(escape))
        self.escape = escape.encode('latin-1')

        # Read the file if necessary
        if not content:
            content = self.filepath.read_bytes()
        if not content:
            raise TemplateAbort('Table file is empty', self.filepath)

        # Identify the line terminator and validate
        try:
            self.crlf = _check_terminators(filepath, content, crlf=crlf)
        except TemplateError as err:
            raise TemplateAbort(err.message, self.filepath)

        self._terminators = 2 if self.crlf else 1
        terminator = b'\r\n' if self.crlf else b'\n'

        # Convert content to a list of byte strings
        if isinstance(content, list):
            records = content
        else:
            records = [rec + terminator for rec in content.split(terminator)[:-1]]

        # Intialize internals
        self._row_bytes = 0
        self._rows = 0
        self._formats = []      # column -> tuple (letter, offset, length[, precision])
        self._start_bytes = []  # column -> first byte of column in row, starting with 1
        self._widths = []       # column -> width in bytes including surrounding quote
        self._bvalues = []      # column -> list of byte strings from column
        self._values_ = []      # column -> list of values, using lazy evaluation

        # Interpret the table shape
        self._row_bytes = len(records[0])
        self._rows = len(records)

        # Interpret the columns in each row
        regex = AsciiTable._COLUMN_REGEX[self.separator]
        for recno, record in enumerate(records):

            # Replace literal quotes with nulls for now
            if self.escape:
                original_length = len(record)
                record = record.replace(self.escape + b'"', b'\x00')
                changed = len(record) != original_length
            else:
                changed = False

            # This pattern matches any valid field delimited by commas outside quotes
            parts = regex.split(record[:-self._terminators])

            # If the record was valid, every even-numbered item will be blank and also
            # the second-to last item
            if not (all(p == b'' for p in parts[::2]) and parts[-2] == b''):
                raise TemplateAbort(f'Invalid use of quotes in record {recno+1}')

            columns = parts[1:-2:2]

            # Restore escaped quotes
            if changed:
                columns = [c.replace(b'\x00', self.escape + b'"') for c in columns]

            if not self._bvalues:
                self._bvalues = [[] for _ in columns]
                self._values_ = [[] for _ in columns]

            if len(self._bvalues) != len(columns):
                raise TemplateAbort('Inconsistent column count')

            for k, value in enumerate(columns):
                self._bvalues[k].append(value)

        # Check each column
        start_byte = 1
        for colno, column in enumerate(self._bvalues):

            # Save widths
            width = len(column[0])
            self._widths.append(width)

            # Get the start bytes ignoring quote offsets
            self._start_bytes.append(start_byte)
            start_byte += width + 1

            # Check that all widths are consistent
            for recno, value in enumerate(column):
                if len(value) != width:
                    raise TemplateAbort(f'Inconsistent width in record {recno+1}, '
                                        f'column {colno+1}')

            # Infer the common format within this column
            self._formats.append(self._column_format(column, colno))

        # Provide global access
        _LATEST_ASCII_TABLE = self
        PdsTemplate.define_global('TABLE_VALUE', self.lookup)

    def _column_format(self, column, colno):
        """Derived the format for the entire column, handling possible mixed formats.

        Parameters:
            column (list[bytes]): Content of column as a list of byte strings.
            colno (int): Index of the column starting from 0.

        Returns:
            tuple: `(type, offset, length[, precision])` where:

            * `type` (str): "I" for int, "E" for exponential notation with uppercase "E",
              "e" for exponential notation with lowercase "e", "F" for float, "A" for
              string, "D" for date, or "T" for date-time.
            * `offset` (int): 1 if the first character is a quote; 0 otherwise.
            * `length` (int): characters used (excluding quotes if quoted).
            * `precision` (int or str, optional): For E and F types, this is the longest
              numeric precision. For D and T types, this is the most specific PDS4 date or
              date-time type.
        """

        def pds4_date_time(formats):
            types = {fmt[0] for fmt in formats}
            type_ = 'ASCII_Date'
            if 'T' in types:
                type_ += '_Time'
            if all(fmt[3].startswith('YD') for fmt in formats):
                type_ += '_DOY'
            elif all(fmt[3].startswith('YMD') for fmt in formats):
                type_ += '_YMD'
            if all(fmt[3].endswith('Z') for fmt in formats):
                type_ += '_UTC'
            return type_

        # Assemble the set of formats found
        formats = set()
        for value in column:
            formats.add(self._cell_format(value))

        # If they're all the same, we're done
        if len(formats) == 1:
            fmt = list(formats)[0]
            if fmt[0] in 'DT':
                fmt = fmt[:3] + (pds4_date_time(formats),)
            return fmt

        # If there's a variation in offsets, any quotes will be part of the string
        offsets = {fmt[1] for fmt in formats}
        if len(offsets) == 1:
            offset = list(offsets)[0]
        else:
            offset = 0

        # Get a string representation of all the cell types
        types = list({fmt[0] for fmt in formats})
        types.sort()
        types = ''.join(types)
        length = max(fmt[2] for fmt in formats)     # use longest length

        # Handle "E" and "F", giving preference to "F", using longest precision
        if types in {'E', 'F', 'EF', 'EI', 'FI', 'EFI'}:
            letter = 'F' if 'F' in types else 'E'
            prec = max(fmt[3] for fmt in formats if fmt[0] == letter)
            return (letter, 0, length, prec)

        # Handle "D" and/or "T", possibly combined with "A"
        if types in {'D', 'T', 'DT'}:
            return ('T' if 'T' in types else 'D', offset, length, pds4_date_time(formats))

        # Handle "A" combined with "D" and/or "T"
        if types in {'AD', 'AT', 'ADT'}:
            subset = {fmt for fmt in formats if fmt[0] != 'A'}
            return ('T' if 'T' in types else 'D', offset, length, pds4_date_time(subset))

        # Same format but different lengths
        if len(types) == 1:
            return (types[0], offset, length)

        raise TemplateAbort(f'Illegal mixture of types in column {colno+1} at '
                            f'start byte {self._start_bytes[-1]}',
                            self.filepath)

    # Regular expressions for numeric cell values
    _INTEGER = re.compile(rb' *[+-]?\d+')
    _EFLOAT = re.compile(rb' *[+-]?(\d*)\.?(\d*)([eE])[+-]?\d{1,3}')
    _FFLOAT = re.compile(rb' *[+-]?\d*\.(\d*)')
    _DATE = re.compile(rb' *\d\d\d\d-(\d\d-\d\d|\d\d\d)(T\d\d:\d\d:\d\d(?:|\.\d*)Z?)? *')

    def _cell_format(self, value):
        """Returns cell format information for a single table cell value.

        Returns:
            tuple: `(type, offset, length[, precision])` where:

            * `type` (str): "I" for int, "E" for exponential notation with uppercase "E",
              "e" for exponential notation with lowercase "e", "F" for float, "A" for
              string, "D" for date, or "T" for date-time.
            * `offset` (int): 1 if the first character is a quote; 0 otherwise.
            * `length` (int): characters used (excluding quotes if quoted).
            * `precision`: For E and F types, this is the numeric precision. For D and T
              types, this is a string that begins with "YMD" for dates in "yyyy-mm-dd" or
              "YD" for dates in "yyyy-ddd" format; for T formats, "T" is appended,
              followed by "Z" if the time ends in "Z".
        """

        stripped = value.rstrip()   # strip trailing blankcs

        # Date checker, which might be inside quotes
        def _date_fmt(string, offset):
            if match := AsciiTable._DATE.fullmatch(string):
                prec = 'YD' if len(match.group(1)) == 3 else 'YMD'
                if match.group(2):
                    prec += 'T'
                    if match.group(2).endswith(b'Z'):
                        prec += 'Z'
                return ('T' if 'T' in prec else 'D', offset, len(string), prec)

            return None

        # Integer
        if AsciiTable._INTEGER.fullmatch(stripped):
            return ('I', 0, len(stripped))

        # Float
        if match := AsciiTable._EFLOAT.fullmatch(stripped):
            prec = len(match.group(1)) + len(match.group(2)) - 1
            return (match.group(3).decode('latin-1').upper(), 0, len(stripped), prec)
        if match := AsciiTable._FFLOAT.fullmatch(stripped):
            prec = len(match.group(1))
            return ('F', 0, len(stripped), prec)

        # Date
        fmt = _date_fmt(stripped, 0)
        if fmt is not None:
            return fmt

        # Quoted string case
        if value.startswith(b'"') and value.endswith(b'"'):
            string = value[1:-1]

            # Could still be a date
            fmt = _date_fmt(string, 1)
            if fmt is not None:
                return fmt

            # Otherwise, it's a quoted string
            return ('A', 1, len(string))

        # Anything else is an un-quoted, full-length string
        return ('A', 0, len(value))

    ######################################################################################
    # Lookup function
    ######################################################################################

    _PDS3_DATA_TYPES = {
        'A': 'CHARACTER',
        'D': 'DATE',
        'E': 'ASCII_REAL',
        'F': 'ASCII_REAL',
        'I': 'ASCII_INTEGER',
        'T': 'TIME',
    }

    _PDS4_DATA_TYPES = {
        'A': 'ASCII_Text_Preserved',
        'D': 'ASCII_Date',
        'E': 'ASCII_Real',
        'F': 'ASCII_Real',
        'I': 'ASCII_Integer',
        'T': 'ASCII_Date_Time'
    }

    def lookup(self, name, column=0):
        """Lookup function for information about this AsciiTable.

        These are all the options; a column is indicated by an integer starting from zero:

        * `lookup("PATH")` = full path to the table file.
        * `lookup("BASENAME")` = basename of the table file.
        * `lookup("ROWS")` = number of rows.
        * `lookup("ROW_BYTES")` = bytes per row.
        * `lookup("COLUMNS")` = number of columns.
        * `lookup["TERMINATORS"]` = length of terminator: 1 for <LF>, 2 for <CR><LF>.
        * `lookup("WIDTH", <column>)` = width of the column in bytes.
        * `lookup("PDS3_FORMAT", <column>)` = a string containing the format for PDS3,
          e.g.,"I7", "A23", or "F12.4".
        * `lookup("PDS4_FORMAT", <column>)` = a string containing the format for PDS4,
          e.g., "%7d", "%23s", or "%12.4f".
        * `lookup("PDS3_DATA_TYPE", <column>)` = PDS3 data type, one of "CHARACTER",
          "ASCII_REAL", "ASCII_INTEGER", or "TIME".
        * `lookup("PDS4_DATA_TYPE", <column>)` = PDS3 data type, e.g.,
          "ASCII_Text_Preserved", "ASCII_Real", or "ASCII_Date_YMD".
        * `lookup("QUOTES", <column>)` = number of quotes before field value, 0 or 1.
        * `lookup("START_BYTE", <column>)` = start byte of column, starting from 1.
        * `lookup("BYTES", <column>)` = number of bytes in column, excluding quotes.
        * `lookup("VALUES", <column>)` = a list of all the values found in the column.
        * `lookup("MINIMUM", <column>)` = the minimum value in the column.
        * `lookup("MAXIMUM", <column>)` = the maximum value in the column.
        * `lookup("FIRST", <column>)` = the first value in the column.
        * `lookup("LAST", <column>)` = the last value in the column.

        Parameters:
            name (str): Name of a parameter.
            column (int, optional): The index of the column, starting from zero.

        Returns:
            (str, int, float, or bool): The value of the specified parameter as inferred
                from the table.
        """

        match name:
            case 'PATH':
                return str(self.filepath)
            case 'BASENAME':
                return self.filepath.name
            case 'ROWS':
                return self._rows
            case 'ROW_BYTES':
                return self._row_bytes
            case 'COLUMNS':
                return len(self._bvalues)
            case 'TERMINATORS':
                return self._terminators
            case 'WIDTH':
                return self._widths[column]
            case 'PDS3_FORMAT':
                fmt = self._formats[column]
                if fmt[0] in 'eEF':
                    return f'{fmt[0]}{fmt[2]}.{fmt[3]}'
                elif fmt[0] == 'I':
                    return f'I{fmt[2]}'
                else:
                    return f'A{fmt[2]}'
            case 'PDS4_FORMAT':
                fmt = self._formats[column]
                if fmt[0] in 'eE':
                    return f'%{fmt[2]}.{fmt[3]}{fmt[0]}'
                elif fmt[0] == 'F':
                    return f'%{fmt[2]}.{fmt[3]}f'
                elif fmt[0] == 'I':
                    return f'%{fmt[2]}d'
                else:
                    return f'%{fmt[2]}s'
            case 'PDS3_DATA_TYPE':
                return AsciiTable._PDS3_DATA_TYPES[self._formats[column][0]]
            case 'PDS4_DATA_TYPE':
                type_ = self._formats[column][0]
                if type_ in 'DT':
                    return self._formats[column][3]
                else:
                    return AsciiTable._PDS4_DATA_TYPES[type_]
            case 'QUOTES':
                return self._formats[column][1]
            case 'START_BYTE':
                return self._start_bytes[column]
            case 'BYTES':
                return self._widths[column] - 2 * self._formats[column][1]
            case 'VALUES':
                return self._values(column)
            case 'MINIMUM':
                return min(self._values(column))
            case 'MAXIMUM':
                return max(self._values(column))
            case 'FIRST':
                return self._values(column)[0]
            case 'LAST':
                return self._values(column)[-1]

        raise KeyError(name)

    def _values(self, column):
        """All the values in a column using lazy evaluation."""

        if not self._values_[column]:
            fmt = self._formats[column]
            if fmt[0] in 'IEeF' or fmt[1] == 1:
                self._values_[column] = [self._eval(bvalue)
                                         for bvalue in self._bvalues[column]]
            else:
                self._values_[column] = [bvalue.decode('utf-8')
                                         for bvalue in self._bvalues[column]]

        return self._values_[column]

    def _eval(self, bvalue):
        """Convert the given bytes value to int, float, or un-quoted string."""

        stripped = bvalue.strip()
        if stripped.startswith(b'"') and stripped.endswith(b'"') and len(bvalue) > 1:
            if self.escape:
                original_length = len(stripped) - 2
                stripped = stripped[1:-1].replace(self.escape + b'"', b'\x00')
                changed = len(stripped) != original_length
                if changed:
                    stripped = stripped.replace(b'\x00', b'"')
                return stripped.decode('utf-8')
            else:
                return stripped.strip()[1:-1].decode('utf-8')

        try:
            return int(bvalue)
        except ValueError:
            pass

        try:
            return float(bvalue)
        except ValueError:                                          # pragma: no cover
            pass

        return bvalue.decode('utf-8')                               # pragma: no cover

    # Alternative name for the lookup function, primarily for when used in templates.
    TABLE_VALUE = lookup

##########################################################################################
