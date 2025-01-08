##########################################################################################
# pdstemplate/_pdsblock.py
##########################################################################################
"""Class used internally during template evaluation."""

import re
from collections import deque, namedtuple
from xml.sax.saxutils import escape

from filecache import FCPath

from .utils import TemplateError, TemplateAbort, _RaisedException
from .utils import get_logger, _NOESCAPE_FLAG

# namedtuple class definition
#
# This is used to describe any subset of lines in the template containing one header and
# any label text up to the next header:
#   header  the header type, e.g., "$FOR" or "$IF" or $END_IF";
#   arg     any expression following the header, inside parentheses;
#   line    the line number of the template in which the header appears;
#   body    the text immediately following this header and up until the next header.
#
# When the template file is first read, it is described by a deque of _Section objects. If
# there is no header before the first line of the template, it is assigned a header type
# of "$ONCE().
_Section = namedtuple('_Section', ['header', 'arg', 'line', 'body'])


class _PdsBlock(object):
    """_PdsBlock is an abstract class that describes a hierarchical section of the label
    template, beginning with a header. There are individual subclasses to support these
    different types of headers:
        _PdsForBlock     for $FOR
        _PdsIfBlock      for $IF and $ELSE_IF
        _PdsElseBlock    for $ELSE
        _PdsIncludeBlock for $INCLUDE
        _PdsNoteBlock    for $NOTE
        _PdsOnceBlock    for $END_FOR, $END_IF, $END_NOTE, and any other section of the
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

    # This pattern matches a header record;
    #  groups(1) = line number; groups(2) = header; groups(3) = argument in parentheses
    _HEADER_WORDS = ['IF', 'ELSE_IF', 'ELSE', 'END_IF', 'FOR', 'END_FOR', 'ONCE', 'NOTE',
                     'END_NOTE', 'INCLUDE']

    # This regular expression splits up the content of the template at the location of
    # each header. For each match, it returns three groups: a leading line number, the
    # header word ("IF", "FOR", etc.), and text inside the parentheses, if any.
    _HEADER_PATTERN = re.compile(r'(?<![^\n]) *\$(\d+):(' + '|'.join(_HEADER_WORDS)
                                 + r')(\(.*\)|) *\n')

    # This pattern matches an internal assignment within an expression;
    # group(0) = variable name; group(1) = expression
    NAMED_PATTERN = re.compile(r' *([A-Za-z_]\w*) *=([^=].*)')
    ELSE_HEADERS = {'$ELSE_IF', '$ELSE', '$END_IF'}

    def preprocess_body(self):
        """Preprocess body text from the template by locating all of the embedded Python
        expressions and returning a list of substrings, where odd-numbered entries are the
        expressions to evaluate, along with the associated line number.
        """

        # Split at the "$"
        parts = self.body.split('$')
        if len(parts) % 2 != 1:
            line = parts[-1].partition(':')[0]
            raise TemplateAbort(f'Mismatched "$" at {self.filepath.name}:{line}')

        # Because we inserted the line number after every "$", every part except the first
        # now begins with a number followed by ":". We need to make the first item
        # consistent with the others.
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

                new_parts.append((expression, name, int(line)))

        self.preprocessed = new_parts

    def evaluate_expression(self, expression, line, state):
        """Evaluate a single expression using the state's dictionaries as needed. Identify
        the file name and line number if an error occurs.

        Parameters:
            expression (str): Expression to evaluate.
            line (int): Line number in the template starting from 1.
            state (_LabelState): State describing the label being generated.

        Returns:
            str: The evaluated expression as a string.
        """

        if expression:
            try:
                return eval(expression, state.global_dict, state.local_dicts[-1])

            # Do not pass go, do not collect $200
            except TemplateAbort:
                raise

            # This handles a call to $RAISE()
            except _RaisedException as err:
                suffix = f' at {self.filepath.name}:{line}'
                if state.raise_exceptions:
                    raise (err.exception)(err.message + suffix) from err
                get_logger().error(err.exception.__name__ + ' ' + err.message + suffix,
                                   state.label_path)
                return (f'[[[{err.exception.__name__}({err.message}){suffix}]]]')

            except Exception as err:
                # Attach the expression, file name and line number to the error message
                suffix = f' in {expression} at {self.filepath.name}:{line}'
                message = str(err) + suffix
                if state.raise_exceptions:
                    raise type(err)(message) from err

                # Log with original stacktrace
                try:
                    raise type(err)(message) from err
                except Exception as err2:
                    get_logger().exception(err2, state.label_path,
                                           more=self._more_error_info(self.line))

                # Return the content of the error message
                if isinstance(err, TemplateError):
                    return f'[[[{message}]]]'

                return f'[[[{type(err).__name__}({err})' + suffix + ']]]'

        # An empty expression is just a "$" followed by another "$"
        else:
            return '$'      # "$$" maps to "$"

    @staticmethod
    def _is_error(value):
        """True if the value is the text of an error message."""

        if not isinstance(value, str):
            return False

        return value.startswith('[[[') and value.endswith(']]]')

    def execute_body(self, state):
        """Generate the label text defined by this body, using the state's dictionaries to
        fill in the blanks. The content is returned as a deque of strings, which are to be
        joined upon completion to create the label.

        Parameters:
            state (_LabelState): State describing the label being generated.

        Returns:
            deque[str]: Deque of strings to concatenate.
        """

        results = deque()
        for k, item in enumerate(self.preprocessed):

            # Even-numbered items are literal text
            if k % 2 == 0:
                results.append(item)

            # Odd-numbered items are expressions
            else:
                (expression, name, line) = item
                value = self.evaluate_expression(expression, line, state)

                if name and not _PdsBlock._is_error(value):
                    state.local_dicts[-1][name] = value

                # Format a float without unnecessary trailing zeros
                if isinstance(value, float):
                    value = _PdsBlock._pretty_truncate(value, state.template.upper_e)
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
        blanks.

        This base class method implements the default procedure, which is to execute the
        body plus any sub-blocks exactly once. It is overridden for $FOR and $IF blocks.

        Parameters:
            state (_LabelState): State describing the label being generated.

        Returns:
            deque[str]: Deque of strings to concatenate.
        """

        results = self.execute_body(state)

        for block in self.sub_blocks:
            results += block.execute(state)

        return results

    def _more_error_info(self, line):
        """The error info text to include following an exception.

        Parameters:
            line (int): Line number in template content, starting from 1.

        Returns:
            str: If template._include_more_error_info, this is the selected line of the
                template's content; otherwise, an empty string.
        """

        if not self.template._include_more_error_info:
            return ''

        recs = self.template.content.split('\n')
        return f'    {line}: ' + recs[line-1]

    ######################################################################################
    # "Compiler" from a list of template records into a deque of _PdsBlock objects
    ######################################################################################

    @staticmethod
    def process_headers(content, template, filepath=None):
        """Process the template content into a deque of _PdsBlock objects, one for each
        header found.

        Parameters:
            content (str): The entire content of the template as a single string with <LF>
                line terminators.
            template (PdsTemplate): The PdsTemplate object.
            filepath (str, Path, or FCPath, optional): Path to the source file. If not
                specified, template.template_path is used.

        Returns:
            deque[_PdsBlock]: A deque of _PdsBlock objects representing the entire content
                of the template.
        """

        # Strip inline comments
        content = _PdsBlock._strip_inline_comments(content)

        # We need to save the line number in which each expression appears so that error
        # messages can be informative. To handle this, we temporarily write the line
        # number followed by a colon after each "$" found in the template.

        # Insert line numbers after each "$"
        records = content.split('\n')
        numbered = [rec.rstrip().replace('$', f'${k+1}:')
                    for k, rec in enumerate(records)]
        content = '\n'.join(numbered)

        # Split based on headers. The entire template is split into substrings...
        # 0: text before the first header, if any
        # 1: line number of the header
        # 2: header word ("IF", "FOR", etc.)
        # 3: text between parentheses in the header line
        # 4: template text from here to the next header line
        # 5: line number of the next header
        # etc.
        parts = _PdsBlock._HEADER_PATTERN.split(content)

        # parts[0] is '' if the file begins with a header, or else it is the body text
        # before the first header. The first header is always described by parts[1:4];
        # every part indexed 4*N + 1 is a line number.

        # Create a list of (header, arg, line, body) tuples, skipping parts[0]
        sections = [_Section('$'+h, a, int(l), b) for (l, h, a, b)
                    in zip(parts[1::4], parts[2::4], parts[3::4], parts[4::4])]

        # Convert to deque and prepend the leading body text if necessary
        sections = deque(sections)
        if parts[0]:
            sections.appendleft(_Section('$ONCE', '', 0, parts[0]))

        # Convert the sections into a list of execution blocks
        # Each call to _PdsBlock.new_block pops one or more items off top of the deque;
        # the loop repeats until no sections are left.
        blocks = deque()
        while sections:
            # Each call to _PdsBlock.new_block takes as many sections off the front of the
            # deque as it needs to in order to be syntactically complete. For example, if
            # the section at the top is "IF", it will remove the subsequent "ELSE_IF" and
            # "ELSE" sections from the deque. It will return when it encounters the
            # associated "END_IF". Calls are recursive, so this handles nesting correctly.
            blocks.append(_PdsBlock.new_block(sections, template, filepath=filepath))

        return blocks

    @staticmethod
    def new_block(sections, template, filepath=None):
        """Construct an _PdsBlock subclass based on a deque of _Section tuples (header,
        arg, line,  body).

        Pop as many _Section tuples off the top of the deque as are necessary to complete
        the block and any of its internal blocks, recursively.

        Parameters:
            sections (deque[_Section]): _Section objects containing template content.
            template (PdsTemplate): The PdsTemplate object..

        Returns:
            deque[_PdsBlock]: A deque of _PdsBlock objects representing the given sections
                of the template.
        """

        filepath = FCPath(filepath) if filepath else template.template_path

        (header, arg, line, body) = sections[0]
        if header.startswith('$ONCE'):
            return _PdsOnceBlock(sections, template, filepath=filepath)
        if header.startswith('$NOTE'):
            return _PdsNoteBlock(sections, template, filepath=filepath)
        if header == '$FOR':
            return _PdsForBlock(sections, template, filepath=filepath)
        if header == '$IF':
            return _PdsIfBlock(sections, template, filepath=filepath)
        if header == '$INCLUDE':
            return _PdsIncludeBlock(sections, template, filepath=filepath)

        if header == '$END_FOR':
            raise TemplateAbort(f'$END_FOR without matching $FOR at '
                                f'{filepath.name}:{line}')
        if header == '$END_NOTE':
            raise TemplateAbort(f'$END_NOTE without matching $NOTE at '
                                f'{filepath.name}:{line}')
        if header in _PdsBlock.ELSE_HEADERS:    # pragma: no coverage - can't get here
            raise TemplateAbort(f'{header} without matching $IF at '
                                f'{filepath.name}:{line}')

        raise TemplateAbort(f'Unrecognized header {header}({arg}) at '
                            f'{filepath.name}:{line}')  # pragma: no coverage

    @staticmethod
    def _strip_inline_comments(content):
        """Strip inline comments from the given content."""

        lines = content.split('\n')
        comment = '$NOTE:'
        newlines = []
        for line in lines:
            parts = line.partition(comment)
            if parts[1]:                # if $NOTE found
                if parts[0] == '':      # remove entire line
                    continue
                newlines.append(parts[0].rstrip())
            else:
                newlines.append(line)

        return '\n'.join(newlines)

    ######################################################################################
    # Utility
    ######################################################################################

    # Modify a number if it contains ten 0's or 9's in a row, followed by other digits
    _ZEROS = re.compile(r'(.*[.1-9])0{10,99}[1-9]\d*')
    _NINES = re.compile(r'(.*\.\d+9{10,99})[0-8]\d*')

    def _pretty_truncate(value, upper_e):
        """Convert a floating-point number to a string, while suppressing any extraneous
        trailing digits by rounding to the nearest value that does not have them.

        This eliminates numbers like "1.0000000000000241" and "0.9999999999999865" in the
        label, by suppressing insignificant digits.

        Parameters:
            value (float): Value to format as a string.
            upper_e (bool): True to use uppercase "E" in exponential notation.

        Returns:
            str: Formatted string.
        """

        str_value = str(value)

        (mantissa, e, exponent) = str_value.partition('e')
        if upper_e:
            e = e.upper()

        if mantissa.endswith('.0'):
            return mantissa[:-1] + e + exponent

        if '.' not in mantissa:         # always a decimal point in the mantissa
            return mantissa + '.' + e + exponent

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

    def __init__(self, sections, template, filepath=None):
        """Define a block to be executed once. Pop the associated sections off the stack.

        Parameters:
            sections (deque[_Section]):
                The remainder of the template's content. This constructor pops as many
                sections off the top of the deque as are needed to complete this block.
            template (PdsTemplate):
                The object being converted into _PdsBlocks.
            filepath (str, Path, or FCPath, optional):
                The file containing this $ONCE block; usually the file path of `template`
                but it could be that of an $INCLUDE file.

        Raises:
            TemplateAbort: Irrecoverable syntax error.

        Note:
            The name of a properly matched $END_IF header is changed internally to
            $ONCE-$END_IF during template initialization. Also, the name of a properly
            matched $END_FOR is changed to $ONCE-$END_FOR during template initialization,
            and $END_NOTE is changed to $ONCE-$END_NOTE. This code must strip away the
            $ONCE- prefix.
        """

        (header, arg, line, body) = sections.popleft()
        self.header = header.replace('$ONCE-', '')
        self.arg = arg
        self.name = ''
        self.line = line
        self.filepath = FCPath(filepath) if filepath else template.template_path
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
            raise TemplateAbort(f'Extraneous argument for {self.header} at '
                                f'{self.filepath.name}:{line}')

    def execute(self, state):
        """Evaluate this block of $ONCE text unconditionally.

        Use the dictionaries to evaluate any embedded expressions.

        Parameters:
            state (_LabelState): State describing the label being generated.

        Returns:
            deque[str]: Deque of strings to concatenate upon completion.
        """

        results = deque()

        # Pop the local dictionary stack if necessary
        if self.pop_local_dict:
            state.local_dicts.pop()

        # Define the local variable if necessary
        if self.arg:
            value = self.evaluate_expression(self.arg, self.line, state)
            if _PdsBlock._is_error(value):
                return deque([value])

            # Write new values into the local dictionary, not a copy
            if self.name:
                state.local_dicts[-1][self.name] = value

        # Include the body and any sub-blocks exactly once
        results += _PdsBlock.execute(self, state)
        return results


################################################

class _PdsNoteBlock(_PdsBlock):
    """A block of text between $NOTE and $END_NOTE, not to be included."""

    def __init__(self, sections, template, filepath=None):
        """Define a block to be executed zero times. Pop the associated sections off the
        stack.

        Parameters:
            sections (deque[_Section]):
                The remainder of the template's content. This constructor pops as many
                sections off the top of the deque as are needed to complete this block.
            template (PdsTemplate):
                The object being converted into _PdsBlocks.
            filepath (str, Path, or FCPath, optional):
                The file containing this $ONCE block; usually the file path of `template`
                but it could be that of an $INCLUDE file.

        Raises:
            TemplateAbort: Irrecoverable syntax error.
        """

        (header, arg, line, body) = sections.popleft()
        self.header = header
        self.arg = arg
        self.line = line
        self.filepath = FCPath(filepath) if filepath else template.template_path
        self.body = body
        self.preprocess_body()
        self.sub_blocks = deque()
        self.template = template

        if arg:
            raise TemplateAbort(f'Extraneous argument for {self.header} at '
                                f'{self.filepath.name}:{line}')

        # Save internal sub-blocks until the $END_NOTE is found
        self.sub_blocks = deque()
        while sections and sections[0].header != '$END_NOTE':
            self.sub_blocks.append(_PdsBlock.new_block(sections, template, self.filepath))

        if not sections:
            raise TemplateAbort(f'Unterminated {header} block starting at '
                                f'{self.filepath.name}:{line}')

        # Handle the matching $END_NOTE section as $ONCE
        (header, arg, line, body) = sections[0]
        sections[0] = _Section('$ONCE-' + header, '', line, body)

    def execute(self, state):
        """Ignore this block of $NOTE text.

        Use the dictionaries to evaluate any embedded expressions.

        Parameters:
            state (_LabelState): State describing the label being generated.

        Returns:
            deque[str]: Deque of strings to concatenate upon completion.
        """

        return deque()


################################################

class _PdsForBlock(_PdsBlock):
    """A block of text between $FOR and $END_FOR. It is to be evaluated zero or more
    times, by iterating through the argument.
    """

    # These patterns match one, two, or three variable names, followed by "=", to be used
    # as temporary variables inside this section of the label
    WORD = r' *([A-Za-z_]\w*) *'
    PATTERN1 = re.compile(r'\(' + WORD + r'=([^=].*)\)')
    PATTERN2 = re.compile(r'\(' + WORD + ',' + WORD + r'=([^=].*)\)')
    PATTERN3 = re.compile(r'\(' + WORD + ',' + WORD + ',' + WORD + r'=([^=].*)\)')

    def __init__(self, sections, template, filepath=None):
        """Define a block to be executed inside a loop. Pop the associated section off the
        stack.

        Parameters:
            sections (deque[_Section]):
                The remainder of the template's content. This constructor pops as many
                sections off the top of the deque as are needed to complete this block.
            template (PdsTemplate):
                The object being converted into _PdsBlocks.
            filepath (str, Path, or FCPath, optional):
                The file containing this $ONCE block; usually the file path of `template`
                but it could be that of an $INCLUDE file.

        Raises:
            TemplateAbort: Irrecoverable syntax error.
        """

        (header, arg, line, body) = sections.popleft()
        self.header = header
        self.line = line
        self.filepath = FCPath(filepath) if filepath else template.template_path
        self.body = body
        self.preprocess_body()
        self.template = template

        # Interpret arg as (value=expression), (value,index=expression), etc.
        if not arg:
            raise TemplateAbort(f'Missing argument for {header} at '
                                f'{self.filepath.name}:{line}')

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
            self.sub_blocks.append(_PdsBlock.new_block(sections, template, self.filepath))

        if not sections:
            raise TemplateAbort(f'Unterminated {header} block starting at '
                                f'{self.filepath.name}:{line}')

        # Handle the matching $END_FOR section as $ONCE
        (header, arg, line, body) = sections[0]
        sections[0] = _Section('$ONCE-' + header, '', line, body)

    def execute(self, state):
        """If the argument evaluates to True, execute this block of label text.

        Use the dictionaries to evaluate any embedded expressions.

        Parameters:
            state (_LabelState): State describing the label being generated.

        Returns:
            deque[str]: Deque of strings to concatenate upon completion.
        """

        iterator = self.evaluate_expression(self.arg, self.line, state)
        if _PdsBlock._is_error(iterator):
            return deque([iterator])    # include the error text inside the label

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
    """A block of text beginning with $IF or $ELSE_IF and continuing to the next $ELSE_IF,
    $ELSE, or $END_IF.

    Note that subsequent $ELSE_IF sections are handled recursively.
    """

    WORD = r' *([A-Za-z_]\w*) *'
    PATTERN = re.compile(r'\(' + WORD + r'=([^=].*)\)')

    def __init__(self, sections, template, filepath=None):
        """A block to be executed conditionally.

        Parameters:
            sections (deque[_Section]):
                The remainder of the template's content. This constructor pops as many
                sections off the top of the deque as are needed to complete this block.
            template (PdsTemplate):
                The object being converted into _PdsBlocks.
            filepath (str, Path, or FCPath, optional):
                The file containing this $ONCE block; usually the file path of `template`
                but it could be that of an $INCLUDE file.

        Raises:
            TemplateAbort: Irrecoverable syntax error.
        """

        (header, arg, line, body) = sections.popleft()
        self.header = header
        self.arg = arg
        self.name = ''
        self.line = line
        self.filepath = FCPath(filepath) if filepath else template.template_path
        self.body = body
        self.preprocess_body()
        self.template = template

        if not arg:
            raise TemplateAbort(f'Missing argument for {header} at '
                                f'{self.filepath.name}:{line}')

        match = _PdsIfBlock.PATTERN.fullmatch(arg)
        if match:
            (self.name, self.arg) = match.groups()

        self.else_if_block = None
        self.else_block = None

        self.sub_blocks = deque()
        while sections and sections[0].header not in _PdsBlock.ELSE_HEADERS:
            self.sub_blocks.append(_PdsBlock.new_block(sections, template, self.filepath))

        if not sections:
            raise TemplateAbort(f'Unterminated {header} block starting at '
                                f'{self.filepath.name}:{line}')

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
        """If the argument evaluates to True, execute this block of label text. Otherwise,
        continue with the next $ELSE_IF or $ELSE block.

        Use the dictionaries to evaluate any embedded expressions.

        Parameters:
            state (_LabelState): State describing the label being generated.

        Returns:
            deque[str]: Deque of strings to concatenate upon completion.
        """

        status = self.evaluate_expression(self.arg, self.line, state)
        if _PdsBlock._is_error(status):
            return deque([status])      # include the error text inside the label

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

    def __init__(self, sections, template, filepath=None):
        """A block to be executed only if all preceding $IF and $ELSE_IF blocks have not
        executed.

        Parameters:
            sections (deque[_Section]):
                The remainder of the template's content. This constructor pops as many
                sections off the top of the deque as are needed to complete this block.
            template (PdsTemplate):
                The object being converted into _PdsBlocks.
            filepath (str, Path, or FCPath, optional):
                The file containing this $ONCE block; usually the file path of `template`
                but it could be that of an $INCLUDE file.

        Raises:
            TemplateAbort: Irrecoverable syntax error.
        """

        (header, arg, line, body) = sections.popleft()
        self.header = header
        self.arg = arg
        self.line = line
        self.filepath = FCPath(filepath) if filepath else template.template_path
        self.body = body
        self.preprocess_body()
        self.template = template

        # Save internal sub-blocks until the $END_IF is found
        self.sub_blocks = deque()
        while sections and sections[0].header != '$END_IF':
            self.sub_blocks.append(_PdsBlock.new_block(sections, template, self.filepath))

        if not sections:
            raise TemplateAbort(f'Unterminated {header} block starting at '
                                f'{self.filepath.name}:{line}')

        # Handle the matching $END_IF section as $ONCE
        (header, arg, line, body) = sections[0]
        sections[0] = _Section('$ONCE-' + header, '', line, body)

################################################

class _PdsIncludeBlock(_PdsBlock):
    """A reference to an external file to be included at this location of the template.

    It is followed by a standard block of text to be executed once.
    """

    def __init__(self, sections, template, filepath=None):
        """A directive to include text from an specified file and then compile and
        execute it.

        Parameters:
            sections (deque[_Section]):
                The remainder of the template's content. This constructor pops as many
                sections off the top of the deque as are needed to complete this block.
            template (PdsTemplate):
                The object being converted into _PdsBlocks.
            filepath (str, Path, or FCPath, optional):
                The file containing this $ONCE block; usually the file path of `template`
                but it could be that of an $INCLUDE file.

        Raises:
            TemplateAbort: Irrecoverable syntax error.
        """

        (header, arg, line, body) = sections.popleft()
        self.header = header
        self.arg = arg
        self.name = ''
        self.line = line
        self.filepath = FCPath(filepath) if filepath else template.template_path
        self.body = body
        self.preprocess_body()
        self.sub_blocks = deque()
        self.template = template

        if not arg:
            raise TemplateAbort(f'Missing argument for {header} at '
                                f'{self.filepath.name}:{line}')

    def execute(self, state):
        """Read, compile, and execute the specified file, followed by the remaining body
        text.

        Use the dictionaries to evaluate any embedded expressions.

        Parameters:
            state (_LabelState): State describing the label being generated.

        Returns:
            deque[str]: Deque of strings to concatenate upon completion.
        """

        results = deque()

        # Interpret the file name
        filename = self.evaluate_expression(self.arg, self.line, state)
        if _PdsBlock._is_error(filename):
            return deque(['$INCLUDE(', filename, ')\n'])  # put error text into the label

        # Read the file
        try:
            content = _PdsIncludeBlock.get_content(filename,
                                                   self.template._include_dirs())
        except Exception as err:
            message = f'{repr(err)} in $INCLUDE at {state.filepath.name}:{self.line}'
            if state.raise_exceptions:
                raise type(err)(message) from err
            try:
                raise type(err)(message) from err
            except Exception as err:
                get_logger().exception(err, state.label_path,
                                       more=self._more_error_info(self.line))
            return deque(['$INCLUDE(', filename, ')\n'])  # put error text into the label

        # Compile and execute the included template
        blocks = _PdsBlock.process_headers(content, self.template, filepath=self.filepath)
        for block in blocks:
            results += block.execute(state)

        # Include the body and any sub-blocks afterward
        results += _PdsBlock.execute(self, state)
        return results

    @staticmethod
    def get_content(filename, include_dirs):
        """The content of the specified include file.

        Parameters:
            filename (str, Path, or FCPath): The name or path to the file to include.
            include_dirs (list[Path or FCPath): Ordered list of directories in which to
                look for the named file.

        Returns:
            str: The content of the file as a single string containing "\n" line
                terminators.

        Raises:
            FileNotFoundError: If the file is not found.
            OSError: Any subclass of OSError explaining why the file could not be read.
        """

        # First try to read the file directly
        filepath = FCPath(filename)
        try:
            return filepath.read_text()     # convert <CR><LF> to <LF>
        except FileNotFoundError:
            pass

        # Try each directory in turn
        for dir in include_dirs:
            try:
                return (dir / filename).read_text()
            except (FileNotFoundError, NotImplementedError):
                pass

        # On failure, re-raise the first exception
        return filepath.read_text()

##########################################################################################
