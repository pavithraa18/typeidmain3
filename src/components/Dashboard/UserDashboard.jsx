import React, { useEffect, useState } from "react";
import "./dashboard.css";


const UserDashboard = ({ setPage, userId, role }) => {
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
					// Admins request system-wide admin summary
					const url = "http://127.0.0.1:5000/api/dashboard/admin?role=admin";
					console.log("[UserDashboard] Admin fetch:", url);
					const res = await fetch(url);
					if (!res.ok) {
						const body = await res.json().catch(() => ({}));
						throw new Error(body.message || res.statusText || "Failed to load admin summary");
					}
					const data = await res.json();
					console.log("[UserDashboard] Admin response:", data);
					if (mounted) setSummary(data);
				} else {
					// student/teacher -> user-specific summary (POST)
					const url = "http://127.0.0.1:5000/api/dashboard/user";
					const body = { user_id: userId, role };
					console.log("[UserDashboard] User fetch:", url, body);
					const res = await fetch(url, {
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify(body)
					});

					if (!res.ok) {
						const body = await res.json().catch(() => ({}));
						throw new Error(body.message || res.statusText || "Failed to load user summary");
					}
					const data = await res.json();
					console.log("[UserDashboard] User response:", data);
					if (mounted) setSummary(data);
				}
			} catch (err) {
				console.error("[UserDashboard] Error:", err.message);
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
			<h2>User Dashboard</h2>

			{loading && <p>Loading...</p>}
			{error && <p className="error">Error: {error}</p>}

			{!loading && !error && summary && (
				<>
					{/* If admin fetched admin summary, show a compact system view */}
					{role === "admin" ? (
						<>
							<div className="card">
								<p>Total Users</p>
								<h3>{summary.total_users ?? "-"}</h3>
							</div>

							<div className="card">
								<p>Total Profiles</p>
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


export default UserDashboard;