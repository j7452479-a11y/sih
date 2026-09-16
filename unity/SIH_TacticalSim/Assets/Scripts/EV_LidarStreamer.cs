// -----------------------------------------------------------------------------
// SIH26053 - TACTICAL EDGE PERCEPTION ENGINE: SIM CIVILIAN
// Unity C# Script: EV_LidarStreamer.cs
// 32-Channel Automotive Grazing-Angle LiDAR Streamer for Autonomous Electric Vehicles
// -----------------------------------------------------------------------------

using System;
using System.IO;
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

        void Start()
        {
            udpClient = new UdpClient();
        }

        void Update()
        {
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

            // Serialize to SIH1 Binary Format
            using (MemoryStream ms = new MemoryStream())
            using (BinaryWriter writer = new BinaryWriter(ms))
            {
                float originX = sensorOrigin.x;
                float originY = sensorOrigin.z; // Unity Z -> World Northing
                float originZ = sensorOrigin.y; // Unity Y -> World Up

                double unixTs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0;

                int validHits = 0;
                for (int i = 0; i < totalBeams; i++)
                {
                    if (results[i].collider != null) validHits++;
                }
                int packetPointCount = Mathf.Min(validHits, 80);

                // 25-byte SIH1 Header
                writer.Write(System.Text.Encoding.ASCII.GetBytes("SIH1"));
                writer.Write(frameId);
                writer.Write(unixTs);
                writer.Write(sensorType);
                writer.Write(packetPointCount);
                writer.Write((uint)0); // Checksum

                // 16-byte Points [X, Y, Z, semantic, pad0, pad1, pad2]
                int written = 0;
                for (int i = 0; i < totalBeams && written < packetPointCount; i++)
                {
                    RaycastHit hit = results[i];
                    if (hit.collider == null) continue;

                    Vector3 hitPt = hit.point;
                    byte semanticClass = 1; // Default Road

                    int layer = hit.collider.gameObject.layer;
                    if (layer == LayerMask.NameToLayer("Road")) semanticClass = 1;
                    else if (layer == LayerMask.NameToLayer("Curb")) semanticClass = 5;
                    else if (layer == LayerMask.NameToLayer("Obstacle")) semanticClass = 2;
                    else if (layer == LayerMask.NameToLayer("Building")) semanticClass = 4;
                    else if (layer == LayerMask.NameToLayer("Pedestrian") || layer == LayerMask.NameToLayer("Hostile")) semanticClass = 8; // VRU target

                    writer.Write(hitPt.x);
                    writer.Write(hitPt.z); // ENU Y (Northing)
                    writer.Write(hitPt.y); // ENU Z (Up)
                    writer.Write(semanticClass);
                    writer.Write((byte)0);
                    writer.Write((byte)0);
                    writer.Write((byte)0);

                    written++;
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

            commands.Dispose();
            results.Dispose();
        }

        void OnDestroy()
        {
            if (udpClient != null) udpClient.Close();
        }
    }
}
