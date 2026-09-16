// -----------------------------------------------------------------------------
// SIH26053 - MUM-T TACTICAL EDGE PERCEPTION ENGINE
// Autonomous Flight Path for UAV Drone (Smooth Circular Orbit at +30m Altitude)
// -----------------------------------------------------------------------------

using UnityEngine;

namespace SIH.Perception
{
    public class UavFlightPath : MonoBehaviour
    {
        [Header("Circular Orbit Parameters")]
        public float radius = 32.0f;
        public float altitude = 30.0f;
        public float orbitSpeedDeg = 14.0f; // ~25 sec per full orbit
        public Vector3 centerPoint = Vector3.zero;

        private float currentAngleDeg = 0f;

        void Update()
        {
            currentAngleDeg += orbitSpeedDeg * Time.deltaTime;
            if (currentAngleDeg >= 360f) currentAngleDeg -= 360f;

            float rad = currentAngleDeg * Mathf.Deg2Rad;
            float x = centerPoint.x + Mathf.Cos(rad) * radius;
            float z = centerPoint.z + Mathf.Sin(rad) * radius;
            Vector3 targetPos = new Vector3(x, altitude, z);

            // Calculate tangent velocity vector for forward facing
            float forwardRad = (currentAngleDeg + 90f) * Mathf.Deg2Rad;
            Vector3 forwardDir = new Vector3(Mathf.Cos(forwardRad), 0f, Mathf.Sin(forwardRad)).normalized;

            transform.position = targetPos;
            if (forwardDir.sqrMagnitude > 0.001f)
            {
                transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(forwardDir), Time.deltaTime * 8f);
            }
        }
    }
}
