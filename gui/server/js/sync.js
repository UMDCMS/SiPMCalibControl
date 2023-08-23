/**
 * sync.js
 *
 * Javascript function for handling the signals sent out by the main
 * calibration session.
 */

function request_sync(msg) {
  socketio.emit('resend', msg);
}

/**
 * Global variables for status monitoring.
 *
 * The structure of this object should mirror the return value of the python
 * script. Except with potential time dependent storage.
 */

function clear_display(msg) {
  $('#display-message').html('');
  $('#tile-layout-grid').html('');
  $('#single-det-summary').html('');
  $('#det-details-content').html('');
  $('#det-plot-and-figure').html('');
}

function display_message(msg) {
  $('#display-message').html(msg);
}

/**
 * When the calibration session type is updated by the main calibration session.
 */
function sync_session_type(new_type) {
  session.session_type = new_type;

  function clear_comment_fields(id_string) {
    $(id_string).children('.signoff-comment-lines').html(``);
  }

  if (session.session_type == SESSION_TYPE_NONE) {
    clear_display();
    $('#system-calib-signoff-container').addClass('hidden');
    $('#standard-calib-signoff-container').addClass('hidden');
    clear_comment_fields('#system-calib-signoff-container');
    clear_comment_fields('#standard-calib-signoff-container');
  } else if (session.session_type == SESSION_TYPE_STANDARD) {
    $('#standard-calib-signoff-container').removeClass('hidden');
    clear_comment_fields('#system-calib-signoff-container');
    clear_comment_fields('#standard-calib-signoff-container');
  } else if (session.session_type == SESSION_TYPE_SYSTEM) {
    $('#system-calib-signoff-container').removeClass('hidden');
    clear_comment_fields('#system-calib-signoff-container');
    clear_comment_fields('#standard-calib-signoff-container');
  }
}

/**
 * Sync wrapper for the update_settings function defined in the the
 * view/settings.js file.
 */
function sync_setting(new_settings) {
  update_settings(new_settings);
}

/**
 * Here we only setup the various used for keeping track of the tileboard view.
 * In case the tileboard type is non-trivial, we setup call the additional
 * functions setup in the tileboard_view.js file to generate the additional
 * display elements.
 */
function sync_tileboard_type(msg) {
  session.board_type = msg;
  // In the case board type is non-trivial setup the document to properly display
  // the a tileboard view elements. These functions are defined in the
  // tileboard_view.js file.
  if (session.board_type != '') {
    make_tileboard_detector_html();
  } else {
    clear_tileboard_detector_html();
  }

  request_sync('state');
  request_sync('progress');
}

/**
 * As updating the the progress bars are potentially very taxing on the client
 * side while short commands are being rapidly executed by the server, here we
 * write a very small safe guard: the sync function will only every handled
 * pushing the progress into the queue, then call the true function to fully
 * process the progress status.
 */
async function sync_calib_progress(progress) {
  session.progress_queue.push(progress); // Pushing the progress to the stack.
  run_progress_update();
}

/**
 * Executing the progress element updates. If an progress update instance is
 * already running do nothing. Otherwise, set the updating progress flag to be
 * true and run the progress update on the oldest element in the queue, update
 * the detector elements accordingly, shift the queue by 1, repeat until no
 * progress updates remain.
 */
function run_progress_update() {
  // early exit if and instance of the update function is already running.
  if (session.updating_progress) {
    return;
  }

  session.updating_progress = true;
  while (session.progress_queue.length) {
    progress = session.progress_queue[0];
    session.progress_queue.shift();

    // Functions defined in view/progress.js
    progress_update_bar(progress);
    progress_update_table(progress);
    progress_update_det_summary(progress);
  }
  session.updating_progress = false;
}

/**
 * Updating the current command progress bar. This wrapper to the
 * progress_update_cmd method in view/progress.js
 */
function sync_cmd_progress(msg) {
  progress_update_cmd(msg);
}
