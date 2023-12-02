import { useEffect, useState, createContext, useContext } from 'react';
import { io } from 'socket.io-client';
import type { Socket } from 'socket.io-client';

import './app.css';

import { GlobalContext } from './contexts/GlobalContext';
import Monitoring from './sections/monitoring/Monitoring';
import CommandLine from './sections/command_line/CommandLine';
import Calibration from './sections/callibration/Calibration';
import Board from './sections/board/Board';

const App = () => {
  // NOTE: using prop drilling for most of the properties/state now, but, if grows to be a lot complex, consider switching to grouping several states, using context API in React. Additionally, create custom hooks for each context to make it easier to use as best practice. Follow the GlobalContext.ts file for an example.
  const [socketInstance, setSocketInstance] = useState<Socket | null>(null);
  const [sessionState, setSessionState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [buttonStatus, setButtonStatus] = useState(false);
  const [monitorMaxLength, setMonitorMaxLength] = useState<number>(1024);
  // TODO add type for monitorLog and sessionLog
  const [monitorLogs, setMonitorLogs] = useState<any[]>([]);
  const [sessionMaxLength, setSessionMaxLength] = useState<number>(65536);
  const [sessionLogs, setSessionLogs] = useState<any[]>([]);
  const [lastCmd, setLastCmd] = useState<any>({});

  const handleClick = () => {
    setButtonStatus((currStatus) => !currStatus);
  };

  useEffect(() => {
    if (buttonStatus === true) {
      const socket = io('localhost:9100/', {
        transports: ['websocket'],
      });

      setSocketInstance(socket);

      socket.on('connect', () => {
        console.log('Connected');
      });

      setLoading(false);

      socket.on('disconnect', (data) => {
        console.log(data);
      });

      return function cleanup() {
        socket.disconnect();
      };
    }
  }, [buttonStatus]);

  // update state when monitorLog changes
  useEffect(() => {
    if (monitorLogs.length > 0) {
      setSessionState(monitorLogs[monitorLogs.length - 1].state);
    } else {
      setSessionState(null);
    }
  }, [monitorLogs]);

  // update last_cmd when sessionLog changes
  useEffect(() => {
    const target = 5;

    const lastIndex = sessionLogs.reverse().findIndex((entry) => entry.levelno === target);
    const result =
      lastIndex !== -1 ? sessionLogs[sessionLogs.length - lastIndex - 1] : sessionLogs[-1];

    setLastCmd(result);
  }, [sessionLogs]);

  return (
    <GlobalContext.Provider
      value={{ socketInstance, setSocketInstance, sessionState, setSessionState }}
    >
      <div>
        {buttonStatus && socketInstance ? (
          <>
            <button onClick={handleClick}>disconnect socket</button>
            <div>
              {!loading && (
                <div className='mainContainer'>
                  <div className='monitoring'>
                    <Monitoring
                      monitorLogs={monitorLogs}
                      monitorMaxLength={monitorMaxLength}
                      setMonitorLogs={setMonitorLogs}
                    />
                  </div>
                  <div className='centerContainer'>
                    <CommandLine />
                    {/* <Tileboard /> */}
                  </div>
                  <div className='calibration'>
                    <Calibration />
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <button onClick={handleClick}>connect socket</button>
        )}
      </div>
    </GlobalContext.Provider>
  );
};

export default App;
