// -----------------------------------------------------------------------------
// SIH26053 - MUM-T TACTICAL EDGE PERCEPTION ENGINE
// Automated Scene Construction Script for Square Tactical Village Proving Ground
// Headless batchmode execution: SceneBuilder.BuildScene
// -----------------------------------------------------------------------------

#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;
using Unity.AI.Navigation;
using SIH.Perception;
using SIH.Civilian;

public static class SceneBuilder
{
    [MenuItem("SIH/Build Tactical Proving Ground")]
    public static void BuildScene()
    {
        Debug.Log("[SceneBuilder] Building Complete Square Tactical Village Proving Ground...");

        // 1. Setup Semantic Layers
        SetupLayers();

        // 2. Create Clean Scene
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        // 3. Create Tactical Materials
        Material matRoad = GetOrCreateMaterial("Mat_Road", new Color(0.12f, 0.14f, 0.16f));
        Material matWhitePaint = GetOrCreateMaterial("Mat_WhitePaint", new Color(0.95f, 0.95f, 0.95f));
        Material matCurb = GetOrCreateMaterial("Mat_Curb", new Color(0.55f, 0.58f, 0.62f));
        Material matBridge = GetOrCreateMaterial("Mat_Bridge", new Color(0.32f, 0.36f, 0.42f));
        Material matBuilding = GetOrCreateMaterial("Mat_Building", new Color(0.82f, 0.78f, 0.72f)); // Warm stone/stucco
        Material matChurch = GetOrCreateMaterial("Mat_Church", new Color(0.58f, 0.63f, 0.70f));
        Material matRoof = GetOrCreateMaterial("Mat_Roof", new Color(0.68f, 0.28f, 0.22f)); // Terracotta gabled roof
        Material matSlateRoof = GetOrCreateMaterial("Mat_SlateRoof", new Color(0.24f, 0.28f, 0.34f)); // Slate dark blue-grey
        Material matWood = GetOrCreateMaterial("Mat_Wood", new Color(0.35f, 0.22f, 0.14f)); // Wooden doors
        Material matWindow = GetOrCreateMaterial("Mat_Window", new Color(0.25f, 0.55f, 0.85f)); // Window glass
        Material matWall = GetOrCreateMaterial("Mat_Wall", new Color(0.46f, 0.50f, 0.56f));
        Material matBorder = GetOrCreateMaterial("Mat_Border", new Color(0.18f, 0.20f, 0.25f));
        Material matBunker = GetOrCreateMaterial("Mat_Bunker", new Color(0.38f, 0.36f, 0.32f));
        Material matUav = GetOrCreateMaterial("Mat_UAV", new Color(0.0f, 0.94f, 1.0f));
        Material matUgv = GetOrCreateMaterial("Mat_UGV", new Color(0.85f, 0.15f, 0.18f));
        Material matCarTire = GetOrCreateMaterial("Mat_CarTire", new Color(0.08f, 0.08f, 0.09f));
        Material matCarRim = GetOrCreateMaterial("Mat_CarRim", new Color(0.75f, 0.78f, 0.82f));
        Material matCarGlass = GetOrCreateMaterial("Mat_CarGlass", new Color(0.08f, 0.12f, 0.16f));
        Material matHeadlight = GetOrCreateMaterial("Mat_Headlight", new Color(1.0f, 0.98f, 0.82f));
        Material matTaillight = GetOrCreateMaterial("Mat_Taillight", new Color(0.95f, 0.10f, 0.12f));
        Material matHostile = GetOrCreateMaterial("Mat_Hostile", new Color(0.95f, 0.18f, 0.24f));

        int layerRoad = LayerMask.NameToLayer("Road");
        int layerBuilding = LayerMask.NameToLayer("Building");
        int layerHostile = LayerMask.NameToLayer("Hostile");
        int layerObstacle = LayerMask.NameToLayer("Obstacle");

        if (layerRoad == -1) layerRoad = 0;
        if (layerBuilding == -1) layerBuilding = 0;
        if (layerHostile == -1) layerHostile = 0;
        if (layerObstacle == -1) layerObstacle = 0;

        // 4. Square Ground Terrain (110m x 110m)
        GameObject ground = GameObject.CreatePrimitive(PrimitiveType.Cube);
        ground.name = "Square_Village_Ground";
        ground.transform.position = new Vector3(0f, -0.15f, 0f);
        ground.transform.localScale = new Vector3(110f, 0.3f, 110f);
        ground.GetComponent<Renderer>().sharedMaterial = matRoad;
        ground.layer = layerRoad;

        // Paved Road Network with White Lane Markings, Curbs & Pedestrian Crosswalks
        CreateRoadsWithMarkings(matRoad, matCurb, matWhitePaint, layerRoad, layerObstacle);

        // Square Perimeter Border Walls (North, South, East, West at ±52m)
        CreateBox("Border_North", new Vector3(0f, 1.5f, 52f), new Vector3(106f, 3f, 1.6f), matBorder, layerObstacle);
        CreateBox("Border_South", new Vector3(0f, 1.5f, -52f), new Vector3(106f, 3f, 1.6f), matBorder, layerObstacle);
        CreateBox("Border_East", new Vector3(52f, 1.5f, 0f), new Vector3(1.6f, 3f, 106f), matBorder, layerObstacle);
        CreateBox("Border_West", new Vector3(-52f, 1.5f, 0f), new Vector3(1.6f, 3f, 106f), matBorder, layerObstacle);

        // 5. Central Concrete Overpass Bridge (40m x 9m with Open 4.4m Underpass Clearance)
        GameObject bridge = new GameObject("Central_Overpass_Bridge");
        bridge.layer = layerObstacle;

        // Bridge Deck at Y = 5.0m elevation
        GameObject deck = CreateBox("Bridge_Deck", new Vector3(0f, 5.0f, 0f), new Vector3(40f, 1.2f, 9f), matBridge, layerObstacle);
        deck.transform.parent = bridge.transform;

        // Concrete Abutment Pillars at X = -17m and X = +17m
        GameObject pillarL = CreateBox("Pillar_Left", new Vector3(-17f, 2.2f, 0f), new Vector3(2.5f, 4.4f, 7.5f), matBridge, layerObstacle);
        pillarL.transform.parent = bridge.transform;
        GameObject pillarR = CreateBox("Pillar_Right", new Vector3(17f, 2.2f, 0f), new Vector3(2.5f, 4.4f, 7.5f), matBridge, layerObstacle);
        pillarR.transform.parent = bridge.transform;

        // Ramps on Left and Right
        GameObject rampL = CreateBox("Ramp_Left", new Vector3(-27.5f, 2.5f, 0f), new Vector3(16f, 0.9f, 9f), matBridge, layerObstacle);
        rampL.transform.rotation = Quaternion.Euler(0f, 0f, -14f);
        rampL.transform.parent = bridge.transform;

        GameObject rampR = CreateBox("Ramp_Right", new Vector3(27.5f, 2.5f, 0f), new Vector3(16f, 0.9f, 9f), matBridge, layerObstacle);
        rampR.transform.rotation = Quaternion.Euler(0f, 0f, 14f);
        rampR.transform.parent = bridge.transform;

        // -------------------------------------------------------------
        // COMBINATION OF DIVERSE VILLAGE STRUCTURES (4 QUADRANTS)
        // -------------------------------------------------------------

        // QUADRANT 1: NORTH-EAST (Gothic Church Complex with 18m Spire + Outposts)
        CreateGothicCathedral(new Vector3(25f, 0f, 25f), matChurch, matSlateRoof, matWood, matWindow, layerBuilding);

        CreateVillageHouse("BLD_NE_01_Parish_Annex", new Vector3(38f, 0f, 22f), new Vector3(9f, 4.8f, 11f), matBuilding, matRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_NE_02_Priest_Cottage", new Vector3(25f, 0f, 42f), new Vector3(10f, 4.5f, 8f), matBuilding, matRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_NE_03_Field_Headquarters", new Vector3(38f, 0f, 38f), new Vector3(12f, 6.0f, 10f), matBuilding, matSlateRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_NE_04_Ammo_Storage", new Vector3(44f, 0f, 16f), new Vector3(10f, 6.5f, 12f), matBuilding, matRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_NE_05_Security_Checkpost", new Vector3(16f, 0f, 36f), new Vector3(8f, 4.5f, 8f), matBuilding, matRoof, matWood, matWindow, layerBuilding);

        // QUADRANT 2: NORTH-WEST (Urban Canyon: Multi-Story Residential & Commercial)
        CreateVillageHouse("BLD_NW_01_4Story_BlockA", new Vector3(-26f, 0f, 26f), new Vector3(14f, 12.0f, 12f), matBuilding, matSlateRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_NW_02_4Story_BlockB", new Vector3(-26f, 0f, 11f), new Vector3(14f, 12.0f, 11f), matBuilding, matSlateRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_NW_03_Commercial_3Story", new Vector3(-14f, 0f, 34f), new Vector3(10f, 9.5f, 8f), matBuilding, matRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_NW_04_Storehouse_2Story", new Vector3(-40f, 0f, 18f), new Vector3(9f, 6.5f, 13f), matBuilding, matRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_NW_05_Command_Facility", new Vector3(-42f, 0f, 34f), new Vector3(11f, 6.5f, 12f), matBuilding, matSlateRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_NW_06_Guard_Quarters", new Vector3(-18f, 0f, 20f), new Vector3(8f, 4.5f, 8f), matBuilding, matRoof, matWood, matWindow, layerBuilding);

        // QUADRANT 3: SOUTH-WEST (Residential Houses, Cottages & Primary Occlusion Wall)
        CreateVillageHouse("BLD_SW_01_House_2Story", new Vector3(-25f, 0f, -25f), new Vector3(12f, 6.5f, 10f), matBuilding, matRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_SW_02_Barn_1Story", new Vector3(-38f, 0f, -22f), new Vector3(10f, 4.2f, 8f), matBuilding, matRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_SW_03_Cottage_1Story", new Vector3(-15f, 0f, -34f), new Vector3(8f, 4.2f, 7f), matBuilding, matRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_SW_04_Supply_Depot", new Vector3(-26f, 0f, -42f), new Vector3(13f, 5.5f, 10f), matBuilding, matSlateRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_SW_05_Power_Substation", new Vector3(-42f, 0f, -38f), new Vector3(10f, 6.0f, 12f), matBuilding, matSlateRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_SW_06_Corner_Outpost", new Vector3(-38f, 0f, -14f), new Vector3(9f, 5.5f, 9f), matBuilding, matRoof, matWood, matWindow, layerBuilding);

        // Primary Stone Occlusion Wall (16m long, 2.5m tall at Z = -14m)
        CreateBox("Stone_Occlusion_Wall_Primary", new Vector3(0f, 1.25f, -14f), new Vector3(16f, 2.5f, 0.8f), matWall, layerObstacle);
        CreateBox("Stone_Wall_Flank_West", new Vector3(-18f, 1.1f, -8f), new Vector3(8f, 2.2f, 0.6f), matWall, layerObstacle);

        // QUADRANT 4: SOUTH-EAST (Market Quarter, Merchant Houses & Clutter)
        CreateVillageHouse("BLD_SE_01_Merchant_House_2Story", new Vector3(26f, 0f, -24f), new Vector3(11f, 6.5f, 10f), matBuilding, matRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_SE_02_Market_Warehouse", new Vector3(40f, 0f, -18f), new Vector3(11f, 4.5f, 9f), matBuilding, matRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_SE_03_Market_Stalls", new Vector3(16f, 0f, -32f), new Vector3(8f, 3.2f, 7f), matBuilding, matRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_SE_04_Grain_Mill_Storage", new Vector3(42f, 0f, -34f), new Vector3(12f, 7.5f, 12f), matBuilding, matSlateRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_SE_05_Tactical_Ops_Center", new Vector3(26f, 0f, -40f), new Vector3(12f, 6.0f, 10f), matBuilding, matSlateRoof, matWood, matWindow, layerBuilding);
        CreateVillageHouse("BLD_SE_06_Eastern_Sentry_Post", new Vector3(18f, 0f, -20f), new Vector3(8f, 4.5f, 8f), matBuilding, matRoof, matWood, matWindow, layerBuilding);
        CreateBox("Stone_Wall_East", new Vector3(12f, 1.1f, -10f), new Vector3(10f, 2.2f, 0.6f), matWall, layerObstacle);

        // PERIMETER WATCHTOWERS (4 Corners)
        CreateBox("TWR_NW", new Vector3(-44f, 4.0f, 44f), new Vector3(4.5f, 8.0f, 4.5f), matBorder, layerObstacle);
        CreateBox("TWR_NE", new Vector3(44f, 4.0f, 44f), new Vector3(4.5f, 8.0f, 4.5f), matBorder, layerObstacle);
        CreateBox("TWR_SW", new Vector3(-44f, 4.0f, -44f), new Vector3(4.5f, 8.0f, 4.5f), matBorder, layerObstacle);
        CreateBox("TWR_SE", new Vector3(44f, 4.0f, -44f), new Vector3(4.5f, 8.0f, 4.5f), matBorder, layerObstacle);

        // CARDINAL SANDBAG BUNKERS
        CreateBox("BNK_North", new Vector3(0f, 1.0f, 36f), new Vector3(6f, 2.0f, 3.5f), matBunker, layerObstacle);
        CreateBox("BNK_South", new Vector3(0f, 1.0f, -36f), new Vector3(6f, 2.0f, 3.5f), matBunker, layerObstacle);
        CreateBox("BNK_East", new Vector3(36f, 1.0f, 0f), new Vector3(3.5f, 2.0f, 6f), matBunker, layerObstacle);
        CreateBox("BNK_West", new Vector3(-36f, 1.0f, 0f), new Vector3(3.5f, 2.0f, 6f), matBunker, layerObstacle);

        // 6. Directional Sunlight & Atmosphere
        GameObject lightObj = new GameObject("Sunlight");
        Light sun = lightObj.AddComponent<Light>();
        sun.type = LightType.Directional;
        sun.color = new Color(0.96f, 0.96f, 1.0f);
        sun.intensity = 1.3f;
        sun.shadows = LightShadows.Soft;
        lightObj.transform.rotation = Quaternion.Euler(50f, -35f, 0f);

        // 7. Bake NavMeshSurface across Square Village & Underpass
        NavMeshSurface navSurface = ground.AddComponent<NavMeshSurface>();
        navSurface.collectObjects = CollectObjects.All;
        navSurface.useGeometry = NavMeshCollectGeometry.PhysicsColliders;
        navSurface.BuildNavMesh();
        Debug.Log("[SceneBuilder] NavMesh successfully baked across square village & bridge underpass!");

        // 8. Dynamic Hostile Actors
        // Hostile Bravo: Steps behind the primary stone wall (Z = -14m)
        GameObject hostileBravo = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        hostileBravo.name = "Hostile_Bravo_ID2";
        hostileBravo.transform.position = new Vector3(-10f, 1.0f, -14f);
        hostileBravo.transform.localScale = new Vector3(0.85f, 1.0f, 0.85f);
        hostileBravo.GetComponent<Renderer>().sharedMaterial = matHostile;
        hostileBravo.layer = layerHostile;
        HostilePatrol patrolB = hostileBravo.AddComponent<HostilePatrol>();
        patrolB.speed = 1.8f;
        patrolB.minX = -12f;
        patrolB.maxX = 12f;
        patrolB.fixedZ = -14f;

        // Hostile Alpha: Patrolling East Cross Street (Z = 2m)
        GameObject hostileAlpha = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        hostileAlpha.name = "Hostile_Alpha_ID1";
        hostileAlpha.transform.position = new Vector3(24f, 1.0f, 2f);
        hostileAlpha.transform.localScale = new Vector3(0.85f, 1.0f, 0.85f);
        hostileAlpha.GetComponent<Renderer>().sharedMaterial = matHostile;
        hostileAlpha.layer = layerHostile;
        HostilePatrol patrolA = hostileAlpha.AddComponent<HostilePatrol>();
        patrolA.speed = 1.5f;
        patrolA.minX = 18f;
        patrolA.maxX = 34f;
        patrolA.fixedZ = 2f;

        // Hostile Charlie: Elevated sniper post on Church Tower (Y = 16.5m)
        GameObject hostileCharlie = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        hostileCharlie.name = "Hostile_Charlie_Sniper_ID3";
        hostileCharlie.transform.position = new Vector3(25f, 16.5f, 14f);
        hostileCharlie.transform.localScale = new Vector3(0.85f, 1.0f, 0.85f);
        hostileCharlie.GetComponent<Renderer>().sharedMaterial = matHostile;
        hostileCharlie.layer = layerHostile;

        // 9. UAV Drone Actor (Circular Orbit R=32m, Alt=+30m & Port 5001 LiDAR)
        GameObject uav = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        uav.name = "UAV_Drone";
        uav.transform.position = new Vector3(32f, 30f, 0f);
        uav.transform.localScale = new Vector3(1.4f, 0.18f, 1.4f);
        uav.GetComponent<Renderer>().sharedMaterial = matUav;

        // Circular Flight Path: Radius = 32m, Height = 30m
        UavFlightPath flight = uav.AddComponent<UavFlightPath>();
        flight.radius = 32.0f;
        flight.altitude = 30.0f;
        flight.orbitSpeedDeg = 14.0f;
        flight.centerPoint = Vector3.zero;

        // Nadir LiDAR Scanner looking down at square village
        LidarJobStreamer uavLidar = uav.AddComponent<LidarJobStreamer>();
        uavLidar.targetPort = 5001;
        uavLidar.sensorType = 1;
        uavLidar.channels = 16;
        uavLidar.beamsPerChannel = 20;
        uavLidar.maxRangeMeters = 80f;
        uavLidar.isNadirDroneScanner = true;

        // Conical Downward Visual Light
        GameObject scanLight = new GameObject("Nadir_Scanner_Beam");
        scanLight.transform.parent = uav.transform;
        scanLight.transform.localPosition = Vector3.zero;
        scanLight.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
        Light spot = scanLight.AddComponent<Light>();
        spot.type = LightType.Spot;
        spot.color = new Color(0f, 0.94f, 1.0f);
        spot.intensity = 4.5f;
        spot.range = 40f;
        spot.spotAngle = 65f;

        GameObject uavChaseSocket = new GameObject("UavChaseSocket");
        uavChaseSocket.transform.parent = uav.transform;
        uavChaseSocket.transform.localPosition = new Vector3(0f, 3.5f, -8.0f);
        uavChaseSocket.transform.localRotation = Quaternion.Euler(22f, 0f, 0f);

        // 10. UGV Tethered RC Car Actor (Rally Car Body with 4 Wheels, Cabin, Headlights & Tether Mast)
        GameObject ugv = new GameObject("UGV_Tethered_Car");
        ugv.transform.position = new Vector3(26f, 0.05f, 0f);
        ugv.layer = layerObstacle;

        BoxCollider ugvCol = ugv.AddComponent<BoxCollider>();
        ugvCol.center = new Vector3(0f, 0.28f, 0f);
        ugvCol.size = new Vector3(0.9f, 0.5f, 1.4f);

        AttachCarVisuals(ugv, matUgv, matCarGlass, matCarTire, matCarRim, matHeadlight, matTaillight, true, layerObstacle);

        NavMeshAgent agent = ugv.AddComponent<NavMeshAgent>();
        agent.speed = 4.5f;
        agent.stoppingDistance = 0.5f;

        LineRenderer tetherLine = ugv.AddComponent<LineRenderer>();
        tetherLine.startWidth = 0.05f;
        tetherLine.endWidth = 0.05f;
        tetherLine.material = matUav;

        // Elliptical Tether Navigation: A = 26m, B = 16m (passes through underpass at Z = 0)
        MUMT_TetherAgent tetherAgent = ugv.AddComponent<MUMT_TetherAgent>();
        tetherAgent.uavDrone = uav.transform;
        tetherAgent.semiMajorAxisA = 26.0f;
        tetherAgent.semiMinorAxisB = 16.0f;
        tetherAgent.maxTetherDistance = 20.0f;
        tetherAgent.minTetherDistance = 14.0f;
        tetherAgent.cableLineRenderer = tetherLine;

        LidarJobStreamer ugvLidar = ugv.AddComponent<LidarJobStreamer>();
        ugvLidar.targetPort = 5002;
        ugvLidar.sensorType = 2;
        ugvLidar.channels = 16;
        ugvLidar.beamsPerChannel = 20;
        ugvLidar.maxRangeMeters = 45f;
        ugvLidar.isNadirDroneScanner = false;

        GameObject ugvBumperSocket = new GameObject("UgvBumperSocket");
        ugvBumperSocket.transform.parent = ugv.transform;
        ugvBumperSocket.transform.localPosition = new Vector3(0f, 0.6f, 1.2f);

        // 11. Soldier Ground Pawn (South Entrance at Z = -45m)
        GameObject soldier = new GameObject("Soldier_Ground_Pawn");
        soldier.transform.position = new Vector3(0f, 0f, -45f);

        GameObject soldierHeadSocket = new GameObject("SoldierHeadSocket");
        soldierHeadSocket.transform.parent = soldier.transform;
        soldierHeadSocket.transform.localPosition = new Vector3(0f, 1.75f, 0f);
        soldierHeadSocket.transform.localRotation = Quaternion.Euler(0f, 0f, 0f);

        // 12. Commander Tactical Camera Reference Socket (Elevated Overview)
        GameObject commanderSocket = new GameObject("CommanderTacticalSocket");
        commanderSocket.transform.position = new Vector3(0f, 52f, -55f);
        commanderSocket.transform.rotation = Quaternion.Euler(46f, 0f, 0f);

        // 13. Tactical Camera Rig with Multi-POV Switcher & Reticle Manager
        GameObject camObj = new GameObject("Main Camera");
        camObj.tag = "MainCamera";
        Camera cam = camObj.AddComponent<Camera>();
        cam.fieldOfView = 65f;
        cam.nearClipPlane = 0.3f;
        cam.farClipPlane = 500f;
        camObj.AddComponent<AudioListener>();

        MUMT_CameraController camCtrl = camObj.AddComponent<MUMT_CameraController>();
        camCtrl.soldierHeadSocket = soldierHeadSocket.transform;
        camCtrl.uavChaseSocket = uavChaseSocket.transform;
        camCtrl.ugvBumperSocket = ugvBumperSocket.transform;
        camCtrl.commanderSocket = commanderSocket.transform;
        camCtrl.mainCamera = cam;

        ThreatReticleManager reticleMgr = camObj.AddComponent<ThreatReticleManager>();
        reticleMgr.activeCamera = cam;
        reticleMgr.cameraController = camCtrl;
        reticleMgr.listenPort = 5003;

        // Tactical 3D Point Visualizer for real-time LiDAR beams
        TacticalPointVisualizer visualizer = camObj.AddComponent<TacticalPointVisualizer>();
        visualizer.uavStreamer = uavLidar;
        visualizer.ugvStreamer = ugvLidar;

        // 13b. Simulation Master Clock & Watchdog Heartbeat Broadcaster (Port 5005)
        GameObject heartbeatObj = new GameObject("[Simulation_Heartbeat_Master]");
        SimulationHeartbeat heartbeat = heartbeatObj.AddComponent<SimulationHeartbeat>();
        heartbeat.edgeNodeIp = "127.0.0.1";
        heartbeat.heartbeatPort = 5005;

        // 14. Save Complete Scene
        string scenesDir = "Assets/Scenes";
        if (!Directory.Exists(scenesDir)) Directory.CreateDirectory(scenesDir);
        string scenePath = Path.Combine(scenesDir, "TacticalProvingGround.unity");
        EditorSceneManager.SaveScene(scene, scenePath);
        Debug.Log($"[SceneBuilder] SUCCESS: Square Tactical Village scene saved to {scenePath}");

        EditorBuildSettings.scenes = new EditorBuildSettingsScene[]
        {
            new EditorBuildSettingsScene(scenePath, true)
        };

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("[SceneBuilder] BUILD COMPLETE. Square Village Proving Ground ready for runtime execution.");
    }

    [MenuItem("SIH/Build Civilian Urban Proving Ground")]
    public static void BuildCivilianScene()
    {
        Debug.Log("[SceneBuilder] Building Complete Civilian Urban Proving Ground for Autonomous EV...");

        SetupLayers();
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        Material matRoad = GetOrCreateMaterial("Mat_Road_Civilian", new Color(0.12f, 0.14f, 0.16f));
        Material matCurb = GetOrCreateMaterial("Mat_Curb_Civilian", new Color(0.42f, 0.44f, 0.48f));
        Material matUnderpass = GetOrCreateMaterial("Mat_Underpass_Civilian", new Color(0.35f, 0.38f, 0.42f));
        Material matVan = GetOrCreateMaterial("Mat_DeliveryVan", new Color(0.25f, 0.30f, 0.38f));
        Material matEv = GetOrCreateMaterial("Mat_CivilianEV", new Color(0.0f, 0.65f, 0.95f));
        Material matPed = GetOrCreateMaterial("Mat_Pedestrian", new Color(1.0f, 0.55f, 0.0f));
        Material matWhitePaint = GetOrCreateMaterial("Mat_White_Paint", new Color(0.95f, 0.95f, 0.95f));
        Material matCarTire = GetOrCreateMaterial("Mat_Car_Tire", new Color(0.08f, 0.08f, 0.09f));
        Material matCarRim = GetOrCreateMaterial("Mat_Car_Rim", new Color(0.75f, 0.78f, 0.82f));
        Material matCarGlass = GetOrCreateMaterial("Mat_Car_Glass", new Color(0.15f, 0.25f, 0.35f, 0.85f));
        Material matHeadlight = GetOrCreateMaterial("Mat_Headlight_LED", new Color(0.95f, 0.98f, 1.0f));
        Material matTaillight = GetOrCreateMaterial("Mat_Taillight_Red", new Color(0.95f, 0.1f, 0.05f));
        Material matHouseWall = GetOrCreateMaterial("Mat_House_Wall", new Color(0.82f, 0.78f, 0.70f));
        Material matHouseRoof = GetOrCreateMaterial("Mat_Slate_Roof", new Color(0.28f, 0.16f, 0.12f));
        Material matWoodDoor = GetOrCreateMaterial("Mat_Wood_Door", new Color(0.35f, 0.20f, 0.10f));

        int layerRoad = LayerMask.NameToLayer("Road");
        int layerBuilding = LayerMask.NameToLayer("Building");
        int layerHostile = LayerMask.NameToLayer("Hostile");
        int layerObstacle = LayerMask.NameToLayer("Obstacle");

        if (layerRoad == -1) layerRoad = 0;
        if (layerBuilding == -1) layerBuilding = 0;
        if (layerHostile == -1) layerHostile = 0;
        if (layerObstacle == -1) layerObstacle = 0;

        // 1. Two-Lane Asphalt Roadway (100m long, 7.0m wide)
        CreateBox("Civilian_Roadway", new Vector3(0f, -0.05f, 0f), new Vector3(7.0f, 0.1f, 100.0f), matRoad, layerRoad);

        // 2. 15cm Raised Sidewalk Curbs
        CreateBox("Curb_Left", new Vector3(-3.8f, 0.075f, 0f), new Vector3(0.6f, 0.15f, 100.0f), matCurb, layerObstacle);
        CreateBox("Curb_Right", new Vector3(3.8f, 0.075f, 0f), new Vector3(0.6f, 0.15f, 100.0f), matCurb, layerObstacle);

        // Dashed White Lane Centerlines along Roadway
        for (float z = -45f; z <= 45f; z += 5.5f)
        {
            if (z >= 14f && z <= 31f) continue; // Underpass clearance
            CreateBox($"Civilian_Line_{z:F0}", new Vector3(0f, 0.02f, z), new Vector3(0.20f, 0.02f, 2.8f), matWhitePaint, layerRoad);
        }

        // Zebra Pedestrian Crosswalk near Pedestrian Crossing (Z = 6.2m)
        for (float x = -3.0f; x <= 3.0f; x += 1.0f)
        {
            CreateBox($"Civilian_Zebra_{x:F1}", new Vector3(x, 0.02f, 6.2f), new Vector3(0.55f, 0.02f, 2.5f), matWhitePaint, layerRoad);
        }

        // 3. Concrete Underpass Structure (3.2m Clearance Ceiling at Z in [15m..30m])
        CreateBox("Underpass_Pillar_L", new Vector3(-4.2f, 1.8f, 22.5f), new Vector3(0.8f, 3.6f, 15.0f), matUnderpass, layerBuilding);
        CreateBox("Underpass_Pillar_R", new Vector3(4.2f, 1.8f, 22.5f), new Vector3(0.8f, 3.6f, 15.0f), matUnderpass, layerBuilding);
        CreateBox("Underpass_Ceiling", new Vector3(0f, 3.4f, 22.5f), new Vector3(9.2f, 0.4f, 15.0f), matUnderpass, layerBuilding);

        // 4. Roadside Suburban Houses
        CreateVillageHouse("Suburban_House_West", new Vector3(-8.5f, 0f, -12f), new Vector3(6.5f, 3.8f, 7.5f), matHouseWall, matHouseRoof, matWoodDoor, matCarGlass, layerBuilding);
        CreateVillageHouse("Suburban_House_East", new Vector3(8.5f, 0f, -18f), new Vector3(7.0f, 4.2f, 8.0f), matHouseWall, matHouseRoof, matWoodDoor, matCarGlass, layerBuilding);

        // 5. Parked Delivery Van at Curb (Z = +5.0m, casting radial blind occlusion cone)
        GameObject van = CreateDeliveryVan("Delivery_Van_Parked", new Vector3(2.8f, 0f, 5.0f), matVan, matUnderpass, matCarTire, matCarGlass, matHeadlight, layerObstacle);

        // 6. Crossing Pedestrian (Steps out from behind the parked delivery van)
        GameObject ped = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        ped.name = "Pedestrian_VRU_01";
        ped.transform.position = new Vector3(4.0f, 0.9f, 6.2f);
        ped.transform.localScale = new Vector3(0.5f, 0.9f, 0.5f);
        ped.GetComponent<Renderer>().sharedMaterial = matPed;
        ped.layer = layerHostile;

        // 7. Ego Civilian EV Sedan with Realistic Shape (Chassis, Cabin, 4 Wheels, Lights, Mirrors)
        GameObject ev = new GameObject("Ego_Civilian_EV");
        ev.transform.position = new Vector3(0f, 0f, -30.0f);
        ev.layer = layerObstacle;
        BoxCollider evCollider = ev.AddComponent<BoxCollider>();
        evCollider.center = new Vector3(0f, 0.7f, 0f);
        evCollider.size = new Vector3(1.9f, 1.3f, 4.4f);
        AttachCarVisuals(ev, matEv, matCarGlass, matCarTire, matCarRim, matHeadlight, matTaillight, false, layerObstacle);

        // Waypoint Destination Marker ahead
        GameObject target = new GameObject("EV_Waypoint_Target");
        target.transform.position = new Vector3(0f, 0.5f, 45.0f);

        // Attach EV Autonomous Controller
        EV_AutonomousController controller = ev.AddComponent<EV_AutonomousController>();
        controller.pathTarget = target.transform;
        controller.normalSpeed = 10.0f;
        controller.corridorWidth = 3.5f;
        controller.corridorLookaheadTime = 2.5f;

        // Roof-mounted Automotive LiDAR Sensor Socket & Physical Sensor Puck
        GameObject lidarSocket = new GameObject("Roof_LiDAR_Socket");
        lidarSocket.transform.parent = ev.transform;
        lidarSocket.transform.localPosition = new Vector3(0f, 1.45f, 0.5f);

        GameObject lidarPuck = CreateCylinder("LiDAR_Puck_Visual", ev.transform.position + new Vector3(0f, 1.42f, 0.5f), new Vector3(0.24f, 0.08f, 0.24f), Quaternion.identity, matCarTire, layerObstacle);
        lidarPuck.transform.parent = ev.transform;

        EV_LidarStreamer streamer = lidarSocket.AddComponent<EV_LidarStreamer>();
        streamer.targetIp = "127.0.0.1";
        streamer.targetPort = 5001;
        streamer.sensorType = 3;
        streamer.verticalChannels = 32;
        streamer.horizontalBeams = 64;
        streamer.vFovMin = -25.0f;
        streamer.vFovMax = 15.0f;

        // Sunlight
        GameObject sun = new GameObject("Directional Light");
        Light sunLight = sun.AddComponent<Light>();
        sunLight.type = LightType.Directional;
        sunLight.intensity = 1.2f;
        sunLight.color = new Color(0.95f, 0.98f, 1.0f);
        sun.transform.rotation = Quaternion.Euler(45f, -30f, 0f);

        // 7. Camera Rig with EV Camera Controller & ADAS Cockpit HUD
        GameObject camObj = new GameObject("Main Camera");
        camObj.tag = "MainCamera";
        Camera cam = camObj.AddComponent<Camera>();
        cam.fieldOfView = 60f;
        cam.nearClipPlane = 0.3f;
        cam.farClipPlane = 300f;
        camObj.AddComponent<AudioListener>();

        SIH.Civilian.EV_CameraController camCtrl = camObj.AddComponent<SIH.Civilian.EV_CameraController>();
        camCtrl.evTransform = ev.transform;
        camCtrl.evController = controller;
        camCtrl.mainCamera = cam;

        // Simulation Master Clock & Watchdog Heartbeat Broadcaster (Port 5005)
        GameObject heartbeatObj = new GameObject("[Simulation_Heartbeat_Master]");
        SimulationHeartbeat heartbeat = heartbeatObj.AddComponent<SimulationHeartbeat>();
        heartbeat.edgeNodeIp = "127.0.0.1";
        heartbeat.heartbeatPort = 5005;

        // Save Civilian Scene
        string scenePath = "Assets/Scenes/CivilianUrbanProvingGround.unity";
        EditorSceneManager.SaveScene(scene, scenePath);

        EditorBuildSettings.scenes = new EditorBuildSettingsScene[]
        {
            new EditorBuildSettingsScene("Assets/Scenes/TacticalProvingGround.unity", true),
            new EditorBuildSettingsScene("Assets/Scenes/CivilianUrbanProvingGround.unity", true)
        };

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("[SceneBuilder] BUILD COMPLETE. Civilian Urban Proving Ground saved to: " + scenePath);
    }

    [MenuItem("SIH/Build Both Proving Grounds")]
    public static void BuildBothScenes()
    {
        Debug.Log("[SceneBuilder] Building BOTH Military & Civilian Proving Grounds...");
        BuildScene();
        BuildCivilianScene();

        EditorBuildSettings.scenes = new EditorBuildSettingsScene[]
        {
            new EditorBuildSettingsScene("Assets/Scenes/TacticalProvingGround.unity", true),
            new EditorBuildSettingsScene("Assets/Scenes/CivilianUrbanProvingGround.unity", true)
        };

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("[SceneBuilder] BOTH PROVING GROUNDS COMPILED & READY FOR RUNTIME!");
    }

    [MenuItem("SIH/Run Military Sim (Play)")]
    public static void RunMilitarySim()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/TacticalProvingGround.unity");
        EditorApplication.isPlaying = true;
    }

    [MenuItem("SIH/Run Civilian Sim (Play)")]
    public static void RunCivilianSim()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/CivilianUrbanProvingGround.unity");
        EditorApplication.isPlaying = true;
    }

    [MenuItem("SIH/Build Standalone Player")]
    public static void BuildStandalonePlayer()
    {
        AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
        BuildBothScenes();
        string buildDir = "Build";
        if (!Directory.Exists(buildDir)) Directory.CreateDirectory(buildDir);

        BuildPlayerOptions opts = new BuildPlayerOptions();
        opts.scenes = new string[] {
            "Assets/Scenes/TacticalProvingGround.unity",
            "Assets/Scenes/CivilianUrbanProvingGround.unity"
        };
        opts.locationPathName = "Build/SIH_TacticalSim.exe";
        opts.target = BuildTarget.StandaloneWindows64;
        opts.options = BuildOptions.CleanBuildCache;

        var report = BuildPipeline.BuildPlayer(opts);
        Debug.Log($"[SceneBuilder] Standalone Player Build result: {report.summary.result} ({report.summary.totalSize} bytes)");
    }

    private static GameObject CreateBox(string name, Vector3 pos, Vector3 scale, Material mat, int layer)
    {
        GameObject box = GameObject.CreatePrimitive(PrimitiveType.Cube);
        box.name = name;
        box.transform.position = pos;
        box.transform.localScale = scale;
        box.GetComponent<Renderer>().sharedMaterial = mat;
        box.layer = layer;
        return box;
    }

    private static GameObject CreateCylinder(string name, Vector3 pos, Vector3 scale, Quaternion rot, Material mat, int layer)
    {
        GameObject cyl = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        cyl.name = name;
        cyl.transform.position = pos;
        cyl.transform.localScale = scale;
        cyl.transform.rotation = rot;
        cyl.GetComponent<Renderer>().sharedMaterial = mat;
        cyl.layer = layer;
        return cyl;
    }

    private static GameObject CreateVillageHouse(string name, Vector3 pos, Vector3 size, Material wallMat, Material roofMat, Material doorMat, Material winMat, int layer)
    {
        GameObject house = new GameObject(name);
        house.transform.position = pos;
        house.layer = layer;

        // 1. Base Wall Block
        GameObject walls = CreateBox("Walls", pos + new Vector3(0, size.y * 0.5f, 0), size, wallMat, layer);
        walls.transform.parent = house.transform;

        // 2. Pitched Gabled Roof
        float roofHeight = size.y * 0.45f;
        GameObject roof = CreateBox("Pitched_Roof", pos + new Vector3(0, size.y + roofHeight * 0.45f, 0), new Vector3(size.x * 1.08f, roofHeight, size.z * 1.08f), roofMat, layer);
        roof.transform.parent = house.transform;

        // 3. Brick Chimney on Roof
        GameObject chimney = CreateBox("Chimney", pos + new Vector3(size.x * 0.28f, size.y + roofHeight * 0.75f, size.z * 0.22f), new Vector3(size.x * 0.14f, roofHeight * 0.9f, size.x * 0.14f), wallMat, layer);
        chimney.transform.parent = house.transform;

        // 4. Wooden Entrance Door
        float doorW = Mathf.Clamp(size.x * 0.18f, 0.9f, 1.4f);
        float doorH = Mathf.Clamp(size.y * 0.4f, 1.8f, 2.4f);
        GameObject door = CreateBox("Door", pos + new Vector3(0, doorH * 0.5f, -size.z * 0.5f - 0.05f), new Vector3(doorW, doorH, 0.1f), doorMat, layer);
        door.transform.parent = house.transform;

        // 5. Windows
        float winW = Mathf.Clamp(size.x * 0.16f, 0.8f, 1.2f);
        float winH = Mathf.Clamp(size.y * 0.22f, 0.9f, 1.4f);
        GameObject winL = CreateBox("Window_L", pos + new Vector3(-size.x * 0.28f, size.y * 0.55f, -size.z * 0.5f - 0.05f), new Vector3(winW, winH, 0.08f), winMat, layer);
        winL.transform.parent = house.transform;

        GameObject winR = CreateBox("Window_R", pos + new Vector3(size.x * 0.28f, size.y * 0.55f, -size.z * 0.5f - 0.05f), new Vector3(winW, winH, 0.08f), winMat, layer);
        winR.transform.parent = house.transform;

        return house;
    }

    private static GameObject CreateGothicCathedral(Vector3 pos, Material stoneMat, Material roofMat, Material doorMat, Material winMat, int layer)
    {
        GameObject church = new GameObject("Gothic_Church_Complex");
        church.transform.position = pos;
        church.layer = layer;

        // 1. Central Nave (Main Hall)
        GameObject nave = CreateBox("Nave_Hall", pos + new Vector3(0, 4.5f, 0), new Vector3(14f, 9f, 24f), stoneMat, layer);
        nave.transform.parent = church.transform;

        // 2. Nave Pitched Roof
        GameObject naveRoof = CreateBox("Nave_Roof", pos + new Vector3(0, 10.5f, 0), new Vector3(14.8f, 3.5f, 24.8f), roofMat, layer);
        naveRoof.transform.parent = church.transform;

        // 3. Transept (Cross Wings - Latin Cross)
        GameObject transept = CreateBox("Transept_Wings", pos + new Vector3(0, 4.0f, 2f), new Vector3(26f, 8f, 10f), stoneMat, layer);
        transept.transform.parent = church.transform;

        GameObject transeptRoof = CreateBox("Transept_Roof", pos + new Vector3(0, 9.2f, 2f), new Vector3(26.6f, 3.2f, 10.6f), roofMat, layer);
        transeptRoof.transform.parent = church.transform;

        // 4. Tall Bell Tower
        GameObject tower = CreateBox("Bell_Tower", pos + new Vector3(0, 7.5f, -14f), new Vector3(7.5f, 15f, 7.5f), stoneMat, layer);
        tower.transform.parent = church.transform;

        GameObject towerBelfry = CreateBox("Belfry_Cap", pos + new Vector3(0, 15.5f, -14f), new Vector3(7.8f, 1.5f, 7.8f), roofMat, layer);
        towerBelfry.transform.parent = church.transform;

        // 5. Pointed Spire (Apex at Y = 18m)
        GameObject spire = CreateCylinder("Spire_18m", pos + new Vector3(0, 17f, -14f), new Vector3(1.6f, 2.5f, 1.6f), Quaternion.identity, roofMat, layer);
        spire.transform.parent = church.transform;

        // 6. Gothic Arched Entrance Portal & Stained Glass Window
        GameObject portal = CreateBox("Gothic_Portal", pos + new Vector3(0, 1.7f, -17.85f), new Vector3(2.6f, 3.4f, 0.15f), doorMat, layer);
        portal.transform.parent = church.transform;

        GameObject roseWin = CreateBox("Rose_Window", pos + new Vector3(0, 5.8f, -17.85f), new Vector3(2.4f, 2.4f, 0.1f), winMat, layer);
        roseWin.transform.parent = church.transform;

        return church;
    }

    private static void AttachCarVisuals(GameObject carRoot, Material bodyMat, Material glassMat, Material wheelMat, Material rimMat, Material headMat, Material tailMat, bool isUgv, int layer)
    {
        Vector3 cSize = isUgv ? new Vector3(0.85f, 0.35f, 1.35f) : new Vector3(1.9f, 0.65f, 4.4f);
        Vector3 gSize = isUgv ? new Vector3(0.65f, 0.28f, 0.75f) : new Vector3(1.55f, 0.55f, 2.3f);
        float wheelRadius = isUgv ? 0.16f : 0.34f;
        float wheelWidth = isUgv ? 0.10f : 0.24f;

        // 1. Lower Aerodynamic Body
        GameObject body = CreateBox("Car_Body_Chassis", carRoot.transform.position + new Vector3(0, cSize.y * 0.5f + wheelRadius * 0.5f, 0), cSize, bodyMat, layer);
        body.transform.parent = carRoot.transform;

        // 2. Cabin / Greenhouse with Windshield & Roof
        Vector3 cabinPos = carRoot.transform.position + new Vector3(0, cSize.y + gSize.y * 0.5f + wheelRadius * 0.5f, -cSize.z * 0.08f);
        GameObject cabin = CreateBox("Car_Cabin_Glass", cabinPos, gSize, glassMat, layer);
        cabin.transform.parent = carRoot.transform;

        // 3. Roof Cap
        GameObject roofCap = CreateBox("Car_Roof_Cap", cabinPos + new Vector3(0, gSize.y * 0.5f + 0.02f, 0), new Vector3(gSize.x * 0.96f, 0.05f, gSize.z * 0.96f), bodyMat, layer);
        roofCap.transform.parent = carRoot.transform;

        // 4. 4 Wheels (Tire + Rim)
        float wheelX = (cSize.x * 0.5f) + (wheelWidth * 0.3f);
        float wheelZ = cSize.z * 0.32f;
        float wheelY = wheelRadius;

        Vector3[] wheelOffsets = new Vector3[] {
            new Vector3(-wheelX, wheelY, wheelZ),  // Front Left
            new Vector3(wheelX, wheelY, wheelZ),   // Front Right
            new Vector3(-wheelX, wheelY, -wheelZ), // Rear Left
            new Vector3(wheelX, wheelY, -wheelZ)   // Rear Right
        };

        Quaternion wheelRot = Quaternion.Euler(0f, 0f, 90f);
        for (int i = 0; i < 4; i++)
        {
            Vector3 wPos = carRoot.transform.position + wheelOffsets[i];
            GameObject tire = CreateCylinder($"Wheel_{i}", wPos, new Vector3(wheelRadius * 2f, wheelWidth * 0.5f, wheelRadius * 2f), wheelRot, wheelMat, layer);
            tire.transform.parent = carRoot.transform;

            GameObject rim = CreateCylinder($"Rim_{i}", wPos + new Vector3(Mathf.Sign(wheelOffsets[i].x) * 0.02f, 0, 0), new Vector3(wheelRadius * 1.2f, wheelWidth * 0.52f, wheelRadius * 1.2f), wheelRot, rimMat, layer);
            rim.transform.parent = carRoot.transform;
        }

        // 5. Front Headlights (Dual LED)
        float lightW = cSize.x * 0.22f;
        float lightH = cSize.y * 0.22f;
        GameObject headL = CreateBox("Headlight_L", carRoot.transform.position + new Vector3(-cSize.x * 0.35f, cSize.y * 0.65f, cSize.z * 0.5f + 0.02f), new Vector3(lightW, lightH, 0.05f), headMat, layer);
        headL.transform.parent = carRoot.transform;

        GameObject headR = CreateBox("Headlight_R", carRoot.transform.position + new Vector3(cSize.x * 0.35f, cSize.y * 0.65f, cSize.z * 0.5f + 0.02f), new Vector3(lightW, lightH, 0.05f), headMat, layer);
        headR.transform.parent = carRoot.transform;

        // 6. Rear Taillights (Red Bar)
        GameObject tailBar = CreateBox("Taillight_Bar", carRoot.transform.position + new Vector3(0, cSize.y * 0.72f, -cSize.z * 0.5f - 0.02f), new Vector3(cSize.x * 0.88f, lightH * 0.8f, 0.05f), tailMat, layer);
        tailBar.transform.parent = carRoot.transform;

        // 7. Side Mirrors
        float mirW = isUgv ? 0.06f : 0.14f;
        float mirH = isUgv ? 0.04f : 0.08f;
        GameObject mirL = CreateBox("Mirror_L", cabinPos + new Vector3(-gSize.x * 0.55f - mirW * 0.5f, 0f, gSize.z * 0.35f), new Vector3(mirW, mirH, mirW * 1.2f), bodyMat, layer);
        mirL.transform.parent = carRoot.transform;

        GameObject mirR = CreateBox("Mirror_R", cabinPos + new Vector3(gSize.x * 0.55f + mirW * 0.5f, 0f, gSize.z * 0.35f), new Vector3(mirW, mirH, mirW * 1.2f), bodyMat, layer);
        mirR.transform.parent = carRoot.transform;
    }

    private static GameObject CreateDeliveryVan(string name, Vector3 pos, Material cabMat, Material boxMat, Material tireMat, Material glassMat, Material lightMat, int layer)
    {
        GameObject van = new GameObject(name);
        van.transform.position = pos;
        van.layer = layer;

        // 1. Cab Front
        GameObject cab = CreateBox("Van_Cab", pos + new Vector3(0, 1.0f, 1.6f), new Vector3(1.85f, 1.6f, 1.6f), cabMat, layer);
        cab.transform.parent = van.transform;

        // 2. Windshield
        GameObject windshield = CreateBox("Van_Windshield", pos + new Vector3(0, 1.3f, 2.3f), new Vector3(1.6f, 0.7f, 0.1f), glassMat, layer);
        windshield.transform.parent = van.transform;

        // 3. Cargo Box
        GameObject cargo = CreateBox("Van_Cargo_Box", pos + new Vector3(0, 1.45f, -0.7f), new Vector3(2.05f, 2.3f, 3.4f), boxMat, layer);
        cargo.transform.parent = van.transform;

        // 4. Wheels
        Quaternion wheelRot = Quaternion.Euler(0f, 0f, 90f);
        float wRadius = 0.38f;
        float wWidth = 0.26f;
        Vector3[] vanWheels = new Vector3[] {
            new Vector3(-0.95f, wRadius, 1.5f),
            new Vector3(0.95f, wRadius, 1.5f),
            new Vector3(-1.0f, wRadius, -1.2f),
            new Vector3(1.0f, wRadius, -1.2f)
        };
        for (int i = 0; i < 4; i++)
        {
            GameObject w = CreateCylinder($"VanWheel_{i}", pos + vanWheels[i], new Vector3(wRadius * 2f, wWidth * 0.5f, wRadius * 2f), wheelRot, tireMat, layer);
            w.transform.parent = van.transform;
        }

        // 5. Headlights
        GameObject hL = CreateBox("VanHead_L", pos + new Vector3(-0.65f, 0.7f, 2.45f), new Vector3(0.35f, 0.25f, 0.05f), lightMat, layer);
        hL.transform.parent = van.transform;
        GameObject hR = CreateBox("VanHead_R", pos + new Vector3(0.65f, 0.7f, 2.45f), new Vector3(0.35f, 0.25f, 0.05f), lightMat, layer);
        hR.transform.parent = van.transform;

        // Add BoxCollider covering entire van for raycasts
        BoxCollider bc = van.AddComponent<BoxCollider>();
        bc.center = new Vector3(0, 1.3f, 0.2f);
        bc.size = new Vector3(2.1f, 2.5f, 5.0f);

        return van;
    }

    private static void CreateRoadsWithMarkings(Material roadMat, Material curbMat, Material whitePaintMat, int roadLayer, int obsLayer)
    {
        // Central North-South Avenue (106m x 8.5m)
        CreateBox("Avenue_NorthSouth_Cobblestone", new Vector3(0f, 0.02f, 0f), new Vector3(8.5f, 0.05f, 106f), roadMat, roadLayer);
        // Central East-West Cross Street (106m x 8.5m)
        CreateBox("CrossStreet_EastWest_Cobblestone", new Vector3(0f, 0.02f, 0f), new Vector3(106f, 0.05f, 8.5f), roadMat, roadLayer);

        // Raised Sidewalk Curbs along North-South Avenue
        CreateBox("Curb_NS_Left", new Vector3(-4.45f, 0.09f, 0f), new Vector3(0.4f, 0.18f, 106f), curbMat, obsLayer);
        CreateBox("Curb_NS_Right", new Vector3(4.45f, 0.09f, 0f), new Vector3(0.4f, 0.18f, 106f), curbMat, obsLayer);

        // Raised Sidewalk Curbs along East-West Cross Street
        CreateBox("Curb_EW_North", new Vector3(0f, 0.09f, 4.45f), new Vector3(106f, 0.18f, 0.4f), curbMat, obsLayer);
        CreateBox("Curb_EW_South", new Vector3(0f, 0.09f, -4.45f), new Vector3(106f, 0.18f, 0.4f), curbMat, obsLayer);

        // Dashed White Lane Centerlines along North-South Avenue
        for (float z = -48f; z <= 48f; z += 5.5f)
        {
            if (Mathf.Abs(z) < 7f) continue; // Underpass clearance
            CreateBox($"Line_NS_{z:F0}", new Vector3(0f, 0.05f, z), new Vector3(0.22f, 0.02f, 2.8f), whitePaintMat, roadLayer);
        }

        // Dashed White Lane Centerlines along East-West Cross Street
        for (float x = -48f; x <= 48f; x += 5.5f)
        {
            if (Mathf.Abs(x) < 7f) continue;
            CreateBox($"Line_EW_{x:F0}", new Vector3(x, 0.05f, 0f), new Vector3(2.8f, 0.02f, 0.22f), whitePaintMat, roadLayer);
        }

        // Pedestrian Zebra Crosswalk Stripes (South Crossing at Z = -16m, North Crossing at Z = +16m)
        for (float x = -3.3f; x <= 3.3f; x += 1.1f)
        {
            CreateBox($"Zebra_S_{x:F1}", new Vector3(x, 0.05f, -16f), new Vector3(0.55f, 0.02f, 3.0f), whitePaintMat, roadLayer);
            CreateBox($"Zebra_N_{x:F1}", new Vector3(x, 0.05f, 16f), new Vector3(0.55f, 0.02f, 3.0f), whitePaintMat, roadLayer);
        }
    }

    private static void SetupLayers()
    {
        SerializedObject tagManager = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
        SerializedProperty layers = tagManager.FindProperty("layers");
        if (layers != null)
        {
            SetLayerName(layers, 6, "Road");
            SetLayerName(layers, 7, "Building");
            SetLayerName(layers, 8, "Hostile");
            SetLayerName(layers, 9, "Obstacle");
            tagManager.ApplyModifiedProperties();
        }
    }

    private static void SetLayerName(SerializedProperty layers, int index, string name)
    {
        if (index < layers.arraySize)
        {
            SerializedProperty element = layers.GetArrayElementAtIndex(index);
            element.stringValue = name;
        }
    }

    private static Material GetOrCreateMaterial(string name, Color color)
    {
        string dir = "Assets/Settings";
        if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
        string path = $"{dir}/{name}.mat";

        Material mat = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (mat == null)
        {
            Shader shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) shader = Shader.Find("Standard");
            mat = new Material(shader);
            mat.color = color;
            AssetDatabase.CreateAsset(mat, path);
        }
        return mat;
    }
}
#endif
