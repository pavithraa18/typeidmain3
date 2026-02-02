import React, { useEffect, useState } from "react";
import "./dashboard.css";


const AdminDashboard = ({ setPage, userId, role }) => {
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);
	const [summary, setSummary] = useState(null);

	useEffect(() => {
		let mounted = true;

		const fetchData = async () => {
			setLoading(true);
			setError(null);

			try {
				if (role === "admin") {
					const url = "http://127.0.0.1:5000/api/dashboard/admin?role=admin";
					console.log("[AdminDashboard] Admin fetch:", url);
					const res = await fetch(url);
					if (!res.ok) {
						const body = await res.json().catch(() => ({}));
						throw new Error(body.message || res.statusText || "Failed to load admin summary");
					}
					const data = await res.json();
					console.log("[AdminDashboard] Admin response:", data);
					if (mounted) setSummary(data);
				} else if (role === "student" || role === "teacher") {
					// Use admin endpoint in student/teacher mode to fetch user-specific summary
					if (!userId) throw new Error("userId required for student/teacher role");
					const params = new URLSearchParams({ role, user_id: userId });
					const url = `http://127.0.0.1:5000/api/dashboard/admin?${params.toString()}`;
					console.log("[AdminDashboard] Student/Teacher fetch:", url);
					const res = await fetch(url);
					if (!res.ok) {
						const body = await res.json().catch(() => ({}));
						throw new Error(body.message || res.statusText || "Failed to load user summary");
					}
					const data = await res.json();
					console.log("[AdminDashboard] Student/Teacher response:", data);
					if (mounted) setSummary(data);
				} else {
					throw new Error("role not provided or invalid");
				}
			} catch (err) {
				console.error("[AdminDashboard] Error:", err.message);
				if (mounted) setError(err.message);
			} finally {
				if (mounted) setLoading(false);
			}
		};

		fetchData();
		return () => {
			mounted = false;
		};
	}, [userId, role]);

	return (
		<div className="dashboard-wrapper">
			<h2>Admin Dashboard</h2>

			{loading && <p>Loading...</p>}
			{error && <p className="error">Error: {error}</p>}

			{!loading && !error && summary && (
				<>
					{/* If admin summary */}
					{role === "admin" ? (
						<>
							<div className="card">
								<p>Total Users</p>
								<h3>{summary.total_users ?? "-"}</h3>
							</div>

							<div className="card">
								<p>Typing Profiles Collected</p>
								<h3>{summary.total_profiles ?? "-"}</h3>
							</div>
						</>
					) : (
						<>
							<div className="card">
								<p>Typing Profile Status</p>
								<h3>{summary.typing_profile && summary.typing_profile.verified ? "Verified ✅" : "Not Verified"}</h3>
							</div>

							<div className="card">
								<p>Last Login</p>
								<h3>{summary.last_login ? summary.last_login.login_time : "Never"}</h3>
							</div>
						</>
					)}
				</>
			)}

			<button onClick={() => setPage("home")}>Logout</button>
		</div>
	);
};


export default AdminDashboard;