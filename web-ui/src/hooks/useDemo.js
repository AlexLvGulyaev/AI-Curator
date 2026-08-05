import { useContext } from 'react';
import DemoContext from '../contexts/DemoContext';

function useDemo() {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error('useDemo must be used within a DemoProvider');
  }
  return context;
}

export default useDemo;
