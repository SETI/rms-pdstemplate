##########################################################################################
# pdstemplate/pds3table.py
##########################################################################################
"""
.. _pds3table:

#####################
pdstemplate.pds3table
#####################

``pds3table`` is a plug-in module to automate the generation and validation of PDS3 labels
for ASCII tables. It works in concert with the :ref:`asciitable` module, which analyzes
the content of ASCII table files. It is used by stand-alone program ``tablelabel`` to
validate and repair existing PDS3 labels as well as to generate new labels; if
``tablelabel`` meets your needs, you can avoid any programming in Python.

To import::

    import pdstemplate.pds3table

Once imported, the following pre-defined functions become available for use within a
:class:`PdsTemplate`:

* :meth:`ANALYZE_PDS3_LABEL` analyzes the content of a PDS3 label or template, gathering
  information about the names and other properties of its TABLE and COLUMN objects. Once
  it is called, the following functions become available.
* :meth:`~asciitable.ANALYZE_TABLE` (from :ref:`asciitable`) takes the path to an existing
  ASCII table and analyzes its content, inferring details about the content and formats of
  all the columns.
* :meth:`VALIDATE_PDS3_LABEL` issues a warning message for any errors found in the label
  or template. Optionally, it can abort the generation of the label if it encounters an
  irrecoverable incompatibility with the ASCII table.
* :meth:`LABEL_VALUE` returns correct and valid PDS3 values for many of the attributes of
  PDS3 TABLE and COLUMN objects, based on its analysis of the table.
* :meth:`OLD_LABEL_VALUE` returns the current (although possibly incorrect or missing)
  values for many of the same PDS3 TABLE and COLUMN attributes.

For example, consider a template that contains this content::

    $ONCE(ANALYZE_TABLE(LABEL_PATH().replace('.lbl', '.tab')))
    $ONCE(ANALYZE_PDS3_LABEL(TEMPLATE_PATH()))
    ...
    OBJECT              = TABLE
      ...
      ROWS              = $LABEL_VALUE('ROWS')$
      COLUMNS           = $LABEL_VALUE('COLUMNS')$

      OBJECT            = COLUMN
        NAME            = FILE_NAME
        COLUMN_NUMBER   = $LABEL_VALUE("COLUMN_NUMBER", "FILE_NAME")$
        DATA_TYPE       = $LABEL_VALUE("DATA_TYPE", "FILE_NAME")$
        START_BYTE      = $LABEL_VALUE("START_BYTE", "FILE_NAME")$
        BYTES           = $LABEL_VALUE("BYTES", "FILE_NAME")$
        FORMAT          = $LABEL_VALUE("FORMAT", "FILE_NAME")$
        MINIMUM_VALUE   = $LABEL_VALUE("MINIMUM_VALUE", "FILE_NAME")$
        MAXIMUM_VALUE   = $LABEL_VALUE("MAXIMUM_VALUE", "FILE_NAME")$
        DESCRIPTION     = "Name of file in the directory"
      END_OBJECT        = COLUMN
    ...

The initial calls to :meth:`~asciitable.ANALYZE_TABLE` and :meth:`ANALYZE_PDS3_LABEL` are
embedded inside a :ref:`ONCE` directive because they return no content. The first call
analyzes the content and structure of the ASCII table, and the second analyzes the
template. The subsequent calls to :meth:`LABEL_VALUE` fill in the correct values for the
specified quantities.

Optionally, you could include this as the third line in the template::

    $ONCE(VALIDATE_PDS3_LABEL())

This function logs a warnings and errors for any incorrect TABLE and COLUMN values
currently in the template.

This module also provides a pre-processor, which can be used to validate or repair an
exising PDS3 label. The function :meth:`pds3_table_preprocessor`, when used as the
`preprocess` input to the :meth:`~pdstemplate.PdsTemplate` constructor, transforms an
existing PDS3 label into a new template by replacing all needed TABLE and COLUMN
attributes with calls to :meth:`LABEL_VALUE`. The effect is that when the label is
generated, it is guaranteed to contain correct information where the earlier label might
have been incorrect. In this case, your program would look something like this::

    from pdstemplate import PdsTemplate
    from pdstemplate.pds3table import pds3_table_preprocessor

    template = PdsTemplate(label_path, crlf=True, ...
                           preprocess=pds3_table_preprocessor, kwargs={...})
    template.write({}, label_path, ...)

The constructor invokes :meth:`pds3_table_preprocessor` to transform the label into a
template. You can use the `kwargs` input dictionary to provide inputs to the
pre-processor, such as adding a requirement that each column contain FORMAT,
COLUMN_NUMBER, MINIMUM/MAXIMUM_VALUEs, etc., and designating how warnings and errors are
to be handled.

Afterward, the call to the template's :meth:`~pdstemplate.PdsTemplate.write` method will
validate the label and/or write a new label, depending on its input parameters.

For example, suppose the label contains this::

    PDS_VERSION_ID          = PDS3
    RECORD_TYPE             = FIXED_LENGTH
    RECORD_BYTES            = 1089
    FILE_RECORDS            = 1711
    ^INDEX_TABLE            = "COVIMS_0094_index.tab"

    OBJECT                  = INDEX_TABLE
      INTERCHANGE_FORMAT    = ASCII
      ROWS                  = 1711
      COLUMNS               = 61
      ROW_BYTES             = 1089
      DESCRIPTION           = "This Cassini VIMS image index ...."

      OBJECT                = COLUMN
        NAME                = FILE_NAME
        DATA_TYPE           = CHARACTER
        START_BYTE          = 2
        BYTES               = 25
        DESCRIPTION         = "Name of file in the directory"
      END_OBJECT            = COLUMN
    ...

You then execute this::

    template = PdsTemplate(label_path, crlf=True,
                           preprocess=pds3_table_preprocessor,
                           kwargs={'numbers': True, 'formats': True})

After the call, you can look at the template's `content` attribute, which contains the
template's content after pre-processing. Its value is this::

    $ONCE(ANALYZE_TABLE(LABEL_PATH().replace(".lbl",".tab").replace(".LBL",".TAB"), crlf=True))
    $ONCE(VALIDATE_PDS3_LABEL(hide_warnings, abort_on_error))
    PDS_VERSION_ID          = PDS3
    RECORD_TYPE             = $LABEL_VALUE("RECORD_TYPE")$
    RECORD_BYTES            = $LABEL_VALUE("RECORD_BYTES")$
    FILE_RECORDS            = $LABEL_VALUE("FILE_RECORDS")$

    OBJECT                  = INDEX_TABLE
      INTERCHANGE_FORMAT    = $LABEL_VALUE("INTERCHANGE_FORMAT")$
      ROWS                  = $LABEL_VALUE("ROWS")$
      COLUMNS               = $LABEL_VALUE("COLUMNS")$
      ROW_BYTES             = $LABEL_VALUE("ROW_BYTES")$
      DESCRIPTION           = "This Cassini VIMS image index ...."

      OBJECT                = COLUMN
        NAME                = FILE_NAME
        COLUMN_NUMBER       = $LABEL_VALUE("COLUMN_NUMBER", 1)$
        DATA_TYPE           = $LABEL_VALUE("DATA_TYPE", 1)$
        START_BYTE          = $LABEL_VALUE("START_BYTE", 1)$
        BYTES               = $LABEL_VALUE("BYTES", 1)$
        FORMAT              = $QUOTE_IF(LABEL_VALUE("FORMAT", 1))$
        DESCRIPTION         = "Name of file in the directory"
      END_OBJECT            = COLUMN
    ...

The TABLE and COLUMN attributes defining table format and structure have been replaced by
calls to :meth:`LABEL_VALUE`, which will provide the correct value whether or not the
value in the original label was correct. Also, COLUMN_NUMBER and FORMAT have been added to
the COLUMN object because of the pre-processor inputs `numbers=True` and `formats=True`.

Another application of the preprocessor is to simplify the construction of a template for
an ASCII table. Within a template, the only required attributes of a COLUMN object are
NAME and DESCRIPTION. Optionally, you can also specify any special constants,
VALID_MINIMUM/MAXIMUM values, OFFSET and SCALING_FACTOR, and the number of ITEMS if the
COLUMN object describes more than one. All remaining information about the column, such as
DATA_TYPE, START_BYTE, BYTES, etc., will be filled in by the pre-processor. Inputs to the
preprocessor let you indicate whether to include FORMATs, COLUMN_NUMBERs, and the
MINIMUM/MAXIMUM_VALUEs attributes automatically.
"""

import re
import warnings

from filecache import FCPath

from . import PdsTemplate
from .asciitable import ANALYZE_TABLE, TABLE_VALUE, _latest_ascii_table
from .utils import get_logger, TemplateError, TemplateAbort, _check_terminators

##########################################################################################
# Pre-defined template functions
##########################################################################################

# For global access to the latest table
_LATEST_PDS3_TABLE = None


def ANALYZE_PDS3_LABEL(labelpath, *, validate=True):
    """Analyze the current template as applied to the most recently analyzed ASCII table.

    After this call, :meth:`LABEL_VALUE` can be used anywhere in the template to fill in
    values derived from the table.

    Parameters:
        labelpath (str, Path, or FCPath):
            Path to the current label.
        validate (bool, optional):
            If True, a warning or error message will be logged for every problem found in
            the template. Otherwise, warnings will be corrected silently.
    """

    global _LATEST_PDS3_TABLE

    get_logger().debug('Analyzing PDS3 label', labelpath)
    _LATEST_PDS3_TABLE = Pds3Table(labelpath, validate=False, analyze_only=True)
    if validate:
        return Pds3Table._validate_inside_template(_LATEST_PDS3_TABLE,
                                                   hide_warnings=False,
                                                   abort_on_error=False)

def VALIDATE_PDS3_LABEL(hide_warnings=False, abort_on_error=True):
    """Log a warning for every error found when generating this PDS3 label.

    :meth:`ANALYZE_PDS3_LABEL` must be called first.

    Parameters:
        abort_on_error (bool): If True and a validation error occurs, further evaluation
            of the template will be aborted.

    Returns:
        int: The number of errors issued.
        int: The number of warnings issued.
    """

    get_logger().debug('Validating PDS3 label', _LATEST_PDS3_TABLE.labelpath)
    return Pds3Table._validate_inside_template(_LATEST_PDS3_TABLE,
                                               hide_warnings=hide_warnings,
                                               abort_on_error=abort_on_error)


def LABEL_VALUE(name, column=0):
    """Lookup function returning information about the PDS3 label after it has been
    analyzed or pre-processed and after the ASCII table has been analyzed.

    Each of the following function calls returns a valid PDS3 parameter value. Columns can
    be identified by name or by number starting from 1.

    * `LABEL_VALUE("PATH")`
    * `LABEL_VALUE("BASENAME")`
    * `LABEL_VALUE("RECORD_TYPE")`
    * `LABEL_VALUE("RECORD_BYTES")`
    * `LABEL_VALUE("FILE_RECORDS")`
    * `LABEL_VALUE("INTERCHANGE_FORMAT")`
    * `LABEL_VALUE("ROWS")`
    * `LABEL_VALUE("COLUMNS")`
    * `LABEL_VALUE("ROW_BYTES")`
    * `LABEL_VALUE("DATA_TYPE", <column>)`
    * `LABEL_VALUE("START_BYTE", <column>)`
    * `LABEL_VALUE("BYTES", <column>)`
    * `LABEL_VALUE("COLUMN_NUMBER", <column>)`
    * `LABEL_VALUE("FORMAT", <column>)`
    * `LABEL_VALUE("UNIT", <column>)`
    * `LABEL_VALUE("MINIMUM_VALUE", <column>)`
    * `LABEL_VALUE("MAXIMUM_VALUE", <column>)`
    * `LABEL_VALUE("DERIVED_MINIMUM", <column>)`
    * `LABEL_VALUE("DERIVED_MAXIMUM", <column>)`

    It also provides these values derived from the existing template or label: "NAME",
    "ITEMS", "SCALING_FACTOR", "OFFSET", "INVALID_CONSTANT", "MISSING_CONSTANT",
    "NOT_APPLICABLE_CONSTANT", "NULL_CONSTANT", "UNKNOWN_CONSTANT", "VALID_MINIMUM", and
    "VALID_MAXIMUM".

    In addition, these options are supported:

    * `LABEL_VALUE("TABLE_PATH")`: full path to the associated ASCII table file.
    * `LABEL_VALUE("TABLE_BASENAME")`: basename of the associated ASCII table file.
    * `LABEL_VALUE("FIRST", <column>)`: value from the first row of this column.
    * `LABEL_VALUE("LAST", <column>)`: value from the last row of this column.

    Parameters:
        name (str): Name of a parameter.
        column (str or int, optional): The name or COLUMN_NUMBER (starting at 1) for a
            column; use 0 for general parameters.

    Returns:
        int, float, str, or None: The correct value for the specified parameter.
    """

    if not _LATEST_PDS3_TABLE:
        raise TemplateAbort('No PDS3 label has been analyzed')

    if _latest_ascii_table():       # make sure we're referring to the latest AsciiTable
        _LATEST_PDS3_TABLE.assign_to()

    try:
        return _LATEST_PDS3_TABLE.lookup(name, column)
    except Exception as err:
        raise TemplateError(err) from err


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
        int, float, str, or None: The correct value for the specified parameter.
    """

    try:
        return _LATEST_PDS3_TABLE.old_lookup(name, column)
    except Exception as err:
        raise TemplateError(err) from err


def _latest_pds3_table():
    """The most recently defined AsciiTable object. Provided for global access."""

    return _LATEST_PDS3_TABLE


PdsTemplate.define_global('ANALYZE_PDS3_LABEL', ANALYZE_PDS3_LABEL)

##########################################################################################
# Preprocessor
##########################################################################################

def pds3_table_preprocessor(labelpath, content, *, validate=True, numbers=False,
                            formats=False, units=False, minmax=(), derived=(), edits=[],
                            reals=[]):
    """A pre-processor function for use in the :meth:~pdstemplate.PdsTemplate`
    constructor.

    This function receives a PDS3 label or template describing an ASCII table and returns
    a revised template in which the supported TABLE and COLUMN attributes have been
    replaced by calls to LABEL_VALUE. This ensures that the generated label will contain a
    complete and accurate set of values.

    Parameters:
        labelpath (str, Path, or FCPath):
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
        units (bool, optional):
            True to repair units to conform to the options in the PDS3 Data Dictionary.
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
            insert or replace values currently in the label.
        reals (str, tuple[str], or list[str]), optional):
            Names of columns that should be treated as ASCII_REAL even if thee column only
            contains integers.

    Returns:
        str: The revised content for the template.
    """

    logger = get_logger()
    logger.debug('PDS3 table preprocessor', labelpath)
    pds3_label = Pds3Table(labelpath, content, validate=validate, numbers=numbers,
                           formats=formats, units=units, minmax=minmax, derived=derived,
                           edits=edits, reals=reals)

    return pds3_label.content

##########################################################################################
# Pds3Table class definition and API
##########################################################################################

class Pds3Table():
    """Class encapsulating a label or template that describes a PDS3 label containing a
    TABLE object.
    """

    # These split a content string into its constituent objects
    _OBJECT_TABLE_REGEX = re.compile(r'(?<![ \w])'
                                     r'( *OBJECT *= *[^\n]*TABLE *\r?\n)(.*?\r?\n)'
                                     r'( *END_OBJECT *= *[^\n]*TABLE *\r?\n)', re.DOTALL)
    _OBJECT_COLUMN_REGEX = re.compile(r'(?<![ \w])'
                                      r'( *OBJECT *= *COLUMN *\r?\n)(.*?\r?\n)'
                                      r'( *END_OBJECT *= *COLUMN *\r?\n)', re.DOTALL)

    def __init__(self, labelpath, label='', *, validate=True, analyze_only=False,
                 crlf=None, numbers=False, formats=False, units=False, minmax=(),
                 derived=(), edits=[], reals=[]):
        """Constructor for a Pds3Table object. It analyzes the content of a PDS3 label or
        template and saves the info for validation or possible repair.

        Parameters:
            labelpath (str, Path, or FCPath):
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
            units (bool, optional):
                True to repair units to conform to the options in the PDS3 Data
                Dictionary.
            minmax (str, tuple[str], or list[str], optional):
                Zero or more names of columns for which to include the MINIMUM_VALUE and
                MAXIMUM_VALUE. In addition or as an alternative, use "float" to include
                these values for all floating-point columns and/or "int" to include these
                values for all integer columns.
            derived (str, tuple[str], or list[str], optional):
                Zero or more names of columns for which to include the DERIVED_MINIMUM and
                DERIVED_MAXIMUM. In addition or as an alternative, use "float" to include
                these values for all floating-point columns.
            edits (str or list[str]), optional):
                Expressions of the form "column:name = value", which should be used to
                insert or replace values currently in the label.
            reals (str, tuple[str], or list[str]), optional):
                Names of columns that should be treated as ASCII_REAL even if thee column
                only contains integers.
        """

        global _LATEST_PDS3_TABLE

        self.labelpath = FCPath(labelpath)
        if not label:
            label = self.labelpath.read_bytes()     # binary to preserve terminators
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
        self.reals = (reals,) if isinstance(reals, str) else reals
        self.units = units

        self._table_values = {}         # parameter name -> value in label or None
        self._column_values = [None]    # list of parameter dicts, one per column
        self._column_name = [None]      # list of column names or str(column number)
        self._column_items = [None]     # list of ITEM counts, minimum 1
        self._column_number = {}        # column name -> column number
        self._table_index = {}          # column name or number -> index in the table
        self._extra_items = 0           # cumulative number of ITEMS > 1 in COLUMN objects
        self._quotes_missing = [None]   # column name -> set of parameters missing quotes

        # Defined by assign_to()
        self.table = None               # AsciiTable to which this label refers
        self._unique_values_ = [None]   # lazily evaluated set of values in each column
        self._unique_valids_ = [None]   # lazily evaluated set of valid valuesn

        # Note that the lists above have one initial value so they can be indexed by
        # column number without subtracting one.

        # Pre-process the edits
        edits = [edits] if isinstance(edits, str) else edits
        self._edit_dict = {}            # [colname][parname] -> replacement value
        self._edited_values = {}        # [colname][parname] -> original value or None
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
            raise TemplateAbort('Template does not contain a PDS3 TABLE object',
                                self.labelpath)
        if len(parts) > 5:
            raise TemplateAbort('Template contains multiple PDS3 TABLE objects',
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
        header = ['$ONCE(ANALYZE_TABLE(LABEL_PATH().replace(".lbl",".tab")'
                  '.replace(".LBL",".TAB"), crlf=True))', self.terminator]
        if validate:
            header += ['$ONCE(VALIDATE_PDS3_LABEL(hide_warnings, abort_on_error))',
                       self.terminator]

        self.content = ''.join(header) + ''.join(parts)
        self.table = None

        # Set globals for access within the template object
        _LATEST_PDS3_TABLE = self
        PdsTemplate.define_global('VALIDATE_PDS3_LABEL', VALIDATE_PDS3_LABEL)
        PdsTemplate.define_global('LABEL_VALUE', LABEL_VALUE)
        PdsTemplate.define_global('OLD_LABEL_VALUE', OLD_LABEL_VALUE)
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

        # Identify parameters with missing quotes
        self._quotes_missing.append(set())
        fmt = Pds3Table._get_value(label, 'FORMAT', raw=True)
        if fmt is not None and '.' in fmt and not fmt.startswith('"'):
            self._quotes_missing[-1].add('FORMAT')
        unit = Pds3Table._get_value(label, 'UNIT', raw=True)
        if (unit is not None and not unit.isidentifier() and not unit.startswith('"')
            and unit != "'N/A'"):
            self._quotes_missing[-1].add('UNIT')

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
                                        f'$QUOTE_IF(LABEL_VALUE("FORMAT", {colnum}))$',
                                        required=self.formats, after='BYTES')

        # Optional UNIT
        if self.units:
            label, self._column_values[-1]['UNIT'] = self._replace_value(
                                        label, 'UNIT',
                                        f'$QUOTE_IF(LABEL_VALUE("UNIT", {colnum}))$',
                                        required=False, after='FORMAT')
        else:
            self._column_values[-1]['UNIT'] = self._get_value(label, 'UNIT')

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

    def assign_to(self, table=None):
        """Assign this PDS3 label to the given ASCII table.

        Parameters:
            table (AsciiTable, optional): Table to which this PDS3 label should apply. If
                not specified, the table defined by AsciiTable._latest_ascii_table() is
                used.
        """

        table = table or _latest_ascii_table()
        if not table:
            raise TemplateAbort('No ASCII table has been analyzed for label',
                                self.labelpath)

        if table is not self.table:
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
            FCPath: Path to the table file if defined in the label; otherwise, an empty
            string.
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

        if table:
            self.assign_to(table)

        messages = self._validation_warnings(table)
        for message in messages:
            warnings.warn(message)

        return len(messages)

    def _validate_inside_template(self, table=None, *, hide_warnings=False,
                                  abort_on_error=True):
        """Compare this object to the given AsciiTable object and log a warning message
        for each erroneous value identified.

        Parameters:
            table (AsciiTable, optional):
                The AsciiTable assigned to this label. If this is specified and is
                different from the currently assigned table, it becomes the assigned
                table.
            hide_warnings (bool, options): True to log errors but not warnings.
            abort_on_error (bool, optional): True to issue a TemplateAbort exception if
                errors are encountered.

        Returns:
            int: The number of errors issued.
            int: The number of warnings issued.
        """

        messages = self._validation_warnings(table)
        if not messages:
            return (0, 0)

        logger = get_logger()
        errors = 0
        warns = 0
        for message in messages:
            if message.startswith('ERROR: '):
                logger.error(message[7:])
                errors += 1
            else:
                warns += 1
                if not hide_warnings:
                    logger.warning(message)

        if errors and abort_on_error:
            raise TemplateAbort('Aborted')

        return (errors, warns)

    def _validation_warnings(self, table=None):
        """Compare this object to the given AsciiTable object and return a list of
        warnings, one for each erroneous value identified.

        Parameters:
            table (AsciiTable, optional): The AsciiTable to assign to this label before
                validation. If not specified, the latest analyzed ASCII table is used.

        Returns:
            list[str]: A list of messages. Messages that begin with "ERROR: " are
                irrecoverable errors; anything else is a warning about something that can
                be repaired by the preprocessor.
        """

        self.assign_to(table)
        table = self.table
        if not table:
            raise TemplateAbort('No ASCII table has been analyzed for label',
                                self.labelpath)

        messages = []       # accumulated list of warnings

        # Check <CR><LF> in original file
        try:
            _check_terminators(self.labelpath, crlf=True)
        except TemplateError as err:
            messages.append(err.message)

        # Required top-level attributes
        for name in ['RECORD_TYPE', 'RECORD_BYTES', 'FILE_RECORDS', 'INTERCHANGE_FORMAT',
                     'ROWS', 'COLUMNS', 'ROW_BYTES']:
            messages += self._check_value(name, required=True)

        # Check each column...
        label_columns = len(self._column_values) - 1
        table_columns = self.lookup('COLUMNS')
        for colnum in range(1, min(label_columns, table_columns)+1):
            colname = self._column_name[colnum]
            data_type = self.lookup('DATA_TYPE', colnum)

            # Direct edits
            edited_names = set(self._edited_values.get(colname, {}).keys())
            for name, old_value in self._edited_values.get(colname, {}).items():
                new_fmt = self._edit_dict[colname][name]
                if old_value is None:
                    messages.append(f'{colname}:{name} was inserted: {new_fmt}')
                else:
                    old_fmt = Pds3Table._format_for_message(old_value)
                    messages.append(f'{colname}:{name} was edited: '
                                    f'{old_fmt} -> {new_fmt}')

            # Required attributes
            for name in ['NAME', 'DATA_TYPE', 'START_BYTE', 'BYTES']:
                if name not in edited_names:
                    messages += self._check_value(name, colnum, required=True)

            # Tests for multiple ITEMS
            items = self._column_items[colnum]
            for name in ['ITEM_BYTES', 'ITEM_OFFSET']:
                if name not in edited_names:
                    messages += self._check_value(name, colnum, required=(items > 1),
                                                  forbidden=(items == 1))

            indx = self._table_index[colnum]
            for k in range(1, items):
                if table.lookup('WIDTH', k+indx) != table.lookup('WIDTH', indx):
                    messages.append(f'ERROR: {colname}:{name} items have inconsistent '
                                    'widths')
                if table.lookup('QUOTES', k+indx) != self.table.lookup('QUOTES', indx):
                    messages.append(f'ERROR: {colname}:{name} items have inconsistent '
                                    'quote usage')

            # Optional attributes
            messages += self._check_value('COLUMN_NUMBER', colnum, required=self.numbers)

            if 'FORMAT' not in edited_names:
                fmt_messages = self._check_value('FORMAT', colnum, required=self.formats)
                if fmt_messages:
                    messages += fmt_messages
                elif 'FORMAT' in self._quotes_missing[colnum]:
                    value = self.lookup('FORMAT', colnum)
                    messages.append(f'{colname}:FORMAT error: {value} -> "{value}"')

            if 'UNIT' not in edited_names:
                test = self._check_value('UNIT', colnum)
#                 messages += self._check_value('UNIT', colnum)
                messages += test
                if self.units:
                    old_value = self._column_values[colnum].get('UNIT', None)
                    if not Pds3Table._unit_is_valid(old_value):
                        old_fmt = Pds3Table._format_for_message(old_value)
                        new_value = self.lookup('UNIT', colnum)
                        if new_value == old_value:
                            messages.append(f'{colname}:UNIT error: {old_fmt} '
                                            'is not a recognized unit')
                        else:
                            messages.append(f'{colname}:UNIT error: {old_fmt} -> '
                                            f'"{new_value}"')
                elif 'UNIT' in self._quotes_missing[colnum]:
                    value = self._column_values[colnum]['UNIT']
                    messages.append(f'{colname}:UNIT error: {value} -> "{value}"')

            # Minima/maxima
            required = ((colname in self.minmax)
                        or ('float' in self.minmax and 'REAL' in data_type)
                        or ('int' in self.minmax and 'INT' in data_type))
            messages += self._check_value('MINIMUM_VALUE', colnum, required=required)
            messages += self._check_value('MAXIMUM_VALUE', colnum, required=required)

            required = ((colname in self.derived)
                        or ('float' in self.derived and 'REAL' in data_type)
                        or ('int' in self.derived and 'INT' in data_type))
            messages += self._check_value('DERIVED_MINIMUM', colnum,
                                          required=required)
            messages += self._check_value('DERIVED_MAXIMUM', colnum,
                                          required=required)

            # Constants
            for name in ['INVALID_CONSTANT', 'MISSING_CONSTANT',
                         'NOT_APPLICABLE_CONSTANT', 'NULL_CONSTANT', 'UNKNOWN_CONSTANT',
                         'VALID_MINIMUM', 'VALID_MAXIMUM']:
                value = self.lookup(name, colnum)
                if value is None:
                    continue

                if isinstance(value, float) and 'REAL' in data_type:
                    continue
                if isinstance(value, int) and 'INT' in data_type:
                    continue
                if isinstance(value, str) and 'CHAR' in data_type or data_type == 'TIME':
                    continue

                valfmt = Pds3Table._format_for_message(value)
                message = (f'ERROR: {colname}:{name} value {valfmt} is incompatible with '
                           f'column type {data_type}')
                messages.append(message)

        # Check for missing or extraneous columns
        for colnum in range(table_columns+1, label_columns+1):
            colname = self._column_name[colnum]
            messages.append(f'ERROR: Column {colname} is missing')

        table_extras = table_columns - label_columns
        if table_extras > 0:
            messages.append(f'ERROR: Table contains {table_extras} undefined column'
                            + ('s' if table_extras > 1 else ''))

        # Check duplicated column names
        if len(self._column_number) != label_columns:
            for k, name in enumerate(self._column_name):
                try:
                    dk = self._column_name[k+1:].index(name)
                except ValueError:
                    pass
                else:
                    messages.append(f'ERROR: Name {name} is duplicated at columns '
                                    f'{k} and {k+dk+1}')

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
            if new_value is None:
                return [f'{prefix}{name} is missing']
            new_fmt = Pds3Table._format_for_message(new_value)
            return [f'{prefix}{name} is missing: {new_fmt}']

        if forbidden:
            if old_value is not None:
                old_fmt = Pds3Table._format_for_message(old_value)
                return [f'ERROR: {prefix}{name} is forbidden: ({old_fmt})']
            return []

        if not required and not forbidden and old_value is None:
            return []

        # Get the new value
        new_value = self.lookup(name, colnum)
        if old_value == new_value:
            return []

        new_fmt = Pds3Table._format_for_message(new_value)  # deal with quoting mismatch
        old_fmt = Pds3Table._format_for_message(old_value)
        if old_fmt == new_fmt:
            return []

        return [f'{prefix}{name} error: {old_fmt} -> {new_fmt}']

    ######################################################################################
    # lookup()
    ######################################################################################

    def lookup(self, name, column=0):
        """Lookup function returning information about the PDS3 label as it has been
        applied to the current table.

        Each of the following function calls returns a valid PDS3 parameter value. Columns
        can be identified by name or by number starting from 1.

        * `lookup("PATH")`
        * `lookup("BASENAME")`
        * `lookup("RECORD_TYPE")`
        * `lookup("RECORD_BYTES")`
        * `lookup("FILE_RECORDS")`
        * `lookup("INTERCHANGE_FORMAT")`
        * `lookup("ROWS")`
        * `lookup("COLUMNS")`
        * `lookup("ROW_BYTES")`
        * `lookup("DATA_TYPE", <column>)`
        * `lookup("START_BYTE", <column>)`
        * `lookup("BYTES", <column>)`
        * `lookup("COLUMN_NUMBER", <column>)`
        * `lookup("FORMAT", <column>)`
        * `lookup("UNIT", <colnum>)`
        * `lookup("MINIMUM_VALUE", <column>)`
        * `lookup("MAXIMUM_VALUE", <column>)`
        * `lookup("DERIVED_MINIMUM", <column>)`
        * `lookup("DERIVED_MAXIMUM", <column>)`

        It also provides these values derived from the existing template or label: "NAME",
        "ITEMS", "SCALING_FACTOR", "OFFSET", "INVALID_CONSTANT", "MISSING_CONSTANT",
        "NOT_APPLICABLE_CONSTANT", "NULL_CONSTANT", "UNKNOWN_CONSTANT", "VALID_MINIMUM",
        and "VALID_MAXIMUM".

        In addition, these options are supported:

        * `lookup("TABLE_PATH")`: full path to the associated ASCII table file.
        * `lookup("TABLE_BASENAME")`: basename of the associated ASCII table file.
        * `lookup("FIRST", <column>)`: value from the first row of this column.
        * `lookup("LAST", <column>)`: value from the last row of this column.

        Parameters:
            name (str): Name of a parameter.
            column (str or int, optional): The name or COLUMN_NUMBER (starting at 1) for a
                column; use 0 for general parameters.

        Returns:
            str: The correct PDS3-formatted value for the specified parameter.
        """

        if not column:
            colnum = 0
            colname = ''
        else:
            colnum = self._column_number[column] if isinstance(column, str) else column
            colname = self._column_name[colnum]

        if name in self._edit_dict.get(colname, {}):
            return Pds3Table._eval(self._edit_dict[colname][name])

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
            case ('NAME' | 'ITEMS' | 'SCALING_FACTOR' | 'OFFSET' | 'INVALID_CONSTANT' |
                  'MISSING_CONSTANT' | 'NOT_APPLICABLE_CONSTANT' | 'NULL_CONSTANT' |
                  'UNKNOWN_CONSTANT' | 'VALID_MINIMUM' | 'VALID_MAXIMUM'):
                return self.old_lookup(name, colnum)

        if not self.table:
            self.assign_to()

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
                return self._columns_carefully()
            case 'DATA_TYPE':
                data_type = self.table.lookup('PDS3_DATA_TYPE', indx)
                if data_type == 'ASCII_INTEGER':
                    # Override ASCII INTEGERS if there's evidence the intent is REAL
                    if (colname in self.reals
                        or self._constant_type(colnum) == 'ASCII_REAL'):
                        return 'ASCII_REAL'
                # Override the derived FORMAT if every value in the table is invalid
                old_type = self._column_values[colnum]['DATA_TYPE']
                if old_type is not None and len(self._unique_valids(colnum)) == 0:
                    return old_type
                return data_type
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
                fmt = self.table.lookup('PDS3_FORMAT', indx)
                # Force "I" to "F" if necessary
                if fmt[0] == 'I':
                    # Override ASCII INTEGERS if there's evidence the intent is REAL
                    if (colname in self.reals
                        or self._constant_type(colnum) == 'ASCII_REAL'):
                        return 'F' + str(self.table.lookup('BYTES', indx)) + '.0'
                # Override the derived FORMAT if every value in the table is invalid
                old_fmt = self._column_values[colnum]['FORMAT']
                if (old_fmt is not None and len(self._unique_valids(colnum)) == 0
                    and Pds3Table._format_is_valid(old_fmt)):
                    return old_fmt
                return fmt
            case 'UNIT':
                unit = self._column_values[colnum]['UNIT']
                if self.units:
                    return Pds3Table._get_valid_unit(unit) or unit
                return unit
            case ('MINIMUM_VALUE' | 'MAXIMUM_VALUE' | 'DERIVED_MINIMUM' |
                  'DERIVED_MAXIMUM'):
                unique = self._unique_valids(colnum) or self._unique_values(colnum)
                new_value = min(unique) if 'MINIMUM' in name else max(unique)
                if 'DERIVED' not in name or self._equals_a_constant(colnum, new_value):
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

            if (value := column_dict['VALID_MINIMUM']) is not None:
                try:
                    unique = {v for v in unique if v >= value}
                except TypeError:       # ignore an invalid VALID_MINIMUM
                    pass

            if (value := column_dict['VALID_MAXIMUM']) is not None:
                try:
                    unique = {v for v in unique if v <= value}
                except TypeError:       # ignore an invalid VALID_MAXIMUM
                    pass

            self._unique_valids_[colnum] = unique

        return unique

    def _equals_a_constant(self, colnum, value):
        """True if the given value matches one of the constants in the specified column.
        """

        column_dict = self._column_values[colnum]
        for name in ['INVALID_CONSTANT', 'MISSING_CONSTANT', 'NOT_APPLICABLE_CONSTANT',
                     'NULL_CONSTANT', 'UNKNOWN_CONSTANT']:
            if value == column_dict[name]:
                return False

        return True

    def _constant_type(self, colnum):
        """The type of the constants for this column, one of ASCII_INTEGER, ASCII_REAL, or
        CHARACTER. None if there are no constants or if constants are inconsistent.
        """

        types = set()
        for name in ['INVALID_CONSTANT', 'MISSING_CONSTANT',
                     'NOT_APPLICABLE_CONSTANT', 'NULL_CONSTANT', 'UNKNOWN_CONSTANT',
                     'VALID_MINIMUM', 'VALID_MAXIMUM']:
            value = self.lookup(name, colnum)
            if value is None:
                continue

            if isinstance(value, float):
                types.add('ASCII_REAL')
            elif isinstance(value, int):
                types.add('ASCII_INTEGER')
            else:
                types.add('CHARACTER')

        if len(types) == 1:
            return list(types)[0]

        return None

    def _columns_carefully(self):
        """Careful tally of the correct number of COLUMN objects, allowing for a mismatch
        between the table and the label.

        Without errors, this should work::

            columns = self.table.lookup('COLUMNS') - self._extra_items

        However, self._extra_items includes extra items that might be missing from the
        table.
        """

        table_columns = self.table.lookup('COLUMNS')
        table_count = 0

        for colnum in range(1, len(self._column_values)):
            table_count += self._column_items[colnum]
            if table_count >= table_columns:            # if we reach last table column
                return colnum

        return colnum + table_columns - table_count     # maybe table has more columns

    def old_lookup(self, name, column=0):
        """Lookup function returning information about the current content of the PDS3
        label, whether or not it is correct.

        Available top-level keywords are "RECORD_TYPE", "RECORD_BYTES", "FILE_RECORDS",
        "INTERCHANGE_FORMAT", "ROWS", "COLUMNS", and "ROW_BYTES".

        Available column-level keywords are "NAME", "COLUMN_NUMBER", "DATA_TYPE",
        "START_BYTE", "BYTES", "FORMAT", "ITEMS", "ITEM_BYTES", "ITEM_OFFSET",
        "SCALING_FACTOR", "OFFSET", "UNIT", "INVALID_CONSTANT", "MISSING_CONSTANT",
        "NOT_APPLICABLE_CONSTANT", "NULL_CONSTANT", "UNKNOWN_CONSTANT", "VALID_MAXIMUM",
        "VALID_MINIMUM", "MINIMUM_VALUE", "MAXIMUM_VALUE", "DERIVED_MINIMUM", and
        "DERIVED_MAXIMUM".

        Parameters:
            name (str): Name of a parameter.
            column (str or int, optional): The name or COLUMN_NUMBER (starting at 1) for a
                column; use 0 for general parameters.

        Returns:
            int, float, str, or None: The current value of the specified parameter; None
            if it is not found in the label.
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
            # where `value` includes any trailing blanks and/or a comment

        if len(parts) == 1:     # if not found
            if not required:
                return (label, None)

            new_label = self._insert_value(label, name, replacement, after=after,
                                           before=before, first=first)
            return (new_label, None)

        # Split trailing blanks and an optional comment
        subparts = parts[2].partition('/*')
        value = subparts[0].rstrip()
        tail = (len(subparts[0]) - len(value)) * ' ' + subparts[1] + subparts[2]

        value = Pds3Table._eval(parts[2])
        if not self.analyze_only:
            label = ''.join(parts[:2]) + replacement + tail + ''.join(parts[3:])

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
    def _get_value(label, name, raw=False):
        """The value of the named parameter within the label.

        Parameters:
            label (str): PDS3 label string.
            name (str): PDS3 parameter name.
            raw (bool, optional): True for a "raw" value without evaluation.

        Returns:
            str or None: The string value of the parameter if present; None otherwise.
        """

        # Find name=value substring
        matches = re.findall(r'(?<!\S)' + name + r' *= *([^\r\n]*)', label)
        if not matches:
            return None

        value = matches[0].partition('/*')[0].rstrip()
        if raw:
            return value

        return Pds3Table._eval(value)

    _UNQUOTED_OK = re.compile(r'[A-Z][A-Z0-9_]*')

    @staticmethod
    def _eval(value):
        """Convert the given string value to int, float, or string.

        Unnecessary quotes are stripped, but necessary quotes are retained.
        """

        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                return value[1:-1]

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
    def _format_for_message(value):
        """Return the value formatted for an error message or the PDS3 label."""

        if isinstance(value, int):
            return str(value)

        if isinstance(value, float):
            value = str(value)
            (before, optional_e, after) = value.partition('e')
            if '.' not in before:
                before += '.'
            before.rstrip('0')
            return before + optional_e.upper() + after

        if value in ('N/A', "'N/A'"):
            return "'N/A'"

        if value.startswith('"'):
            return value

        if Pds3Table._UNQUOTED_OK.fullmatch(value):
            return value

        return '"' + value + '"'

    _VALID_AI_FORMAT_STRING = re.compile(r'([AI])(\d+)')
    _VALID_EF_FORMAT_STRING = re.compile(r'([EF])(\d+)\.(\d+)')

    @staticmethod
    def _format_is_valid(value):
        """True if the given value is a valid PDS3 format string."""

        if not isinstance(value, str):
            return False

        match = Pds3Table._VALID_AI_FORMAT_STRING.fullmatch(value)
        if match:
            return int(match.group(2)) > 0

        match = Pds3Table._VALID_EF_FORMAT_STRING.fullmatch(value)
        if match:
            i1 = int(match.group(2))
            i2 = int(match.group(3))
            if match.group(1) == 'F' and i1 > i2 + 1:
                return True
            if match.group(1) == 'E' and i1 > i2 + 5:
                return True

        return False

    ######################################################################################
    # Translator/validator for PDS3 units
    ######################################################################################

    _VALID_UNITS = {            # from pdsdd.full
        'A', 'A/m', 'A/m**2', 'B', 'Bq', 'C', 'C/kg', 'C/m**2', 'C/m**3', 'F',
        'F/m', 'Gy', 'Gy/s', 'H', 'H/m', 'Hz', 'J', 'J/(kg.K)', 'J/(m**2)/s',
        'J/(mol.K)', 'J/K', 'J/T', 'J/kg', 'J/m**3', 'J/mol', 'K', 'MB', 'N',
        'N.m', 'N/A', 'N/m', 'N/m**2', 'Pa', 'Pa.s', 'S', 'Sv', 'T', 'V',
        'V/m', 'W', 'W.m**-2.sr**-1', 'W/(m.K)', 'W/m**2', 'W/sr', 'Wb',
        'arcsec/pixel', 'arcsecond',
        'bar', 'cd', 'cd/m**2', 'd', 'dB', 'deg', 'deg/day', 'deg/s', 'degC',
        'g', 'g/cm**3', 'h', 'kHz', 'kb/s', 'kg', 'kg/m**3', 'km', 'km**-1',
        'km**2', 'km/pixel', 'km/s', 'lm', 'local day/24', 'lx', 'm', 'm**-1',
        'm**2', 'm**2/s', 'm**3', 'm**3/kg', 'm/pixel', 'm/s', 'm/s**2', 'mA',
        'mag', 'micron', 'min', 'mm', 'mm/s', 'mol', 'mol/m**3', 'mrad', 'ms',
        'n/a', 'nT', 'nm', 'none', 'ohm', 'p/line', 'pixel', 'pixel/deg',
        'rad', 'rad/s', 'rad/s**2', 's', 'sr', 'uW', 'us', 'us_dollar',
        #
        # disallowed: b -> bit; pix -> pixel; degree -> deg
        # 'b/pixel', 'b/s', 'km/pix', 'm/pix', 'pix/deg', 'pix/degree', 'pixel/degree'
        #
        # added manually...
        'bit', 'kbit', 'bit/s', 'kbit/s', 'bit/pixel', 'kbit/pixel', 'cm', 'KB', 'KB/s',
        'MB/s', 'erg/s/cm**2/micron/sr',
        "'N/A'", None,
    }

    _COMMON_UNITS_TO_REPAIR = {
        ('celsius degree', 'degC'),
        ('kelvin', 'K'),
        ('degree', 'deg'),
        ('radian', 'rad'),
        ('arcsecond', 'arcsec'),
        ('arcsec', 'arcsecond'),
        ('steradian', 'sr'),
        ('ster', 'sr'),
        ('centimeter', 'cm'),
        ('kilometer', 'km'),
        ('meter', 'm'),
        ('micron', 'micron'),   # needed for "microns" -> "micron"
        ('micrometer', 'micron'),
        ('second', 's'),
        ('sec', 's'),
        ('minute', 'min'),
        ('hour', 'h'),
        ('millisec', 'ms'),
        ('millisecond', 'ms'),
        ('pix', 'pixel'),
        ('bit', 'bit'),         # needed for "bits" -> "bit"
        ('kbit', 'kbit'),       # needed for "kbits" -> "kbit"
        ('kilobit', 'kbit'),
        ('kilobyte', 'KB'),
        ('megabyte', 'MB'),
        ('erg', 'erg'),         # needed for "ergs" -> erg
        ('hz', 'Hz'),
    }

    _WORD_SPLITTER = re.compile(r'([a-zA-Z ]+).*?')

    @staticmethod
    def _get_valid_unit(unit):
        """The valid version of the given unit, or an empty string on failure."""

        if unit in Pds3Table._VALID_UNITS:
            return unit

        unit_lc = unit.lower()
        if unit_lc in Pds3Table._VALID_UNITS:
            return unit_lc

        # Fix exponent style, punctuation
        if '^' in unit:
            return Pds3Table._get_valid_unit(unit.replace('^', '**'))
        if unit.startswith("'") and unit.endswith("'"):
            return Pds3Table._get_valid_unit(unit[1:-1])

        # Split into words (split by punctuation but not by blanks)
        parts = Pds3Table._WORD_SPLITTER.split(unit)

        # Convert each word to lower case if it's a unit in and of itself
        parts_lc = [part.lower() for part in parts]
        for k, part_lc in enumerate(parts_lc):
            if part_lc in Pds3Table._VALID_UNITS:
                parts[k] = part_lc

        # Replace other units with common options
        words = set(parts_lc[1::2])
        for (before, after) in Pds3Table._COMMON_UNITS_TO_REPAIR:
            for suffix in ('', 's'):
                test = (before + suffix).lower()
                if test in words:
                    k = parts_lc.index(test)
                    parts[k] = after

        unit = ''.join(parts)
        return unit if unit in Pds3Table._VALID_UNITS else ''

    @staticmethod
    def _unit_is_valid(unit):
        """True if the given unit is valid."""

        valid_unit = Pds3Table._get_valid_unit(unit)
        return bool(valid_unit != '')

##########################################################################################
