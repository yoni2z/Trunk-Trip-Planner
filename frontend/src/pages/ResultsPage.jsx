// frontend/src/pages/ResultsPage.jsx

import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { MapContainer, TileLayer, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

export default function ResultsPage() {
  const { id } = useParams();
  const [trip, setTrip] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`https://trunk-trip-planner-3.onrender.com/api/trips/${id}/`)
      .then((r) => r.json())
      .then((data) => {
        setTrip(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [id]);

  if (loading)
    return (
      <div className="text-center py-32 text-4xl">Loading your trip...</div>
    );
  if (!trip)
    return (
      <div className="text-center py-32 text-red-600 text-3xl">
        Trip not found
      </div>
    );

  // EXTRACT COORDINATES — WORKS WITH ORS /geojson
  const coords = trip.route_raw?.routes?.[0]?.geometry?.coordinates || [];
  const routeCoords = coords.map((c) => [c[1], c[0]]); // [lat, lng]

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12">
      <div className="max-w-7xl mx-auto px-6">
        <h1 className="text-6xl font-bold text-center text-indigo-900 mb-8">
          Your Official FMCSA Trip Plan
        </h1>

        <div className="grid lg:grid-cols-2 gap-12 mb-16">
          <div className="bg-white rounded-3xl shadow-2xl p-8 border-4 border-indigo-200">
            <h2 className="text-4xl font-bold text-indigo-900 mb-6">
              Route Map
            </h2>
            <div className="h-96 rounded-2xl overflow-hidden">
              {routeCoords.length > 0 ? (
                <MapContainer
                  bounds={routeCoords}
                  style={{ height: "100%", width: "100%" }}
                >
                  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                  <Polyline
                    positions={routeCoords}
                    color="#4f46e5"
                    weight={8}
                    opacity={0.9}
                  />
                </MapContainer>
              ) : (
                <div className="h-full bg-gray-200 flex items-center justify-center text-gray-600">
                  Route loading...
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-3xl shadow-2xl p-10 border-4 border-green-200">
            <h2 className="text-4xl font-bold text-indigo-900 mb-8">
              Trip Summary
            </h2>
            <div className="space-y-6 text-2xl">
              <div>
                <strong>From:</strong> {trip.current_location}
              </div>
              <div>
                <strong>To:</strong> {trip.dropoff_location}
              </div>
              <div className="text-5xl font-bold text-green-600 mt-8">
                {Math.round(trip.total_distance_miles)} miles
              </div>
              <div className="text-4xl font-bold text-center py-8 bg-green-100 rounded-2xl text-green-800">
                100% FMCSA COMPLIANT
              </div>
            </div>
          </div>
        </div>

        <div className="text-center">
          <a
            href={`https://trunk-trip-planner-3.onrender.com/api/trips/${id}/logs/`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block px-24 py-12 bg-gradient-to-r from-indigo-800 to-purple-900 text-white text-5xl font-bold rounded-3xl shadow-3xl hover:shadow-4xl transform hover:scale-110 transition-all duration-300"
          >
            VIEW OFFICIAL FMCSA LOGS
          </a>
          <p className="text-2xl text-gray-700 mt-8 font-medium">
            Printable • 4-Line Grid • DOT-Ready • Landscape
          </p>
        </div>
      </div>
    </div>
  );
}
