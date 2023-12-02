import TelemetryData from './components/TelemetryData';
import VisualSystem from './components/VisualSystem';
import GantryStatus from './components/GantryStatus';
import SystemStatus from './components/SystemStatus';

type Props = {
  monitorLogs: any[];
  monitorMaxLength: number;
  setMonitorLogs: (monitorLogs: any[]) => void;
  // setSessionState: (sessionState: string | null) => void;
  // setMonitorMaxLength: (monitorMaxLength: number) => void;
};

const Monitoring = ({ monitorLogs, setMonitorLogs, monitorMaxLength }: Props) => {
  return (
    <div>
      <h2>Monitoring</h2>
      <SystemStatus />
      <GantryStatus monitorLogs={monitorLogs} />
      <TelemetryData
        monitorLogs={monitorLogs}
        setMonitorLogs={setMonitorLogs}
        monitorMaxLength={monitorMaxLength}
      />
      <VisualSystem />
    </div>
  );
};

export default Monitoring;
