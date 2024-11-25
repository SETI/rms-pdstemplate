##########################################################################################
# pdstemplate/pds3table.py
##########################################################################################
"""PDS Ring-Moon Systems Node, SETI Institute

Definition of the pre-processor `pds3_table_preprocessor` and the functions
`ANALYZE_PDS3_LABEL`, `VALIDATE_PDS3_LABEL`, `LABEL_VALUE`, and `OLD_LABEL_VALUE` for PDS3
labels that describe an ASCII table.
"""

import re
import pathlib
import warnings

from . import PdsTemplate
from .asciitable import ANALYZE_TABLE, TABLE_VALUE, _latest_ascii_table
from ._utils import get_logger, TemplateError, _check_terminators


class Pds3Table():
    """Class encapsulating a label or template that describes a PDS3 label containing a
    TABLE object.
    """

    # These split a content string into its constituent objects
    _OBJECT_TABLE_REGEX = re.compile(r'( *OBJECT *= *\w*TABLE *\r?\n)(.*?\r?\n)'
                                     r'( *END_OBJECT *= *\w*TABLE *\r?\n)', re.DOTALL)
    _OBJECT_COLUMN_REGEX = re.compile(r'( *OBJECT *= *COLUMN *\r?\n)(.*?\r?\n)'
                                      r'( *END_OBJECT *= *COLUMN *\r?\n)', re.DOTALL)

    # For global access to the latest table
    _LATEST_PDS3_TABLE = None

    def __init__(self, labelpath, label='', *, validate=True, analyze_only=False,
                 crlf=None, numbers=False, formats=False, minmax=(), derived=(),
                 edits=[]):
        """Constructor for a Pds3Table object. It analyzes the content of a PDS3 label or
        template and saves the info for validation or possible repair.

        Parameters:
            labelpath (str or pathlib.Path):
                The path to a PDS3 label or template file.
            label (str, optional): The full content of the template as a single string or
                list of strings, one per record (including line terminators).
            validate (bool, optional):
                True to issue a warning for each error in the label or template when the
                label is generated; False to correct errors silently.
            analyze_only (bool, optional):
                True to prevent the generating an alternative label for purposes of
                repair. This step can be slow for large labels so it should be avoided if
                it is not needed.
            crlf (bool, optional):
                True to raise an error if the line terminators are not <CR><LF>; False to
                raise an error if the line terminator is not <LF> alone; None to accept
                either line terminator.
            numbers (bool, optional):
                True to include COLUMN_NUMBER into each COLUMN object if it is not already
                there.
            formats (bool, optional):
                True to include FORMAT into each COLUMN object if it is not already there.
            minmax (str, tuple[str], or list[str], optional):
                Zero or more names of columns for which to include the MINIMUM_VALUE and
                MAXIMUM_VALUE. In addition or as an alternative, use "float" to include
                these values for all floating-point columns and/or "int" to include these
                values for all integer columns.
            derived (str, tuple[str], or list[str], optional):
                Zero or more names of columns for which to include the DERIVED_MINIMUM and
                DERIVED_MAXIMUM. In addition or as an alternative, use "float" to include
                these values for all floating-point columns.
            edits (list[str]), optional):
                A list of strings of the form "column:name = value", which should be used
                to insert or replace values currently in the label. derived FORMAT and
                DATA_TYPE values.
        """

        self.labelpath = pathlib.Path(labelpath)

        if not label:
            with self.labelpath.open('rb') as f:    # binary to preserve terminators
                label = f.read()
            label = label.decode('latin-1')

        # Identify the line terminator and validate it
        self.crlf = _check_terminators(self.labelpath, label, crlf)
        self.terminator = '\r\n' if self.crlf else '\n'

        # Convert to a single string
        if isinstance(label, list):
            label = ''.join(label)
        self.label = label

        self.analyze_only = analyze_only
        self.numbers = numbers
        self.formats = formats
        self.minmax = (minmax,) if isinstance(minmax, str) else minmax
        self.derived = (derived,) if isinstance(derived, str) else derived

        self._table_values = {}         # parameter name -> value in label or None
        self._column_values = [None]    # list of parameter dicts, one per column
        self._column_name = [None]      # list of column names or str(column number)
        self._column_items = [None]     # list of ITEM counts, minimum 1
        self._column_number = {}        # column name -> column number
        self._table_index = {}          # column name or number -> index in the table
        self._extra_items = 0           # cumulative number of ITEMS > 1 in COLUMN objects

        # Defined by assign_to()
        self.table = None               # AsciiTable to which this label refers
        self._unique_values_ = [None]   # lazily evaluated set of values in each column
        self._unique_valids_ = [None]   # lazily evaluated set of valid valuesn

        # Note that the lists above have one initial value so they can be indexed by
        # column number without subtracting one.

        # Pre-process the edits
        self._edit_dict = {}        # [colname][parname] -> replacement value
        self._edited_values = {}    # [colname][parname] -> original value or None
        for edit in edits:
            colname, _, tail = edit.partition(':')
            colname = colname.strip()
            if colname not in self._edit_dict:
                self._edit_dict[colname] = {}
                self._edited_values[colname] = {}
            name, _, value = tail.partition('=')
            self._edit_dict[colname][name.strip()] = value.strip()

        # parts[0] = label records before the first table
        # parts[1] = record containing "OBJECT = ...TABLE"
        # parts[2] = interior of table object including all COLUMN objects
        # parts[3] = record containing "END_OBJECT = ...TABLE"
        # parts[4] = remainder of label
        parts = Pds3Table._OBJECT_TABLE_REGEX.split(label)
        if len(parts) == 1:
            raise TemplateError('template does not contain a PDS3 TABLE object',
                                self.labelpath)
        if len(parts) > 5:
            raise TemplateError('template contains multiple PDS3 TABLE objects',
                                self.labelpath)

        # Process the table interior
        parts[2] = self._process_table_interior(parts[2])

        # Process the file header
        parts[0], self._table_values['RECORD_TYPE'] = self._replace_value(
                                            parts[0], 'RECORD_TYPE',
                                            '$LABEL_VALUE("RECORD_TYPE")$',
                                            required=True, after='PDS_VERSION_ID')
        parts[0], self._table_values['RECORD_BYTES'] = self._replace_value(
                                            parts[0], 'RECORD_BYTES',
                                            '$LABEL_VALUE("RECORD_BYTES")$',
                                            required=True, after='RECORD_TYPE')
        parts[0], self._table_values['FILE_RECORDS'] = self._replace_value(
                                            parts[0], 'FILE_RECORDS',
                                            '$LABEL_VALUE("FILE_RECORDS")$',
                                            required=True, after='RECORD_BYTES')

        # Create header to analyze the table
        header = ['$ONCE(ANALYZE_TABLE('
                  'LABEL_PATH().replace(".lbl",".tab").replace(".LBL",".TAB")'
                  ', crlf=True))', self.terminator]
        if validate:
            header += ['$ONCE(VALIDATE_PDS3_LABEL())', self.terminator]

        self.content = ''.join(header) + ''.join(parts)

        # Set globals for access within the template object
        Pds3Table._LATEST_PDS3_TABLE = self
        PdsTemplate.define_global('VALIDATE_PDS3_LABEL', VALIDATE_PDS3_LABEL)
        PdsTemplate.define_global('LABEL_VALUE', self.lookup)
        PdsTemplate.define_global('OLD_LABEL_VALUE', self.old_lookup)

        self.table = _latest_ascii_table()
        if self.table:
            PdsTemplate.define_global('ANALYZE_TABLE', ANALYZE_TABLE)
            PdsTemplate.define_global('TABLE_VALUE', TABLE_VALUE)

    def _process_table_interior(self, label):

        # parts[0] = label records before the first column
        # parts[1] = record containing "OBJECT = COLUMN"
        # parts[2] = interior of column object
        # parts[3] = record containing "END_OBJECT = COLUMN"
        # parts[4] = anything after the column object, usually empty
        # parts[5-8] repeat parts[1-4] for each column
        parts = Pds3Table._OBJECT_COLUMN_REGEX.split(label)

        # Process each column
        for k, part in enumerate(parts[2::4]):
            self._column_values.append({})
            parts[2 + 4*k] = self._process_column(part, k+1)

        # Prepare for lazy evaluation as needed
        self._unique_values_ = [None for c in self._column_values] + [None]
        self._unique_valids_ = [None for c in self._column_values] + [None]

        # Process the TABLE object header
        head = parts[0]
        head, self._table_values['INTERCHANGE_FORMAT'] = self._replace_value(
                                            head, 'INTERCHANGE_FORMAT',
                                            '$LABEL_VALUE("INTERCHANGE_FORMAT")$',
                                            required=True, first=True)
        head, self._table_values['ROWS'] = self._replace_value(
                                            head, 'ROWS',
                                            '$LABEL_VALUE("ROWS")$',
                                            required=True, after='INTERCHANGE_FORMAT')
        head, self._table_values['COLUMNS'] = self._replace_value(
                                            head, 'COLUMNS',
                                            '$LABEL_VALUE("COLUMNS")$',
                                            required=True, after='ROWS')
        head, self._table_values['ROW_BYTES'] = self._replace_value(
                                            head, 'ROW_BYTES',
                                            '$LABEL_VALUE("ROW_BYTES")$',
                                            required=True, after='COLUMNS')

        return head + ''.join(parts[1:])

    def _process_column(self, label, colnum):

        # Add this COLUMN object to the mapping from object to column index in the table
        name = Pds3Table._get_value(label, 'NAME')
        self._column_values[-1]['NAME'] = name
        self._column_name.append(name or str(colnum))
        self._column_number[name] = colnum

        # Edit the label if necessary
        edits = self._edit_dict.get(name, {})
        for parname, value in edits.items():
            label, value = self._replace_value(label, parname, value, required=True,
                                               before='DESCRIPTION')
            self._edited_values[name][parname] = value

        self._table_index[name] = colnum + self._extra_items - 1
        self._table_index[colnum] = colnum + self._extra_items - 1

        # Interpret ITEMS, ITEM_BYTES, ITEM_OFFSETS
        items = Pds3Table._get_value(label, 'ITEMS')
        self._column_values[-1]['ITEMS'] = items

        items = items or 1      # change None to 1
        self._column_items.append(items)
        label, self._column_values[-1]['ITEM_BYTES'] = self._replace_value(
                                            label, 'ITEM_BYTES',
                                            f'$LABEL_VALUE("ITEM_BYTES", {colnum})$',
                                            required=(items > 1), after='ITEMS')
        label, self._column_values[-1]['ITEM_OFFSET'] = self._replace_value(
                                            label, 'ITEM_OFFSET',
                                            f'$LABEL_VALUE("ITEM_OFFSET", {colnum})$',
                                            required=(items > 1), after='ITEM_BYTES')

        # Update the offset for the next column
        self._extra_items += items - 1   # accumulate the column offset

        # Parameters always present: DATA_TYPE, START_BYTE, BYTES
        label, data_type = self._replace_value(
                                            label, 'DATA_TYPE',
                                            f'$LABEL_VALUE("DATA_TYPE", {colnum})$',
                                            required=True, after='NAME')
        self._column_values[-1]['DATA_TYPE'] = data_type

        label, self._column_values[-1]['START_BYTE'] = self._replace_value(
                                            label, 'START_BYTE',
                                            f'$LABEL_VALUE("START_BYTE", {colnum})$',
                                            required=True, after='DATA_TYPE')
        label, self._column_values[-1]['BYTES'] = self._replace_value(
                                            label, 'BYTES',
                                            f'$LABEL_VALUE("BYTES", {colnum})$',
                                            required=True, after='START_BYTE')

        # Optional COLUMN_NUMBER
        label, self._column_values[-1]['COLUMN_NUMBER'] = self._replace_value(
                                            label, 'COLUMN_NUMBER',
                                            f'$LABEL_VALUE("COLUMN_NUMBER", {colnum})$',
                                            required=self.numbers, after='NAME')

        # Optional FORMAT
        label, self._column_values[-1]['FORMAT'] = self._replace_value(
                                            label, 'FORMAT',
                                            f'$LABEL_VALUE("FORMAT", {colnum})$',
                                            required=self.formats, after='BYTES')

        # Optional MINIMUM_VALUE, MAXIMUM_VALUE
        required = ((name in self.minmax)
                    or ('float' in self.minmax and 'REAL' in data_type)
                    or ('int' in self.minmax and 'INT' in data_type))
        label, self._column_values[-1]['MINIMUM_VALUE'] = self._replace_value(
                                            label, 'MINIMUM_VALUE',
                                            f'$LABEL_VALUE("MINIMUM_VALUE", {colnum})$',
                                            required=required, before='DESCRIPTION')
        label, self._column_values[-1]['MAXIMUM_VALUE'] = self._replace_value(
                                            label, 'MAXIMUM_VALUE',
                                            f'$LABEL_VALUE("MAXIMUM_VALUE", {colnum})$',
                                            required=required, after='MINIMUM_VALUE')

        # Optional DERIVED_MINIMUM, DERIVED_MAXIMUM
        required = ((name in self.derived)
                    or ('float' in self.derived and 'REAL' in data_type)
                    or ('int' in self.derived and 'INT' in data_type))
        label, self._column_values[-1]['DERIVED_MINIMUM'] = self._replace_value(
                                            label, 'DERIVED_MINIMUM',
                                            f'$LABEL_VALUE("DERIVED_MINIMUM", {colnum})$',
                                            required=required, before='DESCRIPTION')
        label, self._column_values[-1]['DERIVED_MAXIMUM'] = self._replace_value(
                                            label, 'DERIVED_MAXIMUM',
                                            f'$LABEL_VALUE("DERIVED_MAXIMUM", {colnum})$',
                                            required=required, after='DERIVED_MINIMUM')

        # Save these for later use if needed
        self._column_values[-1]['INVALID_CONSTANT'] = \
                                    Pds3Table._get_value(label, 'INVALID_CONSTANT')
        self._column_values[-1]['MISSING_CONSTANT'] = \
                                    Pds3Table._get_value(label, 'MISSING_CONSTANT')
        self._column_values[-1]['NOT_APPLICABLE_CONSTANT'] = \
                                    Pds3Table._get_value(label, 'NOT_APPLICABLE_CONSTANT')
        self._column_values[-1]['NULL_CONSTANT'] = \
                                    Pds3Table._get_value(label, 'NULL_CONSTANT')
        self._column_values[-1]['UNKNOWN_CONSTANT'] = \
                                    Pds3Table._get_value(label, 'UNKNOWN_CONSTANT')
        self._column_values[-1]['VALID_MAXIMUM'] = \
                                    Pds3Table._get_value(label, 'VALID_MAXIMUM')
        self._column_values[-1]['VALID_MINIMUM'] = \
                                    Pds3Table._get_value(label, 'VALID_MINIMUM')
        self._column_values[-1]['SCALING_FACTOR'] = \
                                    Pds3Table._get_value(label, 'SCALING_FACTOR')
        self._column_values[-1]['OFFSET'] = \
                                    Pds3Table._get_value(label, 'OFFSET')

        return label

    ######################################################################################
    # assign_to()
    ######################################################################################

    def assign_to(self, table):
        """Assign this PDS3 label to the given ASCII table.

        Parameters:
            table (AsciiTable): Table to which this PDS3 label should apply.
        """

        if not table and not self.table:
            raise TemplateError('no ASCII table has been analyzed for label',
                                self.labelpath)

        if table and table is not self.table:
            self.table = table
            self._unique_values_ = [None for _ in self._column_values] + [None]
            self._unique_valids_ = [None for _ in self._column_values] + [None]

        PdsTemplate.define_global('TABLE_VALUE', self.table.lookup)

    _TABLE_NAME_REGEX = re.compile(r'.*\^\w*TABLE *= *"?(\w+\.\w+)"? *\r?\n', re.DOTALL)

    def get_table_basename(self):
        """The table basename in the template or label, if present.

        If the TABLE value in the template is a variable name or expression, an empty
        string is returned instead.
        """

        match = Pds3Table._TABLE_NAME_REGEX.match(self.label)
        if match:
            return match.group(1)

        return ''

    def get_table_path(self):
        """The file path to the table described by this label.

        If the TABLE value in the template is a variable name or expression, an empty
        string is returned instead.

        Returns:
            pathlib.Path: Path to the table file if defined in the label; otherwise, an
                empty string.
        """

        basename = self.get_table_basename()
        if basename:
            return self.labelpath.parent / basename

        return ''

    ######################################################################################
    # validate()
    ######################################################################################

    def validate(self, table=None):
        """Compare this object to the given AsciiTable object and issue a warning for each
        erroneous value identified.

        Parameters:
            table (AsciiTable, optional):
                The AsciiTable assigned to this label. If this is specified and is
                different from the currently assigned table, it becomes the assigned
                table.

        Returns:
            int: The number of warning messages issued.
        """

        messages = self._validation_warnings(table)
        for message in messages:
            warnings.warn(message)

        return len(messages)

    def _validate_inside_template(self, table=None):
        """Compare this object to the given AsciiTable object and log a warning message
        for each erroneous value identified.

        Parameters:
            table (AsciiTable, optional):
                The AsciiTable assigned to this label. If this is specified and is
                different from the currently assigned table, it becomes the assigned
                table.

        Returns:
            int: The number of warnings issued.
        """

        messages = self._validation_warnings(table)
        if messages:
            for message in messages:
                get_logger().warn(message, force=True)
        else:
            get_logger().info('Validation successful')

        return len(messages)

    def _validation_warnings(self, table=None):
        """Compare this object to the given AsciiTable object and return a list of
        warnings, one for each erroneous value identified.

        Parameters:
            table (AsciiTable, optional): The AsciiTable assigned to this label. If this
                is specified and is different from the currently assigned table, it
                becomes the assigned table.

        Returns:
            list[str]: A list of warning messages.
        """

        if table and table is not self.table:
            self.assign_to(table)
        table = self.table
        if not table:
            raise TemplateError('No ASCII table has been analyzed for label',
                                self.labelpath)

        messages = []       # accumulated list of warnings
        for name in ['RECORD_TYPE', 'RECORD_BYTES', 'FILE_RECORDS', 'INTERCHANGE_FORMAT',
                     'ROWS', 'COLUMNS', 'ROW_BYTES']:
            messages += self._check_value(name, required=True)

        label_columns = len(self._column_values) - 1
        table_columns = self.lookup('COLUMNS')
        for colnum in range(1, min(label_columns, table_columns)+1):
            colname = self._column_name[colnum]
            data_type = self.lookup('DATA_TYPE', colnum)

            for name in ['NAME', 'DATA_TYPE', 'START_BYTE', 'BYTES']:
                messages += self._check_value(name, colnum, required=True)

            items = self._column_items[colnum]
            for name in ['ITEM_BYTES', 'ITEM_OFFSET']:
                messages += self._check_value(name, colnum, required=(items > 1),
                                              forbidden=(items == 1))

            indx = self._table_index[colnum]
            for k in range(1, items):
                if table.lookup('WIDTH', k+indx) != table.lookup('WIDTH', indx):
                    messages.append(f'{colname}:{name} items have inconsistent widths')
                if table.lookup('QUOTES', k+indx) != self.table.lookup('QUOTES', indx):
                    messages.append(f'{colname}:{name} items have inconsistent quote '
                                    'usage')

            messages += self._check_value('COLUMN_NUMBER', colnum, required=self.numbers)
            messages += self._check_value('FORMAT', colnum, required=self.formats)

            required = ((colname in self.minmax)
                        or ('float' in self.minmax and 'REAL' in data_type)
                        or ('int' in self.minmax and 'INT' in data_type))
            messages += self._check_value('MINIMUM_VALUE', colnum, required=required)
            messages += self._check_value('MAXIMUM_VALUE', colnum, required=required)

            required = ((colname in self.derived)
                        or ('float' in self.derived and 'REAL' in data_type)
                        or ('int' in self.derived and 'INT' in data_type))
            messages += self._check_value('DERIVED_MINIMUM', colnum, required=required)
            messages += self._check_value('DERIVED_MAXIMUM', colnum, required=required)

            for name, old_value in self._edited_values.get(colname, {}).items():
                new_value = self._edit_dict[colname][name]
                if old_value is None:
                    messages.append(f'{colname}:{name} was inserted: {new_value}')
                else:
                    messages.append(f'{colname}:{name} was edited: '
                                    f'{old_value} -> {new_value}')

        for colnum in range(table_columns+1, label_columns+1):
            colname = self._column_name[colnum]
            messages.append(f'column {colname} is missing')

        table_extras = table_columns - label_columns
        if table_extras > 0:
            messages.append(f'table contains {table_extras} undefined column'
                            + ('s' if table_extras > 1 else ''))

        return messages

    def _check_value(self, name, colnum=0, *, required=False, forbidden=False):
        """A list of warnings about anything wrong with the specified PDS3 parameter."""

        # Get the old value from the template; None if absent
        if colnum:
            old_value = self._column_values[colnum][name]
            prefix = self._column_name[colnum] + ':'
        else:
            old_value = self._table_values[name]
            prefix = ''

        # If the old value is an expression, don't warn
        if isinstance(old_value, str) and '$' in old_value:
            return []

        if required and old_value is None:
            new_value = self.lookup(name, colnum)
            new_fmt = Pds3Table._format(new_value)
            return [f'{prefix}{name} is missing: {new_fmt}']

        if forbidden:
            if old_value is not None:
                old_fmt = Pds3Table._format(old_value)
                return [f'{prefix}{name} is forbidden: ({old_fmt})']
            return []

        if not required and not forbidden and old_value is None:
            return []

        # Get the new value
        new_value = self.lookup(name, colnum)

        if old_value == new_value:
            return []

        new_fmt = Pds3Table._format(new_value)
        old_fmt = Pds3Table._format(old_value)
        return [f'{prefix}{name} error: {old_fmt} -> {new_fmt}']

    ######################################################################################
    # lookup()
    ######################################################################################

    def lookup(self, name, column=0):
        """Lookup function returning information about the PDS3 label as it has been
        applied to the current table.

        Each of the following function calls returns a valid PDS3 parameter value. Columns
        can be identified by name or by number starting from 1.

        * `lookup("PATH")
        * `lookup("BASENAME")
        * `lookup("RECORD_TYPE")`
        * `lookup("RECORD_BYTES")`
        * `lookup("FILE_RECORDS")`
        * `lookup("INTERCHANGE_FORMAT")`
        * `lookup("ROWS")`
        * `lookup("COLUMNS")`
        * `lookup("ROW_BYTES")`
        * 'lookup("DATA_TYPE", <column>)`
        * 'lookup("START_BYTE", <column>)`
        * 'lookup("BYTES", <column>)`
        * 'lookup("COLUMN_NUMBER", <column>)`
        * 'lookup("FORMAT", <column>)` (quoted if it contains a period)
        * 'lookup("MINIMUM_VALUE", <column>)`
        * 'lookup("MAXIMUM_VALUE", <column>)`
        * 'lookup("DERIVED_MINIMUM", <column>)`
        * 'lookup("DERIVED_MAXIMUM", <column>)`

        It also provides these values derived from the existing template or label: "NAME",
        "ITEMS", "SCALING_FACTOR", "OFFSET", "INVALID_CONSTANT", "MISSING_CONSTANT",
        "NOT_APPLICABLE_CONSTANT", "NULL_CONSTANT", "UNKNOWN_CONSTANT", "VALID_MINIMUM",
        and "VALID_MAXIMUM".

        In addition, these options are supported:

        * `lookup("TABLE_PATH")`: full path to the associated ASCII table file.
        * `lookup("TABLE_BASENAME")`: basename of the associated ASCII table file.
        * 'lookup("FIRST", <column>)`: value from the first row of this column.
        * 'lookup("LAST", <column>)`: value from the last row of this column.

        Parameters:
            name (str): Name of a parameter.
            column (str or int, optional): The name or COLUMN_NUMBER (starting at 1) for a
                column; use 0 for general parameters.

        Returns:
            str: The correct PDS3-formatted value for the specified parameter.
        """

        if not column:
            colnum = 0
        else:
            colnum = self._column_number[column] if isinstance(column, str) else column

        indx = self._table_index[colnum] if colnum else None
        match name:
            case 'PATH':
                return str(self.labelpath)
            case 'BASENAME':
                return self.labelpath.name
            case 'RECORD_TYPE':
                return 'FIXED_LENGTH'
            case 'INTERCHANGE_FORMAT':
                return 'ASCII'
            case 'COLUMN_NUMBER':
                return colnum
            case 'TABLE_PATH':
                if self.get_table_path():
                    return str(self.get_table_path())
            case 'TABLE_BASENAME':
                if self.get_table_basename():
                    return self.get_table_basename()

        if not self.table:
            self.assign_to(_latest_ascii_table())

        if self.table:
            match name:
                case 'TABLE_PATH':
                    return self.table.lookup('PATH')
                case 'TABLE_BASENAME':
                    return self.table.lookup('BASENAME')
                case 'RECORD_BYTES' | 'ROW_BYTES':
                    return self.table.lookup('ROW_BYTES')
                case 'FILE_RECORDS' | 'ROWS':
                    return self.table.lookup('ROWS')
                case 'COLUMNS':
                    return self.table.lookup('COLUMNS') - self._extra_items
                case 'DATA_TYPE':
                    # Override derived DATA_TYPE if every value in the table is invalid
                    old_value = self._column_values[colnum]['DATA_TYPE']
                    if old_value is not None and len(self._unique_valids(colnum)) == 0:
                        return old_value
                    return self.table.lookup('PDS3_DATA_TYPE', indx)
                case 'START_BYTE':
                    return (self.table.lookup('START_BYTE', indx)
                            + self.table.lookup('QUOTES', indx))
                case 'ITEM_BYTES':
                    return self.table.lookup('BYTES', indx)
                case 'ITEM_OFFSET':
                    return self.table.lookup('WIDTH', indx) + 1
                case 'BYTES':
                    items = self._column_items[colnum]
                    if items == 1:
                        return self.table.lookup('BYTES', indx)
                    else:
                        item_bytes = self.table.lookup('BYTES', indx)
                        item_offset = (self.table.lookup('START_BYTE', indx+1)
                                       - self.table.lookup('START_BYTE', indx))
                        return (items-1) * item_offset + item_bytes
                case 'FORMAT':
                    # Override the derived FORMAT if every value in the table is invalid
                    old_value = self._column_values[colnum]['FORMAT']
                    if old_value is not None and len(self._unique_valids(colnum)) == 0:
                        return old_value
                    return self.table.lookup('PDS3_FORMAT', indx)
                case ('MINIMUM_VALUE' | 'MAXIMUM_VALUE' | 'DERIVED_MINIMUM' |
                      'DERIVED_MAXIMUM'):
                    unique = self._unique_valids(colnum) or self._unique_values(colnum)
                    new_value = min(unique) if 'MINIMUM' in name else max(unique)
                    if 'DERIVED' not in name or self._is_a_constant(colnum, new_value):
                        return new_value
                    scaling = self._column_values[colnum].get('SCALING_FACTOR', 1) or 1
                    offset = self._column_values[colnum].get('OFFSET', 0) or 0
                    if (scaling, offset) != (1, 0):     # can't multiply string values!
                        new_value = new_value * scaling + offset
                    return new_value
                case 'FIRST' | 'LAST':
                    return Pds3Table._eval(self.table.lookup(name, indx))
                case _:
                    return self.old_lookup(name, colnum)

        raise TemplateError('no ASCII table has been analyzed')

    def _unique_values(self, colnum):
        """The set of unique values in the specified column number.

        Values are cached so any value only needs to be validated once.
        """

        unique = self._unique_values_[colnum]       # first check the cache
        if unique is None:
            indx = self._table_index[colnum]
            items = self._column_items[colnum]

            unique = set()
            for i in range(indx, indx+items):
                unique |= {Pds3Table._eval(v) for v in self.table.lookup('VALUES', i)}

            self._unique_values_[colnum] = unique

        return unique

    def _unique_valids(self, colnum):
        """The set of unique, valid values in the specified column number.

        Values are cached so any value only needs to be validated once.
        """

        unique = self._unique_valids_[colnum]       # first check the cache
        if unique is None:
            column_dict = self._column_values[colnum]
            constants = {
                column_dict['INVALID_CONSTANT'],
                column_dict['MISSING_CONSTANT'],
                column_dict['NOT_APPLICABLE_CONSTANT'],
                column_dict['NULL_CONSTANT'],
                column_dict['UNKNOWN_CONSTANT'],
            }
            unique = self._unique_values(colnum) - constants

            if (value := self._column_values[colnum]['VALID_MINIMUM']) is not None:
                unique = {v for v in unique if v >= value}
            if (value := self._column_values[colnum]['VALID_MAXIMUM']) is not None:
                unique = {v for v in unique if v <= value}

            self._unique_valids_[colnum] = unique

        return unique

    def _is_a_constant(self, colnum, value):
        """True if the given value matches one of the constants in the specified column.
        """

        column_dict = self._column_values[colnum]
        for name in ['INVALID_CONSTANT', 'MISSING_CONSTANT', 'NOT_APPLICABLE_CONSTANT',
                     'NULL_CONSTANT', 'UNKNOWN_CONSTANT']:
            if value == column_dict[name]:
                return False

        return True

    def old_lookup(self, name, column=0):
        """Lookup function returning information about the current content of the PDS3
        label, whether or not it is correct.

        Available top-level keywords are "RECORD_TYPE", "RECORD_BYTES", "FILE_RECORDS",
        "INTERCHANGE_FORMAT", "ROWS", "COLUMNS", and "ROW_BYTES".

        Available column-level keywords are "NAME", "COLUMN_NUMBER", "DATA_TYPE",
        "START_BYTE", "BYTES", "FORMAT", "ITEMS", "ITEM_BYTES", "ITEM_OFFSET",
        "SCALING_FACTOR", "OFFSET", "INVALID_CONSTANT", "MISSING_CONSTANT",
        "NOT_APPLICABLE_CONSTANT", "NULL_CONSTANT", "UNKNOWN_CONSTANT", "VALID_MAXIMUM",
        "VALID_MINIMUM", "MINIMUM_VALUE", "MAXIMUM_VALUE", "DERIVED_MINIMUM", and
        "DERIVED_MAXIMUM".

        Parameters:
            name (str): Name of a parameter.
            column (str or int, optional): The name or COLUMN_NUMBER (starting at 1) for a
                column; use 0 for general parameters.

        Returns:
            str: The current value of the specified parameter, or None if it is not found
                in the label.
        """

        if not column:
            return self._table_values[name]
        else:
            colnum = self._column_number[column] if isinstance(column, str) else column
            return self._column_values[colnum][name]

        raise KeyError(name)

    # Alternative names for use inside templates
    LABEL_VALUE = lookup
    OLD_LABEL_VALUE = old_lookup

    ######################################################################################
    # PDS3 label utilities
    ######################################################################################

    def _replace_value(self, label, name, replacement, *, required=False, after=None,
                       before=None, first=False):
        """Replace a value in a label string with the given replacement.

        Parameters:
            label (str): PDS3 label substring.
            name (str): PDS3 parameter name.
            replacement (str): Replacement string, formatted as needed for the label.
            required (bool): True if the parameter is required. If required, the name and
                replacement will be inserted if not present already.
            after (str, optional): If the new parameter must be inserted, it will appear
                immediately after this parameter.
            before (str, optional): If the new parameter must be inserted, it will apppear
                immediately before this parameter.
            first (str, optional): If the new parameter must be inserted, it will apppear
                first in the label.

        Returns:
            str: The revised label string.
            str or None: The prior value of the parameter before replacement, if present.

        Notes:
            If the replacement string contains "$", meaning that it already contains a
            PdsTemplate expression, it is not replaced.
        """

        # Split by the name=value substring
        parts = re.split(r'(?<!\S)(' + name + r' *= *)([^\r\n]*)', label)
            # If a match is found, this will be a list [before, "<name> = ", value, after]

        if len(parts) == 1:     # if not found
            if not required:
                return (label, None)

            new_label = self._insert_value(label, name, replacement, after=after,
                                            before=before, first=first)
            return (new_label, None)

        value = Pds3Table._eval(parts[2])
        if not self.analyze_only:
            label = parts[0] + parts[1] + replacement + ''.join(parts[3:])
        return (label, value)

    def _insert_value(self, label, name, value, *, after=None, before=None, first=False):
        """Insert a new name=value entry into the label string.

        Parameters:
            label (str): PDS3 label substring.
            name (str): PDS3 parameter name.
            value (str): Value string, formatted as needed for the label.
            after (str, optional): Insert the new name=value entry immediately after this
                parameter, if present.
            before (str, optional): Insert the new name=value entry immediately before
                this parameter, if present.
            first (str, optional): If True, insert the new name=value entry first.

        Returns:
            str: The revised label.

        Notes:
            If neither `after` nor `before` is specified and `first` is False, the new
            entry appears at the end. The order of precedence is `first`, `after`,
            before`.
        """

        if self.analyze_only:
            return label

        # Figure out the alignments and terminator for the new entry
        indent = len(label) - len(label.lstrip())
        equal = len(label.partition('=')[0])
        terminator = '\r\n' if label.endswith('\r\n') else '\n'

        # Define the full line to be inserted
        new_line = indent * ' ' + name + equal * ' '
        new_line = new_line[:equal] + '= ' + value + terminator

        # Apply `first`
        if first:
            return new_line + label

        # Apply `after`
        if after:
            parts = re.split(r'(?<!\S)(' + after + r' *=.*?\n)', label)
            if len(parts) > 1:
                return parts[0] + parts[1] + new_line + ''.join(parts[2:])

        # Apply `before`
        if before:
            parts = re.split(r'(?<![^\n])( *' + before + r' *=)', label)
            if len(parts) > 1:
                return parts[0] + new_line + ''.join(parts[1:])

        # Otherwise, insert at the end
        return label + new_line

    @staticmethod
    def _get_value(label, name):
        """The value of the named parameter within the label.

        Parameters:
            label (str): PDS3 label string.
            name (str): PDS3 parameter name.

        Returns:
            (int, float, str, or None): The value of the parameter if present; None
                otherwise.
        """

        # Find name=value substring
        matches = re.findall(r'(?<!\S)' + name + r' *= *([^\r\n]*)', label)
        if not matches:
            return None

        return Pds3Table._eval(matches[0].rstrip())

    @staticmethod
    def _eval(value):
        """Convert the given string value to int, float, or un-quoted string."""

        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            if value[0] == '"':
                return value[1:-1].strip()

            try:
                return int(value)
            except ValueError:
                pass

            try:
                return float(value)
            except ValueError:
                pass

        return value

    @staticmethod
    def _format(value):
        """Return the value formatted for the PDS3 label."""

        if isinstance(value, int):
            return str(value)

        if isinstance(value, float):
            value = str(value)
            (before, optional_e, after) = value.partition('e')
            if '.' not in before:
                before += '.'
            before.rstrip('0')
            return before + optional_e + after

        if value.startswith('"'):
            value = value.rstrip()[1:-1]
        value = value.rstrip()

        if value in ('N/A', "'N/A'"):
            return "'N/A'"

        if value.isidentifier():
            return value

        return '"' + value + '"'

##########################################################################################
# Preprocessor
##########################################################################################

def pds3_table_preprocessor(labelpath, content, *, validate=True, numbers=False,
                            formats=False, minmax=(), derived=(), edits=[]):
    """Update the PDS3 label or template for an ASCII table, replacing given values with
    those to be derived from an ASCII table.

    After the template is preprocessed, the function "`$LABEL_VALUE()$`" can be used
    anywhere in the template to fill in values derived from the table.

    Parameters:
        labelpath (str or pathlib.Path):
            The path to the PDS3 label or template file.
        content (str): The full content of the template as a single string with a newline
            character after each line.
        validate (bool, optional):
            If True, a warning will be issued for each error found when the label is
            generated; otherwise, errors will be repaired silently.
        numbers (bool, optional):
            True to include COLUMN_NUMBER into each COLUMN object if it is not already
            there.
        formats (bool, optional):
            True to include FORMAT into each COLUMN object if it is not already there.
        minmax (str, tuple[str], or list[str], optional):
            Zero or more names of columns for which to include the MINIMUM_VALUE and
            MAXIMUM_VALUE. In addition or as an alternative, use "float" to include these
            values for all floating-point columns and/or "int" to include these values for
            all integer columns.
        derived (str, tuple[str], or list[str], optional):
            Zero or more names of columns for which to include the DERIVED_MINIMUM and
            DERIVED_MAXIMUM. In addition or as an alternative, use "float" to include
            these values for all floating-point columns.
        edits (list[str]), optional):
            A list of strings of the form "column:name = value", which should be used to
            insert or replace values currently in the label. derived FORMAT and DATA_TYPE
            values.

    Returns:
        str: The revised content for the template.
    """

    with get_logger().open('PDS3 table preprocessor', labelpath):
        pds3_label = Pds3Table(labelpath, content, validate=validate, numbers=numbers,
                               formats=formats, minmax=minmax, derived=derived,
                               edits=edits)

    return pds3_label.content

##########################################################################################
# Template functions
##########################################################################################

def VALIDATE_PDS3_LABEL():
    """Log a warning for every error found when generating this PDS3 label.

    Returns:
        int: The number of warnings issued.
    """

    label = Pds3Table._LATEST_PDS3_TABLE
    with get_logger().open('Validating PDS3 label', label.labelpath):
        count = Pds3Table._validate_inside_template(label)

    return count


def ANALYZE_PDS3_LABEL(labelpath, *, validate=True, numbers=False, formats=False,
                       minmax=(), derived=(), edits=[]):
    """Analyze the current PDS3 label as applied to the most recently analyzed ASCII table
    or template for an ASCII table, replacing given values with
    those to be derived from an ASCII table.

    After the template is preprocessed, the function "`$LABEL_VALUE()$`" can be used
    anywhere in the template to fill in values derived from the table.

    Parameters:
        labelpath (str or pathlib.Path):
            Path to the current label.
        validate (bool, optional):
            If True, warning message will be logged for every error found in the template;
            otherwise, errors will be corrected silently.
        numbers (bool, optional):
            True to include COLUMN_NUMBER into each COLUMN object if it is not already
            there.
        formats (bool, optional):
            True to include FORMAT into each COLUMN object if it is not already there.
        minmax (str, tuple[str], or list[str], optional):
            Zero or more names of columns for which to include the MINIMUM_VALUE and
            MAXIMUM_VALUE. In addition or as an alternative, use "float" to include these
            values for all floating-point columns and/or "int" to include these values for
            all integer columns.
        derived (str, tuple[str], or list[str], optional):
            Zero or more names of columns for which to include the DERIVED_MINIMUM and
            DERIVED_MAXIMUM. In addition or as an alternative, use "float" to include
            these values for all floating-point columns.
        edits (list[str]), optional):
            A list of strings of the form "column:name = value", which should be used to
            insert or replace values currently in the label. derived FORMAT and DATA_TYPE
            values.
    """

    with get_logger().open('Analyzing PDS3 label', labelpath):
        label = Pds3Table(labelpath, numbers=numbers, formats=formats, minmax=minmax,
                          derived=derived, edits=edits, analyze_only=True)

        if validate:
            Pds3Table._validate_inside_template(label)


def LABEL_VALUE(name, column=0):
    """Lookup function returning information about the PDS3 label after it has been
    analyzed or pre-processed and after the ASCII table has been analyzed.

    Each of the following function calls returns a valid PDS3 parameter value. Columns
    can be identified by name or by number starting from 1.

    * `LABEL_VALUE("TABLE")
    * `LABEL_VALUE("RECORD_TYPE")`
    * `LABEL_VALUE("RECORD_BYTES")`
    * `LABEL_VALUE("FILE_RECORDS")`
    * `LABEL_VALUE("INTERCHANGE_FORMAT")`
    * `LABEL_VALUE("ROWS")`
    * `LABEL_VALUE("COLUMNS")`
    * `LABEL_VALUE("ROW_BYTES")`
    * 'LABEL_VALUE("NAME", <column>)`
    * 'LABEL_VALUE("DATA_TYPE", <column>)`
    * 'LABEL_VALUE("START_BYTE", <column>)`
    * 'LABEL_VALUE("BYTES", <column>)`
    * 'LABEL_VALUE("COLUMN_NUMBER", <column>)`
    * 'LABEL_VALUE("FORMAT", <column>)` (quoted if it contains a period)
    * 'LABEL_VALUE("MINIMUM_VALUE", <column>)`
    * 'LABEL_VALUE("MAXIMUM_VALUE", <column>)`
    * 'LABEL_VALUE("DERIVED_MINIMUM", <column>)`
    * 'LABEL_VALUE("DERIVED_MAXIMUM", <column>)`

    In addition, column values from the first and last rows of a table can be accessed as:

    * 'LABEL_VALUE("FIRST", <column>)`
    * 'LABEL_VALUE("LAST", <column>)`

    Parameters:
        name (str): Name of a parameter.
        column (str or int, optional): The name or COLUMN_NUMBER (starting at 1) for a
            column; use 0 for general parameters.

    Returns:
        str: The correct PDS3-formatted value for the specified parameter.
    """

    if not Pds3Table._LATEST_PDS3_TABLE:
        raise TemplateError('no PDS3 label has been analyzed')

    return Pds3Table._LATEST_PDS3_TABLE.lookup(name, column)


def OLD_LABEL_VALUE(name, column=0):
    """Lookup function returning information about the current content of the PDS3 label,
    whether or not it is correct.

    Available top-level keywords are "RECORD_TYPE", "RECORD_BYTES", "FILE_RECORDS",
    "INTERCHANGE_FORMAT", "ROWS", "COLUMNS", and "ROW_BYTES".

    Available column-level keywords are "NAME", "COLUMN_NUMBER", "DATA_TYPE",
    "START_BYTE", "BYTES", "FORMAT", "ITEMS", "ITEM_BYTES", "ITEM_OFFSET",
    "SCALING_FACTOR", "OFFSET", "INVALID_CONSTANT", "MISSING_CONSTANT",
    "NOT_APPLICABLE_CONSTANT", "NULL_CONSTANT", "UNKNOWN_CONSTANT", "VALID_MAXIMUM",
    "VALID_MINIMUM", "MINIMUM_VALUE", "MAXIMUM_VALUE", "DERIVED_MINIMUM", and
    "DERIVED_MAXIMUM".

    Parameters:
        name (str): Name of a parameter.
        column (str or int, optional): The name or COLUMN_NUMBER (starting at 1) for a
            column; use 0 for general parameters.

    Returns:
        str: The current value of the specified parameter, or None if it is not found in
            the label.
    """

    return Pds3Table._LATEST_PDS3_TABLE.old_lookup(name, column)


PdsTemplate.define_global('ANALYZE_PDS3_LABEL', ANALYZE_PDS3_LABEL)

##########################################################################################