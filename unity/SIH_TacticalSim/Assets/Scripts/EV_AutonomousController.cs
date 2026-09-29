// -----------------------------------------------------------------------------
// SIH26053 - TACTICAL EDGE PERCEPTION ENGINE: SIM CIVILIAN
// Unity C# Script: EV_AutonomousController.cs
// Autonomous Electric Vehicle NavMesh Agent & Predictive AEB Corridor Monitor
// -----------------------------------------------------------------------------

using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using UnityEngine;
using UnityEngine.AI;

namespace SIH.Civilian
{
    [System.Serializable]
    public class TargetEntry
    {
        public int id;
        public float x;
        public float y;
        public float z;
        public float speed;
        public float heading;
        public string state;
    }

    [System.Serializable]
    public class TelemetryPayload
    {
        public double timestamp;
        public string status;
        public bool simulation_paused;
        public bool emergency_stop;
        public TargetEntry[] targets;
        public float[] uav_pose;
        public float[] ugv_pose;
    }

    public class EV_AutonomousController : MonoBehaviour
    {
        [Header("Vehicle Control")]
        public NavMeshAgent agent;
        public Transform pathTarget;
        public float normalSpeed = 10.0f;
        public float emergencyBrakeDecel = 25.0f;

        [Header("Safety Corridor Geometry")]
        public float corridorWidth = 3.5f;
        public float corridorLookaheadTime = 2.5f; // Seconds ahead

        [Header("Telemetry Ingest")]
        public int telemetryPort = 5003;

        private UdpClient listener;
        private IPEndPoint groupEP;
        private bool emergencyStopActive = false;
        private float stopTimeout = 0f;

        void Start()
        {
            if (agent == null) agent = GetComponent<NavMeshAgent>();
            if (agent != null)
            {
                agent.speed = normalSpeed;
                if (pathTarget != null) agent.SetDestination(pathTarget.position);
            }

            try
            {
                var client = new UdpClient();
                client.Client.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
                client.Client.Bind(new IPEndPoint(IPAddress.Any, telemetryPort));
                listener = client;
                groupEP = new IPEndPoint(IPAddress.Any, telemetryPort);
                listener.BeginReceive(new AsyncCallback(OnTelemetryReceived), null);
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[EV_AutonomousController] UDP Port {telemetryPort} note: {ex.Message}");
            }
        }

        void OnTelemetryReceived(IAsyncResult ar)
        {
            try
            {
                byte[] bytes = listener.EndReceive(ar, ref groupEP);
                string json = Encoding.UTF8.GetString(bytes);
                TelemetryPayload payload = JsonUtility.FromJson<TelemetryPayload>(json);

                if (payload != null)
                {
                    // Watchdog simulation pause or hardware emergency halt
                    if (payload.simulation_paused || payload.emergency_stop || payload.status == "SIMULATION_PAUSED_HARDWARE_HALT")
                    {
                        emergencyStopActive = true;
                        stopTimeout = 0.5f;
                    }

                    if (payload.targets != null)
                    {
                        foreach (var target in payload.targets)
                        {
                            // Convert ENU (X: East, Y: North, Z: Up) -> Unity (X: East, Y: Up, Z: North)
                            Vector3 targetPos = new Vector3(target.x, target.z, target.y);
                            EvaluateBrakingCorridor(targetPos);
                        }
                    }
                }

                listener.BeginReceive(new AsyncCallback(OnTelemetryReceived), null);
            }
            catch
            {
                // Socket closed or teardown
            }
        }

        public void EvaluateBrakingCorridor(Vector3 pedestrianPos)
        {
            // Vector from EV to Pedestrian in local coordinate frame
            Vector3 localOffset = transform.InverseTransformPoint(pedestrianPos);

            float currentSpeed = (agent != null) ? agent.velocity.magnitude : normalSpeed;
            float dynamicCorridorLength = Mathf.Max(6.0f, currentSpeed * corridorLookaheadTime);

            // Check if pedestrian is inside the longitudinal and lateral safety envelope
            bool inLateralCorridor = Mathf.Abs(localOffset.x) <= (corridorWidth / 2.0f);
            bool inLongitudinalPath = localOffset.z > 0.5f && localOffset.z <= dynamicCorridorLength;

            if (inLateralCorridor && inLongitudinalPath)
            {
                emergencyStopActive = true;
                stopTimeout = 1.2f; // Hold emergency brake
            }
        }

        void Update()
        {
            if (emergencyStopActive)
            {
                if (agent != null && agent.isOnNavMesh)
                {
                    agent.speed = 0f;
                    agent.isStopped = true;
                }

                // Tilt vehicle nose-down under emergency braking (-2.5 deg)
                transform.localRotation = Quaternion.Slerp(transform.localRotation, Quaternion.Euler(-2.5f, 0f, 0f), Time.deltaTime * 8f);

                stopTimeout -= Time.deltaTime;
                if (stopTimeout <= 0f)
                {
                    // Pedestrian has cleared corridor; resume cruise
                    emergencyStopActive = false;
                    if (agent != null && agent.isOnNavMesh)
                    {
                        agent.isStopped = false;
                        agent.speed = normalSpeed;
                    }
                }
            }
            else
            {
                // Level vehicle back to horizontal
                transform.localRotation = Quaternion.Slerp(transform.localRotation, Quaternion.identity, Time.deltaTime * 6f);

                // Waypoint navigation
                if (agent != null && agent.isOnNavMesh)
                {
                    if (pathTarget != null && !agent.pathPending && agent.remainingDistance < 1.5f)
                    {
                        agent.SetDestination(pathTarget.position);
                    }
                }
                else if (pathTarget != null)
                {
                    // Direct transform translation along road
                    transform.position = Vector3.MoveTowards(transform.position, pathTarget.position, normalSpeed * Time.deltaTime);
                    if (Vector3.Distance(transform.position, pathTarget.position) < 1.5f)
                    {
                        transform.position = new Vector3(0f, 0.6f, -35.0f);
                    }
                }
            }
        }

        void OnDrawGizmosSelected()
        {
            // Visualize the dynamic braking corridor in the Unity Scene View
            Gizmos.color = emergencyStopActive ? new Color(1f, 0.1f, 0.2f, 0.8f) : new Color(0.1f, 1f, 0.4f, 0.7f);
            float currentSpeed = Application.isPlaying && agent != null ? agent.velocity.magnitude : normalSpeed;
            float length = Mathf.Max(6.0f, currentSpeed * corridorLookaheadTime);

            Vector3 center = transform.position + transform.forward * (length / 2.0f) + Vector3.up * 0.2f;
            Gizmos.matrix = Matrix4x4.TRS(center, transform.rotation, Vector3.one);
            Gizmos.DrawWireCube(Vector3.zero, new Vector3(corridorWidth, 0.1f, length));
        }

        void OnDestroy()
        {
            if (listener != null) listener.Close();
        }
    }
}
