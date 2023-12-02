import { useEffect, useState } from 'react';
import { useGlobalContext } from '../../../contexts/GlobalContext';

// import rellevant types from utils/types.ts
// import type

import {
  LineChart,
  Line,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// type CustomLineChartProps = {
//   data: any[];
//   xKey: string;
//   yKeys: string[];
//   yTitles: string[];
//   yRange: number[];
// };
// const CustomLineChart = ({ data, xKey, yKeys, yTitles, yRange }: CustomLineChartProps) => (
//   <ResponsiveContainer width='100%' height={300}>
//     <LineChart data={data}>
//       <CartesianGrid strokeDasharray='3 3' />
//       <XAxis dataKey={xKey} />
//       <YAxis />
//       <Legend />
//       {yKeys.map((key, index) => (
//         <Line
//           key={key}
//           type='monotone'
//           dataKey={key}
//           name={yTitles[index]}
//           stroke={index === 0 ? 'blue' : 'red'}
//         />
//       ))}
//     </LineChart>
//   </ResponsiveContainer>
// );

type TelemetryDataProps = {
  monitorLogs: any[];
  monitorMaxLength: number;
  setMonitorLogs: (monitorLogs: any[]) => void;
};

const TelemetryData = ({ monitorLogs, setMonitorLogs, monitorMaxLength }: TelemetryDataProps) => {
  const { socketInstance } = useGlobalContext();
  const [plotsData, setPlotsData] = useState<any[]>([]);

  const commonLayout = {
    margin: { top: 10, right: 5, bottom: 40, left: 60 },
    legend: { verticalAlign: 'top', align: 'center' },
    xAxis: { dataKey: 'time', label: 'Time' },
    tooltip: { formatter: (value: number) => `${value}` },
  };

  const temperatureLayout = {
    ...commonLayout,
    yAxis: { label: 'Temperature [°C]', domain: [15, 24] },
  };

  const voltageLayout = {
    ...commonLayout,
    yAxis: { label: 'Voltage [mV]', domain: [0, 5000] },
  };

  /**
   * Getting the monitoring stream update from a log signal.
   */
  const update_monitor_entry = (msg: any) => {
    setMonitorLogs([...monitorLogs, msg]);
    while (monitorLogs.length > monitorMaxLength) {
      setMonitorLogs(monitorLogs.shift());
    }
    // update temperature data and voltage data
    setPlotsData([
      ...plotsData,
      {
        time: new Date(Math.round(msg.created * 1000)),
        pulserTemp: msg.pulser_temp,
        sipmTemp: msg.sipm_temp,
        pulserVolt: msg.pulser_lv,
      },
    ]);
  };

  useEffect(() => {
    if (socketInstance) {
      socketInstance.on('monitor-info', update_monitor_entry);

      return function cleanup() {
        // set some random data
        setPlotsData([
          { time: new Date(), pulserTemp: 20, sipmTemp: 30, pulserVolt: 5 },
          { time: new Date(), pulserTemp: 20, sipmTemp: 30, pulserVolt: 5 },
          { time: new Date(), pulserTemp: 20, sipmTemp: 30, pulserVolt: 5 },
        ]);
        socketInstance.off('monitor-info');
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [socketInstance, monitorLogs, monitorMaxLength]);

  return (
    <div>
      <div>
        <h3>Temperatures</h3>
        <ResponsiveContainer width='100%' height={300} key={`rc_${plotsData.length}`}>
          <LineChart {...temperatureLayout} data={plotsData}>
            <CartesianGrid strokeDasharray='3 3' />
            <XAxis dataKey='time' />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type='monotone' dataKey='pulserTemp' name='Pulser' stroke='blue' />
            <Line type='monotone' dataKey='sipmTemp' name='Tileboard' stroke='red' />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div>
        <h3>Voltages</h3>
        <ResponsiveContainer width='100%' height={300} key={`rc_${plotsData.length}`}>
          <LineChart {...voltageLayout} data={plotsData}>
            <CartesianGrid strokeDasharray='3 3' />
            <XAxis dataKey='time' />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type='monotone' dataKey='pulserVolt' name='Pulser board Bias' stroke='green' />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default TelemetryData;
