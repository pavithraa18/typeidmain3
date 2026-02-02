import React from "react";
import { useNavigate } from "react-router-dom";
import TypingLogin from "./TypingLogin";

const Signin = ({ setPage, setUserId, setRole }) => {
  const navigate = useNavigate();

  const handleLoginSuccess = (userId, role) => {
    // Set app-level state
    if (setUserId) setUserId(userId);
    if (setRole) setRole(role);
    
    // Route based on role
    if (role === "admin") {
      navigate("/admin");
    } else {
      navigate("/dashboard");
    }
  };

  return <TypingLogin setPage={setPage} onLoginSuccess={handleLoginSuccess} />;
};

export default Signin;
