import React, { useState } from "react";
import './rank.css';
import { useNavigate } from "react-router-dom";

const MarksToRank = () => {
    const navigate = useNavigate();

    const [marks, setMarks] = useState("");
    const [year, setYear] = useState(2025);

    const [predictedRank, setPredictedRank] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handlePredict = async () => {
        if (marks === "" || marks < -75 || marks > 300) {
            return alert("Please enter valid JEE marks (between -75 and 300).");
        }

        setLoading(true);
        setError(null);
        setPredictedRank(null);

        try {
            // Fixed URL — now points to /predict-rank/jee
            const response = await fetch(
                `http://127.0.0.1:8000/api/v1/predict-rank/jee?marks=${marks}&year=${year}`
            );

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to fetch prediction.");
            }

            const data = await response.json();
            setPredictedRank(data.predicted_rank);

        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="rank-page">
            <div className="rank-navbar">
                <div className="rank-container">
                    <h2>Rank Vision</h2>
                    <div>
                        <button onClick={() => navigate("/rank")} style={{marginRight: "10px"}}>College Predictor</button>
                        <button onClick={() => navigate("/about")}>About</button>
                    </div>
                </div>
            </div>

            <div className="rank-hero-section">
                <div className="rank-container rank-hero">

                    <div className="rank-hero-left">
                        <h1>Predict Your <span>Rank</span></h1>
                        <p>Enter your expected JEE marks to get an AI-powered rank prediction instantly.</p>

                        <div className="rank-form-box">
                            <div className="rank-input-group">
                                <label>Target Year</label>
                                <select value={year} onChange={(e) => setYear(e.target.value)}>
                                    <option value={2024}>2024</option>
                                    <option value={2025}>2025</option>
                                    <option value={2026}>2026</option>
                                </select>
                            </div>

                            <div className="rank-input-group">
                                <label>Expected Marks (out of 300)</label>
                                <input
                                    type="number"
                                    placeholder="e.g. 150"
                                    value={marks}
                                    onChange={(e) => setMarks(e.target.value)}
                                />
                            </div>

                            <button onClick={handlePredict} disabled={loading}>
                                {loading ? "Analyzing Data..." : "Predict My Rank"}
                            </button>

                            {error && <p style={{color: "red", marginTop: "10px"}}>{error}</p>}
                        </div>
                    </div>

                    <div className="rank-hero-right">
                        {predictedRank !== null ? (
                            <div className="results-container" style={{backgroundColor: "white", padding: "40px", borderRadius: "10px", color: "black", textAlign: "center"}}>
                                <h3>Your Estimated JEE Rank is</h3>
                                <h1 style={{fontSize: "3.5rem", color: "#2E8B57", margin: "20px 0"}}>
                                    🏆 {predictedRank.toLocaleString()}
                                </h1>
                                <p style={{marginBottom: "20px"}}>Based on {year} expected student data.</p>
                                <button
                                    style={{padding: "12px 24px", backgroundColor: "#000", color: "#fff", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold"}}
                                    onClick={() => navigate('/rank')}
                                >
                                    Find Colleges →
                                </button>
                            </div>
                        ) : (
                            <div className="graph-placeholder">Your AI predicted rank will appear here</div>
                        )}
                    </div>

                </div>
            </div>
        </div>
    );
};

export default MarksToRank;