// -----------------------------------------------------------------------------
// SIH26053 - REAL-TIME MULTI-SCREEN SIMULATION SYSTEM
// Unity C# Component: MultiScreenDisplayManager.cs
// Manages dual-display hardware rendering & real-time POV distribution
// -----------------------------------------------------------------------------

using System;
using System.Collections;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace SIH.MultiScreen
{
    public enum SecondaryScreenPOV
    {
        // Military / Army Module
        SoldierFirstPerson = 0,
        CommanderOverhead = 1,
        UavTacticalRecon = 2,

        // Civilian EV Module
        CivilianDriverCockpit = 3,
        VehicleThirdPerson = 4,
        UrbanPedestrian = 5
    }

    public class MultiScreenDisplayManager : MonoBehaviour
    {
        [Header("Display Architecture")]
        [Tooltip("Camera dedicated to primary laptop (Master Simulation View - Display 1)")]
        public Camera masterDisplayCamera;

        [Tooltip("Camera dedicated to secondary laptop / screen (Display 2)")]
        public Camera secondaryDisplayCamera;

        [Header("Military / Army Sockets")]
        public Transform soldierHeadSocket;
        public Transform commanderOverheadSocket;
        public Transform uavChaseSocket;

        [Header("Civilian EV Sockets")]
        public Transform civilianDriverSocket;
        public Transform vehicleExternalSocket;
        public Transform urbanPedestrianSocket;

        [Header("Smooth Blending")]
        public float positionSmoothSpeed = 14f;
        public float rotationSmoothSpeed = 14f;

        [Header("Current Mode")]
        [SerializeField]
        private SecondaryScreenPOV activePOV = SecondaryScreenPOV.SoldierFirstPerson;

        // Internal rendering state
        private Transform activeTargetSocket;
        private Texture2D hudTexture;
        private GUIStyle headerStyle;
        private GUIStyle metricStyle;
        private GUIStyle statusStyle;

        public SecondaryScreenPOV ActivePOV => activePOV;

        void Awake()
        {
            Application.runInBackground = true;
            SIH.Perception.SimulationHeartbeat.EnsureExists();

            // 1. Initialize Multi-Display Hardware
            Debug.Log($"[MULTI-SCREEN] Detected {Display.displays.Length} display hardware outputs.");
            
            // Display 0 is primary screen by default
            if (Display.displays.Length > 1)
            {
                Display.displays[1].Activate();
                Debug.Log("[MULTI-SCREEN] Display 2 (Secondary Screen) activated successfully.");
            }
            if (Display.displays.Length > 2)
            {
                Display.displays[2].Activate();
                Debug.Log("[MULTI-SCREEN] Display 3 activated.");
            }

            // 2. Assign Camera Target Displays
            if (masterDisplayCamera != null)
            {
                masterDisplayCamera.targetDisplay = 0; // Screen 1 (Primary Powerhouse)
            }
            if (secondaryDisplayCamera != null)
            {
                // In standalone builds, targetDisplay = 1 routes directly to Screen 2
                // If only 1 physical screen exists in testing, fallback to 0 or split-screen
                secondaryDisplayCamera.targetDisplay = Display.displays.Length > 1 ? 1 : 0;
            }

            // Create 1x1 GUI texture for HUD panels
            hudTexture = new Texture2D(1, 1);
            hudTexture.SetPixel(0, 0, Color.white);
            hudTexture.Apply();
        }

        void Start()
        {
            Application.runInBackground = true;
            SIH.Perception.SimulationHeartbeat.EnsureExists();
            AutoBindSocketsIfMissing();
            SwitchPOV(activePOV);
        }

        void Update()
        {
            // -------------------------------------------------------------
            // HOTKEY ROUTING FOR DEDICATED SECONDARY SCREEN (F1-F6 or 1-6)
            // -------------------------------------------------------------
            if (SIH.Common.SimInput.GetKeyDown(KeyCode.F1) || SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha1))
            {
                SwitchPOV(SecondaryScreenPOV.SoldierFirstPerson);
            }
            else if (SIH.Common.SimInput.GetKeyDown(KeyCode.F2) || SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha2))
            {
                SwitchPOV(SecondaryScreenPOV.CommanderOverhead);
            }
            else if (SIH.Common.SimInput.GetKeyDown(KeyCode.F3) || SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha3))
            {
                SwitchPOV(SecondaryScreenPOV.UavTacticalRecon);
            }
            else if (SIH.Common.SimInput.GetKeyDown(KeyCode.F4) || SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha4))
            {
                SwitchPOV(SecondaryScreenPOV.CivilianDriverCockpit);
            }
            else if (SIH.Common.SimInput.GetKeyDown(KeyCode.F5) || SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha5))
            {
                SwitchPOV(SecondaryScreenPOV.VehicleThirdPerson);
            }
            else if (SIH.Common.SimInput.GetKeyDown(KeyCode.F6) || SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha6))
            {
                SwitchPOV(SecondaryScreenPOV.UrbanPedestrian);
            }

            // Smoothly interpolate secondary camera to active socket
            if (secondaryDisplayCamera != null && activeTargetSocket != null)
            {
                secondaryDisplayCamera.transform.position = Vector3.Lerp(
                    secondaryDisplayCamera.transform.position,
                    activeTargetSocket.position,
                    Time.deltaTime * positionSmoothSpeed
                );

                secondaryDisplayCamera.transform.rotation = Quaternion.Slerp(
                    secondaryDisplayCamera.transform.rotation,
                    activeTargetSocket.rotation,
                    Time.deltaTime * rotationSmoothSpeed
                );
            }
        }

        public void SwitchPOV(SecondaryScreenPOV newPOV)
        {
            activePOV = newPOV;
            switch (newPOV)
            {
                case SecondaryScreenPOV.SoldierFirstPerson:
                    activeTargetSocket = soldierHeadSocket;
                    break;
                case SecondaryScreenPOV.CommanderOverhead:
                    activeTargetSocket = commanderOverheadSocket;
                    break;
                case SecondaryScreenPOV.UavTacticalRecon:
                    activeTargetSocket = uavChaseSocket;
                    break;
                case SecondaryScreenPOV.CivilianDriverCockpit:
                    activeTargetSocket = civilianDriverSocket;
                    break;
                case SecondaryScreenPOV.VehicleThirdPerson:
                    activeTargetSocket = vehicleExternalSocket;
                    break;
                case SecondaryScreenPOV.UrbanPedestrian:
                    activeTargetSocket = urbanPedestrianSocket;
                    break;
            }

            Debug.Log($"[MULTI-SCREEN] Secondary Screen POV set to: {activePOV}");
        }

        private void AutoBindSocketsIfMissing()
        {
            // Auto-locate objects if not assigned in Inspector
            if (soldierHeadSocket == null)
            {
                GameObject soldier = GameObject.Find("Soldier_Ground_Pawn") ?? GameObject.Find("Soldier");
                if (soldier != null) soldierHeadSocket = soldier.transform;
            }

            if (commanderOverheadSocket == null)
            {
                GameObject commanderObj = GameObject.Find("Commander_Socket");
                if (commanderObj == null)
                {
                    commanderObj = new GameObject("Commander_Socket");
                    commanderObj.transform.position = new Vector3(0f, 65f, -15f);
                    commanderObj.transform.rotation = Quaternion.Euler(75f, 0f, 0f);
                }
                commanderOverheadSocket = commanderObj.transform;
            }

            if (civilianDriverSocket == null)
            {
                GameObject ev = GameObject.Find("AutonomousEV") ?? GameObject.Find("EgoVehicle") ?? GameObject.Find("Ego_Civilian_EV");
                if (ev != null)
                {
                    GameObject driverSock = new GameObject("CivilianDriver_Socket");
                    driverSock.transform.SetParent(ev.transform);
                    driverSock.transform.localPosition = new Vector3(0f, 1.25f, 0.4f);
                    driverSock.transform.localRotation = Quaternion.identity;
                    civilianDriverSocket = driverSock.transform;

                    GameObject extSock = new GameObject("VehicleExternal_Socket");
                    extSock.transform.SetParent(ev.transform);
                    extSock.transform.localPosition = new Vector3(0f, 2.3f, -5.5f);
                    extSock.transform.localRotation = Quaternion.Euler(12f, 0f, 0f);
                    vehicleExternalSocket = extSock.transform;
                }
            }

            if (urbanPedestrianSocket == null)
            {
                GameObject ped = GameObject.Find("Pedestrian_VRU_01") ?? GameObject.Find("Pedestrian_Pawn");
                if (ped != null)
                {
                    urbanPedestrianSocket = ped.transform;
                }
                else
                {
                    ped = new GameObject("Pedestrian_Pawn");
                    ped.transform.position = new Vector3(-8f, 1.6f, 12f);
                    ped.transform.rotation = Quaternion.Euler(0f, 110f, 0f);
                    urbanPedestrianSocket = ped.transform;
                }
            }
        }

        // -------------------------------------------------------------
        // DEDICATED HUD RENDERING FOR SECONDARY DISPLAY
        // -------------------------------------------------------------
        void OnGUI()
        {
            InitStyles();

            // When rendering on secondary display (or single display test), draw contextual HUD
            switch (activePOV)
            {
                case SecondaryScreenPOV.SoldierFirstPerson:
                    DrawSoldierHUD();
                    break;
                case SecondaryScreenPOV.CommanderOverhead:
                    DrawCommanderHUD();
                    break;
                case SecondaryScreenPOV.CivilianDriverCockpit:
                    DrawCivilianCockpitHUD();
                    break;
                case SecondaryScreenPOV.VehicleThirdPerson:
                    DrawVehicleExternalHUD();
                    break;
                case SecondaryScreenPOV.UrbanPedestrian:
                    DrawUrbanPedestrianHUD();
                    break;
                default:
                    break;
            }

            DrawPOVModeBadge();
        }

        private void DrawSoldierHUD()
        {
            // Tactical Reticle in center
            float cx = Screen.width / 2f;
            float cy = Screen.height / 2f;
            DrawBox(new Rect(cx - 15f, cy - 1f, 30f, 2f), new Color(1f, 0.15f, 0.15f, 0.85f));
            DrawBox(new Rect(cx - 1f, cy - 15f, 2f, 30f), new Color(1f, 0.15f, 0.15f, 0.85f));

            // Status Card Bottom Left
            DrawBox(new Rect(20, Screen.height - 110, 240, 90), new Color(0.04f, 0.08f, 0.12f, 0.88f));
            GUI.color = Color.white;
            GUI.Label(new Rect(30, Screen.height - 105, 220, 24), "SOLDIER POV: DISMOUNTED INFANTRY", headerStyle);
            GUI.color = new Color(0f, 1f, 0.5f);
            GUI.Label(new Rect(30, Screen.height - 82, 220, 20), "HEALTH: 100% | STAMINA: 94%", metricStyle);
            GUI.color = new Color(0f, 0.85f, 1f);
            GUI.Label(new Rect(30, Screen.height - 62, 220, 20), "WEAPON: INSAS 5.56mm | MAG: 30/30", metricStyle);
            GUI.Label(new Rect(30, Screen.height - 42, 220, 20), "THREAT STATUS: SCANNING (20 Hz)", statusStyle);
        }

        private void DrawCommanderHUD()
        {
            // Strategic Overhead Grid Card Top Right
            float w = 320f;
            float h = 130f;
            float x = Screen.width - w - 20f;
            DrawBox(new Rect(x, 20, w, h), new Color(0.02f, 0.05f, 0.10f, 0.90f));
            GUI.color = new Color(0f, 0.85f, 1f);
            GUI.Label(new Rect(x + 12, 28, w - 24, 24), "COMMANDER C2 OVERHEAD COP", headerStyle);
            GUI.color = Color.white;
            GUI.Label(new Rect(x + 12, 54, w - 24, 20), "TACTICAL GRID: 110m x 110m SECTOR", metricStyle);
            GUI.Label(new Rect(x + 12, 74, w - 24, 20), "MUM-T TETHER: UAV ORBIT + UGV ROVER", metricStyle);
            GUI.color = new Color(0f, 1f, 0.5f);
            GUI.Label(new Rect(x + 12, 94, w - 24, 20), "CLEARANCE: 4.4m UNDERPASS VOID CARVED", statusStyle);
            GUI.color = new Color(1f, 0.8f, 0.1f);
            GUI.Label(new Rect(x + 12, 114, w - 24, 20), "TRACKING: 3 TARGETS (HUNGARIAN-KALMAN)", statusStyle);
        }

        private void DrawCivilianCockpitHUD()
        {
            // Digital Instrument Cluster Bottom Center
            float w = 480f;
            float h = 80f;
            float x = (Screen.width - w) / 2f;
            float y = Screen.height - h - 16f;

            DrawBox(new Rect(x, y, w, h), new Color(0.03f, 0.06f, 0.10f, 0.90f));
            GUI.color = new Color(0f, 1f, 0.55f);
            GUI.Label(new Rect(x + 20, y + 14, 160, 36), "36 KM/H", headerStyle);
            GUI.color = Color.white;
            GUI.Label(new Rect(x + 170, y + 14, 290, 20), "AUTONOMOUS EV DRIVER COCKPIT", metricStyle);
            GUI.color = new Color(0f, 0.85f, 1f);
            GUI.Label(new Rect(x + 170, y + 36, 290, 20), "LIDAR: 16-CH VLP-16 | FOV: 360° | MLS: 20 Hz", statusStyle);
            GUI.color = new Color(0f, 1f, 0.55f);
            GUI.Label(new Rect(x + 170, y + 54, 290, 20), "BATTERY: 84% | DRIVE MODE: AUTONOMOUS", statusStyle);
        }

        private void DrawVehicleExternalHUD()
        {
            float w = 320f;
            float x = 20f;
            float y = 20f;
            DrawBox(new Rect(x, y, w, 80), new Color(0.02f, 0.05f, 0.09f, 0.88f));
            GUI.color = new Color(0f, 0.85f, 1f);
            GUI.Label(new Rect(x + 12, y + 10, w - 24, 24), "VEHICLE EXTERNAL CHASE POV", headerStyle);
            GUI.color = Color.white;
            GUI.Label(new Rect(x + 12, y + 34, w - 24, 20), "OBJECT TRACKING: 3D BOUNDING BOXES", metricStyle);
            GUI.color = new Color(0f, 1f, 0.5f);
            GUI.Label(new Rect(x + 12, y + 54, w - 24, 20), "PATH PLANNING: SPLINE TRAJECTORY LIVE", statusStyle);
        }

        private void DrawUrbanPedestrianHUD()
        {
            float w = 340f;
            float x = 20f;
            float y = 20f;
            DrawBox(new Rect(x, y, w, 80), new Color(0.03f, 0.07f, 0.12f, 0.88f));
            GUI.color = new Color(1f, 0.75f, 0.1f);
            GUI.Label(new Rect(x + 12, y + 10, w - 24, 24), "URBAN PEDESTRIAN CROSSWALK POV", headerStyle);
            GUI.color = Color.white;
            GUI.Label(new Rect(x + 12, y + 34, w - 24, 20), "V2P SAFETY BEACON: ACTIVE", metricStyle);
            GUI.color = new Color(0f, 1f, 0.5f);
            GUI.Label(new Rect(x + 12, y + 54, w - 24, 20), "APPROACHING EV: YIELDING (36 -> 0 KM/H)", statusStyle);
        }

        private void DrawPOVModeBadge()
        {
            // Top Mode Indicator Bar
            float w = 480f;
            float h = 34f;
            float x = (Screen.width - w) / 2f;
            float y = 10f;

            DrawBox(new Rect(x, y, w, h), new Color(0.01f, 0.03f, 0.06f, 0.92f));
            GUI.color = new Color(0f, 0.9f, 1f);
            GUI.Label(new Rect(x + 10, y + 7, w - 20, 20), $"SCREEN 2 OUTPUT: [{activePOV}]  (Press F1-F6 to Switch)", metricStyle);
        }

        private void DrawBox(Rect r, Color c)
        {
            Color prev = GUI.color;
            GUI.color = c;
            GUI.DrawTexture(r, hudTexture);
            GUI.color = prev;
        }

        private void InitStyles()
        {
            if (headerStyle == null)
            {
                headerStyle = new GUIStyle(GUI.skin.label);
                headerStyle.fontSize = 14;
                headerStyle.fontStyle = FontStyle.Bold;
            }
            if (metricStyle == null)
            {
                metricStyle = new GUIStyle(GUI.skin.label);
                metricStyle.fontSize = 11;
                metricStyle.fontStyle = FontStyle.Bold;
            }
            if (statusStyle == null)
            {
                statusStyle = new GUIStyle(GUI.skin.label);
                statusStyle.fontSize = 10;
                statusStyle.fontStyle = FontStyle.Normal;
            }
        }

        void OnDestroy()
        {
            if (hudTexture != null) Destroy(hudTexture);
        }
    }
}
