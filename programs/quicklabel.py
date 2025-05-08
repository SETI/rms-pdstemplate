#!/usr/bin/env python3
##########################################################################################
# rms-pdstemplate/programs/quicklabel.py
##########################################################################################
"""
.. quicklabel:

##########
quicklabel
##########

This is a stand-alone program that can be used to create a label for a file from a
template. Type::

    quicklabel --help

for more information.
"""

import argparse
import pathlib
import sys

from pdstemplate import PdsTemplate
from pdstemplate.pds3_syntax_checker import pds3_syntax_checker

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

LOGNAME = 'pds.quicklabel'

# Set up parser
parser = argparse.ArgumentParser(
    description='quicklabel: Create a PDS3 label for an existing file given a template.')

parser.add_argument('path', nargs='*', type=str,
                    help='Path to one or more files to label.')
parser.add_argument('--template', '-t', type=str, required=True,
                    help='Path to the template file.')
parser.add_argument('--dict', '-d', nargs='*', type=str,
                    help='One or more keyword definitions of the form "name=value", '
                         'which will be used when the label is generated. Each value '
                         'must be an integer, float, or quoted string.')
parser.add_argument('--nobackup', '-B', action='store_true',
                    help='Do not save a backup of an existing label. Otherwise, an '
                         'existing label is renamed with a suffix identifying its '
                         'original creation date and time.')

def main():

    # Parse and validate the command line
    args = parser.parse_args()

    label_paths = [pathlib.Path(p).with_suffix('.lbl') for p in args.path]
    if not label_paths:
        print('error: no input files')
        sys.exit(1)

    template = PdsTemplate(args.template, crlf=True, postprocess=pds3_syntax_checker)

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
    for k, path in enumerate(label_paths):

        # Process one label
        status = template.write(dictionary, path, mode='save', backup=(not args.nobackup))

        # Keep track of errors and warnings
        errors += status[0]

    # Report the error status if any error occurred
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()

##########################################################################################
