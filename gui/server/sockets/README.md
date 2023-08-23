@defgroup gui_server GUI Server
@ingroup gui_design

The server session uses the [flask socketio][flasksocket] for the socket i/o
handling. A single global `SocketIO()` instance is initiated in the package
`__init__.py` file for all sub-routines to emit signals. In the same
`__init__.py` file, a global instance of the `Session` object is used to record
the system status and progress, as well as containing and controlling the
underlying command line session. All server interactions are then defined as
functions that interact with these two global objects.

- [`parsing.py`](parsing.py) contains the functions for immediately processing
  the socket signals and AJAX request, determining whether to process the signal
  and which subsequent functions to call for the client side request.
- [`action.py`](action.py) Functions to perform server side calibration actions,
  including individual commands and sets of calibration commands for the full
  tileboard calibration runs.
- [`sync.py`](sync.py) Functions for emitting operation critical signals to
  ensure that the GUI client sees the precise server state. Sync-like signals can
  be emitted at any time and the client should respond accordingly.
- [`report.py`](report.py) Functions for emitting non-critical information to the
  client, either for aesthetic for progress checking or basic data quality
  management.
- [`format.py`](format.py) Additional helper functions for ensuring the format of
  certain actions.

[flasksocket]: https://flask-socketio.readthedocs.io/en/latest/