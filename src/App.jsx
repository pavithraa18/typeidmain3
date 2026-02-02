import { useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

import Navbar from "./components/navbar/Navbar";
import Background from "./components/background/Background";
import Signup from "./components/Signup/Signup";
import Signin from "./components/Signin/Signin";
import UserDashboard from "./components/Dashboard/UserDashboard";
import AdminDashboard from "./components/Dashboard/AdminDashboard";

const App = () => {
  const [page, setPage] = useState("home");
  const [userId, setUserId] = useState(null);
  const [role, setRole] = useState(null);

  return (
    <Router>
      <Navbar setPage={setPage} />

      <Routes>
        <Route
          path="/"
          element={
            <>
              {page === "home" && <Background />}
              {page === "signup" && <Signup setPage={setPage} />}
              {page === "signin" && (
                <Signin
                  setPage={setPage}
                  setUserId={setUserId}
                  setRole={setRole}
                />
              )}
            </>
          }
        />

        <Route
          path="/dashboard"
          element={
            <UserDashboard
              setPage={setPage}
              userId={userId}
              role={role}
            />
          }
        />

        <Route
          path="/admin"
          element={
            <AdminDashboard
              setPage={setPage}
              userId={userId}
              role={role}
            />
          }
        />
      </Routes>
    </Router>
  );
};

export default App;
