| PyPI Release | Test Status | Code Coverage |
| ------------ | ----------- | ------------- |
| [![PyPI version](https://badge.fury.io/py/rms-pdstemplate.svg)](https://badge.fury.io/py/rms-pdstemplate) | [![Build status](https://img.shields.io/github/actions/workflow/status/SETI/rms-pdstemplate/run-tests.yml?branch=master)](https://github.com/SETI/rms-pdstemplate/actions) | [![Code coverage](https://img.shields.io/codecov/c/github/SETI/rms-pdstemplate/main?logo=codecov)](https://codecov.io/gh/SETI/rms-pdstemplate) |

# rms-pdstemplate

PDS Ring-Moon Systems Node, SETI Institute

Supported versions: Python >= 3.7

Class to generate PDS labels based on templates.

The general procedure is as follows.

1. Create a template object by calling the PdsTemplate constructor to read a template
file:

      `template = PdsTemplate(template_file_path)`

2. Create a dictionary that contains the parameter values to use inside the label.
3. Construct the label as follows:

      `template.write(dictionary, label_file)`

    This will create a new label of the given name, using the values in the given
    dictionary. Once the template has been constructed, steps 2 and 3 can be repeated any
    number of times.

## SUBSTITUTIONS

A template file will look generally like a label file, except for certain embedded
expressions that will be replaced when the template's write() method is called.

In general, everything between dollar signs `$` in the template is interpreted as a
Python expression to be evaluated. The result of this expression then replaces it
inside the label. For example, if `dictionary['INSTRUMENT_ID'] = 'ISSWA'`, then

    <instrument_id>$INSTRUMENT_ID$</instrument_id>

in the template will become

    <instrument_id>ISSWA</instrument_id>

in the label. The expression between `$` in the template can include indexes, function
calls, or just about any other Python expression. As another example, using the same
dictionary above,

    <camera_fov>$"Narrow" if INSTRUMENT_ID == "ISSNA" else "Wide"$</camera_fov>

in the template will become

    <camera_fov>Wide</camera_fov>

in the label.

An expression in the template of the form `$name=expression$`, where the `name` is a
valid Python variable name, will also also have the side-effect of defining this
variable so that it can be re-used later in the template. For example, if this appears
as an expression,

    $cruise_or_saturn=('cruise' if START_TIME < 2004 else 'saturn')$

then later in the template, one can write:

    <lid_reference>
    urn:nasa:pds:cassini_iss_$cruise_or_saturn$:data_raw:cum-index
    </lid_reference>

To embed a literal `$` inside a label, enter `$$` into the template.

## PRE-DEFINED FUNCTIONS

The following pre-defined functions can be used inside any expression in the template.

`BASENAME(filepath)`:
        The basename of the given file path, with leading directory paths removed.

`BOOL(value, true='true', false='false')`:
        This value as a PDS4 boolean, typically either "true" or "false".

`COUNTER(name)`:
        The current value of a counter of the given name, starting at 1.

`CURRENT_ZULU(date_only=False)`:
        The current UTC time as a string of the form "yyyy-mm-ddThh:mm:ssZ".

`DATETIME(string, offset=0, digits=None)`:
        Convert the given date/time string to a year-month-day format with a trailing
        "Z". An optional offset in seconds can be applied. It makes an educated guess
        at the appropriate number of digits in the fractional seconds if this is not
        specified explicitly.

`DATETIME_DOY(string)`:
        Convert the given date/time string to a year and day of year format with a
        trailing "Z". Inputs are the same as for DATETIME.

`DAYSECS(string)`:
        The number of elapsed seconds since the beginning of the most recent day.

`FILE_BYTES(filepath)`:
        The size of the specified file in bytes.

`FILE_MD5(filepath)`:
        The MD5 checksum of the specified file.

`FILE_RECORDS(filepath)`:
        The number of records in the specified file if it is ASCII; 0 if the file is
        binary.

`FILE_ZULU(filepath)`:
        The UTC modification time of the specified file as a string of the form
        "yyyy-mm-ddThh:mm:ss.sssZ".

`NOESCAPE(text)`:
        Normally, evaluated expressions are "escaped", to ensure that they are
        suitable for embedding in a PDS label. For example, `>` inside a string
        in an XML label will be replaced by `&gt;`. This function prevents the
        returned text from being escaped, allowing it to contain literal XML.

`RAISE(exception, message)`:
        Raise an exception with the given class and message.

`REPLACE_NA(value, if_na)`:
        Return the value of the second argument if the first argument is "N/A";
        otherwise, return the first value.

`REPLACE_UNK(value, if_unk)`:
        Return the value of the second argument if the first argument is "UNK";
        otherwise, return the first value.

`TEMPLATE_PATH()`:
        The directory path to the template file.

`VERSION_ID()`:
        Version ID of this module, e.g., "1.0 (2022-10-05)".

`WRAP(left, right, text)`:
        Format the text to fit between the given left and right column numbers. The
        first line is not indented, so the text will begin in the column where "$WRAP"
        first appears.

These functions can also be used directly by the programmer; simply import them by
name from this module.

### COMMENTS

Any text appearing on a line after the symbol `$NOTE:` will not appear in the label.
Trailing blanks resulting from this removal are also removed.

### HEADERS

The template may also contain any number of headers. These appear alone on a line of
the template and begin with `$` as the first non-blank character. They determine
whether or how subsequent text of the template will appear in the file, from here up
to the next header line.

You can include one or more repetitions of the same text using `$FOR` and `$END_FOR`
headers. The format is

    $FOR(expression)
        <template text>
    $END_FOR

where the expression evaluates to a Python iterable. Within the template text, these
new variable names are assigned:

- VALUE = the next value of the iterator;
- INDEX = the index of this iterator, starting at zero;
- LENGTH = the number of items in the iteration.

For example, if

    dictionary["targets"] = ["Jupiter", "Io", "Europa"]
    dictionary["naif_ids"] = [599, 501, 502],

then

    $FOR(targets)
        <target_name>$VALUE (naif_ids[INDEX])$</target_name>
    $END_FOR

in the template will become

    <target_name>Jupiter (599)</target_name>
    <target_name>Io (501)</target_name>
    <target_name>Europa (502)</target_name>

in the label.

Instead of using the names `VALUE`, `INDEX`, and `LENGTH`, you can customize the
variable names by listing up to three comma-separated names and an equal sign `=`
before the iterable expression. For example, this will produce the same results as the
example above:

    $FOR(name,k=targets)
        <target_name>$name (naif_ids[k])$</target_name>
    $END_FOR

You can also use `$IF`, `$ELSE_IF`, `$ELSE`, and `$END_IF` headers to select among
alternative blocks of text in the template:

- `$IF(expression)` - Evaluate the expression and include the next lines of the
                        template if the expression is logically True (e.g., boolean
                        True, a nonzero number, a non-empty list or string, etc.).
- `$ELSE_IF(expression)` - Include the next lines of the template if this expression is
                        logically True and every previous expression was not.
- `$ELSE` - Include the next lines of the template only if all prior
                        expressions were logically False.
- `$END_IF` - This marks the end of the set of if/else alternatives.

As with other substitutions, you can define a new variable of a specified name by
using `name=expression` inside the parentheses of an `$IF()` or `$ELSE_IF()` header.

Note that headers can be nested arbitrarily inside the template.

You can use the `$NOTE` and `$END_NOTE` headers to embed any arbitrary comment block into
the template. Any text between these headers does not appear in the label.

One additional header is supported: `$ONCE(expression)`. This header evaluates the
expression but does not alter the handling of subsequent lines of the template. You
can use this capability to define variables internally without affecting the content
of the label produced. For example:

    $ONCE(date=big_dictionary["key"]["date"])

will assign the value of the variable named "date" for subsequent use within the
template.

### LOGGING AND EXCEPTION HANDLING

The `pdslogger` module is used to handle logging. By default, the `pdslogger.NullLogger`
class is used, meaning that no actions are logged. To override, call

    set_logger(logger)

in your Python program to use the specified logger. For example,

    set_logger(pdslogger.EasyLogger())

will log all messages to the terminal.

By default, exceptions during a call to `write()` or `generate()` are handled as follows:

1. They are written to the log.
2. The template attribute `ERROR_COUNT` contains the number of exceptions raised.
3. The expression that triggered the exception is replaced by the error text in the
label, surrounded by `[[[` and `]]]` to make it easier to find.
4. The exception is otherwise suppressed.

This behavior can be modified by calling method `raise_exceptions(True)`. In this case,
the call to `write()` or `generate()` raises the exception and then halts.
