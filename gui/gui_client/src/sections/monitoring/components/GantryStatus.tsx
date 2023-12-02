import React, { useEffect } from 'react';

// import relevant types from utils/types.ts
import { MonitorLog, MonitorLogs } from '../../../utils/types';

type Props = { monitorLogs: MonitorLogs };

const GantryStatus = ({ monitorLogs }: Props) => {
  const [lastMonitorLog, setLastMonitorLog] = React.useState<MonitorLog | null>(null);

  useEffect(() => {
    if (monitorLogs.length === 0) {
      setLastMonitorLog(null);
    } else {
      setLastMonitorLog(monitorLogs[monitorLogs.length - 1]);
    }
  }, [monitorLogs]);

  return (
    <div>
      <h3>Gantry Status</h3>
      <div>
        {lastMonitorLog ? (
          <span>
            Gantry Coordinates: ({lastMonitorLog.gantry_coord[0].toFixed(1) || 'unknown'},
            {lastMonitorLog.gantry_coord[1].toFixed(1) || 'unknown'},
            {lastMonitorLog.gantry_coord[2].toFixed(1) || 'unknown'})
          </span>
        ) : (
          <p>Cannot be determined. Please check system status or try re-connecting.</p>
        )}
      </div>
    </div>
  );
};

export default GantryStatus;
