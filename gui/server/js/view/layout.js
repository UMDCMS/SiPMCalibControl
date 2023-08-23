/**
 * For the chevron indicators used in the tab displays, ensure that the chevron
 * indicators match the current display state.
 */
function update_indicator() {
  $('.tab-content').each(function () {
    if ($(this).hasClass('hidden')) {
      $(this).removeClass('hidden');
      $(this).siblings('.tab-title').children('i').addClass('fa-angle-left');
      $(this).siblings('.tab-title').children('i').removeClass('fa-angle-down');
    } else {
      $(this).slideToggle('fast');
      $(this).siblings('.tab-title').children('i').removeClass('fa-angle-left');
      $(this).siblings('.tab-title').children('i').addClass('fa-angle-down');
    }
  });
}

/**
 * For ech of the tabs, this is the behavior to exhibit when the tab header is
 * clicked.
 */
function tab_click(element) {
  if (element.siblings('.tab-content').is(':hidden')) {
    element.children('i').removeClass('fa-angle-left');
    element.children('i').addClass('fa-angle-down');
  } else {
    element.children('i').removeClass('fa-angle-down');
    element.children('i').addClass('fa-angle-left');
  }
  element.siblings('.tab-content').slideToggle('fast');
}

/**
 * Given the hex-color code, lighten or darken the color by some fixed amount.
 *
 * Effectively, given RGB values (r,g,b) and shift amount a, return the hex code
 * for the color (r+a,g+a,b+a). The return values will be clipped at the nominal
 * 8-bit limit.
 */
function hex_lumi_shift(col, amt) {
  let usePound = false;
  if (col[0] == '#') {
    col = col.slice(1);
    usePound = true;
  }
  let num = parseInt(col, 16);
  let r = (num >> 16) + amt;
  if (r > 255) r = 255;
  else if (r < 0) r = 0;
  let b = ((num >> 8) & 0x00ff) + amt;
  if (b > 255) b = 255;
  else if (b < 0) b = 0;
  let g = (num & 0x0000ff) + amt;
  if (g > 255) g = 255;
  else if (g < 0) g = 0;
  return (usePound ? '#' : '') + (g | (b << 8) | (r << 16)).toString(16);
}

/**
 * Adding a comment line to the calibration sign-off segment.
 */
function add_comment_line(element) {
  let det_select_dom = dom('select', { class: 'comment-header' }, [
    dom('option', { value: 'general' }, 'General'),
  ]);

  board_layout.detectors.forEach((detid) => {
    det_select_dom.append(
      dom('option', { value: `det${detid}` }, `Det. ${detid}`),
    );
  });

  console.log(element);
  element
    .siblings('.signoff-comment-lines')
    .append(
      dom('div', { class: 'input-row' }, [
        dom('div', { class: 'input-name' }, [det_select_dom]),
        dom(
          'div',
          { class: 'input-units comment-content' }[
            dom('input', { type: 'text', class: 'comment-text' })
          ],
        ),
      ]),
    );
}

/**
 * Drawing common elements of the tile board view.
 *
 * The elements includes the
 */
function draw_tileboard_view_common() {
  // Getting the main canvas element
  let svg = $(`#tile-layout-common-svg`);

  // Wiping the existing elements
  svg.html('');

  // Adding the various elements into the tileboard view

  // The arrow marker style
  svg.append(
    svgdom('defs', {}, [
      svgdom(
        'marker',
        {
          id: 'arrow',
          viewBox: '0 0 10 10',
          refX: '5',
          refY: '5',
          markerWidth: '6',
          markerHeight: '6',
          orient: 'auto-start-reverse',
        },
        svgdom('path', { d: 'M 0 0 L 10 5 L 0 10 z' }),
      ),
    ]),
  );

  // The outer rectangle
  svg.append(
    svgdom('rect', {
      x: '25',
      y: '25',
      width: '500',
      height: '500',
      fill: 'none',
      stroke: '#303030',
      'stroke-width': '3px',
    }),
  );

  // Adding the axis arrows
  svg.append(
    svgdom('polyline', {
      points: '12,475 12,537 75,537',
      fill: 'none',
      stroke: '#303030',
      'stroke-width': '2px',
      'marker-start': 'url(#arrow)',
      'marker-end': 'url(#arrow)',
    }),
  );

  // Adding the axis title
  svg.append(svgdom('text', { x: '85', y: '541' }, 'x'));
  svg.append(svgdom('text', { x: '8', y: '465' }, 'y'));

  // Adding the z axis.
  svg.append(
    svgdom('polyline', {
      points: `537,525 560,525 537,525 537,425 560,425 537,425 537,325 560,325
               537,325 537,225 560,225 537,225 537,125 560,125 537,125 537,25
               560,25  537,25`,
      'stroke-width': '3px',
      stroke: '#303030',
      fill: 'none',
    }),
  );
}

/**
 * Function related to the display of the action column
 */
const action_column_width = 500;
function toggle_action_column() {
  if ($(`#action-column`).css('right').startsWith('-')) {
    //
    show_action_column();
  } else {
    hide_action_column();
  }
}

function show_action_column() {
  $('#action-column').css('width', `${action_column_width}px`);
  $('#action-column').css('right', '0px');
}

function hide_action_column() {
  $('#action-column').css('width', `${action_column_width}px`);
  $('#action-column').css('right', `-${action_column_width}px`);
}

/**
 * Functions related to the display of the monitor column
 */
const monitor_column_width = 400;
function toggle_monitor_column() {
  if ($(`#monitor-column`).css('left').startsWith('-')) {
    show_monitor_column();
  } else {
    hide_monitor_column();
  }
}

function show_monitor_column() {
  $('#monitor-column').css('width', `${monitor_column_width}px`);
  $('#monitor-column').css('left', `0`);
  $('#session-column').css(
    'width',
    `${window.innerWidth - monitor_column_width}px`,
  );
  $('#session-column').css('margin-left', `${monitor_column_width}px`);
}

function hide_monitor_column() {
  $('#monitor-column').css('width', `${monitor_column_width}px`);
  $(`#monitor-column`).css('left', `-${monitor_column_width}px`);
  $('#session-column').css('margin-left', `0px`);
  $(`#session-column`).css('width', `${window.innerWidth}px`);
}

function update_valid_reference(json) {
  // clearing the html containers for references
  $('#standard-calibration-boardtype-container')
    .children('.input-row')
    .each(function () {
      if ($(this).find("input[name='ref-calibration']").length > 0) {
        $(this).html(``);
      }
    });

  // Making the new reference calibration objects
  let new_html = $('#standard-calibration-boardtype-container').html();

  for (var i = 0; i < json.valid.length; ++i) {
    $('#standard-calibration-boardtype-container').append(
      dom('div', { class: 'input-row' }, [
        dom('span', { class: 'input-name' }, i == 0 ? 'Reference' : ''),
        dom('span', { class: 'input-units' }, [
          dom('input', {
            type: 'radio',
            name: 'ref-calibration',
            value: `${json.valid[i].tag}`,
          }),
        ]),
        dom(
          'span',
          { class: 'input-units' },
          `${json.valid[i].boardtype} (${json.value[i].time})`,
        ),
      ]),
    );
  }
}

/**
 * Updating the selector interface for specifying a board type for either the
 * system or the standard calibration sequence.
 */
function update_tileboard_list(type, json) {
  let list_dom = $(`#${type}-calibration-boardtype-container`);
  list_dom.html(''); // Wiping existing content

  // Adding header for standard type.dd
  if (type == 'standard') {
    list_dom.append(
      dom('div', { class: 'input-row' }, [
        dom('span', { class: 'input-name' }, 'Board ID'),
        dom('span', { class: 'input-units' }),
        dom('input', {
          type: 'text',
          id: 'std-calibration-boardid',
          class: 'input-units',
        }),
      ]),
    );
  }

  console.log(json);

  let first = true;
  for (var boardtype in json) {
    const prefix = first ? 'Board type' : '';
    first = false;
    list_dom.append(
      dom('div', { class: 'input-row' }, [
        dom('span', { class: 'input-name' }, prefix),
        dom('input', {
          type: 'radio',
          name: `${type}-calibration-boardtype`,
          value: `${boardtype}`,
        }),
        dom(
          'span',
          { class: 'input-units' },
          `${json[boardtype]['name']} (${json[boardtype]['number']})`,
        ),
      ]),
    );
  }
}
