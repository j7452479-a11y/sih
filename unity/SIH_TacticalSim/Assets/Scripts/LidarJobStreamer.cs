// -----------------------------------------------------------------------------
// SIH26053 - MUM-T TACTICAL EDGE PERCEPTION ENGINE
// Unity C# Bridge: LidarJobStreamer.cs
// High-performance asynchronous raycasting & UDP telemetry streamer to port 5001/5002
// Conforms strictly to Python SIH1 binary protocol (<4sIdBII + N*16B)
// -----------------------------------------------------------------------------

using System;
using System.IO;
using System.Net.Sockets;
using System.Collections.Generic;
using Unity.Collections;
using Unity.Jobs;
using UnityEngine;

namespace SIH.Perception
{
    public class LidarJobStreamer : MonoBehaviour
    {
        [Header("Network Pipeline")]
        public string targetIp = "127.0.0.1";
        public int targetPort = 5001; // 5001 for UAV, 5002 for UGV
        public byte sensorType = 1;   // 1 = UAV, 2 = UGV

        [Header("Scanning Matrix")]
        public int channels = 16;
        public int beamsPerChannel = 20;
        public float maxRangeMeters = 100.0f;
        public bool isNadirDroneScanner = true;

        [Header("Visual Feedback")]
        public bool showVisualBeams = true;
        public Color beamColor = new Color(0f, 0.94f, 1f, 0.4f);

        private UdpClient udpClient;
        private uint frameId = 0;
        private float scanTimer = 0f;
        private const float SCAN_INTERVAL = 0.05f; // 20 Hz deterministic rate
        private List<Vector3> recentHits = new List<Vector3>();

        public List<Vector3> GetRecentHits() => recentHits;

        void Start()
        {
            udpClient = new UdpClient();
            if (sensorType == 1)
            {
                isNadirDroneScanner = true;
                beamColor = new Color(0f, 0.94f, 1f, 0.5f);
            }
            else
            {
                isNadirDroneScanner = false;
                beamColor = new Color(1f, 0.6f, 0f, 0.5f);
            }
        }

        void Update()
        {
            scanTimer += Time.deltaTime;
            if (scanTimer >= SCAN_INTERVAL)
            {
                scanTimer -= SCAN_INTERVAL;
                ExecuteRaycastSweep();
            }
        }

        void ExecuteRaycastSweep()
        {
            frameId++;
            int totalBeams = channels * beamsPerChannel;
            NativeArray<RaycastCommand> commands = new NativeArray<RaycastCommand>(totalBeams, Allocator.TempJob);
            NativeArray<RaycastHit> results = new NativeArray<RaycastHit>(totalBeams, Allocator.TempJob);

            Vector3 sensorOrigin = transform.position;
            int idx = 0;

            // Build Batched Ray Directions
            for (int c = 0; c < channels; c++)
            {
                float pitch;
                if (sensorType == 1 && isNadirDroneScanner)
                {
                    // UAV Drone: Nadir downward sweep (-90° straight down to -32° wide perimeter)
                    pitch = Mathf.Lerp(-90.0f, -32.0f, (float)c / Mathf.Max(1, channels - 1));
                }
                else
                {
                    // UGV RC Car: Horizontal panoramic sweep (-14° to +14° pitch for underpass and street objects)
                    pitch = Mathf.Lerp(-14.0f, 14.0f, (float)c / Mathf.Max(1, channels - 1));
                }

                for (int b = 0; b < beamsPerChannel; b++)
                {
                    // 360-degree continuous azimuthal coverage
                    float yaw = ((float)b / beamsPerChannel) * 360.0f;
                    Quaternion rot = Quaternion.Euler(pitch, yaw, 0f);
                    Vector3 direction = transform.rotation * (rot * Vector3.forward);
                    commands[idx] = new RaycastCommand(sensorOrigin, direction, new QueryParameters(-1, false, QueryTriggerInteraction.Ignore, false), maxRangeMeters);
                    idx++;
                }
            }

            // Schedule Multi-Threaded Physics Sweep across all CPU Cores
            JobHandle handle = RaycastCommand.ScheduleBatch(commands, results, 16);
            handle.Complete();

            // Collect valid hit returns
            List<RaycastHit> validHits = new List<RaycastHit>();
            recentHits.Clear();
            for (int i = 0; i < totalBeams; i++)
            {
                if (results[i].collider != null)
                {
                    validHits.Add(results[i]);
                    if (recentHits.Count < 120)
                    {
                        recentHits.Add(results[i].point);
                    }
                }
            }

            // Binary Serialization conforming strictly to Python SIH1 Protocol (<4sIdBII)
            double unixTimestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0;
            int layerRoad = LayerMask.NameToLayer("Road");
            int layerBuilding = LayerMask.NameToLayer("Building");
            int layerObstacle = LayerMask.NameToLayer("Obstacle");
            int layerHostile = LayerMask.NameToLayer("Hostile");

            Vector3 euler = transform.rotation.eulerAngles;

            // Stream packets in chunks of up to 80 points to guarantee < 1500B MTU
            for (int chunkStart = 0; chunkStart < validHits.Count && chunkStart < 800; chunkStart += 80)
            {
                int chunkCount = Mathf.Min(80, validHits.Count - chunkStart);

                using (MemoryStream ms = new MemoryStream())
                using (BinaryWriter writer = new BinaryWriter(ms))
                {
                    // 49-byte SIH2 Header: <4sIdBII6f
                    writer.Write(System.Text.Encoding.ASCII.GetBytes("SIH2")); // 4 bytes
                    writer.Write(frameId);                                     // uint32 (4 bytes)
                    writer.Write(unixTimestamp);                               // float64 (8 bytes)
                    writer.Write(sensorType);                                  // uint8 (1 byte)
                    writer.Write((uint)chunkCount);                            // uint32 (4 bytes)
                    writer.Write((uint)0);                                     // checksum uint32 (4 bytes)
                    writer.Write(sensorOrigin.x);                              // origin_x (East) float32
                    writer.Write(sensorOrigin.z);                              // origin_y (North) float32
                    writer.Write(sensorOrigin.y);                              // origin_z (Up) float32
                    writer.Write(euler.z);                                     // roll float32
                    writer.Write(euler.x);                                     // pitch float32
                    writer.Write(euler.y);                                     // yaw float32

                    // 16-byte Points: <fffBBBB (x, y, z, semantic, intensity, pad1, pad2)
                    for (int i = chunkStart; i < chunkStart + chunkCount; i++)
                    {
                        RaycastHit hit = validHits[i];

                        // Send true WORLD surface hit coordinates: X = East, Y = North (Unity Z), Z = Up (Unity Y)
                        float wx = hit.point.x;
                        float wy = hit.point.z;
                        float wz = hit.point.y;

                        // Match Python SemanticClass: 0=GROUND, 1=ROAD, 2=OBSTACLE, 3=BRIDGE, 4=BUILDING, 8=HOSTILE
                        byte semanticClass = 0; // Default Ground
                        int hitLayer = hit.collider.gameObject.layer;
                        string hitName = hit.collider.gameObject.name;

                        if (hitLayer == layerHostile || hitName.Contains("Hostile"))
                        {
                            semanticClass = 8;
                        }
                        else if (hitName.Contains("Bridge") || hitName.Contains("Deck") || hitName.Contains("Pillar") || hitName.Contains("Ramp"))
                        {
                            semanticClass = 3;
                        }
                        else if (hitLayer == layerBuilding || hitName.Contains("Church") || hitName.Contains("Bldg") || hitName.Contains("House") || hitName.Contains("Depot"))
                        {
                            semanticClass = 4;
                        }
                        else if (hitLayer == layerObstacle || hitName.Contains("Wall") || hitName.Contains("Border") || hitName.Contains("Bunker") || hitName.Contains("Tower"))
                        {
                            semanticClass = 2;
                        }
                        else if (hitLayer == layerRoad || hitName.Contains("Road") || hitName.Contains("Avenue") || hitName.Contains("Street"))
                        {
                            semanticClass = 1;
                        }

                        byte intensity = (byte)Mathf.Clamp((1.0f - (hit.distance / maxRangeMeters)) * 255f, 25f, 255f);

                        writer.Write(wx);
                        writer.Write(wy);
                        writer.Write(wz);
                        writer.Write(semanticClass);
                        writer.Write(intensity);
                        writer.Write((byte)0);
                        writer.Write((byte)0);
                    }

                    byte[] dgram = ms.ToArray();
                    try
                    {
                        udpClient.Send(dgram, dgram.Length, targetIp, targetPort);
                    }
                    catch (Exception)
                    {
                        // Non-blocking UDP transport
                    }
                }
            }

            commands.Dispose();
            results.Dispose();
        }

        void OnDrawGizmosSelected()
        {
            if (recentHits != null && recentHits.Count > 0)
            {
                Gizmos.color = beamColor;
                foreach (var p in recentHits)
                {
                    Gizmos.DrawLine(transform.position, p);
                    Gizmos.DrawSphere(p, 0.15f);
                }
            }
        }

        void OnDestroy()
        {
            if (udpClient != null) udpClient.Close();
        }
    }
}
