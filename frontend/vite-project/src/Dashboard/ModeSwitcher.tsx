import { useState, useEffect } from "react";

interface ModeResponse {
  mode: "manual" | "auto";
}

const API_MODE_URL = "http://192.168.100.171:5050/api/mode";

export default function ModeSwitcher({
  mode,
  setMode,
  setIsLoading
}: {
  mode: string;
  setMode: React.Dispatch<React.SetStateAction<"auto" | "manual">>
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>
}) {
  const [loading, setLoading] = useState(false);

  // Sync mode from server on mount
  useEffect(() => {
    const fetchMode = async () => {
      try {
        const res = await fetch(API_MODE_URL);
        const data: ModeResponse = await res.json();

        if(data) setMode(data.mode);

      } catch (err) {
        console.error("Error fetching mode:", err);
      }
    };
    fetchMode();
  }, [setMode]);

  const toggleMode = async () => {
    const newMode = mode === "manual" ? "auto" : "manual";
    setLoading(true);
    if (newMode === 'manual'){
      setIsLoading(true);
    }
    try {
      const res = await fetch(API_MODE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: newMode }),
      });
      if (res.ok) {
        setMode(newMode);
      } else {
        console.error("Failed to set mode:", res.status);
      }
    } catch (err) {
      console.error("Error setting mode:", err);
    } finally {
      setLoading(false)
      setIsLoading(false)
    }
  };

  return (
    <div className="flex items-center justify-center gap-4 mb-6">
      <button
        onClick={toggleMode}
        disabled={loading}
        className={`px-6 py-3 rounded-xl font-semibold text-white transition ${
          mode === "manual" ? "bg-blue-500" : "bg-green-500"
        }`}
      >
        {loading ? "Switching..." : `Mode: ${mode.toUpperCase()}`}
      </button>
    </div>
  );
}
