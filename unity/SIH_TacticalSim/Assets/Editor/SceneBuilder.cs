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
        Material matRoad = GetOrCreateMaterial("Mat_Road", new Color(0.12f, 0.15f, 0.18f));
        Material matBridge = GetOrCreateMaterial("Mat_Bridge", new Color(0.32f, 0.36f, 0.42f));
        Material matBuilding = GetOrCreateMaterial("Mat_Building", new Color(0.72f, 0.76f, 0.82f));
        Material matChurch = GetOrCreateMaterial("Mat_Church", new Color(0.58f, 0.63f, 0.70f));
        Material matRoof = GetOrCreateMaterial("Mat_Roof", new Color(0.22f, 0.26f, 0.32f));
        Material matWall = GetOrCreateMaterial("Mat_Wall", new Color(0.46f, 0.50f, 0.56f));
        Material matBorder = GetOrCreateMaterial("Mat_Border", new Color(0.18f, 0.20f, 0.25f));
        Material matBunker = GetOrCreateMaterial("Mat_Bunker", new Color(0.38f, 0.36f, 0.32f));
        Material matUav = GetOrCreateMaterial("Mat_UAV", new Color(0.0f, 0.94f, 1.0f));
        Material matUgv = GetOrCreateMaterial("Mat_UGV", new Color(1.0f, 0.15f, 0.22f));
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

        // Cobblestone Road Network
        // Central North-South Avenue (100m x 8m)
        GameObject roadNS = CreateBox("Avenue_NorthSouth_Cobblestone", new Vector3(0f, 0.02f, 0f), new Vector3(8.5f, 0.05f, 106f), matRoad, layerRoad);
        // Central East-West Cross Street (100m x 8m)
        GameObject roadEW = CreateBox("CrossStreet_EastWest_Cobblestone", new Vector3(0f, 0.02f, 0f), new Vector3(106f, 0.05f, 8.5f), matRoad, layerRoad);

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

        // QUADRANT 1: NORTH-EAST (Church Complex with 18m Spire + Outposts)
        GameObject church = new GameObject("Gothic_Church_Complex");
        church.layer = layerBuilding;

        GameObject nave = CreateBox("Church_Nave", new Vector3(25f, 5f, 25f), new Vector3(14f, 10f, 22f), matChurch, layerBuilding);
        nave.transform.parent = church.transform;
        GameObject naveRoof = CreateBox("Nave_Roof", new Vector3(25f, 11f, 25f), new Vector3(12f, 2.5f, 20f), matRoof, layerBuilding);
        naveRoof.transform.parent = church.transform;

        GameObject tower = CreateBox("Church_Tower", new Vector3(25f, 8f, 12f), new Vector3(6.5f, 16f, 6.5f), matChurch, layerBuilding);
        tower.transform.parent = church.transform;

        // Tall Pointed Spire (Apex at Y = 18m)
        GameObject spire = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        spire.name = "Church_Spire_18m";
        spire.transform.parent = church.transform;
        spire.transform.position = new Vector3(25f, 17f, 12f);
        spire.transform.localScale = new Vector3(1.3f, 2.5f, 1.3f);
        spire.GetComponent<Renderer>().sharedMaterial = matRoof;
        spire.layer = layerBuilding;

        CreateBox("BLD_NE_01_Parish_Annex", new Vector3(38f, 2.5f, 22f), new Vector3(9f, 5.0f, 11f), matBuilding, layerBuilding);
        CreateBox("BLD_NE_02_Priest_Cottage", new Vector3(25f, 2.25f, 40f), new Vector3(10f, 4.5f, 8f), matBuilding, layerBuilding);
        CreateBox("BLD_NE_03_Field_Headquarters", new Vector3(38f, 3.25f, 38f), new Vector3(12f, 6.5f, 10f), matBuilding, layerBuilding);
        CreateBox("BLD_NE_04_Ammo_Storage", new Vector3(44f, 3.5f, 16f), new Vector3(10f, 7.0f, 12f), matBuilding, layerBuilding);
        CreateBox("BLD_NE_05_Security_Checkpost", new Vector3(16f, 2.5f, 36f), new Vector3(8f, 5.0f, 8f), matBuilding, layerBuilding);

        // QUADRANT 2: NORTH-WEST (Urban Canyon: 4-Story High-Rise Blocks & Commercial)
        CreateBox("BLD_NW_01_4Story_BlockA", new Vector3(-26f, 7f, 26f), new Vector3(14f, 14f, 12f), matBuilding, layerBuilding);
        CreateBox("BLD_NW_02_4Story_BlockB", new Vector3(-26f, 7f, 11f), new Vector3(14f, 14f, 11f), matBuilding, layerBuilding);
        CreateBox("BLD_NW_03_Commercial_3Story", new Vector3(-14f, 5.25f, 34f), new Vector3(10f, 10.5f, 8f), matBuilding, layerBuilding);
        CreateBox("BLD_NW_04_Storehouse_2Story", new Vector3(-40f, 3.5f, 18f), new Vector3(9f, 7.0f, 13f), matBuilding, layerBuilding);
        CreateBox("BLD_NW_05_Command_Facility", new Vector3(-42f, 3.5f, 34f), new Vector3(11f, 7.0f, 12f), matBuilding, layerBuilding);
        CreateBox("BLD_NW_06_Guard_Quarters", new Vector3(-18f, 2.5f, 20f), new Vector3(8f, 5.0f, 8f), matBuilding, layerBuilding);

        // QUADRANT 3: SOUTH-WEST (Residential Houses, Cottages & Primary Occlusion Wall)
        CreateBox("BLD_SW_01_House_2Story", new Vector3(-25f, 3.5f, -25f), new Vector3(12f, 7.0f, 10f), matBuilding, layerBuilding);
        CreateBox("BLD_SW_02_Barn_1Story", new Vector3(-38f, 2.25f, -22f), new Vector3(10f, 4.5f, 8f), matBuilding, layerBuilding);
        CreateBox("BLD_SW_03_Cottage_1Story", new Vector3(-15f, 2.25f, -34f), new Vector3(8f, 4.5f, 7f), matBuilding, layerBuilding);
        CreateBox("BLD_SW_04_Supply_Depot", new Vector3(-26f, 3.0f, -42f), new Vector3(13f, 6.0f, 10f), matBuilding, layerBuilding);
        CreateBox("BLD_SW_05_Power_Substation", new Vector3(-42f, 3.5f, -38f), new Vector3(10f, 7.0f, 12f), matBuilding, layerBuilding);
        CreateBox("BLD_SW_06_Corner_Outpost", new Vector3(-38f, 3.0f, -14f), new Vector3(9f, 6.0f, 9f), matBuilding, layerBuilding);

        // Primary Stone Occlusion Wall (16m long, 2.5m tall at Z = -14m)
        CreateBox("Stone_Occlusion_Wall_Primary", new Vector3(0f, 1.25f, -14f), new Vector3(16f, 2.5f, 0.8f), matWall, layerObstacle);
        CreateBox("Stone_Wall_Flank_West", new Vector3(-18f, 1.1f, -8f), new Vector3(8f, 2.2f, 0.6f), matWall, layerObstacle);

        // QUADRANT 4: SOUTH-EAST (Market Quarter, Merchant Houses & Clutter)
        CreateBox("BLD_SE_01_Merchant_House_2Story", new Vector3(26f, 3.5f, -24f), new Vector3(11f, 7.0f, 10f), matBuilding, layerBuilding);
        CreateBox("BLD_SE_02_Market_Warehouse", new Vector3(40f, 2.25f, -18f), new Vector3(11f, 4.5f, 9f), matBuilding, layerBuilding);
        CreateBox("BLD_SE_03_Market_Stalls", new Vector3(16f, 1.5f, -32f), new Vector3(8f, 3.0f, 7f), matBuilding, layerBuilding);
        CreateBox("BLD_SE_04_Grain_Mill_Storage", new Vector3(42f, 4.0f, -34f), new Vector3(12f, 8.0f, 12f), matBuilding, layerBuilding);
        CreateBox("BLD_SE_05_Tactical_Ops_Center", new Vector3(26f, 3.25f, -40f), new Vector3(12f, 6.5f, 10f), matBuilding, layerBuilding);
        CreateBox("BLD_SE_06_Eastern_Sentry_Post", new Vector3(18f, 2.5f, -20f), new Vector3(8f, 5.0f, 8f), matBuilding, layerBuilding);
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

        // 10. UGV Tethered RC Car Actor (Elliptical Path Through Underpass & Port 5002 LiDAR)
        GameObject ugv = GameObject.CreatePrimitive(PrimitiveType.Cube);
        ugv.name = "UGV_Tethered_Car";
        ugv.transform.position = new Vector3(26f, 0.25f, 0f);
        ugv.transform.localScale = new Vector3(0.7f, 0.4f, 1.2f);
        ugv.GetComponent<Renderer>().sharedMaterial = matUgv;

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

        // 3. Concrete Underpass Structure (3.2m Clearance Ceiling at Z in [15m..30m])
        CreateBox("Underpass_Pillar_L", new Vector3(-4.2f, 1.8f, 22.5f), new Vector3(0.8f, 3.6f, 15.0f), matUnderpass, layerBuilding);
        CreateBox("Underpass_Pillar_R", new Vector3(4.2f, 1.8f, 22.5f), new Vector3(0.8f, 3.6f, 15.0f), matUnderpass, layerBuilding);
        CreateBox("Underpass_Ceiling", new Vector3(0f, 3.4f, 22.5f), new Vector3(9.2f, 0.4f, 15.0f), matUnderpass, layerBuilding);

        // 4. Parked Delivery Van at Curb (Z = +5.0m, casting radial blind occlusion cone)
        GameObject van = CreateBox("Delivery_Van_Parked", new Vector3(2.8f, 1.2f, 5.0f), new Vector3(1.8f, 2.4f, 4.8f), matVan, layerObstacle);

        // 5. Crossing Pedestrian (Steps out from behind the parked delivery van)
        GameObject ped = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        ped.name = "Pedestrian_VRU_01";
        ped.transform.position = new Vector3(4.0f, 0.9f, 6.2f);
        ped.transform.localScale = new Vector3(0.5f, 0.9f, 0.5f);
        ped.GetComponent<Renderer>().sharedMaterial = matPed;
        ped.layer = layerHostile;

        // 6. Ego Civilian EV Sedan
        GameObject ev = GameObject.CreatePrimitive(PrimitiveType.Cube);
        ev.name = "Ego_Civilian_EV";
        ev.transform.position = new Vector3(0f, 0.6f, -30.0f);
        ev.transform.localScale = new Vector3(1.9f, 1.2f, 4.4f);
        ev.GetComponent<Renderer>().sharedMaterial = matEv;

        // Waypoint Destination Marker ahead
        GameObject target = new GameObject("EV_Waypoint_Target");
        target.transform.position = new Vector3(0f, 0.5f, 45.0f);

        // Attach EV Autonomous Controller
        EV_AutonomousController controller = ev.AddComponent<EV_AutonomousController>();
        controller.pathTarget = target.transform;
        controller.normalSpeed = 10.0f;
        controller.corridorWidth = 3.5f;
        controller.corridorLookaheadTime = 2.5f;

        // Roof-mounted Automotive LiDAR Sensor Socket
        GameObject lidarSocket = new GameObject("Roof_LiDAR_Socket");
        lidarSocket.transform.parent = ev.transform;
        lidarSocket.transform.localPosition = new Vector3(0f, 1.1f, 0.5f); // 0.6 + 1.1 = 1.7m above road

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

        // Save Civilian Scene
        string scenePath = "Assets/Scenes/CivilianUrbanProvingGround.unity";
        EditorSceneManager.SaveScene(scene, scenePath);

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("[SceneBuilder] BUILD COMPLETE. Civilian Urban Proving Ground saved to: " + scenePath);
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
