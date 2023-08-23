/**
 * session.js
 *
 * Defining the client side session instance. Session will be declared as a
 * variable container, and all function will use this same instance. Function
 * attempting to synchronize information between the client and server side as
 * close as possible is defined in js/synchronize.js.
 *
 * In this files, we also provide functions will be commonly used by the client
 * side functions.
 */
class Session {
  // Static variable for global objects
  static SESSION_IDLE = 0;
  static SESSOIN_RUNNING_CMD = 1;

  // Variables used for storing the socket.io connection.
  constructor() {
    this.socketio = null;

    // This is the array for storing the logging entries. As these array logs are
    // also used display element generation, we will also set a maximum length
    // here and have the log entries be a first-in-first-out dequeue.
    this.monitor_max_length = 1024;
    this.monitor_log = [];
    this.session_max_length = 65536;
    this.session_log = [];
  }
}

/**
 * Checking whether the session is currently executing a command.
 *
 * As state changes are always reported in the monitoring log, and is updated
 * immediately whenever the server session receives and action request, this is
 * simply done by looking at the last entry in the monitoring log.
 */
Session.prototype.state = function () {
  if (this.monitor_log.length > 0) {
    return this.monitor_log[this.monitor_log.length - 1].state;
  } else {
    return null
  }
};

/**
 * Getting the last command entry in the system log. Since this is used rather
 * often for the various output elements, this is now a designated member function
 */
Session.prototype.last_cmd = function () {
  return this.session_log.findLast(function (entry) {
    return entry.levelno == 5;
  });
};

var session = new Session();

/**
 * Basic function to allow for async functions to sleep for a certain duration.
 * Main reference:
 * https://www.sitepoint.com/delay-sleep-pause-wait/
 */
function sleep_ms(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Simple function for making DOM elements in a single function call without the
 * need for custom tag handling.
 */
function dom(tag, attr, content = '') {
  let ans = $(`<${tag}></${tag}>`);
  ans.attr(attr);

  if (typeof content === 'string') {
    ans.html(content);
  } else if (content instanceof Array) {
    content.forEach((element) => {
      ans.append(element);
    });
  }
  return ans;
}

/**
 * Simple function for making DOM elements for svg inputs. This needs because the
 * HTML/SVG uses not-entirely compatible XML tags and thus and requires
 * additional namespace settings to work [1]. For the sake of consistency, we
 * will be using the JQuery-flavored version of generation the tag [2].
 * [1] https://stackoverflow.com/questions/3642035/jquerys-append-not-working-with-svg-element
 * [2] https://stackoverflow.com/questions/2572304/what-is-jquery-for-document-createelementns
 */
function svgdom(tag, attr, content = '') {
  let ans = $(document.createElementNS('http://www.w3.org/2000/svg', tag));
  ans.attr(attr);

  if (typeof content === 'string') {
    ans.html(content);
  } else if (content instanceof Array) {
    content.forEach((element) => {
      ans.append(element);
    });
  }

  return ans;
}

/**
 * Master function for submitting an AJAX request, since most of all return types
 * are JSON object. The user is responsible for providing:
 * - The URL for the request
 * - The function to execute on success (should have a single json input as the return).
 * - A retry interval (leave negative if the request should not be done)
 * - A custom fail message (leave blank if default)
 */
async function ajax_request(
  url,
  success,
  retry = -1,
  fail_msg = '',
  max_try = 10,
) {
  $.ajax({
    dataType: 'json',
    mimeType: 'application/json',
    url: url,
    success: success,
    error: async function () {
      // Logging the fail message
      msg = fail_msg == '' ? `AJAX request for URL "${url}" failed.` : fail_msg;
      console.log(msg);

      if (retry > 0 && max_try > 0) {
        if (max_try > 0) {
          await sleep(retry);
          ajax_request(url, success, retry, fail_msg, max_try - 1);
        } else {
          console.log(
            `Failed too many times, not attempting ajax request at ${url}`,
          );
        }
      }
    },
  });
}
