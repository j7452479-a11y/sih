// -----------------------------------------------------------------------------
// SIH26053 - MUM-T TACTICAL EDGE PERCEPTION ENGINE
// UGV RC Car Elliptical Tether Navigation through Square Village Underpass
// -----------------------------------------------------------------------------

using UnityEngine;
using UnityEngine.AI;

namespace SIH.Perception
{
    public class MUMT_TetherAgent : MonoBehaviour
    {
        [Header("Tether Master")]
        public Transform uavDrone;

        [Header("Elliptical Ground Track")]
        public float semiMajorAxisA = 26.0f; // East-West width
        public float semiMinorAxisB = 16.0f; // North-South through underpass
        public float baseAngularSpeedDeg = 14.0f;
        public Vector3 villageCenter = Vector3.zero;

        [Header("Tether Dynamic Constraints")]
        public float maxTetherDistance = 20.0f;
        public float minTetherDistance = 14.0f;
        public float baseSpeed = 4.5f;

        [Header("Cable Visualization")]
        public bool renderCable = true;
        public LineRenderer cableLineRenderer;
        public int cableSegments = 24;
        public Color normalCableColor = new Color(0f, 0.94f, 1f, 0.85f);
        public Color overstrainColor = new Color(1f, 0.15f, 0.2f, 1f);

        private float currentAngleDeg = 0f;
        private Vector3[] cablePoints;
        private NavMeshAgent agent;

        void Awake()
        {
            agent = GetComponent<NavMeshAgent>();
            if (agent != null) agent.speed = baseSpeed;

            if (renderCable)
            {
                if (cableLineRenderer == null) cableLineRenderer = GetComponent<LineRenderer>();
                if (cableLineRenderer != null)
                {
                    cableLineRenderer.positionCount = cableSegments;
                    cableLineRenderer.startWidth = 0.05f;
                    cableLineRenderer.endWidth = 0.05f;
                    cableLineRenderer.useWorldSpace = true;
                    cablePoints = new Vector3[cableSegments];
                }
            }
        }

        void Update()
        {
            // 1. Calculate Current Euclidean Tether Distance
            float currentTetherDist = 18.0f;
            if (uavDrone != null)
            {
                currentTetherDist = Vector3.Distance(transform.position, uavDrone.position);
            }

            // 2. Dynamic Pacing based on Tether Tension Envelope (14m - 20m)
            float speedMultiplier = 1.0f;
            if (currentTetherDist > maxTetherDistance)
            {
                speedMultiplier = 1.4f; // Drone is pulling ahead, speed up
            }
            else if (currentTetherDist < minTetherDistance)
            {
                speedMultiplier = 0.6f; // Too close, ease off
            }

            // 3. Advance along Elliptical Ground Path
            currentAngleDeg += baseAngularSpeedDeg * speedMultiplier * Time.deltaTime;
            if (currentAngleDeg >= 360f) currentAngleDeg -= 360f;

            float rad = currentAngleDeg * Mathf.Deg2Rad;
            float targetX = villageCenter.x + Mathf.Cos(rad) * semiMajorAxisA;
            float targetZ = villageCenter.z + Mathf.Sin(rad) * semiMinorAxisB;
            float groundY = transform.position.y;

            Vector3 targetGroundPos = new Vector3(targetX, groundY, targetZ);

            // Steer NavMeshAgent or programmatic translation
            if (agent != null && agent.isOnNavMesh)
            {
                agent.speed = baseSpeed * speedMultiplier;
                agent.SetDestination(targetGroundPos);
            }
            else
            {
                Vector3 moveDir = (targetGroundPos - transform.position).normalized;
                transform.position = Vector3.MoveTowards(transform.position, targetGroundPos, baseSpeed * speedMultiplier * Time.deltaTime);
                if (moveDir.sqrMagnitude > 0.001f)
                {
                    transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(moveDir), Time.deltaTime * 8f);
                }
            }

            // 4. Render Physical Cable Catenary Sag
            if (cableLineRenderer != null && uavDrone != null && cablePoints != null)
            {
                Vector3 pA = uavDrone.position;
                Vector3 pB = transform.position + Vector3.up * 0.25f;
                float sag = Mathf.Max(0.1f, maxTetherDistance - currentTetherDist) * 0.25f;

                bool isStrained = currentTetherDist > (maxTetherDistance + 2.0f);
                cableLineRenderer.startColor = isStrained ? overstrainColor : normalCableColor;
                cableLineRenderer.endColor = isStrained ? overstrainColor : normalCableColor;

                for (int i = 0; i < cableSegments; i++)
                {
                    float t = (float)i / (cableSegments - 1);
                    Vector3 pt = Vector3.Lerp(pA, pB, t);
                    // Catenary sag parabolic profile
                    pt.y -= 4f * sag * t * (1f - t);
                    cablePoints[i] = pt;
                }
                cableLineRenderer.SetPositions(cablePoints);
            }
        }
    }
}
