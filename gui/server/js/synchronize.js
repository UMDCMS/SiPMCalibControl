/**
 * synchronize.js
 *
 * Functions for synchronizing the information between obtained from the main
 * system-server side and the client side. The function here aims to handle the
 * immediate data parsing of the synchronization requests. The editing of the
 * display elements should be handled in separate layout functions.
 *
 * There are also at set of session.
 */

/**
 * Getting the monitoring stream log that is stored in memory of the main server
 * session. Here we pull the entire log via a ajax request rather than have the
 * server send individual log entries to avoid race conditions.
 */
function sync_monitor_log() {
  ajax_request('/logdump/monitor', async function (json) {
    session.monitor_log = json.log_dump;
    if (session.monitor_log.length > session.monitor_max_length) {
      session.monitor_log = session.monitor_log.slice(
        // Getting the last entries
        -1 * session.monitor_max_length,
      );
    }
    monitor_common();
  });
}

/**
 * Getting the monitoring stream update from a log signal.
 */
function update_monitor_entry(msg) {
  session.monitor_log.push(msg);
  while (session.monitor_log.length > session.monitor_max_length) {
    session.monitor_log.shift();
  }
  monitor_common();
}

/**
 * Common tasks to perform after a monitoring update is received.
 *
 * Aside from updating the plots used for the system monitoring, we also make
 * some simple string checks.
 *
 */
function monitor_common() {
  plot_monitor_data(); /** in view/plotting.js */
  plot_coordinate_data(); /** in view/plotting.js */

  const state_str = session.state() ? 'RUNNING' : 'IDLE';
  $('#up-time-since').html(`Session is: ${state_str}`);

  // Setting all action buttons to be disabled.
  $('button.action-button').each(function () {
    $(this).prop('disabled', session.state() == Session.SESSOIN_RUNNING_CMD);
  });
}

/**
 * Getting the command output log that is stored in memory of the main server
 * session. Here we pull the entire log via a ajax request rather than have the
 * server send individual log entries to avoid race conditions.
 */
function sync_system_log(msg) {
  ajax_request('/logdump/session', async function (json) {
    session.session_log = json.log_dump;
    if (session.session_log.length > session.session_max_length) {
      session.session_log = session.session_log.slice(
        // Getting the last entries
        -1 * session.session_max_length,
      );
    }

    system_log_common();
  });
}

/**
 * Function to run on a new command log entry emitted by the server session.
 */
function update_system_entry(msg) {
  session.session_log.push(msg);
  while (session.session_log.length > session.session_max_length) {
    session.session_log.shift();
  }

  system_log_common();
}

/**
 * Common element routines for updating the display element when receiving the
 * session_log update.
 */
function system_log_common() {
  // Making the display table, defined in views/controls.js
  tabular_session();

  // Checking the last command entry. Update the command progress bar
  // accordingly.
  const last_cmd = session.last_cmd();
  let pbar_dom = $('#command-progress-display');
  pbar_dom.removeClass();
  if (last_cmd === undefined) {
    // If last command was not found
    pbar_dom.addClass('progress-complete');
  } else if (last_cmd.args[0] == 'stop') {
    // If last command is stopped check if it is in error state.
    if (last_cmd.args[1] == 0) {
      pbar_dom.addClass('progress-complete');
    } else {
      pbar_dom.addClass('progress-error');
    }
  } else if (last_cmd.args[0] == 'start') {
    pbar_dom.addClass('progress-complete');
  } else if (last_cmd.args[0] == 'request_input') {
    pbar_dom.addClass('progress-running');
  }

  // Check the last command entry. If it is a request input entry. Open the user
  // interface request. Otherwise, explicitly wipe and hide the user action tab
  if (last_cmd == undefined) {
  } else if (last_cmd.args[0] == 'request_input') {
    $('#user-action-msg').html(last_cmd.msg);
    $('#user-action').removeClass('hidden');
  } else {
    $('#user-action-msg').html('');
    $('#user-action').addClass('hidden');
  }
}

/**
 * Updating the the progress bar.
 */
function update_progress(msg) {
  if (msg.desc != 'session-progress') {
    // Command progress
    const cmd = msg.desc.replace(/\].*/, '').replace(/.*\[/, '');
    const n = msg.n;
    const total = msg.total;
    const rate = (n / total) * 100;
    $('#command-progress-display').attr('style', `width:${rate}%;`);
    $('#command-progress-desc').html(
      `${cmd} ${rate.toFixed(1)}% [${n}/${total}]`,
    );
  } else {
  }
}

/**
 * Server shutdown signal. To avoid issues with trailing script states loading
 * when the server maybe restarted, here we force the client to move to a blank
 * page to force clear the client script state.
 */
function server_shutdown(msg) {
  console.log('shutdown signal received!');
  location.replace('about:blank'); // Standard blank page for Firefox and Chromium
}
