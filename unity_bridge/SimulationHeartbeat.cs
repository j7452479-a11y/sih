// -----------------------------------------------------------------------------
// SIH26053 - MUM-T TACTICAL EDGE PERCEPTION ENGINE
// SimulationHeartbeat.cs: Simulation Master Clock & Watchdog Heartbeat Broadcaster
// Broadcasts lightweight UDP heartbeats at 10 Hz to edge node on Port 5005.
// Runs inside Update(): Pausing the simulation freezes execution and stops heartbeats,
// triggering immediate hardware safe-stop on physical robots/vehicles.
// -----------------------------------------------------------------------------

using System;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

namespace SIH.Perception
{
    public class SimulationHeartbeat : MonoBehaviour
    {
        [Header("Watchdog Edge Node Endpoint")]
        public string edgeNodeIp = "127.0.0.1";
        public int heartbeatPort = 5005;

        private UdpClient udpClient;
        private float timer = 0f;
        private const float HEARTBEAT_INTERVAL = 0.05f; // 20 Hz

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        private static void AutoInitBefore()
        {
            EnsureExists();
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void AutoInitialize()
        {
            EnsureExists();
        }

        public static void EnsureExists()
        {
            try
            {
                if (FindAnyObjectByType<SimulationHeartbeat>() == null)
                {
                    GameObject go = new GameObject("[Simulation_Heartbeat_Master]");
                    go.AddComponent<SimulationHeartbeat>();
                    DontDestroyOnLoad(go);
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[SimulationHeartbeat] Auto-spawn note: {ex.Message}");
            }
        }

        void Awake()
        {
            Application.runInBackground = true;
            InitSocket();
        }

        void Start()
        {
            Application.runInBackground = true;
            InitSocket();
        }

        private void InitSocket()
        {
            if (udpClient == null)
            {
                try
                {
                    udpClient = new UdpClient();
                }
                catch (Exception ex)
                {
                    Debug.LogWarning($"[SimulationHeartbeat] Socket initialization note: {ex.Message}");
                }
            }
        }

        void Update()
        {
            // Update only runs when the simulation is active and unpaused.
            if (!Application.runInBackground)
            {
                Application.runInBackground = true;
            }

            timer += Time.deltaTime;
            if (timer >= HEARTBEAT_INTERVAL)
            {
                timer = 0f;
                InitSocket();
                if (udpClient == null) return;

                // Send current simulation time and UTC epoch
                string simTimeStr = Time.time.ToString("F3", System.Globalization.CultureInfo.InvariantCulture);
                string payload = $"{{\"source\": \"unity\", \"sim_time\": {simTimeStr}, \"real_ts\": {DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0}}}";
                byte[] bytes = Encoding.UTF8.GetBytes(payload);
                try
                {
                    udpClient.Send(bytes, bytes.Length, edgeNodeIp, heartbeatPort);
                }
                catch
                {
                    // Non-fatal if socket is cycling
                }
            }
        }

        void OnApplicationQuit()
        {
            if (udpClient != null)
            {
                udpClient.Close();
                udpClient = null;
            }
        }

        void OnDestroy()
        {
            if (udpClient != null)
            {
                udpClient.Close();
                udpClient = null;
            }
        }
    }
}
