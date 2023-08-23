/**
 * view/settings.js
 *
 * Manipulation of display elements related to the settings configuration on the
 * client side.
 */

/**
 * Given a new settings in json format. Update all DOM elements according to the
 * new settings.
 */
function update_settings(json) {
  // Image settings.
  $('#image-threshold-text').val(json.image.threshold);
  $('#image-blur-text').val(json.image.blur);
  $('#image-lumi-text').val(json.image.lumi);
  $('#image-size-text').val(json.image.size);
  $('#image-ratio-text').val(json.image.ratio);
  $('#image-poly-text').val(json.image.poly);

  unify_range_to_text_by_id(`image-threshold-text`);
  unify_range_to_text_by_id(`image-blur-text`);
  unify_range_to_text_by_id(`image-lumi-text`);
  unify_range_to_text_by_id(`image-size-text`);
  unify_range_to_text_by_id(`image-ratio-text`);
  unify_range_to_text_by_id(`image-poly-text`);

  // Z-scan settings
  $('#zscan-settings-samples').val(json.zscan.samples);
  $('#zscan-settings-pwm').val(json.zscan.pwm.join(' '));
  $('#zscan-settings-zval-dense').val(json.zscan.zdense.join(' '));
  $('#zscan-settings-zval-sparse').val(json.zscan.zsparse.join(' '));

  // Low-light settings
  $('#lowlight-settings-samples').val(json.lowlight.samples);
  $('#lowlight-settings-pwm').val(json.lowlight.pwm);
  $('#lowlight-settings-zval').val(json.lowlight.zval);

  // luminosity alignment settings
  $('#lumialign-settings-samples').val(json.lumialign.samples);
  $('#lumialign-settings-pwm').val(json.lumialign.pwm);
  $('#lumialign-settings-zval').val(json.lumialign.zval);
  $('#lumialign-settings-range').val(json.lumialign.range);
  $('#lumialign-settings-distance').val(json.lumialign.distance);

  // DRS settings
  $('#drs-triggerdelay').val(json.drs['triggerdelay']);
  $('#drs-samplerate').val(json.drs['samplerate']);
  $('#drs-samples').val(json.drs['samples']);

  // Picoscope settings.
  $('#channel-a-range').val(json.picoscope['channel-a-range']);
  $('#channel-b-range').val(json.picoscope['channel-b-range']);
  $('#trigger-delay').val(json.picoscope['trigger-delay']);
  $('#trigger-presample').val(json.picoscope['trigger-presample']);
  $('#trigger-postsample').val(json.picoscope['trigger-postsample']);
  $('#trigger-blocksize').val(json.picoscope['blocksize']);

  $('#trigger-level-text').val(adc_from_value(json.picoscope['trigger-value']));
  $('#trigger-level-range').val(
    adc_from_value(json.picoscope['trigger-value']),
  );
  $(
    `input[name="trigger-channel"][value="${json.picoscope['trigger-channel']}"]`,
  ).prop('checked', true);
  $(
    `input[name="trigger-direction"][value="${json.picoscope['trigger-direction']}"]`,
  ).prop('checked', true);
  unify_pico_range();
  unify_pico_trigger();
}

/**
 * Converting the range index to the corresponding mV value.
 */
function range_to_mv(range) {
  switch (range) {
    case '3':
      return 100;
    case '4':
      return 200;
    case '5':
      return 500;
    case '6':
      return 1000;
    case '7':
      return 2000;
    case '8':
      return 5000;
    case '9':
      return 10000;
    case '10':
      return 20000;
    default:
      return 0;
  }
}

/**
 * Given the raw ADC value and a given channel, convert to the corresponding mV
 * value. Not used for readout, only for client side trigger level conversion.
 */
function value_from_adc(adc, channel) {
  const range_idx =
    parseInt(channel) == 0
      ? $('#channel-a-range').val()
      : parseInt(channel) == 1
      ? $('#channel-b-range').val()
      : '10';
  return (adc * range_to_mv(range_idx)) / 32768;
}

/**
 * Given some mV value for a given channel, translate to a raw ADC value (round
 * down). Not used for readout, only for client side trigger level conversion.
 */
function adc_from_value(value, channel) {
  const range_idx =
    parseInt(channel) == 0
      ? $('#channel-a-range').val()
      : parseInt(channel) == 1
      ? $('#channel-b-range').val()
      : '10';
  return parseInt((value * 32768) / range_to_mv(range_idx));
}

/**
 * Showing the (non-input) text of the range for each channel. According to the
 * slider settings.
 */
function unify_pico_range() {
  const id_list = ['channel-a-range', 'channel-b-range'];

  for (const id of id_list) {
    const range_mv = range_to_mv($(`#${id}`).val());
    $(`#${id}-value`).html(
      range_mv < 1000
        ? `${parseInt(range_mv)} mV`
        : `${parseInt(range_mv / 1000)} V`,
    );
  }
}

/**
 * Ensuring that the pico trigger settings in text and slider form match.
 */
function unify_pico_trigger() {
  var adc = $('#trigger-level-text').val();
  var channel = $("input[name='trigger-channel']:checked").val();
  var level = value_from_adc(parseInt(adc), channel);
  var unit = 'mV';
  if (level > 1000) {
    unit = 'V';
    level /= 1000;
  } else if (level < -1000) {
    unit = 'V';
    level /= 1000;
  }

  $('#trigger-level-converted').html('(' + level.toFixed(1) + unit + ')');
}
/**
 * Helper function to parse a strings separated by white spaces to an array of
 * floats
 */
function split_string_to_float_array(input_string) {
  let str_array = input_string.split(/(\s+)/).filter((e) => e.length > 1);
  var ans = [];
  for (const str of str_array) {
    const token = parseFloat(str);
    if (!token.isNaN()) {
      ans.append(token);
    }
  }
  return ans;
}
/**
 * Given an id of a slider (range) field. Find the corresponding DOM element of
 * a text input field and update the text input field to match the slider input.
 */
function unify_text_to_range_by_id(range_id) {
  const text_id = range_id.replace('-range', '-text');
  $(`#${text_id}`).val($(`#${range_id}`).val());
}

/**
 * Given an id of the text input file, find the corresponding DOM element of a
 * slider (range) input field and update the slider value to match the text
 * input. In the case that the text input is out of the slider range, move to end
 * points, and fix the text value to end point.
 */
function unify_range_to_text_by_id(text_id) {
  var range_id = text_id.replace('-text', '-range');
  var max_val = parseFloat($(`#${range_id}`).attr('max'));
  var min_val = parseFloat($(`#${range_id}`).attr('min'));

  // Truncating the range.
  if ($(`#${text_id}`).val() > max_val) {
    $(`#${text_id}`).val(max_val);
  } else if ($(`#${text_id}`).val() < min_val) {
    $(`#${text_id}`).val(min_val);
  }

  $(`#${range_id}`).val($(`#${text_id}`).val());
}

/**
 * Thin wrapper to call unify_text_to_range_by_id given a DOM event.
 */
function unify_text_to_range(event) {
  unify_text_to_range_by_id(event.target.id);
}

/**
 * Thin wrapper to call unify_range_to_text_by_id given an DOM event.
 */
function unify_range_to_text(event) {
  unify_range_to_text_by_id(event.target.id);
}
