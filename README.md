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

`pdstemplate` is a Python module that defines the `PdsTemplate` class, which is
used to generate PDS labels based on template files. Both PDS3 and PDS4 (xml) labels are
supported. Although specifically designed to facilitate data deliveries by PDS data
providers, the template system is generic and can be used to generate files from templates
for other purposes.

`pdstemplate` is a product of the [PDS Ring-Moon Systems Node](https://pds-rings.seti.org).

# Installation

The `pdstemplate` module is available via the `rms-pdstemplate`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://pypi.org/project/rms-pdstemplate)
package on PyPI and can be installed with:

```sh
pip install rms-pdstemplate
```

# Getting Started

The general procedure is as follows:

1. Create a template object by calling the
`PdsTemplate`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate)
constructor to read a template file:

        from pdstemplate import PdsTemplate
        template = PdsTemplate(template_file_path)

2. Create a dictionary that contains the parameter values to use inside the label.
3. Construct the label using the
`write()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.write)
method as follows:

        template.write(dictionary, label_file)

This will create a new label of the given name, using the values in the given
dictionary. Once the template has been constructed, steps 2 and 3 can be repeated any
number of times.

Alternatively, you can obtain the content of a label without writing it to a file using
`generate()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.generate).

`pdstemplate` employs the RMS Node's `rms-filecache`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://pypi.org/project/rms-filecache)
module and its `FCPath`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-filecache.readthedocs.io/en/latest/module.html#filecache.file_cache_path.FCPath)
class to support the handling of files at a website or in the cloud. You can refer to a
remote file by URL and the `PdsTemplate` will treat it as if it were a local file.
See filecache's [documentation](https://rms-filecache.readthedocs.io/en/latest/index.html)
for further details.

Details of the `PdsTemplate` class are available in the [module documentation](https://rms-pdstemplate.readthedocs.io/en/latest/module.html).

# Template Syntax

A template file will look generally like a label file, except for certain embedded
expressions that will be replaced when the template's
`write()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.write)
or
`generate()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.generate)
method is called.

## Substitutions

In general, everything between dollar signs "$" in the template is interpreted as a
Python expression to be evaluated. The result of this expression then replaces it
inside the label. For example, if `dictionary['INSTRUMENT_ID'] == 'ISSWA'`, then

    <instrument_id>$INSTRUMENT_ID$</instrument_id>

in the template will become

    <instrument_id>ISSWA</instrument_id>

in the label. The expression between "$" in the template can include indexes, function
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

To embed a literal "$" inside a label, enter "$$" into the template.

## Headers

Headers provide even more sophisticaed control over the content of a label. A header
appears alone on a line of the template and begins with "$" as the first non-blank
character. It determines whether or how subsequent text of the template will appear in the
file, from here up to the next header line.

### FOR and END_FOR

You can include one or more repetitions of the same text using `FOR` and `END_FOR`
headers. The format is

    $FOR(expression)
        <template text>
    $END_FOR

where `expression` evaluates to a Python iterable. Within the `template text`, these new
variable names are assigned:

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

### IF, ELSE_IF, ELSE, and END_IF

You can also use `IF`, `ELSE_IF`, `ELSE`, and `END_IF` headers to select among
alternative blocks of text in the template:

- `IF(expression)` - Evaluate `expression` and include the next lines of the
   template if it is logically True (e.g., boolean True, a nonzero number, a non-empty
   list or string, etc.).
- `ELSE_IF(expression)` - Include the next lines of the template if `expression` is
   logically True and every previous expression was not.
- `ELSE` - Include the next lines of the template only if all prior
  expressions were logically False.
- `END_IF` - This marks the end of the set of if/else alternatives.

As with other substitutions, you can define a new variable of a specified name by
using `name=expression` inside the parentheses of `IF()` or `ELSE_IF()`.

Note that headers can be nested arbitrarily inside the template.

### ONCE

`ONCE` is a header that simply includes the content that follows it one time. However,
it is useful for its side-effect, which is that `ONCE(expression)` allows the embedded
`expression` to be evaluated without writing new text into the label. You can use this
capability to define variables internally without affecting the content of the label
produced. For example:

    $ONCE(date=big_dictionary["key"]["date"])

will assign the value of the variable named `date` for subsequent use within the template.

### INCLUDE

This header will read the content of another file and insert its content into the template
here:

    $INCLUDE(filename)

Using the environment variable `PDSTEMPLATE_INCLUDES`, you can define one or more
directories that will be searched for a file to be included. If multiple directories are
to be searched, they should be separated by colons. You can also specify one or more
directories to search in the
`PdsTemplate`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate)
constructor using the `includes` input parameter.

Include files are handled somewhat differently from other headers. When `INCLUDE`
references a file as a literal string rather than as an expression to evaluate, it is
processed at the time that the
`PdsTemplate`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate)
is constructed. However, if the
filename is given as an expression, it is not evaluated until the
`write()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.write)
or
`generate()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.generate)
method is called for each label.

### NOTE and END_NOTE

You can use `NOTE` and `END_NOTE` to embed any arbitrary comment block into the
template. Any text between these headers does not appear in the label:

    $NOTE
    Here is an extended comment about the templae
    $END_NOTE

You can also use `$NOTE:` for an in-line comment. This text, and any blanks before it,
are not included in the label::

    <filter>$FILTER$</filter>   $NOTE: This is where we identify the filter

## Pre-defined Functions

The following pre-defined functions can be used inside any expression in the template.

- `BASENAME(filepath)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.BASENAME):
  The basename of `filepath`, with leading directory path removed.

- `BOOL(value, true='true', false='false')`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.BOOL):
  Return "true" if `value` evaluates to Boolean True; otherwise, return "false".

- `COUNTER(name, reset=False)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.COUNTER):
  The current value of a counter identified by `name`, starting at 1. If `reset` is True, the counter is reset to 0.

- `CURRENT_TIME(date_only=False)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.CURRENT_TIME):
  The current time in the local time zone as a string of the form
  "yyyy-mm-ddThh:mm:sss" if `date_only=False` or "yyyy-mm-dd" if `date_only=True`.

- `CURRENT_ZULU(date_only=False)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.CURRENT_ZULU):
  The current UTC time as a string of the form "yyyy-mm-ddThh:mm:sssZ" if
  `date_only=False` or "yyyy-mm-dd" if `date_only=True`.

- `DATETIME(time, offset=0, digits=None)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.DATETIME):
  Convert `time` as an arbitrary date/time string or TDB seconds to an ISO date
  format with a trailing "Z". An optional `offset` in seconds can be applied. The
  returned string contains an appropriate number of decimal digits in the seconds
  field unless `digits` is specified explicitly. If `time` is "UNK", then "UNK" is
  returned.

- `DATETIME_DOY(time, offset=0, digits=None)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.DATETIME_DOY):
  Convert `time` as an arbitrary date/time string or TDB seconds to an ISO date
  of the form "yyyy-dddThh:mm:ss[.fff]Z". An optional `offset` in seconds can be
  applied. The returned string contains an appropriate number of decimal digits in
  the seconds field unless `digits` is specified explicitly. If `time` is "UNK",
  then "UNK" is returned.

- `DAYSECS(string)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.DAYSECS):
  The number of elapsed seconds since the most recent midnight. `time` can be
  a date/time string, a time string, or TDB seconds.

- `FILE_BYTES(filepath)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.FILE_BYTES):
  The size in bytes of the file specified by `filepath`.

- `FILE_MD5(filepath)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.FILE_MD5):
  The MD5 checksum of the file specified by `filepath`.

- `FILE_RECORDS(filepath)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.FILE_RECORDS):
  The number of records in the the file specified by `filepath` if it is ASCII; 0
  if the file is binary.

- `FILE_TIME(filepath)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.FILE_TIME):
  The modification time in the local time zone of the file specified by `filepath`
  in the form "yyyy-mm-ddThh:mm:ss".

- `FILE_ZULU(filepath)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.FILE_ZULU):
  The UTC modification time of the the file specified by `filepath` in the form
  "yyyy-mm-ddThh:mm:ssZ".

- `GETENV(name, default='')`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.GETENV):
  The value of any environment variable.

- `LABEL_PATH()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.LABEL_PATH):
  The full directory path to the label file being written.

- `LOG(level, message, filepath='', force=False)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.LOG):
  Write a message to the current log.

- `NOESCAPE(text)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.NOESCAPE):
  If the template is XML, evaluated expressions are "escaped" to ensure that they
  are suitable for embedding in a PDS4 label. For example, ">" inside a string will
  be replaced by `&gt;`. This function prevents `text` from being escaped in the
  label, allowing it to contain literal XML.

- `QUOTE_IF(text)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.QUOTE_IF):
  Quote the given text if it requires quotes within a PDS3 label.

- `RAISE(exception, message)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.RAISE):
  Raise an exception with the given class `exception` and the `message`.

- `RECORD_BYTES(filepath)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.RECORD_BYTES):
  The maximum number of bytes in any record of the file specified by `filepath`, including terminators.

- `REPLACE_NA(value, if_na, flag='N/A')`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.REPLACE_NA):
  Return `if_na` if `value` equals "N/A" (or `flag` if specified); otherwise, return `value`.

- `REPLACE_UNK(value, if_unk)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.REPLACE_UNK):
  Return `if_unk` if `value` equals "UNK"; otherwise, return `value`.

- `TEMPLATE_PATH()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.TEMPLATE_PATH):
  The directory path to the template file.

- `VERSION_ID()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.VERSION_ID):
  Version ID of this module using two digits, e.g., "v1.0".

- `WRAP(left, right, text, preserve_single_newlines=True)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.WRAP):
  Wrap the given text to a specified indentation and width.

These functions can also be used directly by the programmer; they are static functions
of class PdsTemplate.

# Logging and Exception Handling

`pdstemplate` employs the RMS Node's `rms-pdslogger`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://pypi.org/project/rms-pdslogger)
module to handle logging. By default, the
logger is a `PdsLogger`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdslogger.readthedocs.io/en/latest/module.html#pdslogger.PdsLogger)
object, although any `logging.Logger` object will work. See
[`pdslogger`'s documentation](https://rms-pdslogger.readthedocs.io) for further details.

You can override the default Logger using static method
`set_logger()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.utils.set_logger).
You can also set the logging level ("info", "warning", "error", etc.) using
`set_log_level()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.utils.set_log_level)
and can select among many log formatting options using
`set_log_format()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.utils.set_log_format)
Use
`get_logger()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.utils.get_logger)
to obtain the current Logger.

By default, exceptions during a call to
`write()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.write)
or
`generate()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.generate)
are handled as follows:

1. They are written to the log.
2. The expression that triggered the exception is replaced by the error text in the
   label, surrounded by "[[[" and "]]]" to make it easier to find.
3. The attributes `fatal_count`, `error_count`, and `warning_count` of the
   `PdsTemplate`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate)
   object contain the number of messages logged by each category.
4. The exception is otherwise suppressed.

This behavior can be modified by calling method `raise_exceptions(True)` in the call to
`write()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.write)
or
`generate()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.generate);
in this case, the exception
will be raised, label generation will stop, and the label will not be written.

# Pre-processors

A pre-processor is a function that takes the text of a template file as input and returns
a new template as output. As described above, `INCLUDE` headers that contain an explicit
file name (rather than an expression to be evaluated) are handled by a pre-processor.

You may define your own functions to pre-process the content of a template. They must have
this call signature::

    func(path: str | Path | FCPath, content: str, *args, **kwargs) -> str

where

- `path` is the path to the template file (used here just for error logging).
- `content` is the content of a template represented by a single string with <LF> line
  terminators.
- `*args` is for any additional positional arguments to `func`.
- `**kwargs` is for any additional keyword arguments to `func`.

When you invoke the
`PdsTemplate`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate)
constructor, one of the optional inputs is
`preprocess`, which takes either a single function or a list of functions to apply after
the `INCLUDE` pre-processor. For the first of these, the `args` and `kwargs` inputs can be
provided as additional inputs to the constructor. Subsequent pre-processors cannot take
additional arguments; define them using lambda notation instead.

Note that a
`PdsTemplate`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate)
object has an attribute `content`, which contains the
full content of the template after all pre-processing has been performed. You can examine
this attribute to see the final result of all processing. Note also that when line numbers
appear in an error message, they refer to the line number of the template after
pre-processing, not before.

# `pdstemplate.pds3table`

`pds3table` is a plug-in module to automate the generation and validation of PDS3 labels
for ASCII tables. It works in concert with the
`asciitable` module, which analyzes
the content of ASCII table files. It is used by stand-alone program `tablelabel` to
validate and repair existing PDS3 labels as well as to generate new labels; if
`tablelabel` meets your needs, you can avoid any programming in Python.

To import:

    import pdstemplate.pds3table

Once imported, the following pre-defined functions become available for use within a
`PdsTemplate`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate):

- `ANALYZE_PDS3_LABEL(labelpath, validate=True)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.pds3table.ANALYZE_PDS3_LABEL):
  analyzes the content of a PDS3 label or template, gathering
  information about the names and other properties of its `TABLE` and `COLUMN` objects. Once
  it is called, the following functions become available.
- `ANALYZE_TABLE(filepath, separator=',', crlf=None, escape='')`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.asciitable.ANALYZE_TABLE)
  (from `asciitable`) takes the path to an existing
  ASCII table and analyzes its content, inferring details about the content and formats of
  all the columns.
- `VALIDATE_PDS3_LABEL(hide_warnings=False, abort_on_error=True)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.pds3table.VALIDATE_PDS3_LABEL):
  issues a warning message for any errors found in the label
  or template. Optionally, it can abort the generation of the label if it encounters an
  irrecoverable incompatibility with the ASCII table.
- `LABEL_VALUE(name, column=0)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.pds3table.LABEL_VALUE):
  returns correct and valid PDS3 values for many of the attributes of
  PDS3 TABLE and COLUMN objects, based on its analysis of the table.
- `OLD_LABEL_VALUE(name, column=0)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.pds3table.OLD_LABEL_VALUE):
  returns the current (although possibly incorrect or missing)
  values for many of the same PDS3 `TABLE` and `COLUMN` attributes.

For example, consider a template that contains this content:

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

The initial calls to
`ANALYZE_TABLE()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.asciitable.ANALYZE_TABLE)
and
`ANALYZE_PDS3_LABEL()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.pds3table.ANALYZE_PDS3_LABEL)
are
embedded inside a `ONCE()` directive because they return no content. The first call
analyzes the content and structure of the ASCII table, and the second analyzes the
template. The subsequent calls to
`LABEL_VALUE()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.pds3table.LABEL_VALUE)
fill in the correct values for the specified quantities.

Optionally, you could include this as the third line in the template::

    $ONCE(VALIDATE_PDS3_LABEL())

This function logs a warnings and errors for any incorrect TABLE and COLUMN values
currently in the template.

This module also provides a pre-processor, which can be used to validate or repair an
exising PDS3 label. The function
`pds3_table_preprocessor`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.pds3table.pds3_table_preprocessor),
when used as the `preprocess` input to the
`PdsTemplate`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate)
constructor, transforms an
existing PDS3 label into a new template by replacing all needed `TABLE` and `COLUMN`
attributes with calls to
`LABEL_VALUE()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.pds3table.LABEL_VALUE).
The effect is that when the label is
generated, it is guaranteed to contain correct information where the earlier label might
have been incorrect. In this case, your program would look something like this:

    from pdstemplate import PdsTemplate
    from pdstemplate.pds3table import pds3_table_preprocessor

    template = PdsTemplate(label_path, crlf=True, ...
                           preprocess=pds3_table_preprocessor, kwargs={...})
    template.write({}, label_path, ...)

The constructor invokes
`pds3_table_preprocessor`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.pds3table.pds3_table_preprocessor)
to transform the label into a
template. You can use the `kwargs` input dictionary to provide inputs to the
pre-processor, such as adding a requirement that each column contain `FORMAT`,
`COLUMN_NUMBER`, `MINIMUM/MAXIMUM_VALUEs`, etc., and designating how warnings and errors are
to be handled.

Afterward, the call to the template's
`write()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.PdsTemplate.write)
method will
validate the label and/or write a new label, depending on its input parameters.

For example, suppose the label contains this:

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

You then execute this:

    template = PdsTemplate(label_path, crlf=True,
                           preprocess=pds3_table_preprocessor,
                           kwargs={'numbers': True, 'formats': True})

After the call, you can look at the template's `content` attribute, which contains the
template's content after pre-processing. Its value is this:

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

The `TABLE` and `COLUMN` attributes defining table format and structure have been replaced by
calls to
`LABEL_VALUE()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.pds3table.LABEL_VALUE),
which will provide the correct value whether or not the
value in the original label was correct. Also, `COLUMN_NUMBER` and `FORMAT` have been added to
the COLUMN object because of the pre-processor inputs `numbers=True` and `formats=True`.

Another application of the preprocessor is to simplify the construction of a template for
an ASCII table. Within a template, the only required attributes of a `COLUMN` object are
`NAME` and `DESCRIPTION`. Optionally, you can also specify any special constants,
`VALID_MINIMUM/MAXIMUM` values, `OFFSET` and `SCALING_FACTOR`, and the number of `ITEMS` if the
`COLUMN` object describes more than one. All remaining information about the column, such as
`DATA_TYPE`, `START_BYTE`, `BYTES`, etc., will be filled in by the pre-processor. Inputs to the
preprocessor let you indicate whether to include `FORMATs`, `COLUMN_NUMBERs`, and the
`MINIMUM/MAXIMUM_VALUEs` attributes automatically.

# `pdstemplate.asciitable`

`asciitable` is a plug-in module to assist with the labeling of ASCII tables in PDS3 and PDS4. It
supports the `pdstemplate.pds3table` module and the `tablelabel` tool, and will also be used by
a future `pds4table` tool. To import:

    import pdstemplate.asciitable

This import creates two new pds-defined functions, which can be accessed within any
template.

- `ANALYZE_TABLE(filepath, *, separator=',', crlf=None, escape='')`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.asciitable.ANALYZE_TABLE)
  takes the path to an existing
  ASCII table and analyzes its content, inferring details about the content and formats of
  all the columns.
- `TABLE_VALUE(name, column=0)`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.asciitable.TABLE_VALUE)
  returns information about the content of the table for use within
  the label to be generated.

For example, consider a template that contains this content:

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


The initial call to
`ANALYZE_TABLE()`[![image](https://raw.githubusercontent.com/SETI/rms-pdstemplate/main/icons/link.png)](https://rms-pdstemplate.readthedocs.io/en/latest/module.html#pdstemplate.asciitable.ANALYZE_TABLE)
is embedded inside a `ONCE` directive
because it returns no content. However, it reads the table file and assembles a database
of what it has found. The subsequent calls to it can be used for multiple labels and each
label will always contain the correct numbers of `ROWS` and `COLUMNS`. `TABLE_VALUE` can
also retrieve information about the content and format about each of the table's columns.

# tablelabel

This is a stand-alone program that can be used to validate and repair existing PDS3 labels
describing ASCII tables and can also generate new labels. Type:

    tablelabel --help

for full information:

    usage: tablelabel.py [-h] (--validate | --repair | --create | --save) [--template TEMPLATE]
                         [--numbers] [--formats] [--minmax [MINMAX ...]]
                         [--derived [DERIVED ...]] [--edit [EDIT ...]] [--real [REAL ...]]
                         [--dict [DICT ...]] [-e] [-E] [--nobackup] [--quiet] [--log] [--debug]
                         [--timestamps]
                         [path ...]

    tablelabel: Validate, repair, or create a PDS3 label file for an existing ASCII table.

    positional arguments:
      path                  Path to one or more PDS3 label or ASCII table files. It is always
                            assumed that a label file has a ".lbl" extension and its associated
                            table file is in the same directory but with a ".tab" extension.

    options:
      -h, --help            show this help message and exit
      --validate, -v        Validate an existing label, logging any errors or other
                            discrepancies as warnings messages; do not write a new label.
      --repair, -r          Update an existing label file only if the new label would be
                            different; otherwise leave it unchanged.
      --create, -c          Create a new label where none exists; leave existing labels alone.
      --save, -s            Save a new label, replacing any existing file.
      --template TEMPLATE, -t TEMPLATE
                            An optional template file path. If specified, this template is used
                            to generate new label content; otherwise, an existing label is
                            validated or repaired.
      --numbers, -n         Require every column to have a COLUMN_NUMBER attribute.
      --formats, -f         Require every column to have a FORMAT attribute.
      --minmax [MINMAX ...], -m [MINMAX ...]
                            One or more column names that should have the MINIMUM_VALUE and
                            MAXIMUM_VALUE attributes. Use "float" to include these attributes
                            for all floating-point columns; use "int" to include these
                            attributes for all integer-valued columns.
      --derived [DERIVED ...]
                            One or more column names that should have the DERIVED_MINIMUM and
                            DERIVED_MAXIMUM attributes. Use "float" to include these attributes
                            for all floating-point columns.
      --edit [EDIT ...]     One or more expressions of the form "column:name=value", which will
                            be used to insert or replace values currently in the label.
      --real [REAL ...]     One or more COLUMN names that should be identified as ASCII_REAL
                            even if every value in the table is an integer.
      --dict [DICT ...], -d [DICT ...]
                            One or more keyword definitions of the form "name=value", which
                            will be used when the label is generated. Each value must be an
                            integer, float, or quoted string.
      -e                    Format values involving an exponential using lower case "e"
      -E                    Format values involving an exponential using upper case "E"
      --nobackup, -B        If a label is repaired, do not save a backup of an existing label.
                            Otherwise, an existing label is renamed with a suffix identifying
                            its original creation date and time.
      --quiet, -q           Do not log to the terminal.
      --log, -l             Save a log file of warnings and steps performed. The log file will
                            have the same name as the label except the extension will be ".log"
                            instead of ".lbl".
      --debug               Include "debug" messages in the log.
      --timestamps          Include a timestamp in each log record.

# quicklabel

This is a stand-alone program that can be used to create a label for a file from a
template. Type:

    quicklabel --help

for full information:

    usage: quicklabel [-h] [--template TEMPLATE] [--dict [DICT ...]] [--nobackup] [path ...]
    
    quicklabel: Create a PDS3 label for an existing file given a template.
    
    positional arguments:
      path                  Path to one or more files to label.
    
    options:
      -h, --help            show this help message and exit
      --template TEMPLATE, -t TEMPLATE
                            Path to the template file.
      --dict [DICT ...], -d [DICT ...]
                            One or more keyword definitions of the form "name=value", which
                            will be used when the label is generated. Each value must be an
                            integer, float, or quoted string.
      --nobackup, -B        Do not save a backup of an existing label. Otherwise, an existing
                            label is renamed with a suffix identifying its original creation
                            date and time.
