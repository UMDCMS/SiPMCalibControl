/**
 * Here is the functions used for generating the displays in the tileboard view.
 *
 * There are two big parts of this.
 * 1. The geometric view of the tileboard with a block used for each detector
 *    instance.
 * 2. Is the detailed view for each detector in the board view. This will
 *    included elements for plotting more displays.
 *
 * Notice that the styling will be handled by the progress_view function as there
 * are a lot of
 */
var board_layout = {}; // Global object for board layout

// Processes flag that can be
const plot_processes = ['zscan', 'lowlight', 'lumialign'];
const can_rerun_process = ['zscan', 'lowlight'];
const can_extend_process = ['zscan', 'lowlight'];
const all_processes = ['vhscan', 'visalign', 'zscan', 'lowlight', 'lumialign'];

/**
 * This is largely split into 2 parts:
 * 1. The SVG section for displaying the tile layout.
 * 2. A table containing all the processes of a the calibration session.
 * 2. the Tabular part displaying the per-detector information and plots.
 *
 * Because new elements can be added on by request, we are leaving this function
 * as a list of other function.
 */
function make_tileboard_detector_html() {
  $.ajax({
    dataType: 'json',
    mimeType: 'application/json',
    url: `report/tileboard_layout`,
    success: function (json) {
      board_layout = json;
      make_tileboard_html();
      make_detector_summary_html();
    },
    error: function () {
      console.log('Failed to get board layout');
    },
  });
}

function clear_tileboard_detector_html() {
  $(`#tile-layout-svg`).html(``);
}

/**
 * Function for making the HTML components required for a tileboard display.
 *
 * Here there are two methods of display:
 * - If a geometry/tileboard.json file exists, the display generating function
 *   the board will be displayed as a true arc segments, fully displaying the
 *   expected tileboard geometry, as defined in the HGCAL documents.
 * - If such a file doesn't exists, then the displays assumes a calibration level
 *   board layout. Detectors elements will be discontinuous blocks in the SVG
 *   canvas.
 *
 * The stark contrast aims to force the user to become aware of the tile identity
 * differences.
 */
function make_tileboard_html() {
  $.ajax({
    dataType: 'json',
    mimeType: 'application/json',
    url: `geometry/${board_layout.boardtype}`,
    success: make_tileboard_segment_html,
    error: make_tileboard_default_html,
  });
}

// couple of constant variables to help with the conversion of the data scaling
const canvas_target = 500;
const corner_offset = 25;

/**
 * By default, the display of the SVG will plot out the detector elements using
 * rectangular blocks. The rectangular blocks can be clicked to bring up the
 * per-detector summary information.
 */
function make_tileboard_default_html() {
  const x_max = 500;
  const scale = canvas_target / x_max;

  // Clear the tile-layout-svg first.
  $(`#tile-layout-svg`).html(``);
  if (Object.keys(board_layout.detectors).length > 0) {
    for (var detid in board_layout.detectors) {
      const x_raw = board_layout.detectors[detid]['orig'][0];
      const y_raw = board_layout.detectors[detid]['orig'][1];

      const x = x_raw * scale + corner_offset;
      const y = x_max - y_raw * scale + corner_offset;

      $(`#tile-layout-svg`).append(
        svgdom('rect', {
          x: `${x - 20}`,
          y: `${y - 20}`,
          width: '40',
          height: '40',
          id: `tile-layout-${detid}`,
          onclick: `show_det_summary(${detid})`,
        }),
      );

      $(`#tile-layout-svg`).append(
        svgdom(
          'text',
          {
            x: `${x}`,
            y: `${y}`,
            'text-anchor': 'middle',
            onclick: `show_det_summary(${detid})`,
          },
          `${detid}`,
        ),
      );
    }
  } else {
    $(`#tile-layout-svg`).append(
      svgdom(
        'text',
        {
          x: '275',
          y: '275',
          'text-anchor': 'middle',
        },
        'NO TILEBOARD LOADED',
      ),
    );
  }
}

/**
 * Generating the SVG path string required for a regular tile board segment.
 *
 * Both tileboards and the SiPM selection (a.k.a the shape of typical
 * scintillating tiles)  are composed to two concentric circular arcs spanning a
 * common angle. This function generates the path required for this display. All
 * styling would be handle by CSS and other functions.
 *
 * Here r1 and r2 are in units of pixels. While t1 and t2 are in units of degrees
 * (since the HGCAL is segmented into args of exactly 10 degrees). ox, and oy
 * refers to the where the center of the circles used for the concentric arcs
 * should be placed in pixel coordinates.
 *
 * Here we need to handle the reversal of the y coordinates. The use is the one
 * responsible for ensuring the offsets are handles properly.
 */
function make_regular_segment(r1, r2, t1, t2, ox, oy) {
  t2 = (-(t1 + t2) * Math.PI) / 180;
  t1 = (-t1 * Math.PI) / 180;
  let x1 = ox + r1 * Math.cos(t1);
  let y1 = oy + r1 * Math.sin(t1);
  let x2 = ox + r1 * Math.cos(t2);
  let y2 = oy + r1 * Math.sin(t2);
  let x3 = ox + r2 * Math.cos(t2);
  let y3 = oy + r2 * Math.sin(t2);
  let x4 = ox + r2 * Math.cos(t1);
  let y4 = oy + r2 * Math.sin(t1);

  let path_str = `M ${x1} ${y1} a ${r1},${r1} 0 0,0 ${x2 - x1},${y2 - y1} `;
  path_str += `L ${x3} ${y3} a ${r2},${r2} 0 0,1 ${x4 - x3},${y4 - y3} `;
  path_str += `z`;
  return path_str;
}

/**
 * Generating the SVG/HTML tags for the segment display of a tile board. Since
 * there the objects themselves will not be handled.
 */
function make_tileboard_segment_html(tileboard_json) {
  // Getting the maximum and minimum radius for plotting offset requirements.
  const angle = tileboard_json.angle;
  const deg = Math.PI / 180.0;

  let min = 100000;
  let max = 0;
  for (const detid of tileboard_json.dets) {
    min = Math.min(tileboard_json.dets[detid][1], min);
    max = Math.max(tileboard_json.dets[detid][2], max);
  }

  let new_html = ``;

  // Setting up the scaling factor such that it uses the most of the canvas
  // area, Setting up the offset such that the center matches that of the
  // object is centered on the canvas
  const scale = 1.0;
  const offset_x = max * Math.sin(4 * angle * deg) * scale + corner_offset;
  const offset_y =
    min * Math.cos(4 * angle * deg) * scale + canvas_target + corner_offset;

  // Main loop for plotting all the objects.
  for (const detid of tileboard_json.dets) {
    // Getting the various parameters
    const det = tileboard_json.dets[detid];
    const column = det[0];
    const inner = det[1];
    const outer = det[2];
    const det_roffset = det.length >= 4 ? det[3] : 0;
    const det_aoffset = det.length >= 5 ? det[4] : 0;

    // Getting hte plot variables.
    const t1 = 90 + (8 - column - 5) * angle;
    const path_str = make_regular_segment(
      outer * scale,
      inner * scale, // The radii information,
      t1,
      angle,
      offset_x,
      offset_y,
    );

    // Path part for display shape
    $(`#tile-layout-svg`).append(
      svgdom('path', {
        id: `tile-layout-${detid}`,
        d: `${path_str}`,
        onclick: `show_det_summary(${detid})`,
        class: '',
      }),
    );

    // Adding text labeling to help with clarity
    const r_det = (inner + outer) / 2 + det_roffset;
    const a_det = -(t1 + angle / 2 + det_aoffset);
    const x = r_det * scale * Math.cos(a_det * deg) + offset_x;
    const y = r_det * scale * Math.sin(a_det * deg) + offset_y;

    $(`#tile-layout-svg`).append(
      svgdom(
        'text',
        {
          x: `${x}`,
          y: `${y}`,
          'text-anchor': 'middle',
        },
        `${detid}`,
      ),
    );
  }
}

/**
 * The detector summary is make of two parts. One is the brief summary of
 * coordinates and calibration action progresses. The other is the container of
 * plots. Since the plot container takes up a lot more space than the expected
 * values. Two functions are used to generated the various html elements.
 *
 * Notice at this stage, there will be no parsing of data just yet. This is left
 * to another function.
 */

function make_detector_summary_html() {
  $('#single-det-summary').html('');
  $('#det-plot-and-figure').html('');
  for (const detid in board_layout.detectors) {
    $('#single-det-summary').append(make_detector_coordinate_dom(detid));
    $('#det-plot-and-figure').append(make_detector_plot_dom(detid));
  }
}

/**
 * Making the text-based coordinate summary part of the detector summary display.
 *
 * Here we are only making the base HTML with no data progress parsing. The only
 * apparent parsing would be for the various processes where re-run/extension
 * button will need to be added.
 */
function make_detector_coordinate_dom(detid) {
  align_dom = dom('div', { class: 'input-align' }, [
    dom('div', { class: 'input-row' }, [
      dom('span', { class: 'input-name' }, 'Det ID:'),
      dom('span', { class: 'input-units' }, `${detid}`),
    ]),
    dom('div', { class: 'input-row' }, [
      dom('span', { class: 'input-name' }, 'Coordinates'),
      dom('span', { class: 'input-name', id: 'coord-orig' }),
    ]),
    // For luminosity alignment  coordinates
    dom('div', { class: 'input-row' }, [
      dom('span', { class: 'input-name' }, 'Lumi. coord'),
      dom('span', { class: 'input-inputs', id: 'coord-lumi' }),
      dom('span', { class: 'input-units' }, [
        dom(
          'button',
          {
            id: `rerun-lumi-scan-${detid}`,
            class: 'action-button',
            onclick: `rerun_single('lumialign','${detid}', false)`,
            disabled: '',
          },
          'Rerun',
        ),
      ]),
    ]),
    // For visual alignment coordinates
    dom('div', { class: 'input-row' }, [
      dom('span', { class: 'input-name' }, 'Vis. coord'),
      dom('span', { class: 'input-inputs', id: 'coord-vis' }),
      dom('span', { class: 'input-units' }, [
        dom(
          'button',
          {
            id: `rerun-vis-scan-${detid}`,
            class: 'action-button',
            onclick: `rerun_single('visalign','${detid}', false)`,
            disabled: '',
          },
          'Rerun',
        ),
      ]),
    ]),
  ]);

  for (const tag of all_processes) {
    align_dom.append(
      dom('div', { class: 'input-row' }, [
        dom('span', { class: 'input-name', id: `process-${tag}` }),
        dom('span', { class: 'input-units' }, `${process_full_name(tag)}`),
        check_rerun_button(detid, tag),
        check_extend_button(detid, tag),
      ]),
    );
  }

  return dom(
    'div',
    {
      id: `single-det-summary-${detid}`,
      class: 'hidden',
    },
    [align_dom],
  );
}

/**
 * Given a process tag, check if the process can be re-run. If it can create the
 * HTML code for the rerun action button. Otherwise return an empty string.
 */
function check_rerun_button(detid, tag) {
  if (can_rerun_process.includes(tag)) {
    return dom('span', { class: 'input-units' }, [
      dom(
        'button',
        {
          id: `rerun-${tag}-${detid}`,
          class: 'action-button',
          onclick: `rerun_single('${tag}','${detid}',false)`,
        },
        'Rerun',
      ),
    ]);
  } else {
    return ``;
  }
}

/**
 * Given a process tag, check if the process can be extended. If it can create
 * the HTML code for the rerun action button. Otherwise return an empty string.
 */
function check_extend_button(detid, tag) {
  if (can_extend_process.includes(tag)) {
    return dom('span', { class: 'input-units' }, [
      dom(
        'button',
        {
          id: `rerun-${tag}-${detid}`,
          class: 'action-button',
          onclick: `rerun_single('${tag}','${detid}',true)`,
        },
        'Extend',
      ),
    ]);
  } else {
    return ``;
  }
}

/**
 * Translation of the abbreviated process tag into a fully human readable string.
 */
function process_full_name(tag) {
  switch (tag) {
    case 'vhscan':
      return 'Visual Matrix';
    case 'visalign':
      return 'Visual alignment';
    case 'zscan':
      return 'Intensity scan';
    case 'lowlight':
      return 'Low light profile';
    case 'lumialign':
      return 'Luminosity alignment';
    default:
      return 'Custom';
  }
}

function detector_plot_id(detid, tag) {
  return `single-det-summary-plot-${detid}-${tag}`;
}

function detector_visalign_img_id(detid) {
  return `single-det-summary-plot-${detid}-visalign-img`;
}

/**
 * Making the dummy detector HTML plot DOM objects
 */
function make_detector_plot_dom(detid) {
  let plot_dom = dom('div', { class: 'plot-container' });
  for (const tag of plot_processes) {
    plot_dom.append(
      dom('div', { class: 'plot', id: `${detector_plot_id(detid, tag)}` }),
    );
  }
  plot_dom.append(
    dom(
      'div',
      { class: 'plot', id: `single-det-summary-plot-${detid}-visalign` },
      [
        dom('img', {
          id: `${detector_visalign_img_id(detid)}`,
          src: 'static/icon/notdone.jpg',
        }),
      ],
    ),
  );

  return dom('div', { class: 'hidden', id: `det-plot-container-${detid}` }, [
    plot_dom,
  ]);
}

/**
 * Updating the tileboard detector coordinates. Since this is expected to be
 * small, we are not going to write a new sub-routine to get only the updated
 * detector coordinates, we are just going to pull the entire tileboard and
 * update everything.
 */
function update_tileboard_coordinates() {
  // Helper functions for generating coordinates in a uniform format.
  // Updating tileboard coordinates.

  function make_coordinate_string(detid, tag) {
    if (board_layout.detectors[detid][tag][0] < 0) {
      return 'NOT DONE';
    } else {
      const x = board_layout.detectors[detid][tag][0].toFixed(1);
      const y = board_layout.detectors[detid][tag][1].toFixed(1);
      return `(${x},${y})`;
    }
  }

  for (const detid of board_layout.detectors) {
    var cont = $(`#single-det-summary-${detid}`);
    cont.find('#coord-orig').html(make_coordinate_string(detid, 'orig'));
    cont.find('#coord-lumi').html(make_coordinate_string(detid, 'lumi'));
    cont.find('#coord-vis').html(make_coordinate_string(detid, 'vis'));
  }
}

function show_det_summary(detid) {
  // Showing the text based detector part.
  $('#single-det-summary')
    .children()
    .each(function () {
      $(this).addClass('hidden');
    });

  $('#det-plot-and-figure')
    .children()
    .each(function () {
      $(this).addClass('hidden');
    });

  $('#single-det-summary')
    .children(`#single-det-summary-${detid}`)
    .removeClass('hidden');

  $('#det-plot-and-figure')
    .children(`#det-plot-container-${detid}`)
    .removeClass('hidden');

  // Requesting the plots
  for (const tag of plot_processes) {
    divid = detector_plot_id(detid, tag);
    // translation
    request_plot_by_detid(detid, tag, divid);
  }
  // check if visual alignment images have been taken
  $.ajax({
    url: `visualalign/${detid}`,
    type: 'get',
    dataType: 'html',
    success: function (data) {
      console.log('Status: ' + status + '\nData: ' + data);
      /* creating image */
      $(`#${detector_visalign_img_id(detid)}`).attr(
        'src',
        'data:image/gif;base64,' + data,
      );
    },
  });
}
