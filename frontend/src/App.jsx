
import { useCallback, useEffect, useState } from "react";
import { analyzeCrop } from "./api";
import Login from "./Login";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";
const REFRESH_MS = 5 * 60 * 1000;

function getWeatherAdvice(weather) {
  if (!weather) return [];

  const notes = [];
  const temp = weather.temperature_c;
  const humidity = weather.humidity_percent;
  const rain = weather.precipitation_mm ?? 0;

  if (temp != null && temp >= 35) {
    notes.push("High heat: keep harvested produce shaded and cool.");
  } else if (temp != null && temp >= 30) {
    notes.push("Warm conditions may accelerate produce deterioration.");
  }

  if (humidity != null && humidity >= 80) {
    notes.push(
      "High humidity: improve ventilation and check for condensation."
    );
  }

  if (rain > 0) {
    notes.push(
      "Precipitation reported: protect produce and check transport conditions."
    );
  }

  if (notes.length === 0) {
    notes.push(
      "Monitor produce condition and use suitable storage and transport."
    );
  }

  return notes;
}

function FarmFlowDashboard({ onLogout }) {
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState("");
  const [marketPrice, setMarketPrice] = useState("100");
  const [storageCost, setStorageCost] = useState("5");
  const [transportCost, setTransportCost] = useState("10");
  const [transportHours, setTransportHours] = useState("4");

  const [locationStatus, setLocationStatus] = useState("Detecting location...");
  const [locationName, setLocationName] = useState("");
  const [coordinates, setCoordinates] = useState(null);
  const [weather, setWeather] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [weatherError, setWeatherError] = useState("");

  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchWeather = useCallback(async (coords, showLoading = false) => {
    if (!coords) return;

    if (showLoading) setWeatherLoading(true);
    setWeatherError("");

    try {
      const params = new URLSearchParams({
        latitude: String(coords.latitude),
        longitude: String(coords.longitude),
      });

      const response = await fetch(
        `${API_BASE_URL}/api/weather?${params.toString()}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to fetch weather.");
      }

      setWeather(data);
      setLocationStatus("Location detected");
    } catch (err) {
      setWeatherError(err.message || "Weather service unavailable.");
    } finally {
      if (showLoading) setWeatherLoading(false);
    }
  }, []);

  const detectLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationStatus("Location is not supported by this browser.");
      setWeatherError("Please use a browser that supports location access.");
      return;
    }

    setLocationStatus("Requesting location permission...");
    setWeatherError("");

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const coords = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        };

        setCoordinates(coords);
       
        setLocationName("");

        // Convert the detected coordinates into a readable place name.
        fetch(
          `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${coords.latitude}&lon=${coords.longitude}`
        )
          .then((response) => {
            if (!response.ok) throw new Error("Reverse geocoding unavailable");
            return response.json();
          })
          .then((data) => {
            const address = data.address || {};
            const place =
              address.city ||
              address.town ||
              address.village ||
              address.municipality ||
              address.suburb ||
              address.county ||
              address.state_district;
            setLocationName(
              place ? `${place}${address.state ? `, ${address.state}` : ""}` : "Location detected"
            );
          })
          .catch(() => setLocationName("Location detected"));

        fetchWeather(coords, true);
      },
      (geoError) => {
        const messages = {
          1: "Location permission denied. Allow location access and try again.",
          2: "Your location could not be determined. Check device location.",
          3: "Location request timed out. Please try again.",
        };

        setLocationStatus("Location unavailable");
        setWeatherError(
          messages[geoError.code] || "Could not detect your location."
        );
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 60000,
      }
    );
  }, [fetchWeather]);

  useEffect(() => {
    detectLocation();
  }, [detectLocation]);

  useEffect(() => {
    if (!coordinates) return undefined;

    const intervalId = window.setInterval(() => {
      fetchWeather(coordinates);
    }, REFRESH_MS);

    return () => window.clearInterval(intervalId);
  }, [coordinates, fetchWeather]);

  function handleImageChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Please select a JPG, PNG, or WEBP image.");
      return;
    }

    if (file.size > 8 * 1024 * 1024) {
      setError("Image must be 8 MB or smaller.");
      return;
    }

    setError("");
    setImage(file);
    setResult(null);

    setPreview((oldPreview) => {
      if (oldPreview) URL.revokeObjectURL(oldPreview);
      return URL.createObjectURL(file);
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (!image) {
      setError("Please upload a crop image first.");
      return;
    }

    const values = [
      marketPrice,
      storageCost,
      transportCost,
      transportHours,
    ];

    if (values.some((value) => value === "" || !Number.isFinite(Number(value)))) {
      setError("Please enter valid numbers in all cost and time fields.");
      return;
    }

    if (values.some((value) => Number(value) < 0)) {
      setError("Costs, price, and transport time cannot be negative.");
      return;
    }

    const formData = new FormData();
    formData.append("image", image);
    formData.append("market_price", marketPrice);
    formData.append("storage_cost", storageCost);
    formData.append("transport_cost", transportCost);
    formData.append("transport_hours", transportHours);

    setLoading(true);

    try {
      const data = await analyzeCrop(formData);
      setResult(data);
    } catch (err) {
      setError(err.message || "Could not analyze the crop.");
    } finally {
      setLoading(false);
    }
  }

  const assessment = result?.assessment;
  const decision = result?.decision;
  const advice = getWeatherAdvice(weather);

  const conditionLabel = (value) => {
    if (value == null) return "—";
    return typeof value === "number" ? `${value}` : value;
  };

  return (
    <main className="app-container">
      <header className="app-header">
        <div>
          <p className="eyebrow">SMART POST-HARVEST ASSISTANT</p>
          <h1>🌾 FarmFlow</h1>
          <p className="subtitle">
            Smarter crop decisions. Less waste. Better returns.
          </p>
        </div>
        <div className="header-actions">
          <span
            className="status-pill"
            title="Location based on your browser's location permission"
          >
            <span className="status-dot" />
            {locationName || locationStatus}
          </span>
          <button className="secondary-button" type="button" onClick={onLogout}>
            Log out
          </button>
        </div>
      </header>

      <section className="weather-card">
        <div className="weather-heading">
          <div>
            <p className="eyebrow">YOUR LOCAL WEATHER</p>
            <h2>Weather at your farm</h2>
            <p className="muted">{locationStatus}</p>
          </div>

          <button
            className="secondary-button"
            type="button"
            onClick={detectLocation}
            disabled={weatherLoading}
          >
            {weatherLoading ? "Updating..." : "↻ Refresh location"}
          </button>
        </div>

        {weatherError && (
          <div className="notice notice-warning">
            {weatherError}
          </div>
        )}

        {weather ? (
          <>
            <div className="weather-main">
              <div>
                <span className="weather-temperature">
                  {weather.temperature_c == null
                    ? "—"
                    : `${weather.temperature_c}°C`}
                </span>
                <p className="weather-condition">{weather.condition}</p>
                {weather.feels_like_c != null && (
                  <p className="muted">
                    Feels like {weather.feels_like_c}°C
                  </p>
                )}
              </div>
              <div className="weather-icon" aria-hidden="true">
                {weather.rain_mm > 0 ? "🌧️" :
                  weather.temperature_c >= 30 ? "☀️" : "🌤️"}
              </div>
            </div>

            <div className="weather-metrics">
              <div className="weather-metric">
                <span>💧 Humidity</span>
                <strong>
                  {conditionLabel(weather.humidity_percent)}
                  {weather.humidity_percent != null ? "%" : ""}
                </strong>
              </div>
              <div className="weather-metric">
                <span>🌧️ Rain</span>
                <strong>
                  {conditionLabel(weather.precipitation_mm)} mm
                </strong>
              </div>
              <div className="weather-metric">
                <span>💨 Wind</span>
                <strong>
                  {conditionLabel(weather.wind_speed_kmh)} km/h
                </strong>
              </div>
            </div>

            <div className="weather-advice">
              <h3>Weather advisory</h3>
              <ul>
                {advice.map((note, index) => (
                  <li key={index}>{note}</li>
                ))}
              </ul>
            </div>

            <p className="weather-footnote">
              Source: {weather.source}. Updated:{" "}
              {weather.fetched_at
                ? new Date(weather.fetched_at).toLocaleTimeString()
                : "just now"}
              {" · "}Automatic refresh every 5 minutes.
            </p>
          </>
        ) : (
          <div className="weather-empty">
            {weatherLoading || locationStatus.includes("Requesting") ||
            locationStatus.includes("Detecting")
              ? "Getting your location and loading weather..."
              : "Allow location access to see weather for your current location."}
          </div>
        )}
      </section>

      <div className="content-grid">
        <section className="panel">
          <div className="section-heading">
            <p className="eyebrow">CROP ANALYSIS</p>
            <h2>Analyze your harvest</h2>
            <p className="muted">
              Upload a clear image and enter your estimated costs.
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            <label className="upload-box">
              {preview ? (
                <img
                  src={preview}
                  alt="Selected crop preview"
                  className="image-preview"
                />
              ) : (
                <div className="upload-placeholder">
                  <span className="upload-icon">📷</span>
                  <strong>Upload crop image</strong>
                  <span>JPG, PNG or WEBP · Maximum 8 MB</span>
                </div>
              )}
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleImageChange}
                hidden
              />
            </label>

            {image && <p className="muted selected-file">{image.name}</p>}

            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="marketPrice">Market price per unit (₹)</label>
                <input
                  id="marketPrice"
                  type="number"
                  min="0"
                  step="any"
                  value={marketPrice}
                  onChange={(e) => setMarketPrice(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="storageCost">Storage cost per unit (₹)</label>
                <input
                  id="storageCost"
                  type="number"
                  min="0"
                  step="any"
                  value={storageCost}
                  onChange={(e) => setStorageCost(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="transportCost">Transport cost per unit (₹)</label>
                <input
                  id="transportCost"
                  type="number"
                  min="0"
                  step="any"
                  value={transportCost}
                  onChange={(e) => setTransportCost(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="transportHours">Transport time (hours)</label>
                <input
                  id="transportHours"
                  type="number"
                  min="0"
                  step="any"
                  value={transportHours}
                  onChange={(e) => setTransportHours(e.target.value)}
                  required
                />
              </div>
            </div>

            {error && <div className="notice notice-error">{error}</div>}

            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? "Analyzing crop..." : "Analyze crop & recommend action"}
            </button>
          </form>
        </section>

        <section className="panel results-panel">
          <div className="section-heading">
            <p className="eyebrow">DECISION SUPPORT</p>
            <h2>Your results</h2>
            <p className="muted">
              Recommendations appear here after crop analysis.
            </p>
          </div>

          {!result && (
            <div className="results-empty">
              <span>🌱</span>
              <p>Upload a crop image to get your assessment and recommendation.</p>
            </div>
          )}

          {result && (
            <>
              {assessment && (
                <div className="result-section">
                  <h3>Crop assessment</h3>
                  <div className="result-metrics">
                    <div className="result-metric">
                      <span>Quality score</span>
                      <strong>
                        {assessment.quality_score ?? "—"}
                        {assessment.quality_score != null ? "/100" : ""}
                      </strong>
                    </div>
                    <div className="result-metric">
                      <span>Damage estimate</span>
                      <strong>
                        {assessment.damage_percent ?? "—"}
                        {assessment.damage_percent != null ? "%" : ""}
                      </strong>
                    </div>
                    <div className="result-metric">
                      <span>Estimated shelf life</span>
                      <strong>
                        {assessment.shelf_life_days ?? "—"}
                        {assessment.shelf_life_days != null ? " days" : ""}
                      </strong>
                    </div>
                  </div>

                  {assessment.predicted_class && (
                    <p>
                      <strong>Predicted condition:</strong>{" "}
                      {assessment.predicted_class}
                    </p>
                  )}

                  {assessment.confidence != null && (
                    <p>
                      <strong>Model confidence:</strong>{" "}
                      {typeof assessment.confidence === "number"
                        ? `${(assessment.confidence * 100).toFixed(1)}%`
                        : assessment.confidence}
                    </p>
                  )}

                  {assessment.assessment_mode && (
                    <p className="muted">
                     
                    </p>
                  )}
                </div>
              )}

              {decision && (
                <div className="decision-card">
                  <p className="eyebrow">RECOMMENDED ACTION</p>
                  <h2>
                    {decision.recommended_action ||
                      decision.action ||
                      "Review recommendation"}
                  </h2>

                  {decision.reason && <p>{decision.reason}</p>}

                  {decision.estimated_returns && (
                    <div className="result-section">
                      <h3>Estimated returns</h3>
                      {Object.entries(decision.estimated_returns).map(
                        ([key, value]) => (
                          <div className="return-row" key={key}>
                            <span>
                              {key.replaceAll("_", " ")}
                            </span>
                            <strong>
                              {typeof value === "number"
                                ? `₹${value.toFixed(2)}`
                                : String(value)}
                            </strong>
                          </div>
                        )
                      )}
                    </div>
                  )}
                </div>
              )}

              <p className="disclaimer">
                Estimates are decision-support guidance, not a guarantee of
                crop shelf life, market price, profit, or transport conditions.
                Verify before making commercial decisions.
              </p>
            </>
          )}
        </section>
      </div>

      <footer className="app-footer">
        FarmFlow · AI-assisted post-harvest decision support
      </footer>
    </main>
  );
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem("farmflow_token"));

  function handleAuthenticated(authData) {
    localStorage.setItem("farmflow_token", authData.access_token);
    localStorage.setItem("farmflow_email", authData.email);
    setToken(authData.access_token);
  }

  function handleLogout() {
    localStorage.removeItem("farmflow_token");
    localStorage.removeItem("farmflow_email");
    setToken(null);
  }

  return token ? (
    <FarmFlowDashboard onLogout={handleLogout} />
  ) : (
    <Login onAuthenticated={handleAuthenticated} />
  );
}

export default App;
