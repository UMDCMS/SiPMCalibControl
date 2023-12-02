import React from 'react';
import { useGlobalContext } from '../../../contexts/GlobalContext';

type Props = {};

const VisualSystem = (props: Props) => {
  const { socketInstance } = useGlobalContext();

  return <h3>Visual System</h3>;
};

export default VisualSystem;
