import React from 'react';
import { useGlobalContext } from '../../../contexts/GlobalContext';

type Props = {};

const SystemStatus = (props: Props) => {
  const { sessionState } = useGlobalContext();

  return (
    <div>
      <h3>System Status</h3>
      <span>System Status: {sessionState || 'System status cannot be determined.'}</span>
    </div>
  );
};

export default SystemStatus;
