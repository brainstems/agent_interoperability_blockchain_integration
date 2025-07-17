"use client";
import { useState, useEffect } from "react";

interface InventoryData {
  current_stock: number;
  weekly_sales: number;
  lead_time_days: number;
  promo_lift: number;
  open_orders: any[];
  lead_time_history: number[];
}

interface ChannelMetrics {
  roas: number;
  ctr: number;
  impressions: number;
  clicks: number;
  spend: number;
  sales: number;
  conversion_rate: number;
  acos: number;
}

interface SystemState {
  base_metrics: {
    impressions: number;
    clicks: number;
    spend: number;
    sales: number;
  };
  budget: number;
  ctr_values: number[];
  roas_values: number[];
  current_date: string;
  growth_rate: number;
  inventory_data: Record<string, InventoryData>;
  quarterly_data: Record<
    string,
    {
      ad_spend_change: number;
      revenue_goal_change: number;
      roas_change: number;
    }
  >;
  historical_data: Record<
    string,
    {
      acos: number;
      clicks: number;
      conversion_rate: number;
      ctr: number;
      impressions: number;
      roas: number;
      sales: number;
      spend: number;
    }
  >;
  pattern_outputs: string;
  channel_metrics?: Record<string, ChannelMetrics>;
}

interface SimulationMetrics {
  amazon: ChannelMetrics;
  retail_store: ChannelMetrics;
  social_media: ChannelMetrics;
  customer_insights: {
    segments: Array<{
      segment_name: string;
      demographics: Record<string, Record<string, number>>;
      behavior_metrics: Record<string, any>;
      satisfaction_metrics: Record<string, number>;
      lifetime_value: number;
    }>;
    age_demographics: Record<
      string,
      {
        population_share: number;
        purchase_frequency: string;
        channel_preference: Record<string, number>;
      }
    >;
  };
  channel_insights: {
    channels: Array<{
      channel_name: string;
      performance_metrics: Record<string, number>;
    }>;
  };
}

interface SimulationStep {
  step: number;
  metrics: SimulationMetrics;
}

interface Message {
  type: string;
  message: string;
  timestamp: number;
}

interface CornFlakesMetrics {
  product: string;
  timestamp: string;
  recommendations: {
    customer_profile: {
      demographics: Record<string, any>;
      preferences: Record<string, any>;
      behaviors: Record<string, any>;
      marketing_recommendations: string[];
    };
    channel_strategy: Array<{
      channel_name: string;
      metrics: Record<string, number>;
      recommendations: string[];
      priority_score: number;
    }>;
    retail_strategy: Array<{
      location_name: string;
      strengths: string[];
      challenges: string[];
      recommendations: string[];
      priority_level: number;
    }>;
    advertising_recommendations: Record<string, any>;
  };
  metrics: Record<string, any>;
  region: string;
  target_demographic: string;
}

export default function Home() {
  const [message, setMessage] = useState("");
  const [errorMessages, setErrorMessages] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [systemState, setSystemState] = useState<SystemState | null>(null);
  const [showSarahPopup, setShowSarahPopup] = useState(false);
  const [simulationMessages, setSimulationMessages] = useState<string[]>([]);
  const [simulationSteps, setSimulationSteps] = useState<SimulationStep[]>([]);
  const [activeStep, setActiveStep] = useState<number>(0);
  const [isSimulationStarted, setIsSimulationStarted] = useState(false);
  const [notificationMessages, setNotificationMessages] = useState<string[]>(
    []
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [cornFlakesData, setCornFlakesData] =
    useState<CornFlakesMetrics | null>(null);

  const sendMessage = async () => {
    if (!message.trim()) {
      setErrorMessage("Message cannot be empty");
      return;
    }
    try {
      const res = await fetch("http://localhost:5001/send_message", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();

      // Clear messages from the queues
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage("Error sending message");
    }
  };

  const popMessage = async () => {
    try {
      const res = await fetch("http://localhost:5001/pop_message");
      const data = await res.json();
      if (data.message) {
        const parsedMessage = JSON.parse(data.message);

        if (parsedMessage.type === "corn_flakes_strategy") {
          setCornFlakesData(parsedMessage.message);
        } else if (parsedMessage.type === "simulation") {
          const simulationData: SimulationMetrics = JSON.parse(
            parsedMessage.message
          );
          setSimulationSteps((prev) => {
            const existingStepIndex = prev.findIndex(
              (step) =>
                JSON.stringify(step.metrics) === JSON.stringify(simulationData)
            );

            if (existingStepIndex !== -1) {
              return prev;
            }

            const nextStepNumber = prev.length + 1;
            const newStep = {
              step: nextStepNumber,
              metrics: simulationData,
            };

            return [...prev, newStep];
          });
          setActiveStep(simulationSteps.length + 1);
        } else {
          // Handle all other message types
          setMessages((prev) => [
            ...prev,
            {
              type: parsedMessage.type,
              message: parsedMessage.message,
              timestamp: Date.now(),
            },
          ]);
        }
      }
    } catch (error) {
      // console.error("Error retrieving message");
    }
  };

  const fetchState = async () => {
    try {
      const [stateRes, metricsRes] = await Promise.all([
        fetch("http://localhost:5001/state"),
        fetch("http://localhost:5001/metrics/channels"),
      ]);

      const stateData = await stateRes.json();
      const metricsData = await metricsRes.json();

      setSystemState({
        ...stateData,
        channel_metrics: metricsData.data,
      });
    } catch (error) {
      console.error("Error fetching state:", error);
    }
  };

  const startSarah = async () => {
    try {
      setSimulationSteps([]);
      // Reset all message states
      setErrorMessage(null);

      const res = await fetch("http://localhost:5001/start_sarah", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });
      const data = await res.json();
      setIsSimulationStarted(true);
    } catch (error) {
      console.error("Error starting Sarah:", error);
    }
  };

  const nextSarah = async () => {
    try {
      // Clear all message states
      setErrorMessage(null);

      // Get the current step's metrics
      const currentStepMetrics =
        activeStep === 0
          ? systemState?.channel_metrics
          : simulationSteps.find((step) => step.step === activeStep)?.metrics;

      if (!currentStepMetrics) {
        console.error("No metrics found for current step");
        return;
      }

      const res = await fetch("http://localhost:5001/next_sarah", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          metrics: currentStepMetrics,
          step: activeStep,
        }),
      });
      const data = await res.json();
    } catch (error) {
      console.error("Error calling next Sarah:", error);
    }
  };

  const selectStep = (stepNumber: number) => {
    setActiveStep(stepNumber);
  };

  useEffect(() => {
    const messageInterval = setInterval(popMessage, 1000);
    const stateInterval = setInterval(fetchState, 5000);

    fetchState();

    return () => {
      clearInterval(messageInterval);
      clearInterval(stateInterval);
    };
  }, []);

  const cleanMessage = (msg: string) => {
    return msg.replace(/^```json\s*|\s*```$/g, "");
  };

  const closePopup = () => {
    setShowSarahPopup(false);
    setIsSimulationStarted(false);
  };

  return (
    <div className="min-h-screen p-4 flex flex-col items-center justify-center bg-white text-black text-sm">
      <button
        onClick={() => setShowSarahPopup(true)}
        className="mb-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
      >
        Start Sarah
      </button>

      {showSarahPopup && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg w-[95vw] h-[95vh] overflow-y-auto">
            <h3 className="text-lg font-bold mb-4">Start Optimization</h3>
            <p className="mb-4">Budget: 10000$ and growth is 3%</p>

            {/* Channel Metrics Section */}
            <div className="mb-4">
              <h4 className="font-bold text-sm mb-4">
                Channel Metrics History
              </h4>

              {/* Step Circles */}
              <div className="flex items-center justify-start mb-4 space-x-4">
                <button
                  onClick={() => selectStep(0)}
                  className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors
                    ${
                      activeStep === 0
                        ? "bg-blue-500 text-white border-blue-500"
                        : "bg-white text-blue-500 border-blue-500 hover:bg-blue-50"
                    }`}
                >
                  0
                </button>
                {simulationSteps.map((step) => (
                  <button
                    key={step.step}
                    onClick={() => selectStep(step.step)}
                    className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors
                      ${
                        activeStep === step.step
                          ? "bg-blue-500 text-white border-blue-500"
                          : "bg-white text-blue-500 border-blue-500 hover:bg-blue-50"
                      }`}
                  >
                    {step.step}
                  </button>
                ))}
              </div>

              {/* Metrics Content */}
              <div className="space-y-4">
                {/* Step 0 Content */}
                {activeStep === 0 && (
                  <div className="border rounded-lg p-4">
                    <div className="grid grid-cols-3 gap-2">
                      {systemState?.channel_metrics &&
                        Object.entries(systemState.channel_metrics).map(
                          ([channel, metrics]) => (
                            <div
                              key={channel}
                              className="p-2 border rounded bg-gray-50"
                            >
                              <h5 className="font-semibold text-blue-600 capitalize mb-1 text-xs">
                                {channel.replace(/_/g, " ")}
                              </h5>
                              <div className="space-y-0.5 text-xs">
                                <p>
                                  ROAS: {metrics?.roas?.toFixed(2) ?? "N/A"}
                                </p>
                                <p>
                                  CTR:{" "}
                                  {(metrics?.ctr * 100)?.toFixed(2) ?? "N/A"}%
                                </p>
                                <p>
                                  Impressions:{" "}
                                  {metrics?.impressions?.toLocaleString() ??
                                    "N/A"}
                                </p>
                                <p>Clicks: {metrics?.clicks ?? "N/A"}</p>
                                <p>
                                  Spend: ${metrics?.spend?.toFixed(2) ?? "N/A"}
                                </p>
                                <p>
                                  Sales: ${metrics?.sales?.toFixed(2) ?? "N/A"}
                                </p>
                                <p>
                                  Conv. Rate:{" "}
                                  {(metrics?.conversion_rate * 100)?.toFixed(
                                    2
                                  ) ?? "N/A"}
                                  %
                                </p>
                                <p>
                                  ACOS:{" "}
                                  {(metrics?.acos * 100)?.toFixed(2) ?? "N/A"}%
                                </p>
                              </div>
                            </div>
                          )
                        )}
                    </div>
                  </div>
                )}

                {/* Simulation Steps Content */}
                {simulationSteps.map(
                  (step) =>
                    activeStep === step.step && (
                      <div key={step.step} className="border rounded-lg p-4">
                        <div className="grid grid-cols-3 gap-2">
                          {Object.entries(step.metrics).map(
                            ([channel, metrics]) => (
                              <div
                                key={channel}
                                className="p-2 border rounded bg-gray-50"
                              >
                                <h5 className="font-semibold text-blue-600 capitalize mb-1 text-xs">
                                  {channel.replace(/_/g, " ")}
                                </h5>
                                <div className="space-y-0.5 text-xs">
                                  <p>
                                    ROAS: {metrics?.roas?.toFixed(2) ?? "N/A"}
                                  </p>
                                  <p>
                                    CTR:{" "}
                                    {(metrics?.ctr * 100)?.toFixed(2) ?? "N/A"}%
                                  </p>
                                  <p>
                                    Impressions:{" "}
                                    {metrics?.impressions?.toLocaleString() ??
                                      "N/A"}
                                  </p>
                                  <p>Clicks: {metrics?.clicks ?? "N/A"}</p>
                                  <p>
                                    Spend: $
                                    {metrics?.spend?.toFixed(2) ?? "N/A"}
                                  </p>
                                  <p>
                                    Sales: $
                                    {metrics?.sales?.toFixed(2) ?? "N/A"}
                                  </p>
                                  <p>
                                    Conv. Rate:{" "}
                                    {(metrics?.conversion_rate * 100)?.toFixed(
                                      2
                                    ) ?? "N/A"}
                                    %
                                  </p>
                                  <p>
                                    ACOS:{" "}
                                    {(metrics?.acos * 100)?.toFixed(2) ?? "N/A"}
                                    %
                                  </p>
                                </div>
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    )
                )}
              </div>
            </div>

            {/* LLM Agent Communication Interface */}
            <div className="w-full overflow-x-auto mb-4">
              <div className="flex min-w-max gap-4 p-4">
                <div className="w-[800px]">
                  <div
                    className="flex-grow p-4 border rounded bg-gray-100"
                    style={{ height: "70vh" }}
                  >
                    <h2 className="font-bold text-sm mb-4">System Messages</h2>
                    <div className="overflow-y-auto h-[calc(70vh-4rem)]">
                      {messages.map((msg, index) => (
                        <div key={index} className="mb-2">
                          <details className="bg-white rounded-lg">
                            <summary className="cursor-pointer p-2 bg-gray-50 rounded-t-lg flex justify-between items-center">
                              <span className="font-medium capitalize">
                                {msg.type.replace(/_/g, " ")}
                              </span>
                              <span className="text-xs text-gray-500">
                                {new Date(msg.timestamp).toLocaleTimeString()}
                              </span>
                            </summary>
                            <div className="p-2 border-t">
                              <pre className="text-xs whitespace-pre-wrap break-words">
                                {cleanMessage(msg.message)}
                              </pre>
                            </div>
                          </details>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Latest notification display and buttons */}
            <div className="flex justify-between items-center mt-4">
              {/* Latest notification display */}
              <div className="flex-1 text-sm text-gray-600">
                {notificationMessages.length > 0 && (
                  <div>
                    {notificationMessages[notificationMessages.length - 1]}
                  </div>
                )}
              </div>

              {/* Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={closePopup}
                  className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={isSimulationStarted ? nextSarah : startSarah}
                  className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                >
                  {isSimulationStarted ? "Next" : "Start"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* System State and other displays remain outside the popup */}
      {systemState && (
        <div className="w-full mb-4 p-2 border rounded bg-gray-50">
          <h2 className="text-lg font-bold mb-2">System State</h2>
          <div className="grid grid-cols-3 gap-2">
            <div className="p-2 border rounded bg-white">
              <h3 className="font-semibold text-blue-600 text-sm">
                Current Metrics
              </h3>
              <div className="mt-1 space-y-0.5 text-xs">
                <p>
                  ROAS:{" "}
                  {systemState.channel_metrics?.sponsored_products?.roas?.toFixed(
                    2
                  ) || "N/A"}
                </p>
                <p>
                  CTR:{" "}
                  {(
                    (systemState.channel_metrics?.sponsored_products?.ctr ||
                      0) * 100
                  )?.toFixed(2) || "N/A"}
                  %
                </p>
                <p>
                  Base Impressions:{" "}
                  {systemState.channel_metrics?.sponsored_products?.impressions?.toLocaleString() ||
                    "N/A"}
                </p>
                <p>
                  Base Clicks:{" "}
                  {systemState.channel_metrics?.sponsored_products?.clicks ||
                    "N/A"}
                </p>
              </div>
            </div>

            <div className="p-2 border rounded bg-white">
              <h3 className="font-semibold text-green-600 text-sm">
                Budget & Growth
              </h3>
              <div className="mt-1 space-y-0.5 text-xs">
                <p>Budget: ${systemState.budget}</p>
                <p>
                  Growth Rate: {(systemState.growth_rate * 100).toFixed(1)}%
                </p>
                <p>Current Date: {systemState.current_date}</p>
              </div>
            </div>

            <div className="p-2 border rounded bg-white">
              <h3 className="font-semibold text-purple-600 text-sm">
                Inventory Overview
              </h3>
              <div className="mt-1 space-y-0.5 text-xs">
                {Object.entries(systemState.inventory_data).map(
                  ([id, data]) => (
                    <div key={id} className="mb-2">
                      <p className="font-medium">{id}</p>
                      <p>Stock: {data.current_stock}</p>
                      <p>Weekly Sales: {data.weekly_sales}</p>
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      )}
      {systemState && (
        <div className="w-full mb-4 p-2 border rounded bg-gray-50">
          <h2 className="text-lg font-bold mb-2">Channel Performance</h2>
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(systemState.channel_metrics || {}).map(
              ([channel, metrics]) => (
                <div key={channel} className="p-2 border rounded bg-white">
                  <h3 className="font-semibold text-blue-600 capitalize mb-1 text-sm">
                    {channel.replace(/_/g, " ")}
                  </h3>
                  <div className="space-y-0.5 text-xs">
                    <p>ROAS: {metrics.roas.toFixed(2)}</p>
                    <p>CTR: {(metrics.ctr * 100).toFixed(2)}%</p>
                    <p>Impressions: {metrics.impressions.toLocaleString()}</p>
                    <p>Clicks: {metrics.clicks}</p>
                    <p>Spend: ${metrics.spend.toFixed(2)}</p>
                    <p>Sales: ${metrics.sales.toFixed(2)}</p>
                    <p>
                      Conv. Rate: {(metrics.conversion_rate * 100).toFixed(2)}%
                    </p>
                    <p>ACOS: {(metrics.acos * 100).toFixed(2)}%</p>
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      )}
      {systemState && (
        <div className="w-full mb-4 p-2 border rounded bg-gray-50">
          <h2 className="text-lg font-bold mb-2">Historical Performance</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white border">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 border">Date</th>
                  <th className="px-4 py-2 border">ROAS</th>
                  <th className="px-4 py-2 border">CTR</th>
                  <th className="px-4 py-2 border">Impressions</th>
                  <th className="px-4 py-2 border">Clicks</th>
                  <th className="px-4 py-2 border">Spend</th>
                  <th className="px-4 py-2 border">Sales</th>
                  <th className="px-4 py-2 border">Conv. Rate</th>
                  <th className="px-4 py-2 border">ACOS</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(systemState.historical_data)
                  .sort(([dateA], [dateB]) => dateB.localeCompare(dateA))
                  .map(([date, metrics]) => (
                    <tr key={date} className="hover:bg-gray-50">
                      <td className="px-4 py-2 border">{date}</td>
                      <td className="px-4 py-2 border">
                        {metrics.roas.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 border">
                        {(metrics.ctr * 100).toFixed(2)}%
                      </td>
                      <td className="px-4 py-2 border">
                        {metrics.impressions.toLocaleString()}
                      </td>
                      <td className="px-4 py-2 border">{metrics.clicks}</td>
                      <td className="px-4 py-2 border">
                        ${metrics.spend.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 border">
                        ${metrics.sales.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 border">
                        {(metrics.conversion_rate * 100).toFixed(2)}%
                      </td>
                      <td className="px-4 py-2 border">
                        {(metrics.acos * 100).toFixed(2)}%
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {systemState && (
        <div className="grid grid-cols-2 gap-2 w-full mb-4">
          <div className="p-2 border rounded bg-gray-50">
            <h2 className="text-lg font-bold mb-2">Quarterly Performance</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full bg-white border">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 border">Quarter</th>
                    <th className="px-4 py-2 border">Ad Spend Change</th>
                    <th className="px-4 py-2 border">Revenue Goal Change</th>
                    <th className="px-4 py-2 border">ROAS Change</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(systemState.quarterly_data).map(
                    ([quarter, data]) => (
                      <tr key={quarter} className="hover:bg-gray-50">
                        <td className="px-4 py-2 border">{quarter}</td>
                        <td className="px-4 py-2 border">
                          {(data.ad_spend_change * 100).toFixed(1)}%
                        </td>
                        <td className="px-4 py-2 border">
                          {(data.revenue_goal_change * 100).toFixed(1)}%
                        </td>
                        <td className="px-4 py-2 border">
                          {(data.roas_change * 100).toFixed(1)}%
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="p-2 border rounded bg-gray-50">
            <h2 className="text-lg font-bold mb-2">Pattern Recognition</h2>
            <div className="bg-white border rounded p-2 overflow-y-auto max-h-[200px]">
              <pre className="whitespace-pre-wrap text-xs">
                {systemState.pattern_outputs}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Simulation Results Section */}
      {simulationSteps.length > 0 && (
        <div className="w-full mb-4 p-2 border rounded bg-gray-50">
          <h2 className="text-lg font-bold mb-2">Simulation Results</h2>
          <div className="bg-white border rounded p-4">
            <pre className="whitespace-pre-wrap text-xs overflow-x-auto">
              {JSON.stringify(simulationSteps[activeStep - 1].metrics, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
