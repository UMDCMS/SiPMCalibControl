/**
 * Parsing the return from the server of a parse request.
 *
 * The return should be in the json format of
 *
 * ```
 * {
 *    'filename': 'file that is used to generate the data',
 *    'type': 'Type of plot used for the reduction of data',
 *    'update': A true/false flag indicating whether the target file is
 *              expecting more updates.
 *    'data': arbitrarily complicated function used for plotting all the
 *            information needed.
 * }
 * ```
 *
 * In case update is set to true, the function will wait for 100ms before
 * resubmitting a data request to the server. As no data caching will be handled
 * on the server, extensive resubmission will be very computationally expensive.
 */

// Default plotting layout settings for all plots
const layout_default_config = {
  displayModeBar: false /** Do not add widgets to change plot range */,
  responsive: true /** Scales with CSS geometry changes */,
};

/**
 * Function for requesting plot data directly by filename.
 *
 * The following inputs is required:
 * - The filename used to extract plotting information.
 * - The plot-type to reduce the information.
 * - The element id to store the plot.
 *
 * The file name needs to be adjusted to replace the slashed with a unique
 * character not typically used for file naming while being URL safe (ex. using
 * @ for now).
 */
function plot_data_to_id(data, plot_type, div_id) {
  token = data.token;
  filename = data.filename;
  plotdata = data.data;

  if ($(`#${div_id}`).length == 0) {
    console.log(`DIV doesn't exist for plotting`);
    console.log(plotdata);
  } else {
    switch (plot_type) {
      case 'xyz':
        plot_heat_map(div_id, plotdata);
        break;
      case 'hist':
        plot_histogram(div_id, plotdata);
        break;
      case 'zscan':
        plot_zscan(div_id, plotdata);
        break;
      case 'time':
        plot_tscan(div_id, plotdata);
      default:
        console.log('Unknown plot type', plot_type);
    }
  }
}

/**
 * Plotting the output x-y-z data format.
 */
function plot_heat_map(div, data) {
  let z = [];
  for (const entry of data.readout) {
    z.push(entry[0]);
  }
  const plotly_data = [
    {
      x: data.x,
      y: data.y,
      z: z,
      type: 'contour',
      colorscale: 'RdBu',
    },
  ];

  const layout = {
    autosize: true,
    xaxis: {
      title: 'x position [mm]',
      autorange: true,
    },
    yaxis: {
      title: 'y position [mm]',
      autorange: true,
    },
    colorbar: {
      title: 'Readout [mV-ns]',
      titleside: 'right',
    },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: {
      l: 60,
      r: 20,
      b: 40,
      t: 20,
      pad: 5,
    },
    title: false,
  };

  $(`#${div}`).css('height', '300px');
  $(`#${div}`).css('width', '400px');
  Plotly.newPlot(div, plotly_data, layout, layout_default_config);
}

/**
 * Plotting the output in histogram format.
 */
function plot_histogram(div, data) {
  var x = [];
  for (var i = 0; i < data.values.length; ++i) {
    x.push((data.edges[i] + data.edges[i + 1]) / 2.0);
  }

  const plotly_data = [
    {
      x: x,
      y: data.values,
      type: 'bar',
      mode: 'markers',
      name: `Mean: ${data.mean.toFixed(2)} RMS:${data.rms.toFixed(2)}`,
      marker: {
        color: 'rgb(41,55,199)',
      },
    },
  ];

  const layout = {
    autosize: true,
    xaxis: {
      title: 'Readout value [mV-ns]',
      autorange: true,
    },
    yaxis: {
      type: 'log',
      title: 'Events',
      autorange: true,
    },
    showlegend: true,
    legend: {
      x: 1,
      y: 1,
      xanchor: 'right',
    },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    bargap: 0, // For a continuous block histogram
    margin: {
      l: 60,
      r: 20,
      b: 40,
      t: 20,
      pad: 5,
    },
    title: false,
  };

  $(`#${div}`).css('height', '300px');
  $(`#${div}`).css('width', '400px');

  Plotly.newPlot(div, plotly_data, layout, layout_default_config);
}

function plot_zscan(div, data) {
  var v = [];
  var vu = [];
  for (const entry of data.readout) {
    v.push(entry[0]);
    vu.push(entry[1]);
  }

  var plotly_data = [
    {
      x: data.z,
      y: v,
      error_y: {
        type: 'data',
        array: vu,
        visible: true,
      },
      marker: {
        size: 5,
        color: data.p,
        colorscale: 'Bluered',
        colorbar: {
          title: 'Bias [mV]',
        },
      },
      type: 'scatter',
      mode: 'markers',
      name: 'Readout value',
    },
  ];

  console.log(plotly_data)

  layout = {
    autosize: true,
    xaxis: {
      type: 'log',
      title: 'Gantry z [mm]',
      autorange: true,
    },
    yaxis: {
      type: 'log',
      title: 'Readout [mV-ns]',
      autorange: true,
    },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: {
      l: 60,
      r: 20,
      b: 40,
      t: 20,
      pad: 5,
    },
    title: false,
  };

  $(`#${div}`).css('height', '300px');
  $(`#${div}`).css('width', '400px');
  Plotly.newPlot(div, plotly_data, layout, layout_default_config);
}

function plot_tscan(div, data) {
  console.log('plotting tscan', data);
}

/**
 * Plotting the the monitoring data.
 *
 * Styling information is placed at the bottom
 * of the file to reduce verbosity.
 */
function plot_monitor_data() {
  let time = [];
  let sipm_temp = [];
  let pulser_temp = [];
  let pulser_volt = [];

  for (const entry of session.monitor_log) {
    time.push(new Date(Math.round(entry.created * 1000)));
    pulser_temp.push(entry.pulser_temp);
    sipm_temp.push(entry.sipm_temp);
    pulser_volt.push(entry.pulser_lv);
  }

  const temperature_data = [
    {
      x: time,
      y: pulser_temp,
      type: 'scatter',
      mode: 'lines',
      name: 'Pulser',
    },
    {
      x: time,
      y: sipm_temp,
      type: 'scatter',
      mode: 'lines',
      name: 'Tileboard',
    },
  ];
  const temperature_plot_layout = {
    autosize: true,
    xaxis: {
      title: 'Time',
      nticks: 4,
    },
    yaxis: {
      title: 'Temperature [°C]',
      range: [
        Math.min(15, Math.min(...sipm_temp) - 2, Math.min(...pulser_temp) - 2),
        Math.max(24, Math.max(...sipm_temp) + 2, Math.max(...pulser_temp) + 2),
      ],
    },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: {
      l: '40',
      r: '5',
      b: '40',
      t: '10',
      pad: 0,
    },
    legend: {
      x: 0.5,
      y: 0.9,
    },
  };

  const voltage_data = [
    {
      x: time,
      y: pulser_volt,
      type: 'scatter',
      mode: 'lines',
      name: 'Pulser board Bias',
      showlegend: true,
    },
  ];

  const voltage_plot_layout = {
    autosize: true,
    xaxis: {
      title: 'Time',
      nticks: 4,
    },
    yaxis: {
      title: 'Voltage [mV]',
      range: [0, 5000],
    },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: {
      l: '60',
      r: '5',
      b: '40',
      t: '10',
      pad: 0,
    },
    legend: {
      x: 0.5,
      y: 0.9,
    },
  };

  if ($(`#temperature-plot`).length != 0) {
    Plotly.newPlot(
      'temperature-plot',
      temperature_data,
      temperature_plot_layout,
      layout_default_config,
    );
  } else {
    console.log('temperature-plot DIV does not exist!');
  }

  if ($('#voltage-plot').length != 0) {
    Plotly.newPlot(
      'voltage-plot',
      voltage_data,
      voltage_plot_layout,
      layout_default_config,
    );
  } else {
    console.log('voltage-plot DIV does nto exist!');
  }
}

/**
 * Two parts needs to be updated regarding the values. One is a text based
 * display of the coordinates values in the monitor tab. The other is the
 * graphical elements in the tile-board view.
 */
function plot_coordinate_data() {
  if (session.monitor_log.length == 0) {
    return;
  } // Early exit for empty log entry.
  const last = session.monitor_log.length - 1;
  const x = session.monitor_log[last].gantry_coord[0];
  const y = session.monitor_log[last].gantry_coord[1];
  const z = session.monitor_log[last].gantry_coord[2];
  $(`#gantry-coordinates`).html(
    `Gantry coordinates: (${x.toFixed(1)}, ${y.toFixed(1)}, ${z.toFixed(1)})`,
  );

  $('#tile-layout-gantry-svg').html('');
  $('#tile-layout-gantry-svg').append(
    svgdom('polyline', {
      points: `${x + 20},${510 - y} ${x + 25},${525 - y}  ${x + 30},${510 - y}`,
      stroke: 'red',
      fill: 'red',
      'stroke-width': '1px',
    }),
  );
  $('#tile-layout-gantry-svg').append(
    svgdom('polyline', {
      points: `548,${520 - z} 538,${525 - z} 548,${530 - z}`,
      stroke: 'red',
      fill: 'red',
      'stroke-width': '1px',
    }),
  );
}
