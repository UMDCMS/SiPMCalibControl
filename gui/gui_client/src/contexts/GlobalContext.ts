import { createContext, useContext } from 'react';

import type { Socket } from 'socket.io-client';

export type GlobalContentType = {
  socketInstance: Socket | null;
  setSocketInstance: (c: Socket | null) => void;
  sessionState: string | null;
  setSessionState: (c: string | null) => void;
};

export const GlobalContext = createContext<GlobalContentType>({
  socketInstance: null,
  setSocketInstance: () => {},
  sessionState: null,
  setSessionState: () => {},
});

export const useGlobalContext = () => useContext(GlobalContext);
