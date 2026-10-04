import React, { createContext, useContext, useState } from 'react';

const StudyContext = createContext();

export function StudyProvider({ children }) {
  const [activeDocument, setActiveDocument] = useState(null);

  return (
    <StudyContext.Provider value={{ activeDocument, setActiveDocument }}>
      {children}
    </StudyContext.Provider>
  );
}

export function useStudyContext() {
  return useContext(StudyContext);
}
