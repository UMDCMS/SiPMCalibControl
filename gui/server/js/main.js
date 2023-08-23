/**
 * main.js
 *
 * Defining the socket, how the socket should initializing the document on load,
 * and various interface initializing processes.
 */
$(function () {
  /**
   * Display settings
   *
   * Setting up the functions for dynamic element styling. This should only
   * include elements that does not require the receiving data from the main
   * session server. Most of these function will be found in the
   * js/view/layout.js file.
   */
  $('button.action-button').each(function () {
    // Setting all action buttons to be disabled.
    $(this).prop('disabled', true);
  });
  show_monitor_column(); // Have all monitor tab be shown by default.
  $('#action-column-toggle').on('click', toggle_action_column);
  $('#monitor-column-toggle').on('click', toggle_monitor_column);
  $('.input-row > input[type="range"]').on('input', unify_text_to_range);
  $('.input-row > input[type="text"]').on('input', unify_range_to_text);
  $('input[id^="channel-"][id$="-range"]').on('input', unify_pico_range);
  $('input[id^="trigger-level"]').on('input', unify_pico_trigger);
  $('.tab-title').on('click', function () {
    tab_click($(this));
  });
  $('.add-comment-line').on('click', function () {
    add_comment_line($(this));
  });
  update_indicator(); // Updating all the close-tag icons

  draw_tileboard_view_common(); // Drawing the common elements of the
  // tileboard layout.
  $('.log-display-check').on('click', update_log_display);

  /**
   * Connecting to the main server through socket.io.
   *
   * All socket related actions should only be done after the connection has
   * been confirmed and some book keeping function have been performed.
   *
   */
  session.socketio = io();
  session.socketio.on('connect', function (msg) {
    console.log('We are connect!'); //

    // Synchronizing the monitor and session log to client side. These functions
    // are defined in the js/synchronize.js file
    sync_monitor_log();
    sync_system_log();

    // Defining show what should be done when receiving a signal from the main
    // server session. These functions are defined in js/synchronize.js
    session.socketio.on('monitor-info', update_monitor_entry);
    session.socketio.on('logging-info', update_system_entry);
    session.socketio.on('progress-update', update_progress);
    session.socketio.on('server-shutdown', server_shutdown);

    // Interaction buttons for the interacting with the main session. Mainly
    // defined in js/action.js
    $('#session-cmd-lock-toggle').on('click', session_cmd_lock_toggle);
    $('#session-cmd-send').on('click', session_cmd_send);
    $('#interrupt-send').on('click', session_interrupt_send);
    $('#user-action-check').on('click', user_action_send_check);
    $('#debug-request-guess').on('click', debug_request_guess);
    $('#debug-request-plot').on('click', debug_request_plot);
  });

  // Connect to the network socket

  //console.log(session);
  //console.log(session.socketio);

  // The display will always be asynchronous, with the client is responsible for
  // asking for the current state of the server. This allows for multiple
  // clients to be connected to the same session for easier on-site debugging.

  /**
   * Listing socket actions to perform on specific button presses
   * And responding to action-response commands.
   * Functions here will be implemented in the action.js file
   */
  // $('#run-system-calibration').on('click', run_system_calibration);
  // $('#run-std-calibration').on('click', run_std_calibration);
  // $('#system-calib-signoff').on('click', system_calibration_signoff);
  // $('#standard-calib-signoff').on('click', standard_calibration_signoff);
  // $('#debug-request-plot').on('click', debug_request_plot);
  // $('#image-settings-update').on('click', image_settings_update);
  // $('#zscan-settings-update').on('click', zscan_settings_update);
  // $('#lowlight-settings-update').on('click', lowlight_settings_update);
  // $('#lumialign-settings-update').on('click', lumialign_settings_update);
  // $('#picoscope-settings-update').on('click', picoscope_settings_update);
  // $('#drs-settings-update').on('click', drs_settings_update);
  // $('#drs-settings-calib').on('click', drs_settings_calib);
  // $('#image-settings-clear').on('click', clear_settings);
  // $('#zscan-settings-clear').on('click', clear_settings);
  // $('#lumialign-settings-clear').on('click', clear_settings);
  // $('#lowlight-settings-clear').on('click', clear_settings);
  // $('#picoscope-settings-clear').on('click', clear_settings);
  // $('#drs-settings-clear').on('click', clear_settings);
  // clear_settings(); // Clearing settings when document first loads
});
