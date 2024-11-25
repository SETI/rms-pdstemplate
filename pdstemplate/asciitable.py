##########################################################################################
# pdstemplate/asciitable.py
##########################################################################################
"""PDS Ring-Moon Systems Node, SETI Institute

Define template functions ANALYZE_TABLE() and TABLE_VALUE() for use within a template
along with the AsciiTable class that supports them.
"""

import pathlib
import re
from . import PdsTemplate
from ._utils import get_logger, TemplateError, _check_terminators


class AsciiTable():

    # This will match any valid fields between un-quoted commas
    _COMMA_REGEX = rb'([^",]*| *"[^"]*" *)(?:,|$)'

    _COLUMN_REGEX = {
        b',' : re.compile(_COMMA_REGEX),
        b'|' : re.compile(_COMMA_REGEX.replace(b',', rb'\|')),
        b';' : re.compile(_COMMA_REGEX.replace(b',', b';')),
        b'\t': re.compile(_COMMA_REGEX.replace(b',', b'\t')),
    }

    # For global access to the latest table
    _LATEST_ASCII_TABLE = None

    def __init__(self, filepath, records=[], *, separator=',', crlf=None, escape=''):
        """Constructor for an AsciiTable represented as a list of records.

        Parameters:
            filepath (str or pathlib.Path):
                The path to an ASCII table file.
            records (list[bytes], optional):
                The table file content as a sequence of byte strings. If the list is
                empty, the file will be read; otherwise, this content is used without
                reading the file. Each record must include its line terminator.
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

        self.filepath = pathlib.Path(filepath)

        if separator not in ',;|\t':
            raise ValueError('disallowed separator: ' + repr(separator))
        self.separator = separator.encode('latin-1')

        if escape not in ('"', '\\', ''):
            raise ValueError('disallowed escape character: ' + repr(escape))
        self.escape = escape.encode('latin-1')

        # Read the file if necessary
        if not records:
            with self.filepath.open('rb') as f:
                records = f.readlines()

        # Identify the line terminator and validate
        self.crlf = _check_terminators(filepath, records, crlf=crlf)
        self._terminators = 2 if self.crlf else 1

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
            if not all(p == b'' for p in parts[::2]) or parts[-2] != b'':
                raise TemplateError(f'invalid use of quotes in record {recno+1}')

            columns = parts[1:-2:2]

            # Restore escaped quotes
            if changed:
                columns = [c.replace(b'\x00', self.escape + b'"') for c in columns]

            if not self._bvalues:
                self._bvalues = [[] for _ in columns]
                self._values_ = [[] for _ in columns]

            if len(self._bvalues) != len(columns):
                raise TemplateError('inconsistent column count')

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
                    raise TemplateError(f'inconsistent width in record {recno+1}, '
                                        f'column {colno+1}')

            # Infer the common format within this column
            self._formats.append(self._column_format(column, colno))

        # Provide global access
        AsciiTable._LATEST_ASCII_TABLE = self
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

        types = {fmt[0] for fmt in formats}
        joined = ''.join(types)
        length = max(fmt[2] for fmt in formats)     # use longest length

        # Handle "E" and "F", giving preference to "F", using longest precision
        if joined in {'E', 'F', 'EF', 'FE'}:
            prec = max(fmt[3] for fmt in formats)
            return ('F' if 'F' in types else 'E', 0, length, prec)

        # Handle "D" and "T"
        if joined in {'D', 'T', 'DT', 'TD'}:
            return ('T' if 'T' in types else 'D', offset, length, pds4_date_time(formats))

        # Same format but different lengths
        if len(types) == 1:
            return (joined, offset, length)

        raise TemplateError(f'illegal mixture of types in column {colno+1}')

    # Regular expressions for numeric cell values
    _INTEGER = re.compile(rb' *[+-]?\d+')
    _EFLOAT = re.compile(rb' *[+-]?(\d*)\.?(\d*)([eE])[+-]?\d{1,3}')
    _FFLOAT = re.compile(rb' *[+-]?\d*\.(\d*)')
    _DATE = re.compile(rb' *\d\d\d\d-(\d\d-\d\d|\d\d\d)(T\d\d:\d\d:\d\d(?:|\.\d*)Z?)?')

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

        # Quoted string case
        if value.startswith(b'"'):
            return ('A', 1, len(stripped) - 2)

        # Integer
        if AsciiTable._INTEGER.fullmatch(stripped):
            return ('I', 0, len(stripped))

        # Float
        if match := AsciiTable._EFLOAT.fullmatch(stripped):
            prec = len(match.group(1)) + len(match.group(2)) - 1
            return (match.group(3).decode('latin-1'), 0, len(stripped), prec)
        if match := AsciiTable._FFLOAT.fullmatch(stripped):
            prec = len(match.group(1))
            return ('F', 0, len(stripped), prec)

        # Date
        if match := AsciiTable._DATE.fullmatch(stripped):
            prec = 'YD' if len(match.group(1)) == 3 else 'YMD'
            if match.group(2):
                prec += 'T'
                if match.group(2).endswith(b'Z'):
                    prec += 'Z'
            return ('T' if 'T' in prec else 'D', 0, len(stripped), prec)

        # Anything else is a full-length string
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
        * `lookup["TERMINATORS"] = length of terminator: 1 for <LF>, 2 for <CR><LF>.
        * `lookup("WIDTH", <column>)` = width of the column in bytes.
        * `lookup("PDS3_FORMAT", <column>)` = a string containing the format for PDS3,
           e.g.,`I7`, `A23`, or `"F12.4"`. If it contains a period, it is surrounded by
           quotes.
        * `lookup("PDS4_FORMAT", <column>)` = a string containing the format for PDS4,
          e.g., `%7d`, `%23s`, or `%12.4f`.
        * 'lookup("PDS3_DATA_TYPE", <column>)` = PDS3 data type, one of `CHARACTER`,
          `ASCII_REAL`, `ASCII_INTEGER`, or `TIME`.
        * 'lookup("PDS4_DATA_TYPE", <column>)` = PDS3 data type, e.g.,
          `ASCII_Text_Preserved`, `ASCII_Real`, or `ASCII_Date_YMD`.
        * 'lookup("QUOTES", <column>)` = number of quotes before field value, 0 or 1.
        * 'lookup("START_BYTE", <column>)` = start byte of column, starting from 1.
        * 'lookup("BYTES", <column>)` = number of bytes in column, excluding quotes.
        * 'lookup("VALUES", <column>)` = a list of all the values found in the column.
        * 'lookup("MINIMUM", <column>)` = the minimum value in the column.
        * 'lookup("MAXIMUM", <column>)` = the maximum value in the column.
        * 'lookup("FIRST", <column>)` = the first value in the column.
        * 'lookup("LAST", <column>)` = the last value in the column.

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
                    return f'"{fmt[0]}{fmt[2]}.{fmt[3]}"'
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
# Template support functions
##########################################################################################

def ANALYZE_TABLE(filepath, *, separator=',', crlf=None, escape=''):
    """Analyze the given table and define it as the default table for subsequent calls to
    `TABLE_VALUE()` inside a template.

    Parameters:
        filepath (str or pathlib.Path):
            The path to an ASCII table file.
        records (list[bytes]):
            The table file content as a sequence of byte strings. If the list is empty,
            the file will be read; otherwise, this content is used instead of reading the
            file.
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

    AsciiTable._LATEST_ASCII_TABLE = None

    logger = get_logger()
    logger.open('Analyzing ASCII table', filepath)
    try:
        _ = AsciiTable(filepath, separator=separator, crlf=crlf, escape=escape)
    except Exception as err:
        logger.exception(err)
    finally:
        logger.close(force='error')


def TABLE_VALUE(name, column=0):
    """Lookup function for information about the table analyzed in the most recent call to
    ANALYZE_TABLE().

    These are all the options; a column is indicated by an integer starting from zero:

    * `TABLE_VALUE("PATH")` = full path to the table file.
    * `TABLE_VALUE("BASENAME")` = basename of the table file.
    * `TABLE_VALUE("ROWS")` = number of rows.
    * `TABLE_VALUE("ROW_BYTES")` = bytes per row.
    * `TABLE_VALUE("COLUMNS")` = number of columns.
    * `TABLE_VALUE["TERMINATORS"] = length of terminator: 1 for <LF>, 2 for <CR><LF>.
    * `TABLE_VALUE("WIDTH", <column>)` = width of the column in bytes.
    * `TABLE_VALUE("PDS3_FORMAT", <column>)` = a string containing the format for PDS3,
      e.g., `I7`, `A23`, or `"F12.4"`. If it contains a period, it is surrounded by
      quotes.
    * `TABLE_VALUE("PDS4_FORMAT", <column>)` = a string containing the format for PDS4,
      e.g., `%7d`, `%23s`, or `%12.4f`.
    * 'TABLE_VALUE("PDS3_DATA_TYPE", <column>)` = PDS3 data type, one of `CHARACTER`,
      `ASCII_REAL`, `ASCII_INTEGER`, or `TIME`.
    * 'TABLE_VALUE("PDS4_DATA_TYPE", <column>)` = PDS3 data type, e.g.,
      `ASCII_Text_Preserved`, `ASCII_Real`, or `ASCII_Date_YMD`.
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
        (str, int, float, or bool): The value of the specified parameter as inferred from
            the ASCII table.
        """

    table = AsciiTable._LATEST_ASCII_TABLE
    if not table:
        raise TemplateError('no ASCII table has been analyzed')

    return table.lookup(name, column)


def _latest_ascii_table():
    """The most recently defined AsciiTable object. Provided for global access."""

    return AsciiTable._LATEST_ASCII_TABLE


PdsTemplate.define_global('ANALYZE_TABLE', ANALYZE_TABLE)

##########################################################################################
