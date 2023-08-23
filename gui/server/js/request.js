/**
 * @file: THis is a atest
 *
 * request.js
 *
 * The handling of the AJAX request to be initiated from client side. Here, the
 * data processing should only be up to the manipulation of the data defined in
 * the global.js related variables, or single line element edits. Any more
 * processing with the manipulation of the display elements should be placed in
 * the corresponding view/*.js files.
 *
 **/

// const { ajax } = require('jquery');

/**
 * Clear client side settings. Request a new set of setting from server side and
 * update accordingly.
 */
async function clear_settings() {
  ajax_request('devicesettings', update_settings, 500);
}


/**
 * Function for requesting plot data by some detector ID of the current
 * calibration session.
 *
 * The following inputs is required:
 * - A legal detector ID in the current calibration session.
 * - The plot-type to reduce the information.
 * - The element id to store the plot.
 *
 * In the case that the corresponding data file is not found. A console log is
 * generated.
 */
async function request_plot_by_detid(detid, type, id) {
  ajax_request(`data/${type}/${detid}`, async function (json) {
    parse_plot_data(json, id);
  });
}

/**
 * Updating the list of tileboards that are available in the calibration server
 * settings. This is done by submitting an ajax request to the tileboard-type.
 * For both the system and standard calibration processes.
 */
function update_tileboard_types() {
  ajax_request(`report/systemboards`, function (json) {
    update_tileboard_list('system', json);
  });
  ajax_request(`report/standardboards`, function (json) {
    update_tileboard_list('standard', json);
  });
  //update_tileboard_list(`system`);
  //update_tileboard_list(`standard`);
}

/**
 * Updating the display of reference calibration results available. This is
 * performed via an AJAX request.
 */
function request_valid_reference() {
  ajax_request('report/validreference', update_valid_reference);
}
