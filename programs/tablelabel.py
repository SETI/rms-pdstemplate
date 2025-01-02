#!/usr/bin/env python3
##########################################################################################
# rms-pdstemplate/programs/tablelabel.py
##########################################################################################
"""
.. tablelabel:

##########
tablelabel
##########

This is a stand-alone program that can be used to validate and repair existing PDS3 labels
describing ASCII tables and can also create new labels. Type::

    tablelabel --help

for more information.
"""

import argparse
import pathlib
import sys

import pdslogger
from pdstemplate import PdsTemplate, set_logger
from pdstemplate.pds3table import pds3_table_preprocessor

LOGNAME = 'pds.tablelabel'

# Set up parser
parser = argparse.ArgumentParser(
    description='tablelabel: Validate, repair, or create a PDS3 label file for an '
                'existing ASCII table.')

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--validate', '-v',
                   dest='task', action='store_const', const='validate',
                   help='Validate an existing label, logging any errors or other '
                        'discrepancies as warnings messages; do not write a new label.')

group.add_argument('--repair', '-r',
                   dest='task', action='store_const', const='repair',
                   help='Update an existing label file only if the new label would be '
                        'different; otherwise leave it unchanged.')

group.add_argument('--create', '-c',
                   dest='task', action='store_const', const='create',
                   help='Create a new label where none exists; leave existing labels '
                        'alone.')

group.add_argument('--save', '-s',
                   dest='task', action='store_const', const='save',
                   help='Save a new label, replacing any existing file.')

parser.add_argument('path', nargs='*', type=str,
                    help='Path to one or more PDS3 label or ASCII table files. It is '
                         'always assumed that a label file has a ".lbl" extension and '
                         'its associated table file is in the same directory but with a '
                         '".tab" extension.')

parser.add_argument('--template', '-t', type=str,
                    help='An optional template file path. If specified, this template is '
                         'used to generate new label content; otherwise, an existing '
                         'label is validated or repaired.')

parser.add_argument('--numbers', '-n', action='store_true',
                    help='Require every column to have a COLUMN_NUMBER attribute.')

parser.add_argument('--formats', '-f', action='store_true',
                    help='Require every column to have a FORMAT attribute.')

parser.add_argument('--minmax', '-m', nargs='*', type=str,
                    help='One or more column names that should have the MINIMUM_VALUE '
                         'and MAXIMUM_VALUE attributes. Use "float" to include these '
                         'attributes for all floating-point columns; use "int" to '
                         'include these attributes for all integer-valued columns.')

parser.add_argument('--derived', nargs='*', type=str,
                    help='One or more column names that should have the DERIVED_MINIMUM '
                         'and DERIVED_MAXIMUM attributes. Use "float" to include these '
                         'attributes for all floating-point columns.')

parser.add_argument('--edit', nargs='*', type=str,
                    help='One or more expressions of the form "column:name=value", '
                         'which will be used to insert or replace values currently in '
                         'the label.')

parser.add_argument('--real', nargs='*', type=str,
                    help='One or more COLUMN names that should be identified as '
                         'ASCII_REAL even if every value in the table is an integer.')

parser.add_argument('--dict', '-d', nargs='*', type=str,
                    help='One or more keyword definitions of the form "name=value", '
                         'which will be used when the label is generated. Each value '
                         'must be an integer, float, or quoted string.')

parser.add_argument('-e', dest='upper_e', action='store_false', default=True,
                    help='Format values involving an exponential using lower case "e"')

parser.add_argument('-E', dest='upper_e', action='store_true',
                    help='Format values involving an exponential using upper case "E"')

parser.add_argument('--nobackup', '-B', action='store_true',
                    help='If a file is repaired, do not save a backup of an existing '
                         'file. Otherwise, an existing file is renamed with a suffix '
                         'identifying its original creation date and time.')

parser.add_argument('--quiet', '-q', action='store_true',
                    help='Do not log to the terminal.')

parser.add_argument('--log', '-l', action='store_true',
                    help='Save a log file of warnings and steps performed. The log file '
                         'will have the same name as the label except the extension '
                         'will be ".log" instead of ".lbl".')

parser.add_argument('--debug', action='store_true',
                    help='Include "debug" messages in the log.')

parser.add_argument('--timestamps', action='store_true',
                    help='Include a timestamp in each log record.')

# Parse and validate the command line
args = parser.parse_args()

kwargs = {
    'numbers' : args.numbers,
    'formats' : args.formats,
    'minmax'  : args.minmax or [],
    'derived' : args.derived or [],
    'edits'   : args.edit or [],
    'reals'   : args.real or [],
    'validate': True,
}

# Interpret paths
paths = [pathlib.Path(p).with_suffix('.lbl') for p in args.path]

# Define the logger
logger = pdslogger.PdsLogger.get_logger(LOGNAME, timestamps=args.timestamps, digits=3,
                                        lognames=False, indent=True, blanklines=False,
                                        level='debug' if args.debug else 'info')
logger.add_handler(pdslogger.NULL_HANDLER)

parents = set(p.parent for p in paths)
logger.add_root(*parents)

# Define the default handlers
set_logger(logger)
if not args.quiet:
    logger.add_handler(pdslogger.STDOUT_HANDLER)

# Intepret the template if provided
template = None
if args.template:
    template = PdsTemplate(args.template, crlf=True, upper_e=args.upper_e,
                           preprocess=pds3_table_preprocessor, kwargs=kwargs)
    if len(paths) > 1:
        logger.blankline()

# Interpret the --dict input
dictionary = {}
for item in args.dict or []:
    name, _, value = item.partition('=')
    try:
        value = eval(value)
    except Exception:
        pass
    dictionary[name] = value

# Process each path...
errors = 0
warnings = 0
for k, path in enumerate(paths):

    # Skip existing files for task == "create"
    if args.task == 'create' and path.exists():
        logger.info('Existing file skipped', path)
        if k > len(paths) - 1:
            logger.blankline()
        continue

    # If there's not a default template, each label is its own template
    if not args.template:
        template = PdsTemplate(path, crlf=True, upper_e=args.upper_e,
                               preprocess=pds3_table_preprocessor, kwargs=kwargs)

    # Save a log file for each path if necessary
    handler = None
    if args.log:
        handler = pdslogger.file_handler(path.with_suffix('.log'))
        logger.add_handler(handler)

    # Process one label
    mode = 'save' if args.task == 'create' else args.task
    try:
        status = template.write(dictionary, path, mode=mode, backup=(not args.nobackup))
    finally:
        if handler:
            logger.remove_handler(handler)

    logger.blankline()

    # Keep track of errors and warnings
    errors += status[0]
    warnings += status[1]

# Report the error status if validation failed or any error occurred
if errors or (args.task == 'validate' and warnings):
    sys.exit(1)

##########################################################################################
