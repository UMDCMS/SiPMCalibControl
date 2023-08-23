/**
 * Updating the display elements required for the progress monitoring.
 */

/**
 * Returning the progress status code as a color
 */
function progress_color(integer) {
  switch (integer) {
    case CMD_COMPLETE:
      return 'green';
    case CMD_PENDING:
      return 'cyan';
    case CMD_RUNNING:
      return 'yellow';
    case CMD_ERROR:
      return 'red';
    default:
      return 'none';
  }
}

function progress_status_string(integer) {
  switch (integer) {
    case CMD_COMPLETE:
      return 'DONE';
    case CMD_PENDING:
      return '';
    case CMD_RUNNING:
      return 'running';
    case CMD_ERROR:
      return 'ERROR';
    default:
      return '';
  }
}

/**
 * Updating the main progress bar.
 */
function progress_update_bar(progress) {
  let total = 0;
  let error = 0;
  let running = 0;
  let complete = 0;
  let pending = 0;

  // Calculating the overall percentage
  for (const tag in progress) {
    for (const detid in progress[tag]) {
      total++;
      if (progress[tag][detid] == CMD_PENDING) {
        pending++;
      } else if (progress[tag][detid] == CMD_RUNNING) {
        running++;
      } else if (progress[tag][detid] == CMD_COMPLETE) {
        complete++;
      } else {
        error++;
      }
    }
  }
  if (total == 0) {
    return;
  }

  // Updating the overall session progress progress bar.
  const complete_percent = (100.0 * complete) / total;
  const error_percent = (100.0 * error) / total;
  const running_percent = (100 * running) / total;

  var bar_elem = $('#session-progress');
  bar_elem.children('.progress-complete').css('width', `${complete_percent}%`);
  bar_elem.children('.progress-running').css('width', `${running_percent}%`);
  bar_elem.children('.progress-error').css('width', `${error_percent}%`);
}

/**
 * The table view as a list of all operations in the calibration to be displayed.
 */
function progress_update_table(progress) {
  div = $('#table-view');
  if (div.html() === ``) {
    // For empty HTML only
    make_table_html();
  }

  // The typical updating progress.
  for (const tag in progress) {
    for (const detid in progress[tag]) {
      const progress_code = progress[tag][detid];
      $(`#table-${detid}-${tag}`).css(
        'background-color',
        progress_color(progress_code),
      );
    }
  }
}

/**
 * Creating the HTML element for the table display.
 */
function make_table_html() {
  let table_dom = dom('table', {});

  // Making the header elements
  let header_row_dom = dom('tr', {}, [dom('th', {})]);
  all_progress.forEach((tag) => {
    header_row_dom.append(
      dom('th', {}, dom('span', {}, `${process_full_name(tag)}`)),
    );
  });
  table_dom.append(header_row_dom);

  // Making each detector as a row
  for (const det_id of board_layout.detectors) {
    let row_dom = dom('tr', { onclick: `show_det_summary(${det_id})` });
    row_dom.append(dom('td', { c: '' }, `${det_id}`));
    all_progress.forEach((tag) => {
      row_dom.append(dom('td', { id: `table-${det_id}-${tag}` }));
    });
    table_dom.append(row_dom);
  }

  $('#table-view').html(table_dom);
}

/**
 * Updating the per detector progress elements.
 *
 * There are two classes of elements that need to be updated: in the text based
 * summary, change the color of the text such that the user can see the
 * completed/error/ongoing calibration process, and an update to the background
 * of the tile board layout so that the user can see whether where on the board
 * errors has occurred.
 */
function progress_update_det_summary(progress) {
  // Variables that contains a map of
  let det_job_progress = {};
  let running_detid = 65536; // Some impossible id number.

  // Calculating the summary percentage.
  for (const tag in progress) {
    for (const detid in progress[tag]) {
      const progress_code = progress[tag][detid];

      // Creating tally entry if it doesn't already exists.
      if (!(detid in det_job_progress)) {
        det_job_progress[detid] = [0, 0];
      }

      // Updating the status detector tally
      ++det_job_progress[detid][0];
      if (progress_code == CMD_RUNNING) {
        running_detid = detid;
      } else if (progress_code == CMD_COMPLETE) {
        ++det_job_progress[detid][1];
      }

      // Updating the text based detector information.
      var element = $(`#single-det-summary-${detid}`).find(`#process-${tag}`);
      element.css('background-color', progress_color(progress_code));
      element.html(progress_status_string(progress_code));
    }
  }

  for (const detid in board_layout.detectors) {
    if (String(detid) == String(running_detid)) {
      $(`#tile-layout-${detid}`).css('fill', 'yellow');
    } else if (detid in det_job_progress) {
      const total = det_job_progress[detid][0];
      const comp = det_job_progress[detid][1];
      const base_color = `#00FF00`;
      const lighten = (200.0 * (total - comp)) / total;
      $(`#tile-layout-${detid}`).css(
        'fill',
        hex_lumi_shift(base_color, lighten),
      );
    }
  }
}
