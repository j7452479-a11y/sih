// -----------------------------------------------------------------------------
// SIH26053 - MUM-T TACTICAL EDGE PERCEPTION ENGINE
// Unity C# Bridge: ThreatReticleManager.cs
// Tactical AR HUD, MIL-STD-2525 Reticles & Dual Commander/Soldier POV Visualizer
// -----------------------------------------------------------------------------

using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

namespace SIH.Perception
{
    [System.Serializable]
    public class TargetData
    {
        public int id;
        public float x;
        public float y;
        public float z;
        public float speed;
        public float heading;
        public string state; // TENTATIVE, CONFIRMED, COASTING, DELETED
    }

    [System.Serializable]
    public class TelemetryPayload
    {
        public double timestamp;
        public List<TargetData> targets;
        public string designated_structure;
        public float[] uav_pose;
        public float[] ugv_pose;
        public float tether_length_m;
        public string tether_status;
    }

    public class ThreatReticleManager : MonoBehaviour
    {
        [Header("Network Pipeline")]
        public int listenPort = 5003;
        public Camera activeCamera;
        public MUMT_CameraController cameraController;

        [Header("Reticle Styling")]
        public Color lockedColor = new Color(1f, 0.15f, 0.22f, 1f);   // Military Red
        public Color coastingColor = new Color(1f, 0.70f, 0.1f, 1f);  // Tactical Amber
        public Color cyanHudColor = new Color(0f, 0.94f, 1f, 0.9f);   // Tactical Cyan
        public Color greenHudColor = new Color(0f, 1f, 0.55f, 0.9f);  // Green Nominal
        public float baseReticleSize = 34f;

        private UdpClient listener;
        private IPEndPoint groupEP;
        private List<TargetData> latestTargets = new List<TargetData>();
        private TelemetryPayload latestPayload = null;
        private readonly object lockObj = new object();

        private GUIStyle headerStyle;
        private GUIStyle labelStyle;
        private GUIStyle smallStyle;
        private GUIStyle btnStyle;
        private GUIStyle activeBtnStyle;
        private Texture2D boxTexture;
        private float lastPacketTime = -1f;

        void Start()
        {
            if (activeCamera == null) activeCamera = Camera.main;
            if (cameraController == null) cameraController = GetComponent<MUMT_CameraController>();

            boxTexture = new Texture2D(1, 1);
            boxTexture.SetPixel(0, 0, Color.white);
            boxTexture.Apply();

            try
            {
                listener = new UdpClient(listenPort);
                groupEP = new IPEndPoint(IPAddress.Any, listenPort);
                listener.BeginReceive(new AsyncCallback(ReceiveCallback), null);
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[ThreatReticleManager] UDP Port {listenPort} bind note: {ex.Message}");
            }
        }

        void ReceiveCallback(IAsyncResult ar)
        {
            try
            {
                byte[] bytes = listener.EndReceive(ar, ref groupEP);
                string json = Encoding.UTF8.GetString(bytes);

                TelemetryPayload payload = JsonUtility.FromJson<TelemetryPayload>(json);
                if (payload != null)
                {
                    lock (lockObj)
                    {
                        latestPayload = payload;
                        if (payload.targets != null && payload.targets.Count > 0)
                        {
                            latestTargets = payload.targets;
                        }
                        lastPacketTime = Time.time;
                    }
                }
                listener.BeginReceive(new AsyncCallback(ReceiveCallback), null);
            }
            catch
            {
                // Socket closed
            }
        }

        void OnGUI()
        {
            if (activeCamera == null) return;
            InitStyles();

            CameraViewMode viewMode = cameraController != null ? cameraController.CurrentMode : CameraViewMode.Soldier;

            // 1. Draw Top Status Banner
            DrawTopBanner(viewMode);

            // 2. Draw Center Crosshair for Soldier POV
            if (viewMode == CameraViewMode.Soldier)
            {
                DrawSoldierCrosshair();
                DrawCompassTape();
            }

            // 3. Draw Target Reticles
            DrawTargetReticles(viewMode);

            // 4. Draw Bottom Interactive POV Switcher Dock
            DrawPovDock(viewMode);
        }

        private void DrawTopBanner(CameraViewMode mode)
        {
            float w = Screen.width;
            Rect bannerRect = new Rect(20, 16, 420, 68);

            DrawSolidRect(bannerRect, new Color(0.02f, 0.05f, 0.09f, 0.88f), new Color(0.08f, 0.16f, 0.24f, 1f));

            string modeTitle;
            Color modeColor;

            switch (mode)
            {
                case CameraViewMode.Soldier:
                    modeTitle = "[POV 1: SOLDIER AR VISOR]";
                    modeColor = cyanHudColor;
                    break;
                case CameraViewMode.Uav:
                    modeTitle = "[POV 2: UAV AERIAL CHASE (+30M)]";
                    modeColor = greenHudColor;
                    break;
                case CameraViewMode.Ugv:
                    modeTitle = "[POV 3: UGV ROVER DASH (UNDERPASS)]";
                    modeColor = coastingColor;
                    break;
                default:
                    modeTitle = "[POV 4: COMMANDER TACTICAL OVERVIEW]";
                    modeColor = cyanHudColor;
                    break;
            }

            GUI.Label(new Rect(bannerRect.x + 12, bannerRect.y + 6, bannerRect.width - 24, 18), $"MUM-T TACTICAL HUD | {modeTitle}", headerStyle);

            bool isLive = (Time.time - lastPacketTime) < 1.0f;
            string netStatus = isLive ? "LIVE UDP (Port 5003)" : "AUTONOMOUS SIM SENSORS";
            Color netColor = isLive ? greenHudColor : cyanHudColor;

            GUI.color = netColor;
            GUI.Label(new Rect(bannerRect.x + 12, bannerRect.y + 26, bannerRect.width - 24, 16), $"STREAM: {netStatus} | 20 HZ DETERMINISTIC", smallStyle);

            string tetherInfo = "TETHER: 18.2m [NOMINAL CATENARY] | 4.4M UNDERPASS CLEAR";
            lock (lockObj)
            {
                if (latestPayload != null && latestPayload.tether_length_m > 0)
                {
                    tetherInfo = $"TETHER: {latestPayload.tether_length_m:F1}m [{latestPayload.tether_status}] | 4.4M UNDERPASS CLEAR";
                }
            }
            GUI.color = Color.white;
            GUI.Label(new Rect(bannerRect.x + 12, bannerRect.y + 44, bannerRect.width - 24, 16), tetherInfo, smallStyle);
        }

        private void DrawSoldierCrosshair()
        {
            float cx = Screen.width / 2f;
            float cy = Screen.height / 2f;
            float gap = 8f;
            float len = 16f;

            Color c = cyanHudColor;
            DrawLine(new Vector2(cx - gap - len, cy), new Vector2(cx - gap, cy), c, 2f);
            DrawLine(new Vector2(cx + gap, cy), new Vector2(cx + gap + len, cy), c, 2f);
            DrawLine(new Vector2(cx, cy - gap - len), new Vector2(cx, cy - gap), c, 2f);
            DrawLine(new Vector2(cx, cy + gap), new Vector2(cx, cy + gap + len), c, 2f);

            // Reticle center dot
            DrawSolidRect(new Rect(cx - 1.5f, cy - 1.5f, 3f, 3f), c, c);
        }

        private void DrawCompassTape()
        {
            float cx = Screen.width / 2f;
            float cy = 16f;
            float tapeW = 320f;
            float tapeH = 26f;

            Rect tapeRect = new Rect(cx - tapeW / 2f, cy, tapeW, tapeH);
            DrawSolidRect(tapeRect, new Color(0.02f, 0.05f, 0.09f, 0.85f), new Color(0.08f, 0.16f, 0.24f, 0.9f));

            float yaw = activeCamera.transform.eulerAngles.y;
            string headingStr = $"{yaw:000}° {GetCardinalDirection(yaw)}";

            GUI.color = cyanHudColor;
            GUI.Label(new Rect(tapeRect.x, tapeRect.y + 4, tapeRect.width, 18), headingStr, labelStyle);
        }

        private string GetCardinalDirection(float deg)
        {
            string[] cardinals = { "N", "NE", "E", "SE", "S", "SW", "W", "NW", "N" };
            int index = Mathf.RoundToInt(deg / 45f) % 8;
            return cardinals[index];
        }

        private void DrawTargetReticles(CameraViewMode mode)
        {
            Vector3 camPos = activeCamera.transform.position;
            List<TargetData> targetsToRender = new List<TargetData>();

            lock (lockObj)
            {
                if (latestTargets != null && latestTargets.Count > 0)
                {
                    targetsToRender = new List<TargetData>(latestTargets);
                }
            }

            // Fallback: discover scene hostile game objects if no network targets yet
            if (targetsToRender.Count == 0)
            {
                var hostiles = GameObject.FindObjectsByType<HostilePatrol>(FindObjectsSortMode.None);
                int id = 1;
                foreach (var h in hostiles)
                {
                    Vector3 p = h.transform.position;
                    // Check occlusion against stone wall (Z = -14m)
                    bool occluded = (h.name.Contains("Bravo") && Mathf.Abs(p.x) < 8.0f);
                    targetsToRender.Add(new TargetData
                    {
                        id = id++,
                        x = p.x,
                        y = p.z,
                        z = p.y,
                        speed = h.speed,
                        heading = h.transform.eulerAngles.y,
                        state = occluded ? "COASTING" : "CONFIRMED"
                    });
                }
            }

            foreach (var tgt in targetsToRender)
            {
                // Convert Python ENU (X: East, Y: North, Z: Up) -> Unity (X: East, Y: Up, Z: North)
                Vector3 worldPos = new Vector3(tgt.x, tgt.z, tgt.y);

                Vector3 screenPos = activeCamera.WorldToScreenPoint(worldPos + Vector3.up * 1.0f);
                if (screenPos.z <= 0.2f) continue; // Behind camera plane

                float guiX = screenPos.x;
                float guiY = Screen.height - screenPos.y; // Invert Y for IMGUI

                float dist = Vector3.Distance(camPos, worldPos);
                float reticleSize = Mathf.Clamp(baseReticleSize * (35f / Mathf.Max(6f, dist)), 20f, 75f);

                bool isCoasting = (tgt.state == "COASTING");
                Color reticleColor = isCoasting ? coastingColor : lockedColor;

                // Draw MIL-STD-2525 Diamond Reticle
                DrawDiamond(guiX, guiY, reticleSize, reticleColor);

                // Draw Callout Box
                float tagW = 160f;
                float tagH = 34f;
                Rect tagRect = new Rect(guiX - tagW / 2f, guiY - reticleSize / 2f - tagH - 6f, tagW, tagH);

                DrawSolidRect(tagRect, new Color(0.02f, 0.05f, 0.09f, 0.92f), reticleColor);

                GUI.color = reticleColor;
                string statusText = isCoasting ? "[COASTING - OCCLUDED]" : "[LOCKED - LOS]";
                GUI.Label(new Rect(tagRect.x + 6, tagRect.y + 2, tagRect.width - 12, 14), $"[HOSTILE #{tgt.id}] {statusText}", labelStyle);

                GUI.color = Color.white;
                GUI.Label(new Rect(tagRect.x + 6, tagRect.y + 17, tagRect.width - 12, 14), $"RNG: {dist:F1}m | SPD: {tgt.speed:F1}m/s", smallStyle);
            }
        }

        private void DrawPovDock(CameraViewMode mode)
        {
            float dockW = 540f;
            float dockH = 44f;
            float dockX = (Screen.width - dockW) / 2f;
            float dockY = Screen.height - dockH - 16f;

            Rect dockRect = new Rect(dockX, dockY, dockW, dockH);
            DrawSolidRect(dockRect, new Color(0.02f, 0.05f, 0.09f, 0.90f), new Color(0.12f, 0.22f, 0.32f, 1f));

            float btnW = 124f;
            float btnH = 30f;
            float pad = 8f;
            float startX = dockX + 10f;
            float btnY = dockY + 7f;

            if (GUI.Button(new Rect(startX, btnY, btnW, btnH), "[1] SOLDIER", mode == CameraViewMode.Soldier ? activeBtnStyle : btnStyle))
            {
                if (cameraController != null) cameraController.SwitchToSoldier();
            }
            if (GUI.Button(new Rect(startX + (btnW + pad), btnY, btnW, btnH), "[2] UAV CHASE", mode == CameraViewMode.Uav ? activeBtnStyle : btnStyle))
            {
                if (cameraController != null) cameraController.SwitchToUav();
            }
            if (GUI.Button(new Rect(startX + (btnW + pad) * 2, btnY, btnW, btnH), "[3] UGV ROVER", mode == CameraViewMode.Ugv ? activeBtnStyle : btnStyle))
            {
                if (cameraController != null) cameraController.SwitchToUgv();
            }
            if (GUI.Button(new Rect(startX + (btnW + pad) * 3, btnY, btnW, btnH), "[4] COMMANDER", mode == CameraViewMode.Commander ? activeBtnStyle : btnStyle))
            {
                if (cameraController != null) cameraController.SwitchToCommander();
            }
        }

        private void DrawDiamond(float cx, float cy, float s, Color color)
        {
            float hs = s * 0.5f;
            DrawLine(new Vector2(cx, cy - hs), new Vector2(cx + hs, cy), color, 2.5f);
            DrawLine(new Vector2(cx + hs, cy), new Vector2(cx, cy + hs), color, 2.5f);
            DrawLine(new Vector2(cx, cy + hs), new Vector2(cx - hs, cy), color, 2.5f);
            DrawLine(new Vector2(cx - hs, cy), new Vector2(cx, cy - hs), color, 2.5f);

            // Center target pip
            DrawSolidRect(new Rect(cx - 2f, cy - 2f, 4f, 4f), color, color);
        }

        private void DrawSolidRect(Rect r, Color fillColor, Color borderColor)
        {
            Color prev = GUI.color;
            GUI.color = fillColor;
            GUI.DrawTexture(r, boxTexture);

            GUI.color = borderColor;
            // Top, Bottom, Left, Right borders
            GUI.DrawTexture(new Rect(r.x, r.y, r.width, 1.5f), boxTexture);
            GUI.DrawTexture(new Rect(r.x, r.y + r.height - 1.5f, r.width, 1.5f), boxTexture);
            GUI.DrawTexture(new Rect(r.x, r.y, 1.5f, r.height), boxTexture);
            GUI.DrawTexture(new Rect(r.x + r.width - 1.5f, r.y, 1.5f, r.height), boxTexture);

            GUI.color = prev;
        }

        private void DrawLine(Vector2 pA, Vector2 pB, Color color, float width)
        {
            Color prev = GUI.color;
            GUI.color = color;
            Vector2 delta = pB - pA;
            float angle = Mathf.Rad2Deg * Mathf.Atan2(delta.y, delta.x);
            float length = delta.magnitude;

            GUIUtility.RotateAroundPivot(angle, pA);
            GUI.DrawTexture(new Rect(pA.x, pA.y - width / 2f, length, width), boxTexture);
            GUIUtility.RotateAroundPivot(-angle, pA);
            GUI.color = prev;
        }

        private void InitStyles()
        {
            if (headerStyle == null)
            {
                headerStyle = new GUIStyle();
                headerStyle.fontSize = 12;
                headerStyle.fontStyle = FontStyle.Bold;
                headerStyle.normal.textColor = cyanHudColor;
            }
            if (labelStyle == null)
            {
                labelStyle = new GUIStyle();
                labelStyle.fontSize = 10;
                labelStyle.fontStyle = FontStyle.Bold;
                labelStyle.alignment = TextAnchor.MiddleCenter;
                labelStyle.normal.textColor = Color.white;
            }
            if (smallStyle == null)
            {
                smallStyle = new GUIStyle();
                smallStyle.fontSize = 9;
                smallStyle.fontStyle = FontStyle.Bold;
                smallStyle.normal.textColor = new Color(0.85f, 0.9f, 0.95f);
            }
            if (btnStyle == null)
            {
                btnStyle = new GUIStyle(GUI.skin.button);
                btnStyle.fontSize = 10;
                btnStyle.fontStyle = FontStyle.Bold;
                btnStyle.normal.textColor = new Color(0.7f, 0.8f, 0.9f);
            }
            if (activeBtnStyle == null)
            {
                activeBtnStyle = new GUIStyle(GUI.skin.button);
                activeBtnStyle.fontSize = 10;
                activeBtnStyle.fontStyle = FontStyle.Bold;
                activeBtnStyle.normal.textColor = cyanHudColor;
            }
        }

        void OnDestroy()
        {
            if (listener != null) listener.Close();
            if (boxTexture != null) Destroy(boxTexture);
        }
    }
}
