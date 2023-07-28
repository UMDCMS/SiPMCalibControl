"""
@defgroup Logging Logging

@details Instead of C/C++'s `printf/std::cout` method and the python `print`
method, all program outputs should used the python [`logging`][python-logging]
module to allow for a unified method for processing output streams, as well as
single call allow for post-processing into persistent log files either for
debugging or for documentation construction, or even later for the construction
of GUI display elements.

On the C++ side, all `printf` or `std::cout` statements should be replaced by
the various `printx` method provided in the logger.hpp file, with the
appropriate logging levels. We will use the facilities provided in the
`pybind11` to expose the python logging module to the C++ functions.

On the python side, various functions and classes will be provided for the
processing and formatting of the logging strings, as well as some niceties for
common string formatting routines.


[python-logging]: https://docs.python.org/3/library/logging.html


Python helper function for helping with logging string formatting. This includes
ASCII color code injection. And well as additional formatting to be performed
for logging. As all outputs should be logged through python logging, we
introduce more logging levels to better track all information.

@{
"""

import logging
import logging.handlers
import re
import os
import copy
import traceback
import time
import collections
import textwrap
import json
import argparse
import numpy as np

##
# @{
# @brief Defining the custom level This should match what is defined the src/logging.cc
logging.CRITICAL = 50

##
# @details After this print out level is requested, the program should probably
# be halted
logging.ERROR = 40

##
# @details After this print out level is requested, the program should continue,
# but messages will have a more visible indicator to help indicate to the
# operator that something might be wrong.
logging.WARNING = 30

##
# @details Similar level as WARNING, by we set traceback print out to the
# separate level so that this level can be muted separately as traceback print
# out can be very verbose.
logging.TRACEBACK = 25

##
# @details General routine information printout
logging.INFO = 20

##
# @details Similar level as INFO, except this is specialized for operation
# interaction message (like action prompts). Mainly separated out for additional
# output format parsing.
logging.INT_INFO = 14

##
# @details Generic debugging information messages. Notice that this is the
# defaults CLI screen output level.
logging.DEBUG = 10

##
# @details Similar level as DEBUG, except this is specialized for hardware
# information dumps.
logging.HW_DEBUG = 6

##
# @details "Output" level Used for command history tracing.
logging.CMD_HIST = 5

##
# @details "Output" level used for continuous monitoring stream.
logging.MONITOR = 4  # For continuous monitoring stream

logging.NOTSET = 0
## @}

##
# @brief Integer to string look up table for logging levels.
#
# @details Getting all string and integer representation of logging levels
# available. Look up from integer value is typically more needed, as the inverse
# can be done with the in-built getattr method in python.
__all_logging_levels__ = {
    val: k
    for k, val in logging.__dict__.items()
    if k.upper() == k and type(val) == int
}


def make_color_text(message: str, colorcode: int) -> str:
  """
  @ingroup Logging

  @brief Adding ASCII color headers around message string. More details
  regarding the ASCII code for string colors can be found [here][ascii].

  [ascii]: https://en.wikipedia.org/wiki/ANSI_escape_code
  """
  return f"\033[1;{colorcode:d}m{message}\033[0m"


def RED(message: str) -> str:
  return make_color_text(message, 31)


def GREEN(message: str) -> str:
  return make_color_text(message, 32)


def YELLOW(message: str) -> str:
  return make_color_text(message, 33)


def CYAN(message: str) -> str:
  return make_color_text(message, 36)


def NOCOLOR(message: str) -> str:
  return message


def oneline_string(text: str) -> str:
  """
  @brief Simplifying multiline text in python to a single line text in python,
  which also removes the additional whitespaces at the beginning of lines.
  """
  return ' '.join(text.split())


def wrapped_string(text: str, width: int = 120) -> str:
  """
  @brief Automatically folding the message to a block of text of a specific
  width.

  @details This operation is performed in 4 steps:

  - remove all explicit new-line characters  '\n' from the input string. This is
    to ensure that multi-line string define in python using the triple-quote
    notation will be displayed in the common format regardless of the
    indentation level of the multiline string
  - The python `textwrap` method is called to break the long string into chunks.
  - The specified line break position with the HTML-style `<br>` tags are
    replaced with the command-line new-line character for all the chunked
    strings.
  - All chunks are joined back together with the python string join method.
  """
  text = oneline_string(text)
  lines = textwrap.wrap(text, width=width, break_long_words=False)
  lines = [x.replace('<br>', '\n') for x in lines]
  return '\n'.join(lines)


def record_timestamp(record):
  """Standard time format for logging record: `YYYY-mm-dd@HH:MM:SS` """
  return time.strftime('%Y-%m-%d@%H:%M:%S', time.localtime(record.created))


def remove_newline(s):
  """
  Removing new-line characters with HTML-style <br> to ensure line-based
  operations does not know the mark-up tags
  """
  return s.replace('\n', '<br>')


class FIFOHandler(logging.Handler):
  """
  @brief Class for Handling logging records in memory using a first-in-first-out
  scheme.

  @details As the action of flushing/clearing the log information would only be
  performed at the explicit request of the operator, here we provide a class
  that stores the logging records in a first-in-first-out list, so that logging
  information can be retrieve for later use. The user should specify a suitable
  maximum capacity, that ensures that memory usage of the record list does not
  get out-of-hand during operations, while still retaining all useful
  information between log clearing (typically performed when loading a new
  tileboard into the system).
  """
  _registered_extras_ = ['table']

  def __init__(self, capacity, level=logging.NOTSET):
    """
    @brief Creating the FIFO object using the python deque module

    @details By default, all possible logging levels would be stored in memory.
    Provide a suitable logging level if this behavior is not desired.
    """
    super().__init__(level=level)
    self.record_list = collections.deque([], maxlen=capacity)

  def emit(self, record):
    """Main logging.Handler method from the python module that needs
    overloading"""
    self.record_list.append(record)

  def record_to_dict(self, record):
    """
    @brief Transforming a logging record to a python dictionary

    @details We will not keep all internal information here, just the the
    following entries of the record:

    - The `time` of when the record was produced. Note that this field is be
      returned as a human readable string format using the
      cmod.fmt.record_timestamp method.
    - The `name` of what logger was used to generate the request.
    - The `level` of the record instance (in string format)
    - The message string attached to the record.
    - The `arg` objects passed to the logging generation.
    - Additional field attached via the `extra` method. Only field listed in the
      FIFOHandler._registered_extra_ will be included here.
    """
    ret_dict = {
        'time': record_timestamp(record),
        'name': record.name,
        'level': __all_logging_levels__[record.levelno],
        'msg': remove_newline(record.msg),
        'args': record.args,
    }
    for extra_keys in self._registered_extras_:
      if hasattr(record, extra_keys):
        ret_dict[extra_keys] = getattr(record, extra_keys)
    return ret_dict

  def record_to_line(self, record) -> str:
    """
    @brief Returning a record instance as a single line of text.

    @details This method is build on the record_to_dict method, with each of the
    entires in the dictionary be column separated by triple colons. This is to
    make the final output easier to process via line-based command line tools
    that might be used.
    """
    rec_dict = self.record_to_dict(record)
    # Base information line
    line = '{time}:::{name}:::{level}:::{msg}'.format(**rec_dict)
    if rec_dict['args']:  # For non empty arguments
      line += f':::{remove_newline(str(rec_dict["args"]))}'
    extra_dict = {
        k: v
        for k, v in rec_dict.items()
        if k in self._registered_extras_
    }
    if extra_dict:
      line += f':::{remove_newline(str(extra_dict))}'
    return line

  def dump_lines(self, file_obj, exclude: list[int]):
    """
    @brief Write records to a file in line-based format

    @details Given the file object with the appropriate `write` method, write
    the record contents stored in Handler objects via the line-based format. An
    additional list of integers can also be provided to explicitly exclude
    record with certain log-levels from being placed in the file.
    """
    _ = [
        file_obj.write(self.record_to_line(record) + '\n')
        for record in self.record_list
        if __all_logging_levels__[record.levelno] not in exclude
    ]

  def dump_json(self, file_obj, exclude: list[int]):
    """
    @brief Write records to a file in json-based format

    @details Given the file object with the appropriate `write` method, write
    the record contents stored in Handler objects via the json-based format. As
    "a list of dictionaries" is not JSON compatible, we have a thin wrapping
    dictionary to add additional information to the the dump request: when the
    dump request was called and which levels where excluded in the dump.
    """
    json_dict = {
        'dumptime':
        time.strftime('%Y-%m-%d@%H:%M:%S', time.localtime(time.time())),
        'excluded':
        exclude,
        'entries': [
            self.record_to_dict(record)
            for record in self.record_list
            if __all_logging_levels__[record.levelno] not in exclude
        ]
    }
    json.dump(json_dict, file_obj, indent=2)


# Custom output formatter
class CmdStreamFormatter(logging.Formatter):
  """
  @brief Given a logging.Record object, format into a string that should be
  printed on string.

  @details The nominal format would be: `[level][module] message`

  Where the level would be omitted should for level that are lower than WARNING.
  For clarity, if the message is long, then when the line wraps, it should not
  pass wrap after the text-column of the `[level][module]` part.

  For the message, because it is typically cleaner to simply have a multiline
  with jagged newline in leading spaces in the code when writing a long string,
  by default we will pass the message string through a standard white string
  reduction functions. Messages that require explicit break-lines can still be
  specified using an html style "<br>" tag.
  """
  def __init__(self, linewidth=120):
    super().__init__(style='{')
    self.linewidth = linewidth

  def make_header(self, record):
    _level_header_ = {
        logging.ERROR: RED(f'[{"ERROR":7s}]'),
        logging.WARNING: YELLOW(f'[{"WARNING":7s}]'),
        logging.TRACEBACK: YELLOW(f'[{"TRACE":7s}]'),
    }
    #Making the first prefixes
    header = _level_header_.get(record.levelno, '')
    hlen = 7 + 2 if record.levelno in _level_header_.keys() else 0

    # removing the header level logger name
    recname = '.'.join(record.name.split('.')[1:])
    header += CYAN(f'[{recname}] ')
    hlen += len(recname) + 3
    return header, hlen

  def default_message_parse(self, record):
    """Reducing the message to a block of text"""
    return wrapped_string(record.msg, self.linewidth)

  def traceback_message_parse(self, record):
    """
    Formatting of the track stack string to something easier to read.
    """
    trace_stack = traceback.TracebackException.from_exception(record.msg).stack

    def get_entries(frame_item):
      return dict(fileloc=frame_item.filename.replace(os.getenv('PWD'), '.') +
                  ':' + str(frame_item.lineno),
                  funcname=frame_item.name,
                  content=frame_item.line)

    tokens = [get_entries(frame) for frame in trace_stack]
    token_size = {
        k: max([len(item[k])
                for item in tokens])
        for k in tokens[0].keys()
    }

    def make_line(item):
      return ''.join([
          CYAN(item['fileloc'].rjust(token_size['fileloc'] + 1, ' ') + '| '),
          YELLOW(item['funcname'].ljust(token_size['funcname'] + 1, ' ') + '| '),
          item['content']
      ])

    return '\n'.join([make_line(x) for x in tokens])

  def interactive_message_parse(self, record):
    msg = record.msg  # To note make modifications!
    if hasattr(record, 'table'):
      if msg:
        msg += '\n' + self.format_table(record.table)
      else:
        msg = self.format_table(record.table)
    return msg

  def format_table(self, table):
    """
    Converting a nested list-of-list to a pleasant table string.
    """
    ncols = np.max([len(x) for x in table])
    padded_table = list([list(x) + [''] * (ncols - len(x)) for x in table])
    colwidth = np.char.str_len(padded_table)
    colwidth = np.max(colwidth, axis=0)
    lines = []
    for i in range(len(padded_table)):
      line = ''
      for j in range(ncols):
        if j == 0:
          line = GREEN(padded_table[i][j].rjust(colwidth[j] + 2))
        else:
          line += ' ' + padded_table[i][j].ljust(colwidth[j] + 1)
      lines.append(line)
    return '\n'.join(lines)

  def format(self, record):
    """
    Over riding the main format method defined in the formatter class.
    """

    _msg_parser_ = {
        logging.TRACEBACK: self.traceback_message_parse,
        logging.INT_INFO: self.interactive_message_parse
    }

    header, hlen = self.make_header(record)
    msg = _msg_parser_.get(record.levelno, self.default_message_parse)(record)
    # Adding additional spacers for multi-line outputs
    msg = msg.replace('\n', '\n' + ' ' * hlen)
    return header + msg


### Miscellaneous items
class ArgumentValueError(ValueError):
  # Pass
  pass


class ArgumentParseError(ValueError):
  # Pass
  pass


class ArgumentParser(argparse.ArgumentParser):
  """
  @brief Thin wrapper for overwriting the 'error' method behavior

  @details Changing the SystemExit error to a ValueError. As the SystemExit is a
  very hard error that needs to be explicitly caught (not caught by simply
  catching 'Exception'), and only contains the exit code not the original error
  message. We also add a prefix to help indicate that this is an error that was
  raise from the ArgumentParser's parsing methods.
  """
  def error(self, message):
    raise ArgumentParseError(message)


"""@}"""
