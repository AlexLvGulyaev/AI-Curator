import { useEffect, useState } from 'react';
import Chat from './components/Chat';
import RoleSelector from './components/RoleSelector';

const STORAGE_KEY = 'ai-curator-role';

function App() {
  const [role, setRole] = useState(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      setRole(saved);
    }
    setIsReady(true);
  }, []);

  const handleSelectRole = (selectedRole) => {
    localStorage.setItem(STORAGE_KEY, selectedRole);
    setRole(selectedRole);
  };

  const handleResetRole = () => {
    localStorage.removeItem(STORAGE_KEY);
    setRole(null);
  };

  if (!isReady) {
    return null;
  }

  return (
    <div className="min-h-screen">
      {role ? (
        <Chat role={role} onChangeRole={handleResetRole} />
      ) : (
        <RoleSelector onSelectRole={handleSelectRole} />
      )}
    </div>
  );
}

export default App;
