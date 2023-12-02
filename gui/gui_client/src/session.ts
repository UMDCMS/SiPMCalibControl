// /**
//  * session.ts
//  *
//  * Defining the client side session instance. Session will be declared as a
//  * variable container, and all function will use this same instance. Function
//  * attempting to synchronize information between the client and server side as
//  * close as possible is defined in js/synchronize.js.
//  *
//  * In this file, we also provide functions will be commonly used by the client
//  * side functions.
//  */
// class Session {
//   // Static variable for global objects
//   static SESSION_IDLE = 0;
//   static SESSOIN_RUNNING_CMD = 1;

//   // Variables used for storing the socket.io connection.
//   constructor() {
//     this.socketio = null;

//     // This is the array for storing the logging entries. As these array logs are
//     // also used display element generation, we will also set a maximum length
//     // here and have the log entries be a first-in-first-out dequeue.
//     this.monitor_max_length = 1024;
//     this.monitor_log = [];
//     this.session_max_length = 65536;
//     this.session_log = [];
//   }
// }

export {};
