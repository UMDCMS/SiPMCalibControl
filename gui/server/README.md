@defgroup gui_design GUI Design

The key tech used in the web based interface is a [web socket][websocket]
communication between a server containing the command line interface described in
the [CLI documentation](../ctlcmd), and a web-page hosting the client JavaScript
for data display. The GUI is designed mainly for standard calibration sequences,
so while a make-shift CLI interface is available for raw command controls, not
every function will be supported.

The “GUI” has two logically disconnected components: the server side that is used
to handle the underlying hardware, and the client side that is used to display
results and controls to the end users. Here we define 3 types of communications:

- The client sending data to the server side as “action requests”: these are
  small data packages that is used to trigger hardware action. In such cases, all
  future action request will be discarded until all requested hardware actions
  have been completed. The creation of such signals can be found in the
  [`static/js/action.js`](static/js) file, while the corresponding processing of
  these signals will be handled in the [`sockets/action.py`](sockets) file.
- The server will send data to the client via a "sync" type data, these are data
  needs the client to see identical values with the data to avoid operation
  errors, or is frequently updated server side. The emission of these
  communications on the server side can be found in the "sync.py" and the
  handling of such signals should be found in the
  [`static/js/sync.js`](static/js) file.
- The server will send data to the client via "report" requests. This is data
  that is either expensive to compute server side or is not critical to the
  operation of the calibration, so is only presented to the client on request.
  For the client side, this should be done via AJAX URL request, and response of
  these requests will be handled in the [`sockets/report.py`](sockets) file.

The socket-io server for handling various signals and communicating user commands
with the underlying command line application is documented in the
[`sockets`](sockets) directory. Client side GUI design element CSS layout is
placed in [static/sass](static), and the JavaScript for processing data for
display is found in [static/js](static)

[websocket]: https://en.wikipedia.org/wiki/WebSocket
