##########################################################################################
# programs/pds3_syntax_checker.py
##########################################################################################
"""
.. _pds3_syntax_checker:

###############################
pdstemplate.pds3_syntax_checker
###############################

``pds3_syntax_checker`` is a function that raises an exception if the given
label string does not strictly conform to the PDS3 standard. It can be used as
a `postprocessor` input to the PdsTemplate constructor and will ensure that
each newly-generated PDS3 label is free of syntax errors.

To use::

    from pdstemplate._pds3_syntax_checker import pds3_syntax_checker

In the template constructor, specify::

    template = PdsTemplate(..., postprocess=pds3_syntax_checker)
"""

from pdsparser import PdsLabel
from pdstemplate import TemplateAbort

# PDS3 Syntax Checker
def pds3_syntax_checker(content):
    """Post-processer to raise a TemplateAbort on a PDS3 parser error; otherwise, return
    content as is.

    Parameters:
        content (str): The content of a label as a string with newlines as line
            terminators.

    Returns:
        The original content of the label, unchanged.

    Raises:
        TemplateAbort: If the pdsparser module identifies a syntax error.
    """

    try:
        _ = PdsLabel.from_string(content)
    except Exception as err:
        message = str(err)
        if message[:2] == ', ':     # fix weird punctuation in pyparsing syntax errors
            message = message[2:]
        raise TemplateAbort('PDS3 syntax: ' + message)

    return content

##########################################################################################
