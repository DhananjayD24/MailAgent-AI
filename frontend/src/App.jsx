import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import { Spinner } from "./components/ui.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import History from "./pages/History.jsx";
import Login from "./pages/Login.jsx";
import Thread from "./pages/Thread.jsx";

function ProtectedRoute() {
  const { user } = useAuth();
  const location = useLocation();

  if (user === undefined) {
    return (
      <div className="fullpage">
        <Spinner label="Loading..." />
      </div>
    );
  }
  // Keep the query string so Login can show ?auth_error=... from the backend redirect.
  if (user === null) return <Navigate to={`/login${location.search}`} replace />;

  return (
    <Layout>
      <Outlet />
    </Layout>
  );
}

function PublicOnly({ children }) {
  const { user } = useAuth();
  if (user === undefined) {
    return (
      <div className="fullpage">
        <Spinner label="Loading..." />
      </div>
    );
  }
  return user ? <Navigate to="/" replace /> : children;
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicOnly>
            <Login />
          </PublicOnly>
        }
      />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/thread/:threadId" element={<Thread />} />
        <Route path="/history" element={<History />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
