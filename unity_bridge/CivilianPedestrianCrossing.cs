// -----------------------------------------------------------------------------
// SIH26053 - TACTICAL EDGE PERCEPTION ENGINE: SIM CIVILIAN
// Unity C# Script: CivilianPedestrianCrossing.cs
// Spawns and animates dynamic crossing pedestrian and parked delivery van
// -----------------------------------------------------------------------------

using System;
using UnityEngine;

namespace SIH.Civilian
{
    public class CivilianPedestrianCrossing : MonoBehaviour
    {
        [Header("Pedestrian Configuration")]
        public GameObject pedestrianInstance;
        public float crosswalkZ = 6.2f;
        public float minX = -3.2f;
        public float maxX = 4.2f;
        public float walkSpeed = 1.4f; // 1.4 m/s standard human walking speed

        [Header("Delivery Van Obstacle")]
        public GameObject vanInstance;
        public Vector3 vanPosition = new Vector3(2.6f, 0f, 5.0f);
        public Vector3 vanDimensions = new Vector3(1.8f, 2.4f, 4.8f);

        private float currentX = 4.0f;
        private float direction = -1f; // -1 = walking left across street, +1 = walking back
        private float pauseTimer = 0f;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        private static void AutoInitBefore()
        {
            EnsureInScene();
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void AutoInitAfter()
        {
            EnsureInScene();
        }

        private static void EnsureInScene()
        {
            string sceneName = UnityEngine.SceneManagement.SceneManager.GetActiveScene().name;
            if (sceneName.Contains("Civilian") || GameObject.Find("Ego_Civilian_EV") != null || GameObject.Find("Civilian_Roadway") != null)
            {
                if (FindAnyObjectByType<CivilianPedestrianCrossing>() == null)
                {
                    GameObject managerObj = new GameObject("[Civilian_Pedestrian_Manager]");
                    managerObj.AddComponent<CivilianPedestrianCrossing>();
                    Debug.Log("[CivilianPedestrianCrossing] Auto-initialized pedestrian crossing for scene: " + sceneName);
                }
            }
        }

        void Awake()
        {
            EnsureDeliveryVanExists();
            EnsurePedestrianExists();
        }

        void Start()
        {
            currentX = 3.8f;
            direction = -1f; // Walking left across street from behind delivery van
            if (pedestrianInstance != null)
            {
                pedestrianInstance.transform.position = new Vector3(currentX, 0.95f, crosswalkZ);
                pedestrianInstance.transform.rotation = Quaternion.Euler(0f, -90f, 0f);
            }
        }

        void Update()
        {
            if (pedestrianInstance == null)
            {
                EnsurePedestrianExists();
                return;
            }

            if (pauseTimer > 0f)
            {
                pauseTimer -= Time.deltaTime;
                return;
            }

            // Move pedestrian along X axis across the road
            currentX += direction * walkSpeed * Time.deltaTime;

            if (currentX <= minX)
            {
                currentX = minX;
                direction = 1f;
                pauseTimer = 1.0f;
                // Face right
                pedestrianInstance.transform.rotation = Quaternion.Euler(0f, 90f, 0f);
            }
            else if (currentX >= maxX)
            {
                currentX = maxX;
                direction = -1f;
                pauseTimer = 1.0f;
                // Face left
                pedestrianInstance.transform.rotation = Quaternion.Euler(0f, -90f, 0f);
            }

            // Natural walking stride vertical bob
            float bobY = 0.95f + Mathf.Abs(Mathf.Sin(Time.time * 6.5f)) * 0.06f;
            pedestrianInstance.transform.position = new Vector3(currentX, bobY, crosswalkZ);
        }

        private void EnsureDeliveryVanExists()
        {
            if (vanInstance == null)
            {
                vanInstance = GameObject.Find("Delivery_Van_Parked");
            }

            if (vanInstance == null)
            {
                vanInstance = GameObject.CreatePrimitive(PrimitiveType.Cube);
                vanInstance.name = "Delivery_Van_Parked";
                vanInstance.transform.position = vanPosition + new Vector3(0f, vanDimensions.y / 2f, 0f);
                vanInstance.transform.localScale = vanDimensions;

                int layerObstacle = LayerMask.NameToLayer("Obstacle");
                if (layerObstacle != -1) vanInstance.layer = layerObstacle;

                Renderer r = vanInstance.GetComponent<Renderer>();
                if (r != null)
                {
                    r.material.color = new Color(0.20f, 0.25f, 0.32f); // Dark delivery van
                }

                // Add delivery van cab visual
                GameObject cab = GameObject.CreatePrimitive(PrimitiveType.Cube);
                cab.name = "Van_Cabin";
                cab.transform.parent = vanInstance.transform;
                cab.transform.localPosition = new Vector3(0f, 0.1f, -0.35f);
                cab.transform.localScale = new Vector3(0.96f, 0.8f, 0.35f);
                Renderer cabR = cab.GetComponent<Renderer>();
                if (cabR != null) cabR.material.color = new Color(0.15f, 0.20f, 0.28f);
                if (layerObstacle != -1) cab.layer = layerObstacle;

                Debug.Log("[CivilianPedestrianCrossing] Created parked delivery van at (X=2.6, Y=0, Z=5.0).");
            }
        }

        private void EnsurePedestrianExists()
        {
            if (pedestrianInstance == null)
            {
                pedestrianInstance = GameObject.Find("Pedestrian_VRU_01");
            }

            if (pedestrianInstance != null)
            {
                // Ensure high-visibility orange material and layer
                int layerHostile = LayerMask.NameToLayer("Hostile");
                if (layerHostile == -1) layerHostile = LayerMask.NameToLayer("Pedestrian");
                if (layerHostile != -1) pedestrianInstance.layer = layerHostile;

                Renderer r = pedestrianInstance.GetComponent<Renderer>();
                if (r != null)
                {
                    r.material.color = new Color(1.0f, 0.45f, 0.0f); // High-vis Orange
                }

                // Add humanoid head if not present without destroying parent object
                if (pedestrianInstance.transform.Find("Pedestrian_Head") == null)
                {
                    GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                    head.name = "Pedestrian_Head";
                    head.transform.parent = pedestrianInstance.transform;
                    head.transform.localPosition = new Vector3(0f, 0.72f, 0f);
                    head.transform.localScale = new Vector3(0.5f, 0.5f, 0.5f);
                    if (layerHostile != -1) head.layer = layerHostile;
                    Renderer hr = head.GetComponent<Renderer>();
                    if (hr != null) hr.material.color = new Color(0.85f, 0.68f, 0.55f);
                }
                return;
            }

            // If not found in scene, create complete 3D Pedestrian Humanoid Avatar
            pedestrianInstance = new GameObject("Pedestrian_VRU_01");
            pedestrianInstance.transform.position = new Vector3(3.8f, 0.95f, crosswalkZ);
            pedestrianInstance.transform.rotation = Quaternion.Euler(0f, -90f, 0f);

            int layerTarget = LayerMask.NameToLayer("Hostile");
            if (layerTarget == -1) layerTarget = LayerMask.NameToLayer("Pedestrian");
            if (layerTarget == -1) layerTarget = 0;
            pedestrianInstance.layer = layerTarget;

            // 1. Torso (Capsule) with bright orange safety jacket
            GameObject torso = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            torso.name = "Pedestrian_Torso";
            torso.transform.parent = pedestrianInstance.transform;
            torso.transform.localPosition = new Vector3(0f, 0f, 0f);
            torso.transform.localScale = new Vector3(0.48f, 0.65f, 0.32f);
            torso.layer = layerTarget;
            Renderer torsoR = torso.GetComponent<Renderer>();
            if (torsoR != null) torsoR.material.color = new Color(1.0f, 0.45f, 0.0f); // High-vis Orange

            // 2. Head (Sphere)
            GameObject headObj = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            headObj.name = "Pedestrian_Head";
            headObj.transform.parent = pedestrianInstance.transform;
            headObj.transform.localPosition = new Vector3(0f, 0.72f, 0f);
            headObj.transform.localScale = new Vector3(0.28f, 0.28f, 0.28f);
            headObj.layer = layerTarget;
            Renderer headR = headObj.GetComponent<Renderer>();
            if (headR != null) headR.material.color = new Color(0.85f, 0.68f, 0.55f);

            // 3. Legs
            GameObject legL = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            legL.name = "Leg_Left";
            legL.transform.parent = pedestrianInstance.transform;
            legL.transform.localPosition = new Vector3(-0.12f, -0.62f, 0f);
            legL.transform.localScale = new Vector3(0.12f, 0.32f, 0.12f);
            legL.layer = layerTarget;
            Renderer legLR = legL.GetComponent<Renderer>();
            if (legLR != null) legLR.material.color = new Color(0.15f, 0.20f, 0.30f);

            GameObject legR = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            legR.name = "Leg_Right";
            legR.transform.parent = pedestrianInstance.transform;
            legR.transform.localPosition = new Vector3(0.12f, -0.62f, 0f);
            legR.transform.localScale = new Vector3(0.12f, 0.32f, 0.12f);
            legR.layer = layerTarget;
            Renderer legRR = legR.GetComponent<Renderer>();
            if (legRR != null) legRR.material.color = new Color(0.15f, 0.20f, 0.30f);

            // Main Capsule Collider & Rigidbody
            CapsuleCollider col = pedestrianInstance.AddComponent<CapsuleCollider>();
            col.center = new Vector3(0f, 0f, 0f);
            col.radius = 0.32f;
            col.height = 1.75f;

            Rigidbody rb = pedestrianInstance.AddComponent<Rigidbody>();
            rb.isKinematic = true;

            Debug.Log("[CivilianPedestrianCrossing] Spawned 3D Pedestrian Avatar (VRU_01) at crosswalk.");
        }
    }
}
