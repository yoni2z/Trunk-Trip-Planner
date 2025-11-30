import { useState } from "react";

export default function TripForm() {
  const [formData, setFormData] = useState({
    currentLocation: "",
    pickupLocation: "",
    dropoffLocation: "",
    cycleUsed: "",
  });

  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitMessage, setSubmitMessage] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
  };

  const validate = () => {
    const newErrors = {};
    if (!formData.currentLocation.trim())
      newErrors.currentLocation = "Required";
    if (!formData.pickupLocation.trim()) newErrors.pickupLocation = "Required";
    if (!formData.dropoffLocation.trim())
      newErrors.dropoffLocation = "Required";
    if (!formData.cycleUsed) {
      newErrors.cycleUsed = "Required";
    } else {
      const num = parseFloat(formData.cycleUsed);
      if (isNaN(num) || num < 0 || num > 70) {
        newErrors.cycleUsed = "Must be 0–70 hours";
      }
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    setSubmitted(false);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/trips/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          current_location: formData.currentLocation,
          pickup_location: formData.pickupLocation,
          dropoff_location: formData.dropoffLocation,
          cycle_used_hours: parseFloat(formData.cycleUsed),
        }),
      });

      const data = await response.json();

      if (response.ok) {
        console.log("Success:", data);

        const tripId = data.trip_id.toLowerCase();
        window.location.href = `/results/${tripId}`;

        setSubmitted(true);
        setSubmitMessage("Generating your FMCSA-compliant trip plan...");
      } else {
        setErrors({ submit: data.message || "Server error" });
      }
    } catch (err) {
      setErrors({ submit: "Network error – is backend running?" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-3xl font-bold text-gray-800 mb-8 text-center">
        ELD Trip Planner
      </h1>

      <form
        onSubmit={handleSubmit}
        className="space-y-6 bg-white shadow-lg rounded-xl p-8"
      >
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Current Location (City, State)
          </label>
          <input
            type="text"
            name="currentLocation"
            value={formData.currentLocation}
            onChange={handleChange}
            placeholder="e.g., Chicago, IL"
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition ${
              errors.currentLocation ? "border-red-500" : "border-gray-300"
            }`}
          />
          {errors.currentLocation && (
            <p className="text-red-500 text-sm mt-1">
              {errors.currentLocation}
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Pickup Location (City, State)
          </label>
          <input
            type="text"
            name="pickupLocation"
            value={formData.pickupLocation}
            onChange={handleChange}
            placeholder="e.g., Dallas, TX"
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition ${
              errors.pickupLocation ? "border-red-500" : "border-gray-300"
            }`}
          />
          {errors.pickupLocation && (
            <p className="text-red-500 text-sm mt-1">{errors.pickupLocation}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Dropoff Location (City, State)
          </label>
          <input
            type="text"
            name="dropoffLocation"
            value={formData.dropoffLocation}
            onChange={handleChange}
            placeholder="e.g., Los Angeles, CA"
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition ${
              errors.dropoffLocation ? "border-red-500" : "border-gray-300"
            }`}
          />
          {errors.dropoffLocation && (
            <p className="text-red-500 text-sm mt-1">
              {errors.dropoffLocation}
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Current 70-Hour Cycle Used (Hours)
          </label>
          <input
            type="number"
            name="cycleUsed"
            value={formData.cycleUsed}
            onChange={handleChange}
            min="0"
            max="70"
            step="0.5"
            placeholder="e.g., 32.5"
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition ${
              errors.cycleUsed ? "border-red-500" : "border-gray-300"
            }`}
          />
          {errors.cycleUsed && (
            <p className="text-red-500 text-sm mt-1">{errors.cycleUsed}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={submitting}
          className={`w-full py-4 px-6 text-white font-semibold rounded-lg transition ${
            submitting
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-700 shadow-lg"
          }`}
        >
          {submitting ? "Planning Trip..." : "Generate Route & Logs"}
        </button>

        {submitted && (
          <div className="mt-6 p-5 bg-green-50 border-2 border-green-300 text-green-800 rounded-lg text-center font-medium">
            {submitMessage}
          </div>
        )}

        {errors.submit && (
          <div className="mt-6 p-5 bg-red-50 border-2 border-red-300 text-red-800 rounded-lg text-center">
            {errors.submit}
          </div>
        )}
      </form>
    </div>
  );
}
