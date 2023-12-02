import React from 'react';
import { Types } from '../../../utils/types';

type Props = { detector: Types.TileboardDetector };

const Detector = ({ detector }: Props) => {
  // add other properties such as plotdata, etc. that are not already in the tileboard structure passed, as react states using useState.

  return (
    <div
      key={detector.id}
      style={{
        width: '50px',
        height: '50px',
        backgroundColor: detector.status ? 'green' : 'red',
      }}
    ></div>
  );
};

export default Detector;
