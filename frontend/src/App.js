import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Trades from './pages/Trades';
import Analytics from './pages/Analytics';
import Journal from './pages/Journal';
import AiHub from './pages/AiHub';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/trades" element={<Trades />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/journal" element={<Journal />} />
          <Route path="/ai-hub" element={<AiHub />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
