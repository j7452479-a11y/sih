// -----------------------------------------------------------------------------
// SIH26053 - MUM-T TACTICAL EDGE PERCEPTION ENGINE
// Unity C# Bridge: MUMT_CameraController.cs
// Multi-POV Camera Controller with Smooth Blend Transition (Keys 1-4 & HUD Dock)
// -----------------------------------------------------------------------------

using System.Collections;
using UnityEngine;

namespace SIH.Perception
{
    public enum CameraViewMode
    {
        Soldier,
        Uav,
        Ugv,
        Commander
    }

    public class MUMT_CameraController : MonoBehaviour
    {
        [Header("View Sockets")]
        public Transform soldierHeadSocket;
        public Transform uavChaseSocket;
        public Transform ugvBumperSocket;
        public Transform commanderSocket;
        public Transform sceneCenter;
        public Camera mainCamera;

        [Header("Transition Settings")]
        public float blendDuration = 1.0f;

        [Header("Commander Orbit Settings")]
        public float orbitRadius = 75f;
        public float orbitHeight = 55f;
        public float orbitSpeed = 8f;
        private float currentOrbitAngle = 45f;
        private bool isOrbiting = false;

        private bool isTransitioning = false;
        private Transform activeSocket;
        private CameraViewMode currentMode = CameraViewMode.Soldier;

        public CameraViewMode CurrentMode => currentMode;

        void Start()
        {
            if (mainCamera == null) mainCamera = Camera.main;
            activeSocket = soldierHeadSocket;
            currentMode = CameraViewMode.Soldier;
            SnapToSocket(soldierHeadSocket);
        }

        void Update()
        {
            // Keyboard Hotkeys
            if (SIH.Common.SimInput.GetKeyDown(KeyCode.Space) && !isTransitioning)
            {
                // Toggle between Soldier and Commander
                if (currentMode == CameraViewMode.Soldier) SwitchToCommander();
                else SwitchToSoldier();
            }

            if (SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha1)) SwitchToSoldier();
            if (SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha2)) SwitchToUav();
            if (SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha3)) SwitchToUgv();
            if (SIH.Common.SimInput.GetKeyDown(KeyCode.Alpha4)) SwitchToCommander();

            // Continuous socket following or orbiting
            if (!isTransitioning)
            {
                if (currentMode == CameraViewMode.Commander && isOrbiting)
                {
                    currentOrbitAngle += orbitSpeed * Time.deltaTime;
                    float rad = currentOrbitAngle * Mathf.Deg2Rad;
                    Vector3 center = sceneCenter != null ? sceneCenter.position : Vector3.zero;
                    Vector3 orbitPos = new Vector3(Mathf.Sin(rad) * orbitRadius, orbitHeight, Mathf.Cos(rad) * orbitRadius) + center;
                    transform.position = orbitPos;
                    transform.LookAt(center + Vector3.up * 4f);
                }
                else if (activeSocket != null)
                {
                    transform.position = activeSocket.position;
                    transform.rotation = activeSocket.rotation;
                }
            }
        }

        public void SwitchToSoldier()
        {
            if (isTransitioning || soldierHeadSocket == null) return;
            isOrbiting = false;
            currentMode = CameraViewMode.Soldier;
            StartCoroutine(BlendToSocket(soldierHeadSocket, blendDuration));
        }

        public void SwitchToUav()
        {
            if (isTransitioning || uavChaseSocket == null) return;
            isOrbiting = false;
            currentMode = CameraViewMode.Uav;
            StartCoroutine(BlendToSocket(uavChaseSocket, blendDuration));
        }

        public void SwitchToUgv()
        {
            if (isTransitioning || ugvBumperSocket == null) return;
            isOrbiting = false;
            currentMode = CameraViewMode.Ugv;
            StartCoroutine(BlendToSocket(ugvBumperSocket, blendDuration));
        }

        public void SwitchToCommander()
        {
            if (isTransitioning) return;
            currentMode = CameraViewMode.Commander;
            if (commanderSocket != null)
            {
                isOrbiting = false;
                StartCoroutine(BlendToSocket(commanderSocket, blendDuration));
            }
            else
            {
                isOrbiting = true;
            }
        }

        private IEnumerator BlendToSocket(Transform targetSocket, float duration)
        {
            if (targetSocket == null) yield break;

            isTransitioning = true;
            Vector3 startPos = transform.position;
            Quaternion startRot = transform.rotation;
            float elapsed = 0f;

            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                float t = Mathf.SmoothStep(0f, 1f, elapsed / duration);

                transform.position = Vector3.Lerp(startPos, targetSocket.position, t);
                transform.rotation = Quaternion.Slerp(startRot, targetSocket.rotation, t);
                yield return null;
            }

            activeSocket = targetSocket;
            SnapToSocket(targetSocket);
            isTransitioning = false;
        }

        private void SnapToSocket(Transform socket)
        {
            if (socket != null)
            {
                transform.position = socket.position;
                transform.rotation = socket.rotation;
            }
        }
    }
}
