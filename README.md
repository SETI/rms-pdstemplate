[![GitHub release; latest by date](https://img.shields.io/github/v/release/SETI/rms-pdstemplate)](https://github.com/SETI/rms-pdstemplate/releases)
[![GitHub Release Date](https://img.shields.io/github/release-date/SETI/rms-pdstemplate)](https://github.com/SETI/rms-pdstemplate/releases)
[![Test Status](https://img.shields.io/github/actions/workflow/status/SETI/rms-pdstemplate/run-tests.yml?branch=main)](https://github.com/SETI/rms-pdstemplate/actions)
[![Documentation Status](https://readthedocs.org/projects/rms-pdstemplate/badge/?version=latest)](https://rms-pdstemplate.readthedocs.io/en/latest/?badge=latest)
[![Code coverage](https://img.shields.io/codecov/c/github/SETI/rms-pdstemplate/main?logo=codecov)](https://codecov.io/gh/SETI/rms-pdstemplate)
<br />
[![PyPI - Version](https://img.shields.io/pypi/v/rms-pdstemplate)](https://pypi.org/project/rms-pdstemplate)
[![PyPI - Format](https://img.shields.io/pypi/format/rms-pdstemplate)](https://pypi.org/project/rms-pdstemplate)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/rms-pdstemplate)](https://pypi.org/project/rms-pdstemplate)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/rms-pdstemplate)](https://pypi.org/project/rms-pdstemplate)
<br />
[![GitHub commits since latest release](https://img.shields.io/github/commits-since/SETI/rms-pdstemplate/latest)](https://github.com/SETI/rms-pdstemplate/commits/main/)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/SETI/rms-pdstemplate)](https://github.com/SETI/rms-pdstemplate/commits/main/)
[![GitHub last commit](https://img.shields.io/github/last-commit/SETI/rms-pdstemplate)](https://github.com/SETI/rms-pdstemplate/commits/main/)
<br />
[![Number of GitHub open issues](https://img.shields.io/github/issues-raw/SETI/rms-pdstemplate)](https://github.com/SETI/rms-pdstemplate/issues)
[![Number of GitHub closed issues](https://img.shields.io/github/issues-closed-raw/SETI/rms-pdstemplate)](https://github.com/SETI/rms-pdstemplate/issues)
[![Number of GitHub open pull requests](https://img.shields.io/github/issues-pr-raw/SETI/rms-pdstemplate)](https://github.com/SETI/rms-pdstemplate/pulls)
[![Number of GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed-raw/SETI/rms-pdstemplate)](https://github.com/SETI/rms-pdstemplate/pulls)
<br />
![GitHub License](https://img.shields.io/github/license/SETI/rms-pdstemplate)
[![Number of GitHub stars](https://img.shields.io/github/stars/SETI/rms-pdstemplate)](https://github.com/SETI/rms-pdstemplate/stargazers)
![GitHub forks](https://img.shields.io/github/forks/SETI/rms-pdstemplate)

# Introduction

`pdstemplate` is a Python module that provide the `PdsTemplate` class, used to generate
PDS labels based on templates. Although specifically designed to facilitate data
deliveries by PDS data providers, the template system is generic and could be used to
generate files from templates for other purposes.

`pdstemplate` is a product of the [PDS Ring-Moon Systems Node](https://pds-rings.seti.org).

# Installation

The `pdstemplate` module is available via the `rms-pdstemplate` package on PyPI and can be
installed with:

```sh
pip install rms-template
```

# Getting Started

The general procedure is as follows:

1. Create a template object by calling the `PdsTemplate` constructor to read a template
file:

        template = PdsTemplate(template_file_path)

2. Create a dictionary that contains the parameter values to use inside the label.
3. Construct the label as follows:

        template.write(dictionary, label_file)

    This will create a new label of the given name, using the values in the given
    dictionary. Once the template has been constructed, steps 2 and 3 can be repeated any
    number of times.

Details of the `PdsTemplate` class are available in the [module documentation](https://rms-pdstemplate.readthedocs.io/en/latest/module.html).

## SUBSTITUTIONS

A template file will look generally like a label file, except for certain embedded
expressions that will be replaced when the template's write() method is called.

In general, everything between dollar signs `$` in the template is interpreted as a
Python expression to be evaluated. The result of this expression then replaces it
inside the label. For example, if `dictionary['INSTRUMENT_ID'] == 'ISSWA'`, then

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


- [`BASENAME(filepath)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.BASENAME):
  The basename of `filepath`, with leading directory path removed.

- [`BOOL(value, true='true', false='false')`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.BOOL):
  Return `true` if `value` evaluates to Boolean True; otherwise, return `false`.

- [`COUNTER(name, reset=False)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.COUNTER):
  The current value of a counter identified by `name`, starting at 1. If `reset` is True, the counter is reset to 0.

- [`CURRENT_TIME(date_only=False)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.CURRENT_TIME):
  The current time in the local time zone as a string of the form
  "yyyy-mm-ddThh:mm:sss" if `date_only=False` or "yyyy-mm-dd" if `date_only=True`.

- [`CURRENT_ZULU(date_only=False)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.CURRENT_ZULU):
  The current UTC time as a string of the form "yyyy-mm-ddThh:mm:sssZ" if
  `date_only=False` or "yyyy-mm-dd" if `date_only=True`.

- [`DATETIME(time, offset=0, digits=None)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.DATETIME):
  Convert `time` as an arbitrary date/time string or TDB seconds to an ISO date
  format with a trailing "Z". An optional `offset` in seconds can be applied. The
  returned string contains an appropriate number of decimal digits in the seconds
  field unless `digits` is specified explicitly. If `time` is "UNK", then "UNK" is
  returned.

- [`DATETIME_DOY(time, offset=0, digits=None)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.DATETIME_DOY):
  Convert `time` as an arbitrary date/time string or TDB seconds to an ISO date
  of the form "yyyy-dddThh:mm:ss[.fff]Z". An optional `offset` in seconds can be
  applied. The returned string contains an appropriate number of decimal digits in
  the seconds field unless `digits` is specified explicitly. If `time` is "UNK",
  then "UNK" is returned.

- [`DAYSECS(string)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.DAYSECS):
  The number of elapsed seconds since the most recent midnight. `time` can be
  a date/time string, a time string, or TDB seconds.

- [`FILE_BYTES(filepath)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.FILE_BYTES):
  The size in bytes of the file specified by `filepath`.

- [`FILE_MD5(filepath)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.FILE_MD5):
  The MD5 checksum of the file specified by `filepath`.

- [`FILE_RECORDS(filepath)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.FILE_RECORDS):
  The number of records in the the file specified by `filepath` if it is ASCII; 0
  if the file is binary.

- [`FILE_TIME(filepath)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.FILE_TIME):
  The modification time in the local time zone of the file specified by `filepath`
  in the form "yyyy-mm-ddThh:mm:ss".

- [`FILE_ZULU(filepath)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.FILE_ZULU):
  The UTC modification time of the the file specified by `filepath` in the form
  "yyyy-mm-ddThh:mm:ssZ".

- [`LABEL_PATH()`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.LABEL_PATH):
  The full directory path to the label file being written.

- [`NOESCAPE(text)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.NOESCAPE):
  If the template is XML, evaluated expressions are "escaped" to ensure that they
  are suitable for embedding in a PDS4 label. For example, ">" inside a string will
  be replaced by `&gt;`. This function prevents `text` from being escaped in the
  label, allowing it to contain literal XML.

- [`RAISE(exception, message)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.RAISE):
  Raise an exception with the given class `exception` and the `message`.

- [`REPLACE_NA(value, if_na, flag='N/A')`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.REPLACE_NA):
  Return `if_na` if `value` equals "N/A" (or `flag` if specified); otherwise, return `value`.

- [`REPLACE_UNK(value, if_unk)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.REPLACE_UNK):
  Return `if_unk` if `value` equals "UNK"; otherwise, return `value`.

- [`TEMPLATE_PATH()`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.TEMPLATE_PATH):
  The directory path to the template file.

- [`VERSION_ID()`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.VERSION_ID):
  Version ID of this module, e.g., "v0.1.0".

- [`WRAP(left, right, text, preserve_single_newlines=True)`](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.WRAP):
  Format `text` to fit between the `left` and `right` column numbers. The
  first line is not indented, so the text will begin in the column where "$WRAP"
  first appears in the template. If `preserve_single_newlines` is true, then all
  newlines in the string will show up in the resultant text. If false, then
  single newlines will be considered part of the text flow and will be wrapped.

These functions can also be used directly by the programmer; they are static functions
of class PdsTemplate.

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

where `expression` evaluates to a Python iterable. Within the `template text`, these
new variable names are assigned:

- `VALUE` = the next value of the iterator;
- `INDEX` = the index of this iterator, starting at zero;
- `LENGTH` = the number of items in the iteration.

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

    $FOR(name, k=targets)
        <target_name>$name (naif_ids[k])$</target_name>
    $END_FOR

You can also use `$IF`, `$ELSE_IF`, `$ELSE`, and `$END_IF` headers to select among
alternative blocks of text in the template:

- `$IF(expression)` - Evaluate `expression` and include the next lines of the
   template if it is logically True (e.g., boolean True, a nonzero number, a non-empty
   list or string, etc.).
- `$ELSE_IF(expression)` - Include the next lines of the template if `expression` is
   logically True and every previous expression was not.
- `$ELSE` - Include the next lines of the template only if all prior
  expressions were logically False.
- `$END_IF` - This marks the end of the set of if/else alternatives.

As with other substitutions, you can define a new variable of a specified name by
using `name=expression` inside the parentheses of an `$IF()` or `$ELSE_IF()` header.

Note that headers can be nested arbitrarily inside the template.

You can use the `$NOTE` and `$END_NOTE` headers to embed any arbitrary comment block into
the template. Any text between these headers does not appear in the label.

One additional header is supported: `$ONCE(expression)`. This header evaluates
`expression` but does not alter the handling of subsequent lines of the template. You
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
