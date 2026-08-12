import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("/api/health")
      .then((res) => {
        if (!res.ok) throw new Error("API unreachable");
        return res.json();
      })
      .then(setHealth)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <main className="app">
      <h1>Hack</h1>
      <p>FastAPI + React starter</p>

      <section className="status-card">
        <h2>Backend status</h2>
        {error && <p className="error">{error}</p>}
        {health && <p className="success">API is {health.status}</p>}
        {!health && !error && <p>Checking...</p>}
      </section>
    </main>
  );
}

export default App;
