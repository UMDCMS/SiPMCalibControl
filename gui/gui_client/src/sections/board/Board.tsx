import { useState, useEffect } from 'react';
import { useGlobalContext } from '../../contexts/GlobalContext';

import { Types } from '../../utils/types';

import Detector from './components/Detector';

type Props = {};

const Board = (props: Props) => {
  const { socketInstance } = useGlobalContext();
  const [board, setBoard] = useState<Types.Board | null>(null);

  /**
   * Getting the latest board.
   */
  useEffect(() => {
    if (socketInstance) {
      socketInstance.on('board-update', (data: Types.Board) => {
        // convert data JSON string to object, then set board state
        setBoard(JSON.parse(data.board));
      });

      return function cleanup() {
        // set some random data
        setBoard(null);
        socketInstance.off('board-update');
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [socketInstance]);

  return (
    <section>
      <h2>Tileboard</h2>
      {/* code to display a board in the form of a square, with each object in the board.detectors list being one cell  */}
      <div>
        {board?.detectors.map((detector: Types.BoardDetector) => (
          <Detector key={detector.id} detector={detector} />
        ))}
      </div>
    </section>
  );
};

export default Board;
