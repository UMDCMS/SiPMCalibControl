/**
 * controls.js
 *
 * Handling the display elements that either the user directly interacts, or
 * */

/**
 * Creating the system log in a tabular form.
 */
function tabular_session() {
  $('#session-log-table').html(''); // Cleaing the existing table

  $('#session-log-table').append(
    // Adding the header row
    dom('tr', {}, [
      dom('th', { class: 'entry-time' }, 'Time'),
      dom('th', { class: 'entry-level' }, 'Level'),
      dom('th', { class: 'entry-name' }, 'Name'),
      dom('th', { class: 'entry-msg' }, 'Message'),
    ]),
  );

  // Adding each entry directly, the handling of the display be carried out by
  // CSS command to have these entries be adjustable on the flow
  for (const entry of session.session_log) {
    $('#session-log-table').append(
      dom(
        'tr',
        {
          class: `session-row-name-${entry.name}`,
          class: `session-row-level-${entry.levelno}`,
        },
        [
          dom('td', { class: 'entry-time' }, date_format(entry)),
          dom('td', { class: 'entry-level' }, level_format(entry)),
          dom('td', { class: 'entry-name' }, name_format(entry)),
          dom('td', { class: 'entry-msg' }, msg_format(entry)),
        ],
      ),
    );
  }

  update_log_display(); // Checking if certain entries should be hidden
  scroll_log_to_bottom();
}

/**
 * Getting the date format string for a given command log entry. Returns the
 * string in the format of "YYYY.mmm.dd@HH:MM:SS"
 */
function date_format(entry) {
  const date_obj = new Date(Math.round(entry.created * 1000));
  const year = date_obj.getFullYear();
  const month = date_obj.getMonth();
  const day = date_obj.getDate();
  const hours = date_obj.getHours();
  const min = date_obj.getMinutes();
  const sec = date_obj.getSeconds();

  const month_arr = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];

  function pad_zero(num, target = 2) {
    return String(num).padStart(target, '0');
  }
  return (
    `${year}.${month_arr[month]}.${pad_zero(day)}` +
    `@` +
    `${pad_zero(hours)}:${pad_zero(min)}:${pad_zero(sec)}`
  );
}

/**
 * Returning the level string for a log level entry.
 */
function level_format(entry) {
  switch (entry.levelno) {
    case 50:
      return 'CRITICAL';
    case 40:
      return 'ERROR';
    case 30:
      return 'WARNING';
    case 25:
      return 'TRACEINFO';
    case 20:
      return 'INFO';
    case 15:
      return 'INFO';
    case 14:
      return 'INFO';
    case 10:
      return 'DEBUG';
    case 5:
      return 'COMMANDS';
    default:
      return '[entry]';
  }
}

/**
 * Formatting the name to be displayed in the log level.
 */
function name_format(entry) {
  return entry.name.replace('SiPMCalibCMD.', '');
}

/**
 * Special formatting required for particular log levels.
 */
function msg_format(entry) {
  if (entry.levelno == 5) {
    // For command line history
    if (entry.args[0] == 'start') {
      return `Starting command ${entry.msg}`;
    } else if (entry.args[0] == 'stop') {
      return `Completed command ${entry.msg} (status: ${entry.args[1]})`;
    }
  } else if (entry.levelno == 14) {
    // For interactive information dumps, getting the information dump. Here we
    // also get the table-information dump format
    table_dom = dom('table', {}, '');
    for (const row of entry.table) {
      table_row = dom('tr', {}, '');
      for (const cell of row) {
        table_row.append(dom('td', {}, cell));
      }
      table_dom.append(table_row);
    }
    if (entry.msg) {
      return entry.msg + '<br><table>' + table_dom.html() + '</table>';
    } else {
      return '<table>' + table_dom.html() + '</table>';
    }
  } else {
    // Default is do nothing.
    return entry.msg;
  }
}

// For the check boxes marking the various label visibilities

function update_log_display(event) {
  const level_map = {
    error: [40],
    warning: [30],
    info: [20],
    config: [15, 14],
    cmd: [5],
  };

  for (var key in level_map) {
    for (var level of level_map[key]) {
      if ($(`#log-display-${key}`).is(':checked')) {
        $(`.session-row-level-${level}`).removeClass('hidden');
      } else {
        $(`.session-row-level-${level}`).addClass('hidden');
      }
    }
  }
  scroll_log_to_bottom();
}

function scroll_log_to_bottom() {
  // On the creation of the table, always scroll to the bottom of the session
  // log. For some reason this only works with vanilla javascript, not jQuery.
  var div = document.getElementById('session-log-table');
  div.scrollTop = div.scrollHeight;
}
