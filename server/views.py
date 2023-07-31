"""

views.py

Response to be submitted for URL requests, there are 2 types of calls that we
will consider:

- Request for an HTML page. This is implemented as jinja templates found in the
  server/template directory.
- Request for non-time critical data, called for via AJAX requests. This is
  implemented by converting python dictionary to a JSON format via the
  `flask.jsonify` method.

As flasks `add_url_rule` method requires a callable with no other inputs other
than the URL, we use a thin wrapper class to allow all function to access the
main session instance.
"""
from flask import render_template, Response, jsonify
import cv2, io, time
import numpy as np


class ViewFunction(object):
  """
  Thin wrapper object, so that all query methods can access the main session
  class. Notice that the ViewFunction objects should never be declared outside
  of the session object constructor.
  """
  def __init__(self, session):
    """Saving a reference to them main session instance"""
    self.session = session

  def __call__(self, *args, **kwargs):
    """
    Method that is registered to the flask application. Here we provide a thin
    wrapper to emit an error message to connected clients should an error be
    detected. Subsequent classes should over the view method.
    """
    try:
      return self.view(*args, **kwargs)
    except Exception as err:
      self.session.devlog(f'guiview.{self.__class__.__name__.lower()}').error(
          str(err))
    pass

  def view(self, *args, **kwargs):
    """Method to overload for the other classes"""
    pass


"""

Pages - Here are the main HTML pages required

"""


class index(ViewFunction):
  """
  This is the main page the is to be rendered to the front user. The
  corresponding file can be found at server/template/index.html
  """
  def view(self):
    return render_template('index.html')


class expert(ViewFunction):
  """
  This is the page containing the debugging GUI, mainly used for the fast data
  turn around and a simple interface for saving single commands and display the
  output in a simplified data format. This corresponding file is found in the
  server/template/debug.html path.
  """
  def view(self):
    return render_template('debug.html')


class playground(ViewFunction):
  """
  This URL is for testing display functions only.
  """
  def view(self):
    return render_template('playground.html')


"""

URLs used for local file and session data exposure via client side AJAX
requests.

"""


class geometry(ViewFunction):
  def view(self, boardtype):
    """
    The geometry json files. These files correspond directly to the json files in
    the cfg/geometry/ directory if they exists.
    """
    if os.path.exists('cfg/geometry/' + boardtype + '.json'):
      with open('cfg/geometry/' + boardtype + '.json', 'r') as f:
        x = json.load(f)
        return jsonify(x)
    else:
      return {}, 404  # Return an empty json file with a error 404


class status(ViewFunction):
  def view(self, reporttype):
    """
    Instead of report via a socket command, display updates are performed using
    the call to a pseudo JSON file that contains the current status of the
    calibration session. This "file" is generated using a python dictionary. To
    reduced the required libraries in the various files. The jsonify routine is
    called here. The various report function should ensure that the return is json
    compliant, without additional input
    """
    __lookup__ = {
        'tileboard_layout': self.report_tileboard_layout,
        'validreference': self.report_valid_reference,
        'systemboards': self.report_system_boards,
        'standardboards': self.report_standard_boards,
        'settings': self.get_settings,
    }
    return jsonify(__lookup__.get(reporttype, self.report_default))


class device_settings(ViewFunction):
  def view(self):
    """
    Returning the list of settings to be parsed by the display client. The
    reason why this function is generated on user request is because the user
    might need to clear the client-side settings. This function allows for this
    to be performed without needing to update all other connect clients.
    """
    settings = {
        'image': {
            'threshold': session.cmd.visual.threshold,
            'blur': session.cmd.visual.blur_range,
            'lumi': session.cmd.visual.lumi_cutoff,
            'size': session.cmd.visual.size_cutoff,
            'ratio': session.cmd.visual.ratio_cutoff * 100,
            'poly': session.cmd.visual.poly_range * 100,
        },
        'zscan': {
            'samples': session.zscan_samples,
            'pwm': session.zscan_power_list,
            'zdense': session.zscan_zlist_dense,
            'zsparse': session.zscan_zlist_sparse,
        },
        'lowlight': {
            'samples': session.lowlight_samples,
            'pwm': session.lowlight_pwm,
            'zval': session.lowlight_zval,
        },
        'lumialign': {
            'samples': session.lowlight_samples,
            'pwm': session.lowlight_pwm,
            'zval': session.lowlight_zval,
            'range': session.lumialign_range,
            'distance': session.lumialign_distance,
        },
        'picoscope': {
            # Picoscope settings are availabe regardless of picoscope availability.
            'channel-a-range': session.cmd.pico.rangeA(),
            'channel-b-range': session.cmd.pico.rangeB(),
            'trigger-channel': session.cmd.pico.triggerchannel,
            'trigger-value': session.cmd.pico.triggerlevel,
            'trigger-direction': session.cmd.pico.triggerdirection,
            'trigger-delay': session.cmd.pico.triggerdelay,
            'trigger-presample': session.cmd.pico.presamples,
            'trigger-postsample': session.cmd.pico.postsamples,
            'blocksize': session.cmd.pico.ncaptures
        }
    }

    # DRS settings are only available if a physical board is attached to the
    # machine.
    if session.cmd.drs.is_available():
      settings.update({
          'drs': {
              'triggerdelay': session.cmd.drs.trigger_delay(),
              'samplerate': session.cmd.drs.rate(),
              'samples': session.cmd.drs.samples(),
          }
      })
    else:
      settings.update(
          {'drs': {
              'triggerdelay': 0,
              'samplerate': 0,
              'samples': 0,
          }})

    return jsonify(settings)


class FileDataParsing(object):
  """
  Common class for for parsing data given a file name, this is so that different
  methods can use the same parsing routine.
  """
  def make_dict_response(self, process, filename):
    """
    Defining the standard response format
    """
    return {
        'filename': filename,
        'type': process,
        'data': self.make_hist_processed_data(filename) if process == 'hist' else \
                self.make_generic_processed_data(filename)
    }

  def make_hist_processed_data(self, filename):
    """
    Here we aggregate the results in a histogram. Here we assume the standard
    write-out format with the last N columns being a list of readout values. The
    first line is then used to create an numpy histogram. All other lines will be
    accumulated into this histogram. We choose to create the histogram early to
    reduce the memory footprint of the program.
    """
    raw_values = np.array([])
    with open(filename, 'r') as f:
      for line in f:
        tokens = line.split()
        if (len(tokens) < 10): continue  # Skipping over lines with bad format
        raw_values = np.append(raw_values,
                               np.array([float(x) for x in tokens[8:]]))
    hist_values, hist_edges = np.histogram(raw_values, bins=40)
    return {
        'edges': hist_edges.tolist(),
        'values': hist_values.tolist(),
        'mean': np.mean(raw_values),
        'rms': np.std(raw_values)
    }

  def make_generic_processed_data(self, filename):
    """
    Returning the full data collected as a set of named array values.
    """
    ret_dict = {
        't': [],
        'x': [],
        'y': [],
        'z': [],
        'p': [],
        'pt': [],
        'st': [],
        'readout': [],
    }
    with open(filename) as f:
      for line in f:
        tokens = line.split()
        if (len(tokens) != 10): continue  # Skipping over line in bad format.
        ret_dict['t'].append(float(tokens[0]))
        ret_dict['x'].append(float(tokens[2]))
        ret_dict['y'].append(float(tokens[3]))
        ret_dict['z'].append(float(tokens[4]))
        ret_dict['p'].append(float(tokens[5]))
        ret_dict['pt'].append(float(tokens[6]))
        ret_dict['st'].append(float(tokens[7]))
        ret_dict['readout'].append([float(x) for x in tokens[8:]])
    return ret_dict


class databyfile(ViewFunction, FileDataParsing):
  def view(self, process, filename):
    """
    Returning the data stored at the requested path, and reduced the data
    according to the requested process format.
    """
    return jsonify(self.make_dict_response(process, filename.replace('@', '/')))


class visual(ViewFunction):
  """
  This is a pseudo URL, which responds with the current camera image stored in
  the session memory, as a byte stream of a JPEG image file. The format of the
  Response object is found from reference:
  https://medium.com/datadriveninvestor/video-streaming-using-flask-and-opencv-c464bf8473d6
  """
  @staticmethod
  def make_jpeg_image_byte(image):
    return (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + image + b'\r\n')

  # Static objects
  @staticmethod
  def default_yield():
    __default_image_io = io.BytesIO(
        cv2.imencode('.jpg', cv2.imread('server/icon/notdone.jpg', 0))[1])
    __default_yield = visual.make_jpeg_image_byte(__default_image_io.read())
    return __default_yield

  def view(self):
    def current_image_bytes():
      while True:  ## This function will always generate a return
        try:
          yield self.make_jpeg_image_byte(
              self.session.cmd.visual.get_image_bytes())
        except Exception as e:
          yield self.default_yield()
        time.sleep(0.1)  # Defining the refresh interval (in seconds)

    return Response(current_image_bytes(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


class logdump(ViewFunction):
  """
  Returning the monitoring stream as a single json file
  """
  def view(self, logtype):
    return jsonify({
        'request_timestamp':
        time.time(),
        'log_dump': [
            x.__dict__
            for x in (self.session.mon_handle.record_list if logtype ==
                      'monitor' else self.session.mem_handle.record_list)
        ]
    })
