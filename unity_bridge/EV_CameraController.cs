// -----------------------------------------------------------------------------
// SIH26053 - TACTICAL EDGE PERCEPTION ENGINE: SIM CIVILIAN
// Unity C# Script: EV_CameraController.cs
// Ego-Centric Automotive Multi-POV Camera Controller & ADAS Cockpit HUD
// -----------------------------------------------------------------------------

using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace SIH.Civilian
{
    public enum EVCameraViewMode
    {
        Windshield,
        RoofChase,
        Bumper,
        Corridor
    }

    public class EV_CameraController : MonoBehaviour
    {
        [Header("Target Vehicle")]
        public Transform evTransform;
        public EV_AutonomousController evController;
        public Camera mainCamera;

        [Header("View Sockets (Offsets relative to EV)")]
        public Vector3 windshieldOffset = new Vector3(0f, 1.25f, 0.4f);
        public Vector3 roofChaseOffset = new Vector3(0f, 2.2f, -5.5f);
        public Vector3 bumperOffset = new Vector3(0f, 0.5f, 2.3f);
        public Vector3 corridorOffset = new Vector3(-2.8f, 2.0f, -1.5f);

        [Header("Lookahead Targets (Offsets relative to EV)")]
        public Vector3 windshieldLook = new Vector3(0f, 1.2f, 40.0f);
        public Vector3 roofChaseLook = new Vector3(0f, 1.5f, 30.0f);
        public Vector3 bumperLook = new Vector3(0f, 0.4f, 30.0f);
        public Vector3 corridorLook = new Vector3(0f, 0.8f, 20.0f);

        [Header("ADAS HUD Styling")]
        public Color cyanColor = new Color(0f, 0.94f, 1f, 0.95f);
        public Color greenColor = new Color(0f, 1f, 0.55f, 0.95f);
        public Color redColor = new Color(1f, 0.12f, 0.25f, 0.95f);
        public Color amberColor = new Color(1f, 0.70f, 0.1f, 0.95f);

        private EVCameraViewMode currentMode = EVCameraViewMode.RoofChase;
        private Texture2D boxTexture;
        private GUIStyle titleStyle;
        private GUIStyle valStyle;
        private GUIStyle btnStyle;
        private GUIStyle activeBtnStyle;

        public EVCameraViewMode CurrentMode => currentMode;

        void Awake()
        {
            boxTexture = new Texture2D(1, 1);
            boxTexture.SetPixel(0, 0, Color.white);
            boxTexture.Apply();
        }

        void Start()
        {
            if (mainCamera == null) mainCamera = Camera.main;
            SwitchMode(EVCameraViewMode.RoofChase);
        }

        void Update()
        {
            // Hotkeys 1-4 for ego-centric vehicle perspectives
            if (SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha1)) SwitchMode(EVCameraViewMode.Windshield);
            if (SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha2)) SwitchMode(EVCameraViewMode.RoofChase);
            if (SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha3)) SwitchMode(EVCameraViewMode.Bumper);
            if (SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha4)) SwitchMode(EVCameraViewMode.Corridor);

            // Hotkey 5 to switch to Military Proving Ground
            if (SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha5))
            {
                SceneManager.LoadScene("TacticalProvingGround");
            }

            if (SIH.Common.SimInput.GetKeyDown(KeyCode.Space))
            {
                int next = ((int)currentMode + 1) % 4;
                SwitchMode((EVCameraViewMode)next);
            }

            // Smoothly position camera relative to EV
            if (evTransform != null)
            {
                Vector3 targetOffset = roofChaseOffset;
                Vector3 targetLook = roofChaseLook;

                switch (currentMode)
                {
                    case EVCameraViewMode.Windshield:
                        targetOffset = windshieldOffset;
                        targetLook = windshieldLook;
                        break;
                    case EVCameraViewMode.RoofChase:
                        targetOffset = roofChaseOffset;
                        targetLook = roofChaseLook;
                        break;
                    case EVCameraViewMode.Bumper:
                        targetOffset = bumperOffset;
                        targetLook = bumperLook;
                        break;
                    case EVCameraViewMode.Corridor:
                        targetOffset = corridorOffset;
                        targetLook = corridorLook;
                        break;
                }

                Vector3 desiredPos = evTransform.TransformPoint(targetOffset);
                Vector3 desiredLookAt = evTransform.TransformPoint(targetLook);

                transform.position = Vector3.Lerp(transform.position, desiredPos, Time.deltaTime * 12.0f);
                Quaternion desiredRot = Quaternion.LookRotation(desiredLookAt - transform.position);
                transform.rotation = Quaternion.Slerp(transform.rotation, desiredRot, Time.deltaTime * 12.0f);
            }
        }

        public void SwitchMode(EVCameraViewMode mode)
        {
            currentMode = mode;
        }

        void OnGUI()
        {
            InitStyles();

            // 1. Top ADAS Banner
            DrawTopAdasBanner();

            // 2. Bottom Camera Dock
            DrawCameraDock();
        }

        private void DrawTopAdasBanner()
        {
            float w = 620f;
            float h = 56f;
            float x = (Screen.width - w) / 2f;
            float y = 14f;

            Rect bannerRect = new Rect(x, y, w, h);
            DrawSolidRect(bannerRect, new Color(0.02f, 0.05f, 0.09f, 0.92f), cyanColor);

            float speedKmh = 36f;
            if (evController != null) speedKmh = evController.normalSpeed * 3.6f;

            GUI.color = greenColor;
            GUI.Label(new Rect(x + 14, y + 10, 140, 36), $"{(int)speedKmh} KM/H", titleStyle);

            GUI.color = Color.white;
            GUI.Label(new Rect(x + 170, y + 8, 260, 20), "SIM CIVILIAN: EGO-CENTRIC LIDAR", valStyle);

            GUI.color = cyanColor;
            GUI.Label(new Rect(x + 170, y + 28, 430, 20), "SE(3) COMP: -2.5° | CAPPED MLS: +1.60m SAFE HEADROOM", valStyle);
        }

        private void DrawCameraDock()
        {
            float dockW = 700f;
            float dockH = 46f;
            float dockX = (Screen.width - dockW) / 2f;
            float dockY = Screen.height - dockH - 16f;

            Rect dockRect = new Rect(dockX, dockY, dockW, dockH);
            DrawSolidRect(dockRect, new Color(0.02f, 0.05f, 0.09f, 0.90f), new Color(0.12f, 0.22f, 0.32f, 1f));

            float btnW = 130f;
            float btnH = 30f;
            float pad = 8f;
            float startX = dockX + 10f;
            float btnY = dockY + 8f;

            if (GUI.Button(new Rect(startX, btnY, btnW, btnH), "[1] WINDSHIELD", currentMode == EVCameraViewMode.Windshield ? activeBtnStyle : btnStyle))
            {
                SwitchMode(EVCameraViewMode.Windshield);
            }
            if (GUI.Button(new Rect(startX + (btnW + pad), btnY, btnW, btnH), "[2] ROOF CHASE", currentMode == EVCameraViewMode.RoofChase ? activeBtnStyle : btnStyle))
            {
                SwitchMode(EVCameraViewMode.RoofChase);
            }
            if (GUI.Button(new Rect(startX + (btnW + pad) * 2, btnY, btnW, btnH), "[3] BUMPER", currentMode == EVCameraViewMode.Bumper ? activeBtnStyle : btnStyle))
            {
                SwitchMode(EVCameraViewMode.Bumper);
            }
            if (GUI.Button(new Rect(startX + (btnW + pad) * 3, btnY, btnW, btnH), "[4] CORRIDOR", currentMode == EVCameraViewMode.Corridor ? activeBtnStyle : btnStyle))
            {
                SwitchMode(EVCameraViewMode.Corridor);
            }
            if (GUI.Button(new Rect(startX + (btnW + pad) * 4, btnY, btnW, btnH), "[5] MILITARY SIM", btnStyle))
            {
                SceneManager.LoadScene("TacticalProvingGround");
            }
        }

        private void DrawSolidRect(Rect r, Color fillColor, Color borderColor)
        {
            Color prev = GUI.color;
            GUI.color = fillColor;
            GUI.DrawTexture(r, boxTexture);

            GUI.color = borderColor;
            GUI.DrawTexture(new Rect(r.x, r.y, r.width, 1.5f), boxTexture);
            GUI.DrawTexture(new Rect(r.x, r.y + r.height - 1.5f, r.width, 1.5f), boxTexture);
            GUI.DrawTexture(new Rect(r.x, r.y, 1.5f, r.height), boxTexture);
            GUI.DrawTexture(new Rect(r.x + r.width - 1.5f, r.y, 1.5f, r.height), boxTexture);

            GUI.color = prev;
        }

        private void InitStyles()
        {
            if (titleStyle == null)
            {
                titleStyle = new GUIStyle(GUI.skin.label);
                titleStyle.fontSize = 24;
                titleStyle.fontStyle = FontStyle.Bold;
            }
            if (valStyle == null)
            {
                valStyle = new GUIStyle(GUI.skin.label);
                valStyle.fontSize = 11;
                valStyle.fontStyle = FontStyle.Bold;
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
                activeBtnStyle.normal.textColor = cyanColor;
            }
        }

        void OnDestroy()
        {
            if (boxTexture != null) Destroy(boxTexture);
        }
    }
}
