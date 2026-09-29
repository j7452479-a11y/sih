// -----------------------------------------------------------------------------
// SIH26053 - TACTICAL EDGE PERCEPTION ENGINE: SIM CIVILIAN
// Unity C# Script: EV_LidarStreamer.cs
// 32-Channel Automotive Grazing-Angle LiDAR Streamer for Autonomous Electric Vehicles
// -----------------------------------------------------------------------------

using System;
using System.IO;
using System.Collections.Generic;
using System.Net.Sockets;
using Unity.Collections;
using UnityEngine;

namespace SIH.Civilian
{
    public class EV_LidarStreamer : MonoBehaviour
    {
        [Header("Network Pipeline")]
        public string targetIp = "127.0.0.1";
        public int targetPort = 5001;
        public byte sensorType = 3; // 3 = Ego Civilian EV

        [Header("Automotive Beam Pattern")]
        public int verticalChannels = 32;
        public int horizontalBeams = 64;
        public float maxRangeMeters = 80.0f;
        public float vFovMin = -25.0f; // Looks down at curbs/asphalt
        public float vFovMax = 15.0f;  // Looks up at overhead clearances

        private UdpClient udpClient;
        private uint frameId = 0;
        private float scanTimer = 0f;
        private const float SCAN_INTERVAL = 0.05f; // 20 Hz

        void Awake()
        {
            Application.runInBackground = true;
            SIH.Perception.SimulationHeartbeat.EnsureExists();
        }

        void Start()
        {
            Application.runInBackground = true;
            udpClient = new UdpClient();
            SIH.Perception.SimulationHeartbeat.EnsureExists();
        }

        void Update()
        {
            if (!Application.runInBackground)
            {
                Application.runInBackground = true;
            }

            scanTimer += Time.deltaTime;
            if (scanTimer >= SCAN_INTERVAL)
            {
                scanTimer -= SCAN_INTERVAL;
                ExecuteEgoLidarSweep();
            }
        }

        void ExecuteEgoLidarSweep()
        {
            frameId++;
            int totalBeams = verticalChannels * horizontalBeams;

            NativeArray<RaycastCommand> commands = new NativeArray<RaycastCommand>(totalBeams, Allocator.TempJob);
            NativeArray<RaycastHit> results = new NativeArray<RaycastHit>(totalBeams, Allocator.TempJob);

            Vector3 sensorOrigin = transform.position;
            int idx = 0;

            for (int c = 0; c < verticalChannels; c++)
            {
                float pitch = Mathf.Lerp(vFovMin, vFovMax, (float)c / Mathf.Max(1, verticalChannels - 1));
                for (int b = 0; b < horizontalBeams; b++)
                {
                    // Full 360-degree horizontal azimuth
                    float yaw = (float)b / horizontalBeams * 360.0f - 180.0f;
                    Quaternion beamRot = transform.rotation * Quaternion.Euler(pitch, yaw, 0f);
                    Vector3 direction = beamRot * Vector3.forward;

                    commands[idx] = new RaycastCommand(sensorOrigin, direction, QueryParameters.Default, maxRangeMeters);
                    idx++;
                }
            }

            Unity.Jobs.JobHandle handle = RaycastCommand.ScheduleBatch(commands, results, 32);
            handle.Complete();

            List<RaycastHit> validHits = new List<RaycastHit>();
            for (int i = 0; i < totalBeams; i++)
            {
                if (results[i].collider != null) validHits.Add(results[i]);
            }

            Vector3 euler = transform.rotation.eulerAngles;
            double unixTs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0;

            if (validHits.Count == 0)
            {
                // Send zero-point SIH2 header packet to maintain ego vehicle pose and watchdog heartbeat
                using (MemoryStream ms = new MemoryStream())
                using (BinaryWriter writer = new BinaryWriter(ms))
                {
                    writer.Write(System.Text.Encoding.ASCII.GetBytes("SIH2"));
                    writer.Write(frameId);
                    writer.Write(unixTs);
                    writer.Write(sensorType); // 3 = Ego EV
                    writer.Write((uint)0);    // chunkCount = 0
                    writer.Write((uint)1);    // isLastChunk = 1
                    writer.Write(sensorOrigin.x);
                    writer.Write(sensorOrigin.z); // ENU Y (Northing)
                    writer.Write(sensorOrigin.y); // ENU Z (Up)
                    writer.Write(euler.z);        // Roll
                    writer.Write(euler.x);        // Pitch (nose dive under braking)
                    writer.Write(euler.y);        // Yaw

                    byte[] dgram = ms.ToArray();
                    try
                    {
                        udpClient.Send(dgram, dgram.Length, targetIp, targetPort);
                    }
                    catch { }
                }
            }
            else
            {
                // Stream packets in chunks of up to 80 points to guarantee < 1500B MTU
                for (int chunkStart = 0; chunkStart < validHits.Count && chunkStart < 800; chunkStart += 80)
                {
                    int chunkCount = Mathf.Min(80, validHits.Count - chunkStart);
                    uint isLastChunk = (chunkStart + chunkCount >= validHits.Count || chunkStart + chunkCount >= 800) ? 1u : 0u;

                    using (MemoryStream ms = new MemoryStream())
                    using (BinaryWriter writer = new BinaryWriter(ms))
                    {
                        // 49-byte SIH2 Header: <4sIdBII6f
                        writer.Write(System.Text.Encoding.ASCII.GetBytes("SIH2"));
                    writer.Write(frameId);
                    writer.Write(unixTs);
                    writer.Write(sensorType); // 3 = Ego EV
                    writer.Write((uint)chunkCount);
                    writer.Write(isLastChunk); // Checksum / is_last flag
                    writer.Write(sensorOrigin.x);
                    writer.Write(sensorOrigin.z); // ENU Y (Northing)
                    writer.Write(sensorOrigin.y); // ENU Z (Up)
                    writer.Write(euler.z);        // Roll
                    writer.Write(euler.x);        // Pitch (nose dive under braking)
                    writer.Write(euler.y);        // Yaw

                    // 16-byte Points: sensor local frame for server SE(3) compensation
                    for (int i = chunkStart; i < chunkStart + chunkCount; i++)
                    {
                        RaycastHit hit = validHits[i];

                        // Transform into sensor-local coordinates
                        Vector3 localHit = Quaternion.Inverse(transform.rotation) * (hit.point - sensorOrigin);
                        float lx = localHit.x; // lateral / right
                        float ly = localHit.z; // longitudinal / forward
                        float lz = localHit.y; // vertical / up

                        byte semanticClass = 1; // Default Road
                        int layer = hit.collider.gameObject.layer;
                        string hitName = hit.collider.gameObject.name;
                        string rootName = hit.collider.transform.root != null ? hit.collider.transform.root.name : "";

                        if (layer == LayerMask.NameToLayer("Pedestrian") || layer == LayerMask.NameToLayer("Hostile") ||
                            hitName.Contains("Pedestrian") || hitName.Contains("VRU") || hitName.Contains("Leg") || hitName.Contains("Torso") ||
                            rootName.Contains("Pedestrian") || rootName.Contains("VRU") || rootName.Contains("Hostile"))
                        {
                            semanticClass = 8; // VRU target
                        }
                        else if (layer == LayerMask.NameToLayer("Curb") || hitName.Contains("Curb"))
                        {
                            semanticClass = 5;
                        }
                        else if (layer == LayerMask.NameToLayer("Building") || hitName.Contains("Underpass") || hitName.Contains("Pillar") || hitName.Contains("Ceiling"))
                        {
                            semanticClass = 4;
                        }
                        else if (layer == LayerMask.NameToLayer("Obstacle") || hitName.Contains("Van"))
                        {
                            semanticClass = 2;
                        }
                        else if (layer == LayerMask.NameToLayer("Road") || hitName.Contains("Road"))
                        {
                            semanticClass = 1;
                        }

                        byte intensity = (byte)Mathf.Clamp((1.0f - (hit.distance / maxRangeMeters)) * 255f, 25f, 255f);

                        writer.Write(lx);
                        writer.Write(ly);
                        writer.Write(lz);
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
                    catch
                    {
                        // Non-blocking UDP transport
                    }
                }
            }
            }

            commands.Dispose();
            results.Dispose();
        }

        void OnDestroy()
        {
            if (udpClient != null) udpClient.Close();
        }
    }
}
