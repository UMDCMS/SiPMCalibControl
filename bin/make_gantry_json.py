#!/bin/env python3
import json
import os
import numpy as np
import argparse

parser = argparse.ArgumentParser('This is a test')

parser.add_argument(
    'inputfile',
    help="""File containing tileboard global coordinates to be translated
    into the gantry coordinates.
    """.strip())
parser.add_argument('outputfile',
                    help="""File to save the translated results.
    """.strip())

if __name__ == "__main__":
  args = parser.parse_args()

  with open(args.inputfile) as f:
    raw_json = json.load(f)

  angle = raw_json['angle']
  gantry_json = {
      'board type': os.path.basename(args.inputfile),
      'board description': '',
      'board id': -1,
      'detectors': {}
  }

  # Iterating to get the maximum values
  max_r = 0.
  min_r = 100000.
  for vals in raw_json['dets'].values():
    max_r = max([max_r, vals[2]])
    min_r = min([min_r, vals[1]])

  deg = np.pi / 180

  x_origin = -max_r * np.sin(4 * angle * deg) + raw_json['global x offset']
  y_origin = min_r * np.cos(4 * angle * deg) + raw_json['global y offset']

  print(x_origin)

  for detid, vals in raw_json['dets'].items():
    column = vals[0]
    inner = vals[1]
    outer = vals[2]

    r_offset = vals[3] if len(vals) >= 4 else 0
    a_offset = vals[4] if len(vals) >= 5 else 0

    r = (inner + outer) / 2 + r_offset
    a = 90 + (3.5 - column) * angle + a_offset
    x = r * np.cos(a * deg) - x_origin
    y = r * np.sin(a * deg) - y_origin
    print(a, x)

    gantry_json['detectors'][str(detid)] = {
        "mode": -1,
        "channel": int(detid),
        "default coordinates": [x, y]
    }

  with open(args.outputfile, 'w') as f:
    json.dump(gantry_json, f, indent=2)

  print(gantry_json)
