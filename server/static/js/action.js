/********************************************************************************
 *
 * action.js
 *
 * Master file for "actions" should be initiated client side. Actions here by
 * means that once the data is sent, the client should not need additional
 * parsing. If display elements should be alter from the server side, the client
 * should wait for the appropriate signals to be initiated form the server side.
 *
 *******************************************************************************/

/**
 * Simplified interface for emitting a user action to the socket interface.
 *
 * 'id' is used to classify the action to be carried out by the main session.
 * 'msg' is used for any accompanying data to be used.
 */
function emit_action_cmd(id, msg) {
  $('#display-message').html('');
  socketio.emit('run-action-cmd', { id: id, data: msg });
}

/**
 * Action to send to the server on the completion of the user action. Hide the
 * tab showing the required user action.
 */
function complete_user_action() {
  hide_action_column();
  $('#user-action').addClass('hidden');
  socketio.emit('complete-user-action', '');
}

/**
 * Process defined to running a system calibration.
 *
 * Check if the inputs are OK. If not then the function will not execute.
 */
function run_system_calibration() {
  console.log(`Starting system calibration`);
  var boardtype = $('input[name="system-calibration-boardtype"]:checked').val();

  if (boardtype == undefined) {
    $('#system-calib-submit-error').html(
      'System calibration board type not selected'
    );
  } else {
    $('#system-calib-submit-error').html('');
    emit_action_cmd('run-system-calibration', {
      boardtype: boardtype,
    });

    hide_action_column();
  }
}

function run_std_calibration() {
  boardid = $('#std-calibration-boardid').val();
  boardtype = $('input[name="standard-calibration-boardtype"]:checked').val();
  reference = $('input[name="ref-calibration"]:checked').val();

  if (boardid === '') {
    $('#standard-calib-submit-error').html('Board ID not specified');
  } else if (boardtype == undefined) {
    $('#standard-calib-submit-error').html(
      'Board type for standard calibration is not selected'
    );
  } else if (reference == undefined) {
    $('#standard-calib-submit-error').html(
      'Reference calibration session is not selected'
    );
  } else {
    $('#standard-calib-submit-error').html('');
    emit_action_cmd('run-std-calibration', {
      boardid: boardid,
      boardtype: boardtype,
      reference: reference,
    });

    hide_action_column();
  }
}

/**
 * Collecting the additional client-side data required for the calibration
 * sign-off. The comments is set up as a map passed to the main calibration
 * session. The user id and the password of the central processing server is also
 * collected here. This function will not clear anything, and will wait for the
 * system to send the sync signal indicating sign-off completion before wiping
 * the display data.
 */
async function calibration_signoff(session_type) {
  var comment_map = {};

  $(`#${session_type}-calib-signoff-container`)
    .children('.signoff-comment-lines')
    .find('.comment-header')
    .each(function (index) {
      var det_id = $(this).val();
      var comment = $(this)
        .parent()
        .siblings('.comment-content')
        .children('.comment-text')
        .val();
      if (!(det_id in comment_map)) {
        comment_map[det_id] = comment;
      } else {
        comment_map[det_id] += '\n' + comment;
      }
    });

  emit_action_cmd(`${session_type}-calibration-signoff`, {
    comments: comment_map,
    user: $(`#${session_type}-calib-user-id`).val(),
    pwd: $(`#${session_type}-calib-user-pwd`).val(),
  });

  await sleep(100);
  request_valid_reference();
}

function system_calibration_signoff() {
  calibration_signoff('system');
}
function standard_calibration_signoff() {
  calibration_signoff('standard');
}

/**
 * Rerunning a calibration process for a single detector, either to extend the
 * amount of data collected or to perform a clean rerun. If the calibration
 * process is tied to a plot, and a hard re-run is requested, then the old plot
 * is first cleared from the existing HTML element.
 */
async function rerun_single(action_tag, detid, extend) {
  emit_action_cmd('rerun-single', {
    action: action_tag,
    detid: detid,
    extend: extend,
  });
  const plot_processes = ['zscan', 'lowlight', 'lumialign'];

  // Adding the plotting section if the plotting section didn't already exists
  if (plot_processes.indexOf(action_tag) > 0) {
    console.log(action_tag);
    console.log($(`#single-det-summary-plot-${detid}-${action_tag}`).length);

    if ($(`#single-det-summary-plot-${detid}-${action_tag}`).length == 0) {
      // Generating a new plot div for data display
      $(`#det-plot-container-${detid}`)
        .children('.plot-container')
        .append(
          dom('div', {
            class: 'plot',
            id: `single-det-summary-plot-${det_id}-${action_tag}`,
          })
        );
    } else {
      if (!extend) {
        Plotly.purge(`single-det-summary-plot-${detid}-${action_tag}`);
        $(`#single-det-summary-plot-${detid}-${action_tag}`).html('');
      }
    }
  }

  await sleep(100);
  request_plot_by_detid(detid, action_tag, detector_plot_id(detid, action_tag));
}

/**
 * Asking the session to execute the drs debugging sequence
 */
async function debug_request_plot() {
  file = $('#debug-plot-file').val();
  type = $('input[name="debug-plot-type"]:checked').val();
  console.log(file, type);
  request_plot_by_file(file, type, 'debug-plot-div');
}

/********************************************************************************
 *
 * SETTING RELATED FUNCTIONS.
 *
 *******************************************************************************/

/**
 * Action emitting function for submitting the changes on the image processing
 * changes from the client to the main session manager.
 */
function image_settings_update() {
  const new_settings = {
    threshold: $('#image-threshold-text').val(),
    blur: $('#image-blur-text').val(),
    lumi: $('#image-lumi-text').val(),
    size: $('#image-size-text').val(),
    ratio: $('#image-ratio-text').val(),
    poly: $('#image-poly-text').val(),
  };

  emit_action_cmd('image-settings', new_settings);
}

/**
 * Action emitting function for submitting the changes on the zscan setting to
 * the main session manager.
 */
function zscan_settings_update() {
  const new_settings = {
    samples: $('#zscan-settings-samples').val(),
    pwm: split_string_to_float_array($('#zscan-settings-pwm').val()),
    zlist_dense: split_string_to_float_array(
      $('#zscan-settings-zval-dense').val()
    ),
    zlist_sparse: split_string_to_float_array(
      $('#zscan-settings-zval-sparse').val()
    ),
  };

  emit_action_cmd('zscan-settings', new_settings);
}

/**
 * Action emitting function for submitting the changes on the lowlight scan
 * settings to the main session manager.
 */
function lowlight_settings_update() {
  const new_settings = {
    samples: $('#lowlight-settings-samples').val(),
    pwm: $('#lowlight-settings-pwm').val(),
    zval: $('#lowlight-settings-zval').val(),
  };

  emit_action_cmd('lowlight-settings', new_settings);
}

/**
 * Action emitting function for submitting the changes on the lumi-alignment
 * calibration settings to the main session manager.
 */
function lumialign_settings_update() {
  const new_settings = {
    samples: $('#lumialign-settings-samples').val(),
    pwm: $('#lumialign-settings-pwm').val(),
    zval: $('#lumialign-settings-zval').val(),
    range: $('#lumialign-settings-range').val(),
    distance: $('#lumialign-settings-distance').val(),
  };

  emit_action_cmd('lumialign-settings', new_settings);
}

/**
 * Action emitting function for submitting the changes on the picoscope readout
 * settings to the main session manager.
 */
function picoscope_settings_update() {
  const trigger_level = value_from_adc(
    $('#trigger-level-text').val(),
    $('input[name="trigger-channel"]:checked').val()
  );

  const new_settings = {
    'channel-a-range': $('#channel-a-range').val(),
    'channel-b-range': $('#channel-b-range').val(),
    'trigger-channel': $('input[name="trigger-channel"]:checked').val(),
    'trigger-level': trigger_level,
    'trigger-direction': $('input[name="trigger-direction"]:checked').val(),
    'trigger-delay': $('#trigger-delay').val(),
    presample: $('#trigger-presample').val(),
    postsample: $('#trigger-postsample').val(),
    blocksize: $('#trigger-blocksize').val(),
  };

  emit_action_cmd('picoscope-settings', new_settings);
}

/**
 * Action emitting function for submitting changes to the drs readout settings to
 * the main session manager.
 */
function drs_settings_update() {
  const new_settings = {
    'drs-triggerdelay': $('#drs-triggerdelay').val(),
    'drs-samplerate': $('#drs-samplerate').val(),
    'drs-samples': $('#drs-samples').val(),
  };

  emit_action_cmd('drs-settings', new_settings);
}

/**
 * Action emitting function for submitting a calibration call to the DRS manager.
 */
var SEND_CALIB_SIGNAL = 0;
function drs_settings_calib() {
  console.log('Sending the DRS calibration signal', session.state);
  emit_action_cmd('drs-calib', {});
  SENT_CALIB_SIGNAL = 1;
}

/**
 * Additional function used to handle additional processes to run when the
 * calibration is done. Since the calibration changes some of the settings. we
 * are going to rerun the drs_settings_update command if this machine is the one
 * that requested the calibration process to be ran.
 */
function drs_calib_complete() {
  if (SENT_CALIB_SIGNAL == 1) {
    drs_settings_update();
    SENT_CALIB_SIGNAL = 0;
  }
}

/** ========================================================================== */
/** PICOSCOPE SETTING FUNCTIONS */
/** Below are function specific to the step of the picoscope readout system.
 *   Since these function are only used by the picoscope function and nowhere
 *   else. Though these function uses css manipulation, it was decided to put the
 *   following function in the settings.js file.
 */
/** ========================================================================== */
