##########################################################################################
# pdstemplate/_pdsblock.py
##########################################################################################
"""Class used internally during template evaluation."""

import re
from collections import deque
from xml.sax.saxutils import escape

from ._utils import TemplateError, _Section, _LOGGER, _NOESCAPE_FLAG


class _PdsBlock(object):
    """_PdsBlock is an abstract class that describes a hierarchical section of the label
    template, beginning with a header. There are individual subclasses to support these
    different types of headers:
        _PdsForBlock   for $FOR
        _PdsIfBlock    for $IF and $ELSE_IF
        _PdsElseBlock  for $ELSE
        _PdsNoteBlock  for $NOTE
        _PdsOnceBlock  for $END_FOR, $END_IF, $END_NOTE, and any other section of the
                       template for which what follows is included exactly once.

    Each _PdsBlock always represents a logically complete section of the template, from
    one header up to its logical completion. For example, if a template contains this
    sequence of headers:
        $FOR(...)
          $IF(...)
          $ELSE
          $END_IF
        $END_FOR
    then every line of the template from the $FOR header down to (but not including) the
    $END_FOR will be described by one _PdsForBlock. Every _PdsBlock object contains a
    "sub_block" attribute, which is a deque of all the _PdsBlocks embedded within it. In
    this case, the sub_blocks attribute will contain a single _PdsIfBlock, which in turn
    will contain a single _PdsElseBlock.

    Each _PdsBlock also has a "body" attribute, which represents the template text between
    this header and the next header. That text is pre-processed for speedier execution by
    locating all the Python expressions (surrounded by "$") embedded within it.

    The constructor for each _PdsBlock subclass takes a single deque of Sequence objects
    as input. As a side-effect, it removes one or more items from the front of the deque
    until its definition, including any nested _PdsBlocks, is complete. The constructor
    handles any nested _PdsBlocks within it by calling the constructor recursively and
    saving the results of each recursive call in its sub_blocks attribute.

    Each _PdsBlock subclass has its own execute() method. This method contains the logic
    that determines whether (for _PdsIfBlocks and _PdsElseBlocks) or how many times (for
    _PdsForBlocks) its body and sub_blocks are written into the label file. Nesting is
    handled by having each _PdsBlock call the execute method of the _PdsBlocks nested
    within it.
    """

    # This pattern matches an internal assignment within an expression;
    # group(0) = variable name; group(1) = expression
    NAMED_PATTERN = re.compile(r' *([A-Za-z_]\w*) *=([^=].*)')
    ELSE_HEADERS = {'$ELSE_IF', '$ELSE', '$END_IF'}

    @staticmethod
    def new_block(sections, template):
        """Construct an _PdsBlock subclass based on a deque of _Section tuples (header,
        arg, line,  body). Pop as many _Section tuples off the top of the deque as are
        necessary to complete the block and any of its internal blocks, recursively.
        """

        (header, arg, line, body) = sections[0]
        if header.startswith('$ONCE'):
            return _PdsOnceBlock(sections, template)
        if header.startswith('$NOTE'):
            return _PdsNoteBlock(sections, template)
        if header == '$FOR':
            return _PdsForBlock(sections, template)
        if header == '$IF':
            return _PdsIfBlock(sections, template)

        if header == '$END_FOR':
            raise TemplateError(f'$END_FOR without matching $FOR at line {line}')
        if header == '$END_NOTE':
            raise TemplateError(f'$END_NOTE without matching $NOTE at line {line}')
        if header in _PdsBlock.ELSE_HEADERS:  # pragma: no coverage - can't get here
            raise TemplateError(f'{header} without matching $IF at line {line}')

        raise TemplateError(f'unrecognized header at line {line}: {header}({arg})'
                            )  # pragma: no coverage - can't get here

    def preprocess_body(self):
        """Preprocess body text from the template by locating all of the embedded
        Python expressions and returning a list of substrings, where odd-numbered entries
        are the expressions to evaluate, along with the associated line number.
        """

        # Split at the "$"
        parts = self.body.split('$')
        if len(parts) % 2 != 1:
            line = parts[-1].partition(':')[0]
            raise TemplateError(f'mismatched "$" at line {line}')

        # Because we inserted the line number after every "$", every part except the first
        # now begins with a number followed by ":". We need to make the first item
        # consistent with the others
        parts[0] = '0:' + parts[0]

        # new_parts is a deque of values that alternates between label substrings and
        # tuples (expression, name, line)

        new_parts = deque()
        for k, part in enumerate(parts):

            # Strip off the line number that we inserted after every "$"
            (line, _, part) = part.partition(':')

            # Even-numbered items are literal text
            if k % 2 == 0:
                new_parts.append(part)

            # Odd-numbered are expressions, possibly with a name
            else:

                # Look for a name
                match = _PdsBlock.NAMED_PATTERN.fullmatch(part)
                if match:
                    expression = match.group(2)
                    name = match.group(1)
                else:
                    expression = part
                    name = ''

                new_parts.append((expression, name, line))

        self.preprocessed = new_parts

    def evaluate_expression(self, expression, line, state):
        """Evaluate a single expression using the given dictionaries as needed. Identify
        the line number if an error occurs.
        """

        if expression:
            try:
                return eval(expression, state.global_dict, state.local_dicts[-1])
            except Exception as err:
                message = f'{type(err).__name__}({err}) at line {line}'
                raise type(err)(message) from err     # pass the exception forward

        # An empty expression is just a "$" followed by another "$"
        else:
            return '$'      # "$$" maps to "$"

    def execute_body(self, state):
        """Generate the label text defined by this body, using the given dictionaries to
        fill in the blanks. The content is returned as a deque of strings, which are to be
        joined upon completion to create the content of the label.
        """

        results = deque()
        for k, item in enumerate(self.preprocessed):

            # Even-numbered items are literal text
            if k % 2 == 0:
                results.append(item)

            # Odd-numbered items are expressions
            else:
                (expression, name, line) = item
                try:
                    value = self.evaluate_expression(expression, line, state)
                except Exception as err:
                    if state.raise_exceptions:
                        raise
                    _LOGGER.exception(err, state.label_path)
                    value = f'[[[{err}]]]'  # include the error text inside the label

                if name:
                    state.local_dicts[-1][name] = value

                # Format a float without unnecessary trailing zeros
                if isinstance(value, float):
                    value = _PdsBlock._pretty_truncate(value)
                else:
                    # Otherwise, just convert to string
                    value = str(value)

                # Escape
                if self.template.xml:
                    if value.startswith(_NOESCAPE_FLAG):
                        value = value[len(_NOESCAPE_FLAG):]
                    else:
                        value = escape(value)

                results.append(value)

        return results

    def execute(self, state):
        """Evaluate this block of label text, using the dictionaries to fill in the
        blanks. The content is returned as a deque of strings, to be joined upon
        completion to create the label content.

        This base class method implements the default procedure, which is to execute the
        body plus any sub-blocks exactly once. It is overridden for $FOR and $IF blocks.
        The execute methods write all of their error messages to the logger rather than
        raising exceptions.
        """

        results = self.execute_body(state)

        for block in self.sub_blocks:
            results += block.execute(state)

        return results

    ######################################################################################
    # Utility
    ######################################################################################

    # Modify a number if it contains ten 0's or 9's in a row, followed by other digits
    _ZEROS = re.compile(r'(.*[.1-9])0{10,99}[1-9]\d*')
    _NINES = re.compile(r'(.*\.\d+9{10,99})[0-8]\d*')

    def _pretty_truncate(value):
        """Convert a floating-point number to a string, while suppressing any extraneous
        trailing digits by rounding to the nearest value that does not have them.

        This eliminates numbers like "1.0000000000000241" and "0.9999999999999865" in the
        label, by suppressing insignificant digits.
        """

        str_value = str(value)

        (mantissa, e, exponent) = str_value.partition('e')
        if mantissa.endswith('.0'):
            return mantissa[:-1] + e + exponent

        # Handle trailing zeros
        match = _PdsBlock._ZEROS.fullmatch(mantissa)
        if match:
            return match.group(1) + e + exponent

        # Check for trailing nines
        match = _PdsBlock._NINES.fullmatch(mantissa)
        if not match:
            # Value looks OK; return as is
            return str_value

        # Replace every digit in the mantissa with a zero
        # This creates an string expression equal to zero, but using the exact same
        # format, including sign.
        offset_str = match.group(1)
        for c in '123456789':       # replace non-zero digits with zeros
            offset_str = offset_str.replace(c, '0')

        # Now replace the last digit with "1"
        # This is an offset (positive or negative) to zero out the trailing digits
        offset_str = offset_str[:-1] + '1'      # replace the last digit with "1"

        # Apply the offset and return
        value = float(match.group(1)) + float(offset_str)
        return str(value).rstrip('0') + e + exponent


################################################

class _PdsOnceBlock(_PdsBlock):
    """A block of text to be included once. This applies to a literal $ONCE header, and
    also to $END_FOR, $END_IF, and $END_NOTE headers."""

    WORD = r' *([A-Za-z_]\w*) *'
    PATTERN = re.compile(r'\(' + WORD + r'=([^=].*)\)')

    def __init__(self, sections, template):
        """Define a block to be executed once. Pop the associated section off the stack.

        Note that the name of a properly matched $END_IF header is changed internally to
        $ONCE-$END_IF during template initialization. Also, the name of a properly matched
        $END_FOR is changed to $ONCE-$END_FOR during template initialization, and
        $END_NOTE is changed to $ONCE-$END_NOTE. This code must strip away the $ONCE-
        prefix.
        """

        (header, arg, line, body) = sections.popleft()
        self.header = header.replace('$ONCE-', '')
        self.arg = arg
        self.name = ''
        self.line = line
        self.body = body
        self.preprocess_body()
        self.sub_blocks = deque()
        self.template = template

        # Pop one entry off the local dictionary stack at the end of IF and FOR loops
        self.pop_local_dict = header in ('$ONCE-$END_FOR', '$ONCE-$END_IF')

        match = _PdsOnceBlock.PATTERN.fullmatch(arg)
        if match:
            (self.name, self.arg) = match.groups()

        if header.startswith('$ONCE-') and arg:  # pragma: no coverage
            # This can't happen in the current code because IF, FOR, and NOTE all
            # ignore the arg that's present in the template and pass in '' instead
            raise TemplateError(f'extraneous argument for {self.header} at line {line}')

    def execute(self, state):
        """Evaluate this block of label text, using the dictionaries to fill in the
        blanks. The content is returned as a deque of strings, to be joined upon
        completion to create the label content.
        """

        # Pop the local dictionary stack if necessary
        if self.pop_local_dict:
            state.local_dicts.pop()

        # Define the local variable if necessary
        if self.arg:
            try:
                result = self.evaluate_expression(self.arg, self.line, state)
            except Exception as err:
                if state.raise_exceptions:
                    raise
                _LOGGER.exception(err, state.label_path)
                return deque([f'[[[{err}]]]'])  # include the error message inside label

            # Write new values into the local dictionary, not a copy
            state.local_dicts[-1][self.name] = result

        # Execute the default procedure, which is to include the body and any sub-blocks
        # exactly once
        return _PdsBlock.execute(self, state)


################################################

class _PdsNoteBlock(_PdsBlock):
    """A block of text between $NOTE and $END_NOTE, not to be included."""

    def __init__(self, sections, template):
        """Define a block to be executed zero times. Pop the associated section off the
        stack.
        """

        (header, arg, line, body) = sections.popleft()
        self.header = header
        self.arg = arg
        self.line = line
        self.body = body
        self.preprocess_body()
        self.sub_blocks = deque()
        self.template = template

        if arg:
            raise TemplateError(f'extraneous argument for {self.header} at line {line}')

        # Save internal sub-blocks until the $END_NOTE is found
        self.sub_blocks = deque()
        while sections and sections[0].header != '$END_NOTE':
            self.sub_blocks.append(_PdsBlock.new_block(sections, template))

        if not sections:
            raise TemplateError(f'unterminated {header} block starting at line {line}')

        # Handle the matching $END_NOTE section as $ONCE
        (header, arg, line, body) = sections[0]
        sections[0] = _Section('$ONCE-' + header, '', line, body)

    def execute(self, state):
        """Evaluate this block of label text, using the dictionaries to fill in the
        blanks. The content is returned as a deque of strings, to be joined upon
        completion to create the label content.
     """

        return deque()


################################################

class _PdsForBlock(_PdsBlock):
    """A block of text preceded by $FOR. It is to be evaluated zero or more times, by
    iterating through the argument.
    """

    # These patterns match one, two, or three variable names, followed by "=", to be used
    # as temporary variables inside this section of the label
    WORD = r' *([A-Za-z_]\w*) *'
    PATTERN1 = re.compile(r'\(' + WORD + r'=([^=].*)\)')
    PATTERN2 = re.compile(r'\(' + WORD + ',' + WORD + r'=([^=].*)\)')
    PATTERN3 = re.compile(r'\(' + WORD + ',' + WORD + ',' + WORD + r'=([^=].*)\)')

    def __init__(self, sections, template):
        (header, arg, line, body) = sections.popleft()
        self.header = header
        self.line = line
        self.body = body
        self.preprocess_body()
        self.template = template

        # Interpret arg as (value=expression), (value,index=expression), etc.
        if not arg:
            raise TemplateError(f'missing argument for {header} at line {line}')

        self.value = 'VALUE'
        self.index = 'INDEX'
        self.length = 'LENGTH'
        self.arg = arg

        for pattern in (_PdsForBlock.PATTERN1, _PdsForBlock.PATTERN2,
                        _PdsForBlock.PATTERN3):
            match = pattern.fullmatch(arg)
            if match:
                groups = match.groups()
                self.arg = groups[-1]
                self.value = groups[0]
                if len(groups) > 2:
                    self.index = groups[1]
                if len(groups) > 3:
                    self.length = groups[2]
                break

        # Save internal sub-blocks until the $END_FOR is found
        self.sub_blocks = deque()
        while sections and sections[0].header != '$END_FOR':
            self.sub_blocks.append(_PdsBlock.new_block(sections, template))

        if not sections:
            raise TemplateError(f'unterminated {header} block starting at line {line}')

        # Handle the matching $END_FOR section as $ONCE
        (header, arg, line, body) = sections[0]
        sections[0] = _Section('$ONCE-' + header, '', line, body)

    def execute(self, state):
        """Evaluate this block of label text, using the dictionaries to fill in the
        blanks. The content is returned as a deque of strings, to be joined upon
        completion.
        """

        try:
            iterator = self.evaluate_expression(self.arg, self.line, state)
        except Exception as err:
            if state.raise_exceptions:
                raise
            _LOGGER.exception(err, state.label_path)
            return deque([f'[[[{err}]]]'])  # include the error message inside the label

        # Create a new local dictionary
        state.local_dicts.append(state.local_dicts[-1].copy())

        results = deque()
        iterator = list(iterator)
        state.local_dicts[-1][self.length] = len(iterator)
        for k, item in enumerate(iterator):
            state.local_dicts[-1][self.value] = item
            state.local_dicts[-1][self.index] = k
            results += _PdsBlock.execute(self, state)

        return results


################################################

class _PdsIfBlock(_PdsBlock):
    """A block of text to be included if the argument evaluates to True, either $IF or
    $ELSE_IF.
    """

    WORD = r' *([A-Za-z_]\w*) *'
    PATTERN = re.compile(r'\(' + WORD + r'=([^=].*)\)')

    def __init__(self, sections, template):
        (header, arg, line, body) = sections.popleft()
        self.header = header
        self.arg = arg
        self.name = ''
        self.line = line
        self.body = body
        self.preprocess_body()
        self.template = template

        if not arg:
            raise TemplateError(f'missing argument for {header} at line {line}')

        match = _PdsIfBlock.PATTERN.fullmatch(arg)
        if match:
            (self.name, self.arg) = match.groups()

        self.else_if_block = None
        self.else_block = None

        self.sub_blocks = deque()
        while sections and sections[0].header not in _PdsBlock.ELSE_HEADERS:
            self.sub_blocks.append(_PdsBlock.new_block(sections, template))

        if not sections:
            raise TemplateError(f'unterminated {header} block starting at line {line}')

        # Handle the first $ELSE_IF. It will handle more $ELSE_IFs and $ELSEs recursively.
        if sections[0].header == '$ELSE_IF':
            self.else_if_block = _PdsIfBlock(sections, template)
            return

        # Handle $ELSE
        if sections[0].header == '$ELSE':
            self.else_block = _PdsElseBlock(sections, template)
            return

        # Handle the matching $END_IF section as $ONCE
        (header, arg, line, body) = sections[0]
        sections[0] = _Section('$ONCE-' + header, '', line, body)

    def execute(self, state):
        """Evaluate this block of label text, using the dictionaries to fill in the
        blanks. The content is returned as a deque of strings, to be joined upon
        completion to be joined upon completion to create the label content.
        """

        try:
            status = self.evaluate_expression(self.arg, self.line, state)
        except Exception as err:
            if state.raise_exceptions:
                raise
            _LOGGER.exception(err, state.label_path)
            return deque([f'[[[{err}]]]'])  # include the error message inside the label

        # Create a new local dictionary for IF but not ELSE_IF
        if self.header == '$IF':
            state.local_dicts.append(state.local_dicts[-1].copy())

        if self.name:
            state.local_dicts[-1][self.name] = status

        if status:
            return _PdsBlock.execute(self, state)

        elif self.else_if_block:
            return self.else_if_block.execute(state)

        elif self.else_block:
            return self.else_block.execute(state)

        else:
            return deque()  # empty response


################################################

class _PdsElseBlock(_PdsBlock):

    def __init__(self, sections, template):
        (header, arg, line, body) = sections.popleft()
        self.header = header
        self.arg = arg
        self.line = line
        self.body = body
        self.preprocess_body()
        self.template = template

        # Save internal sub-blocks until the $END_IF is found
        self.sub_blocks = deque()
        while sections and sections[0].header != '$END_IF':
            self.sub_blocks.append(_PdsBlock.new_block(sections, template))

        if not sections:
            raise TemplateError(f'unterminated {header} block starting at line {line}')

        # Handle the matching $END_IF section as $ONCE
        (header, arg, line, body) = sections[0]
        sections[0] = _Section('$ONCE-' + header, '', line, body)

##########################################################################################
