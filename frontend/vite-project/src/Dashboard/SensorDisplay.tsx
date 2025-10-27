import { useState, useEffect } from "react";

interface SensorData {
  humidity: number;
  temp_dht22: number;
  temp_ds18b20: number;
}

function SesnsorDisplay() {
    const [sensors, setSensors] = useState<SensorData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const API_URL = "http://192.168.100.171:5050/api/sensors";

  useEffect(() => {
    const fetchSensors = async () => {
      try {
        const res = await fetch(API_URL);
        if (!res.ok) throw new Error(`Failed to fetch sensors: ${res.status}`);
        const data: SensorData = await res.json();
        setSensors(data);
      } catch (err: any) {
        setError(err.message);
      }
    };

    fetchSensors(); // fetch immediately
    const interval = setInterval(fetchSensors, 60000); // then every 1 min
    return () => clearInterval(interval); // cleanup
  }, []);
    
    if (error) return <div className="text-red-500">Error: {error}</div>

    if(!sensors) return <div>Loading...</div>

    return (
    <div className="grid grid-cols-3 gap-6 bg-white rounded-2xl shadow-md p-6 w-full max-w-3xl">
      <div className="text-center">
        <h2 className="text-lg font-medium text-gray-700">Humidity</h2>
        <p className="text-3xl font-bold text-blue-500">
          {sensors.humidity.toFixed(1) || 0}%
        </p>
      </div>
      <div className="text-center">
        <h2 className="text-lg font-medium text-gray-700">Temperature (Area)</h2>
        <p className="text-3xl font-bold text-orange-500">
          {sensors.temp_dht22.toFixed(1) || 0}°C
        </p>
      </div>
      <div className="text-center">
        <h2 className="text-lg font-medium text-gray-700">Temperature (Fridge)</h2>
        <p className="text-3xl font-bold text-green-600">
          {sensors.temp_ds18b20.toFixed(1) || 0}°C
        </p>
      </div>
    </div>
  );
}

export default SesnsorDisplay;