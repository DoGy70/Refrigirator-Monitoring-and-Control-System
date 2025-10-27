import { useState, useEffect } from "react";

interface Config {
  temp_start_compressor: number;
  temp_stop_compressor: number;
}

const API_CONFIG_URL = "http://192.168.100.171:5050/api/config";

export default function AutoControls() {
  const [config, setConfig] = useState<Config>({
    temp_start_compressor: 4.5,
    temp_stop_compressor: 3.5,
  });

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await fetch(API_CONFIG_URL);
        const data = await res.json();
        setConfig(data);
      } catch (err) {
        console.error("Failed to fetch config:", err);
      }
    };
    fetchConfig();
  }, []);

  const updateConfig = async () => {
    setSaving(true);
    console.log(config)
    try {
      const res = await fetch(API_CONFIG_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!res.ok) console.error("Failed to update config");
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-md p-6 w-full max-w-3xl mt-4">
      <h2 className="text-xl font-semibold mb-4">Automatic Control Settings</h2>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-gray-700 mb-2">
            Start Compressor Above (°C)
          </label>
          <input
            type="number"
            step="0.1"
            value={config.temp_start_compressor}
            onChange={(e) =>
              setConfig({
                ...config,
                temp_start_compressor: parseFloat(e.target.value),
              })
            }
            className="border p-2 rounded w-full"
          />
        </div>
        <div>
          <label className="block text-gray-700 mb-2">
            Stop Compressor Below (°C)
          </label>
          <input
            type="number"
            step="0.1"
            value={config.temp_stop_compressor}
            onChange={(e) =>
              setConfig({
                ...config,
                temp_stop_compressor: parseFloat(e.target.value),
              })
            }
            className="border p-2 rounded w-full"
          />
        </div>
      </div>
      <button
        onClick={updateConfig}
        disabled={saving}
        className="mt-4 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded font-semibold"
      >
        {saving ? "Saving..." : "Save Settings"}
      </button>
    </div>
  );
}
