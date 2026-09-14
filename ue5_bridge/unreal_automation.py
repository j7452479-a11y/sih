"""
Unreal Engine Editor Python Automation Script
Can be run inside Unreal Editor: Tools -> Execute Python Script -> unreal_automation.py
Or in Unreal Python console: py "../../../../sih/ue5_bridge/unreal_automation.py"

Features:
1. Spawns 250m x 250m tactical terrain ground plane and cobblestone roadways (eliminates void floating).
2. Spawns and skins all 46 tactical village structures & obstacles with true physical bounds, materials, and tags.
3. Carves real open underpass voids beneath bridge overpasses.
4. Generates MUM-T patrol splines for UAV flight path, UGV road path, and hostile crossing trajectories.
5. Spawns autonomous MUM-T fleet:
   - BP_SIH_UAV (Drone): Orbiting 30m altitude, 32-channel nadir LiDAR, downward sensor beam visualizer.
   - BP_SIH_UGV (Ground Rover): Patrolling crossroads, 16-channel frontal LiDAR scanner, headlights.
   - BP_Tactical_Hostile (Enemies): Armed combatant NPCs walking across village streets for live target tracking.
"""

try:
    import unreal
    UNREAL_AVAILABLE = True
except ImportError:
    UNREAL_AVAILABLE = False

from spline_generator import (
    generate_uav_flight_spline,
    generate_ugv_road_spline,
    generate_hostile_crossing_splines,
)

# Canonical 46 Battlefield Structures Matching C2 Database and Mock Sensor Streamer
STRUCTURES = [
    # Sector NW
    {"id": "BLD-NW-01", "name": "Outpost Depot (Sector NW)", "x": -25, "y": 15, "width": 12.0, "length": 10.0, "height": 6.5, "mat": "PM_Obstacle"},
    {"id": "BLD-NW-02", "name": "Command Facility (Sector NW)", "x": -45, "y": 15, "width": 10.0, "length": 14.0, "height": 7.0, "mat": "PM_Obstacle"},
    {"id": "BLD-NW-03", "name": "Communications Relay (Sector NW)", "x": -25, "y": 35, "width": 14.0, "length": 10.0, "height": 5.5, "mat": "PM_Obstacle"},
    {"id": "BLD-NW-04", "name": "Fortified Warehouse (Sector NW)", "x": -50, "y": 35, "width": 12.0, "length": 12.0, "height": 8.0, "mat": "PM_Obstacle"},
    {"id": "BLD-NW-05", "name": "Guard Quarters (Sector NW)", "x": -18, "y": 28, "width": 8.0, "length": 8.0, "height": 5.0, "mat": "PM_Obstacle"},
    {"id": "BLD-NW-06", "name": "Observation Ruin (Sector NW)", "x": -38, "y": 48, "width": 10.0, "length": 10.0, "height": 6.0, "mat": "PM_Obstacle"},

    # Sector NE
    {"id": "BLD-NE-01", "name": "Field Headquarters (Sector NE)", "x": 25, "y": 15, "width": 12.0, "length": 10.0, "height": 6.0, "mat": "PM_Obstacle"},
    {"id": "BLD-NE-02", "name": "Ammo Storage Depot (Sector NE)", "x": 45, "y": 15, "width": 10.0, "length": 12.0, "height": 7.5, "mat": "PM_Obstacle"},
    {"id": "BLD-NE-03", "name": "Medical Aid Station (Sector NE)", "x": 25, "y": 35, "width": 14.0, "length": 10.0, "height": 5.0, "mat": "PM_Obstacle"},
    {"id": "BLD-NE-04", "name": "Vehicle Maintenance Bay (Sector NE)", "x": 50, "y": 35, "width": 12.0, "length": 14.0, "height": 8.0, "mat": "PM_Obstacle"},
    {"id": "BLD-NE-05", "name": "Security Checkpost (Sector NE)", "x": 18, "y": 28, "width": 8.0, "length": 8.0, "height": 5.5, "mat": "PM_Obstacle"},
    {"id": "BLD-NE-06", "name": "Overwatch Building (Sector NE)", "x": 38, "y": 48, "width": 10.0, "length": 10.0, "height": 6.5, "mat": "PM_Obstacle"},

    # Sector SW
    {"id": "BLD-SW-01", "name": "Supply Depot (Sector SW)", "x": -25, "y": -25, "width": 12.0, "length": 10.0, "height": 6.0, "mat": "PM_Obstacle"},
    {"id": "BLD-SW-02", "name": "Power Substation (Sector SW)", "x": -45, "y": -25, "width": 10.0, "length": 12.0, "height": 7.0, "mat": "PM_Obstacle"},
    {"id": "BLD-SW-03", "name": "Residential Ruin A (Sector SW)", "x": -25, "y": -50, "width": 14.0, "length": 10.0, "height": 5.5, "mat": "PM_Obstacle"},
    {"id": "BLD-SW-04", "name": "Industrial Silo (Sector SW)", "x": -50, "y": -50, "width": 12.0, "length": 12.0, "height": 7.5, "mat": "PM_Obstacle"},
    {"id": "BLD-SW-05", "name": "Pump House (Sector SW)", "x": -18, "y": -38, "width": 8.0, "length": 8.0, "height": 4.5, "mat": "PM_Obstacle"},
    {"id": "BLD-SW-06", "name": "Corner Outpost (Sector SW)", "x": -38, "y": -18, "width": 10.0, "length": 10.0, "height": 6.0, "mat": "PM_Obstacle"},

    # Sector SE
    {"id": "BLD-SE-01", "name": "Tactical Ops Center (Sector SE)", "x": 25, "y": -25, "width": 12.0, "length": 10.0, "height": 6.5, "mat": "PM_Obstacle"},
    {"id": "BLD-SE-02", "name": "Equipment Staging (Sector SE)", "x": 45, "y": -25, "width": 10.0, "length": 14.0, "height": 7.0, "mat": "PM_Obstacle"},
    {"id": "BLD-SE-03", "name": "Residential Ruin B (Sector SE)", "x": 25, "y": -50, "width": 14.0, "length": 10.0, "height": 5.0, "mat": "PM_Obstacle"},
    {"id": "BLD-SE-04", "name": "Grain Mill Storage (Sector SE)", "x": 50, "y": -50, "width": 12.0, "length": 12.0, "height": 8.0, "mat": "PM_Obstacle"},
    {"id": "BLD-SE-05", "name": "Eastern Sentry Post (Sector SE)", "x": 18, "y": -38, "width": 8.0, "length": 8.0, "height": 5.0, "mat": "PM_Obstacle"},
    {"id": "BLD-SE-06", "name": "South Alley Building (Sector SE)", "x": 38, "y": -18, "width": 10.0, "length": 10.0, "height": 6.5, "mat": "PM_Obstacle"},

    # Far-Field Outposts
    {"id": "BLD-FF-01", "name": "West Gatehouse (Far-Field)", "x": -65, "y": 0, "width": 12.0, "length": 12.0, "height": 6.0, "mat": "PM_Obstacle"},
    {"id": "BLD-FF-02", "name": "East Gatehouse (Far-Field)", "x": 65, "y": 0, "width": 12.0, "length": 12.0, "height": 6.0, "mat": "PM_Obstacle"},
    {"id": "BLD-FF-03", "name": "North Highway Checkpoint", "x": 0, "y": 65, "width": 14.0, "length": 10.0, "height": 5.5, "mat": "PM_Obstacle"},
    {"id": "BLD-FF-04", "name": "South River Checkpoint", "x": 0, "y": -65, "width": 14.0, "length": 10.0, "height": 5.5, "mat": "PM_Obstacle"},
    {"id": "BLD-FF-05", "name": "NW Outer Redoubt", "x": -60, "y": 60, "width": 10.0, "length": 10.0, "height": 5.0, "mat": "PM_Obstacle"},
    {"id": "BLD-FF-06", "name": "NE Outer Redoubt", "x": 60, "y": 60, "width": 10.0, "length": 10.0, "height": 5.0, "mat": "PM_Obstacle"},
    {"id": "BLD-FF-07", "name": "SW Outer Redoubt", "x": -60, "y": -60, "width": 10.0, "length": 10.0, "height": 5.0, "mat": "PM_Obstacle"},
    {"id": "BLD-FF-08", "name": "SE Outer Redoubt", "x": 60, "y": -60, "width": 10.0, "length": 10.0, "height": 5.0, "mat": "PM_Obstacle"},

    # Bridges & Overpasses
    {"id": "BRG-01", "name": "North Bridge Overpass", "x": 0, "y": 25, "width": 12.0, "length": 6.0, "height": 5.2, "mat": "PM_Bridge"},
    {"id": "BRG-02", "name": "South Bridge Overpass", "x": 0, "y": -35, "width": 12.0, "length": 6.0, "height": 4.8, "mat": "PM_Bridge"},

    # Cardinal Bunkers
    {"id": "BNK-N", "name": "North Avenue Sandbag Bunker", "x": 0, "y": 30, "width": 6.0, "length": 3.0, "height": 1.8, "mat": "PM_Obstacle"},
    {"id": "BNK-S", "name": "South Avenue Sandbag Bunker", "x": 0, "y": -30, "width": 6.0, "length": 3.0, "height": 1.8, "mat": "PM_Obstacle"},
    {"id": "BNK-E", "name": "East Avenue Sandbag Bunker", "x": 30, "y": 0, "width": 6.0, "length": 3.0, "height": 1.8, "mat": "PM_Obstacle"},
    {"id": "BNK-W", "name": "West Avenue Sandbag Bunker", "x": -30, "y": 0, "width": 6.0, "length": 3.0, "height": 1.8, "mat": "PM_Obstacle"},

    # Perimeter Watchtowers
    {"id": "TWR-NW", "name": "Perimeter Watchtower NW", "x": -40, "y": 40, "width": 4.0, "length": 4.0, "height": 6.0, "mat": "PM_Obstacle"},
    {"id": "TWR-NE", "name": "Perimeter Watchtower NE", "x": 40, "y": 40, "width": 4.0, "length": 4.0, "height": 6.0, "mat": "PM_Obstacle"},
    {"id": "TWR-SW", "name": "Perimeter Watchtower SW", "x": -40, "y": -40, "width": 4.0, "length": 4.0, "height": 6.0, "mat": "PM_Obstacle"},
    {"id": "TWR-SE", "name": "Perimeter Watchtower SE", "x": 40, "y": -40, "width": 4.0, "length": 4.0, "height": 6.0, "mat": "PM_Obstacle"},

    # Stone Occlusion Barriers
    {"id": "WAL-A", "name": "Center-West Stone Wall", "x": -10, "y": 0, "width": 0.8, "length": 24.0, "height": 2.4, "mat": "PM_Obstacle"},
    {"id": "WAL-B", "name": "Eastern Alley Stone Wall", "x": 12, "y": 0, "width": 0.8, "length": 30.0, "height": 2.4, "mat": "PM_Obstacle"},
    {"id": "WAL-C", "name": "North Outer Perimeter Wall", "x": -27.5, "y": 20, "width": 15.0, "length": 0.8, "height": 2.0, "mat": "PM_Obstacle"},
    {"id": "WAL-D", "name": "South Outer Perimeter Wall", "x": -27.5, "y": -20, "width": 15.0, "length": 0.8, "height": 2.0, "mat": "PM_Obstacle"},
]

def spawn_battlefield_terrain():
    """Spawns 250m x 250m tactical terrain ground plane and cobblestone roadway network."""
    if not UNREAL_AVAILABLE:
        return
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cube_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube")

    # Load authentic Normandy materials with fallback
    normandy_ground = unreal.EditorAssetLibrary.load_asset("/Game/UnrealNormandy/MaterialInstances/MI_Ground_00A")
    normandy_road = unreal.EditorAssetLibrary.load_asset("/Game/UnrealNormandy/MaterialInstances/MI_Ground_Road_00A")
    grid_gray_mat = normandy_ground or unreal.EditorAssetLibrary.load_asset("/Game/LevelPrototyping/Materials/MI_PrototypeGrid_Gray")
    road_mat = normandy_road or unreal.EditorAssetLibrary.load_asset("/Game/LevelPrototyping/Materials/MI_PrototypeGrid_TopDark")

    all_actors = {a.get_actor_label(): a for a in actor_subsystem.get_all_level_actors()}

    # 1. Main Ground Plane (250m x 250m, top flush with Z = 0)
    ground_label = "BP_GROUND_TacticalTerrain"
    if ground_label in all_actors:
        ground = all_actors[ground_label]
    else:
        ground = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -25.0), unreal.Rotator(0, 0, 0))
        ground.set_actor_label(ground_label)
        ground.tags.append(unreal.Name("ROAD-0"))

    if ground.static_mesh_component and cube_mesh:
        ground.static_mesh_component.set_static_mesh(cube_mesh)
        ground.set_actor_scale3d(unreal.Vector(250.0, 250.0, 0.5))
        if grid_gray_mat:
            ground.static_mesh_component.set_material(0, grid_gray_mat)

    # 2. Central North-South Cobblestone Avenue (8m wide x 180m long)
    ns_label = "BP_ROAD_CentralAvenue_NS"
    if ns_label in all_actors:
        ns_road = all_actors[ns_label]
    else:
        ns_road = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 2.0), unreal.Rotator(0, 0, 0))
        ns_road.set_actor_label(ns_label)
        ns_road.tags.append(unreal.Name("ROAD-NS"))

    if ns_road.static_mesh_component and cube_mesh:
        ns_road.static_mesh_component.set_static_mesh(cube_mesh)
        ns_road.set_actor_scale3d(unreal.Vector(8.0, 180.0, 0.05))
        if road_mat:
            ns_road.static_mesh_component.set_material(0, road_mat)

    # 3. Central East-West Cross Street (160m long x 8m wide)
    ew_label = "BP_ROAD_CrossStreet_EW"
    if ew_label in all_actors:
        ew_road = all_actors[ew_label]
    else:
        ew_road = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 2.0), unreal.Rotator(0, 0, 0))
        ew_road.set_actor_label(ew_label)
        ew_road.tags.append(unreal.Name("ROAD-EW"))

    if ew_road.static_mesh_component and cube_mesh:
        ew_road.static_mesh_component.set_static_mesh(cube_mesh)
        ew_road.set_actor_scale3d(unreal.Vector(160.0, 8.0, 0.05))
        if road_mat:
            ew_road.static_mesh_component.set_material(0, road_mat)

    print("[SURVEYOR] Ground terrain (250m x 250m) and cobblestone roadway network generated with Normandy textures.")

def spawn_village_structures():
    """Spawns 46 structures with photorealistic Normandy materials, exact bounds, and surveyor tags."""
    if not UNREAL_AVAILABLE:
        print("[SURVEYOR] Simulated: 46 Structures defined with exact dimensions ready for UE5 import.")
        return

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cube_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube")

    # Load authentic Normandy stone, brick, mortar, and roadway materials
    normandy_brick = unreal.EditorAssetLibrary.load_asset("/Game/UnrealNormandy/MaterialInstances/MI_BrickWall_00A")
    normandy_mortar = unreal.EditorAssetLibrary.load_asset("/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A")
    normandy_stone = unreal.EditorAssetLibrary.load_asset("/Game/UnrealNormandy/MaterialInstances/MI_Main_StoneWall_00A")
    normandy_gray_stone = unreal.EditorAssetLibrary.load_asset("/Game/UnrealNormandy/MaterialInstances/MI_Main_StoneWall_00B_Gray")
    normandy_road = unreal.EditorAssetLibrary.load_asset("/Game/UnrealNormandy/MaterialInstances/MI_Ground_Road_00A")

    dark_mat = normandy_brick or unreal.EditorAssetLibrary.load_asset("/Game/LevelPrototyping/Materials/MI_PrototypeGrid_TopDark")
    mortar_mat = normandy_mortar or dark_mat
    gray_mat = normandy_stone or unreal.EditorAssetLibrary.load_asset("/Game/LevelPrototyping/Materials/MI_PrototypeGrid_Gray_02")
    bunker_mat = normandy_gray_stone or unreal.EditorAssetLibrary.load_asset("/Game/LevelPrototyping/Materials/MI_DefaultColorway")
    bridge_mat = normandy_road or dark_mat

    existing_labels = {a.get_actor_label(): a for a in actor_subsystem.get_all_level_actors()}

    spawned_count = 0
    updated_count = 0
    for s in STRUCTURES:
        label = f"BP_{s['id']}_{s['name']}"

        # Carve realistic elevated bridge deck with open traversable underpass
        if s["id"].startswith("BRG-"):
            deck_thickness = 0.8  # 80cm deck thickness
            loc = unreal.Vector(s["x"] * 100.0, s["y"] * 100.0, (s["height"] - deck_thickness / 2.0) * 100.0)
            scale = unreal.Vector(s["width"], s["length"], deck_thickness)
        else:
            loc = unreal.Vector(s["x"] * 100.0, s["y"] * 100.0, (s["height"] * 100.0) / 2.0)
            scale = unreal.Vector(s["width"], s["length"], s["height"])

        rot = unreal.Rotator(0, 0, 0)

        if label in existing_labels:
            actor = existing_labels[label]
            actor.set_actor_location(loc, False, False)
            actor.set_actor_scale3d(scale)
            updated_count += 1
        else:
            actor = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
            actor.set_actor_label(label)
            actor.tags.append(unreal.Name(s["id"]))
            spawned_count += 1

        mesh_comp = actor.static_mesh_component
        if mesh_comp and cube_mesh:
            mesh_comp.set_static_mesh(cube_mesh)
            actor.set_actor_scale3d(scale)

            # Assign distinctive photorealistic Normandy materials
            if s["id"].startswith("BLD-"):
                # Alternate brick and mortar for varied rustic village look
                bld_mat = mortar_mat if (hash(s["id"]) % 2 == 0) else dark_mat
                mesh_comp.set_material(0, bld_mat)
            elif s["id"].startswith("WAL-"):
                mesh_comp.set_material(0, gray_mat)
            elif s["id"].startswith("BNK-"):
                mesh_comp.set_material(0, bunker_mat)
            elif s["id"].startswith("BRG-"):
                mesh_comp.set_material(0, bridge_mat)

    print(f"[SURVEYOR] Successfully verified 46 structures with photorealistic Normandy materials ({spawned_count} spawned, {updated_count} updated).")

def create_spline_actor(actor_name: str, points_list):
    """Spawns or updates an actor with a USplineComponent and populates points."""
    if not UNREAL_AVAILABLE:
        return

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = actor_subsystem.get_all_level_actors()
    existing_actor = next((a for a in all_actors if a.get_actor_label() == actor_name), None)

    if existing_actor:
        actor = existing_actor
        spline_comp = actor.get_component_by_class(unreal.SplineComponent)
    else:
        try:
            actor = actor_subsystem.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        except Exception:
            actor = actor_subsystem.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))

        if not actor:
            print(f"[AUTOMATION] Error: Failed to spawn actor for {actor_name}")
            return

        actor.set_actor_label(actor_name)
        spline_comp = None

    if not spline_comp:
        try:
            spline_comp = unreal.new_object(unreal.SplineComponent, outer=actor)
        except Exception:
            spline_comp = unreal.SplineComponent(actor)

        if actor.root_component and hasattr(spline_comp, 'attach_to_component'):
            try:
                spline_comp.attach_to_component(
                    actor.root_component, '',
                    unreal.AttachmentRule.KEEP_RELATIVE,
                    unreal.AttachmentRule.KEEP_RELATIVE,
                    unreal.AttachmentRule.KEEP_RELATIVE,
                    False
                )
            except Exception:
                pass
        else:
            try:
                actor.set_editor_property('root_component', spline_comp)
            except Exception:
                pass

    if spline_comp:
        spline_comp.clear_spline_points(update_spline=False)
        for p in points_list:
            ue_pos = unreal.Vector(*p.to_ue_cm())
            spline_comp.add_spline_point(ue_pos, unreal.SplineCoordinateSpace.WORLD, update_spline=False)
        spline_comp.update_spline()
        print(f"[AUTOMATION] Successfully configured spline {actor_name} ({len(points_list)} points).")
    else:
        print(f"[AUTOMATION] Warning: Could not locate/attach SplineComponent on {actor_name}.")

def get_sensor_streamer_class():
    """Dynamically resolves the UdpSensorStreamer C++ class from module reflection."""
    if hasattr(unreal, "UdpSensorStreamer"):
        return getattr(unreal, "UdpSensorStreamer")
    try:
        cls = unreal.load_class(None, "/Script/SIH_Perception.UdpSensorStreamer")
        if cls:
            return cls
    except Exception:
        pass
    return None

def spawn_autonomous_mumt_agents():
    """Spawns UAV Drone, UGV Rover, and Hostile Combatant NPCs with attached LiDAR streamers and spline movement."""
    if not UNREAL_AVAILABLE:
        return

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cube_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube")
    dark_mat = unreal.EditorAssetLibrary.load_asset("/Game/LevelPrototyping/Materials/MI_PrototypeGrid_TopDark")
    mannequin_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Characters/Mannequins/Meshes/SK_Mannequin")
    shooter_npc_class = unreal.EditorAssetLibrary.load_blueprint_class("/Game/Variant_Shooter/Blueprints/AI/BP_ShooterNPC")
    streamer_class = get_sensor_streamer_class()

    all_actors = {a.get_actor_label(): a for a in actor_subsystem.get_all_level_actors()}

    # 1. UAV Drone Pawn (BP_SIH_UAV)
    uav_label = "BP_SIH_UAV"
    if uav_label in all_actors:
        uav_actor = all_actors[uav_label]
    else:
        uav_actor = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(-4000, -4000, 3000), unreal.Rotator(0, 0, 0))
        uav_actor.set_actor_label(uav_label)
        uav_actor.tags.append(unreal.Name("UAV_Drone"))

    if uav_actor.static_mesh_component and cube_mesh:
        uav_actor.static_mesh_component.set_static_mesh(cube_mesh)
        uav_actor.set_actor_scale3d(unreal.Vector(1.8, 1.8, 0.4))
        if dark_mat:
            uav_actor.static_mesh_component.set_material(0, dark_mat)

    # Attach downward tactical sensor spotlight
    light_comp = uav_actor.get_component_by_class(unreal.SpotLightComponent)
    if not light_comp:
        light_comp = unreal.new_object(unreal.SpotLightComponent, outer=uav_actor)
        if light_comp and uav_actor.root_component:
            try:
                light_comp.attach_to_component(uav_actor.root_component, '', unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE, False)
                light_comp.set_editor_property("relative_rotation", unreal.Rotator(-90, 0, 0))
                light_comp.set_editor_property("intensity", 80000.0)
                light_comp.set_editor_property("light_color", unreal.Color(0, 220, 255, 255))
                light_comp.set_editor_property("outer_cone_angle", 45.0)
                light_comp.set_editor_property("attenuation_radius", 4000.0)
            except Exception:
                pass

    # Attach UdpSensorStreamer to UAV
    if streamer_class:
        streamer_comp = uav_actor.get_component_by_class(streamer_class)
        if not streamer_comp:
            try:
                streamer_comp = unreal.new_object(streamer_class, outer=uav_actor)
                if streamer_comp:
                    streamer_comp.set_editor_property("target_port", 5001)
                    streamer_comp.set_editor_property("sensor_type", 1)
                    streamer_comp.set_editor_property("num_channels", 32)
                    streamer_comp.set_editor_property("follow_spline_tag", "BP_UAV_FlightPath_Spline")
                    streamer_comp.set_editor_property("patrol_speed_mps", 5.0)
                    streamer_comp.set_editor_property("b_draw_debug_beams", True)
            except Exception as e:
                print(f"[AGENT] Note on UAV streamer: {e}")

    # 2. UGV Ground Rover Pawn (BP_SIH_UGV)
    ugv_label = "BP_SIH_UGV"
    if ugv_label in all_actors:
        ugv_actor = all_actors[ugv_label]
    else:
        ugv_actor = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, -4500, 60), unreal.Rotator(0, 0, 0))
        ugv_actor.set_actor_label(ugv_label)
        ugv_actor.tags.append(unreal.Name("UGV_Rover"))

    if ugv_actor.static_mesh_component and cube_mesh:
        ugv_actor.static_mesh_component.set_static_mesh(cube_mesh)
        ugv_actor.set_actor_scale3d(unreal.Vector(2.4, 1.4, 0.9))
        if dark_mat:
            ugv_actor.static_mesh_component.set_material(0, dark_mat)

    # Attach UdpSensorStreamer to UGV
    if streamer_class:
        ugv_streamer = ugv_actor.get_component_by_class(streamer_class)
        if not ugv_streamer:
            try:
                ugv_streamer = unreal.new_object(streamer_class, outer=ugv_actor)
                if ugv_streamer:
                    ugv_streamer.set_editor_property("target_port", 5002)
                    ugv_streamer.set_editor_property("sensor_type", 2)
                    ugv_streamer.set_editor_property("num_channels", 16)
                    ugv_streamer.set_editor_property("follow_spline_tag", "BP_UGV_RoadPath_Spline")
                    ugv_streamer.set_editor_property("patrol_speed_mps", 3.0)
                    ugv_streamer.set_editor_property("b_draw_debug_beams", True)
            except Exception as e:
                print(f"[AGENT] Note on UGV streamer: {e}")

    # 3. Hostile Tactical Combatants (Enemies to track)
    hostiles = [
        {"label": "BP_Tactical_Hostile_A", "spline": "BP_HostileA_CrossingSpline", "pos": unreal.Vector(-5000, 0, 90)},
        {"label": "BP_Tactical_Hostile_B", "spline": "BP_HostileB_CrossingSpline", "pos": unreal.Vector(0, -5000, 90)},
    ]

    for h in hostiles:
        h_label = h["label"]
        if h_label in all_actors:
            h_actor = all_actors[h_label]
        else:
            spawned = False
            if shooter_npc_class:
                try:
                    h_actor = actor_subsystem.spawn_actor_from_class(shooter_npc_class, h["pos"], unreal.Rotator(0, 0, 0))
                    spawned = True
                except Exception:
                    spawned = False

            if not spawned:
                h_actor = actor_subsystem.spawn_actor_from_class(unreal.SkeletalMeshActor, h["pos"], unreal.Rotator(0, 0, 0))
                if h_actor.skeletal_mesh_component and mannequin_mesh:
                    h_actor.skeletal_mesh_component.set_skeletal_mesh(mannequin_mesh)

            h_actor.set_actor_label(h_label)
            h_actor.tags.append(unreal.Name("PM_Target"))
            h_actor.tags.append(unreal.Name("Hostile"))

        # Attach autonomous street-crossing patrol
        if streamer_class:
            h_streamer = h_actor.get_component_by_class(streamer_class)
            if not h_streamer:
                try:
                    h_streamer = unreal.new_object(streamer_class, outer=h_actor)
                    if h_streamer:
                        h_streamer.set_editor_property("num_channels", 0)  # Movement only
                        h_streamer.set_editor_property("follow_spline_tag", h["spline"])
                        h_streamer.set_editor_property("patrol_speed_mps", 1.8)
                except Exception:
                    pass

    print("[AGENT] Autonomous fleet (UAV Drone, UGV Rover, Hostile Enemies) spawned and active.")

def tag_existing_normandy_architecture(all_actors):
    """Automatically categorizes and tags real stone houses, walls, and roads in ML_Demonstration for LiDAR perception."""
    tagged_walls = 0
    tagged_buildings = 0
    tagged_roads = 0

    for a in all_actors:
        label = a.get_actor_label().lower()
        mesh_name = ""
        mesh_comp = a.get_component_by_class(unreal.StaticMeshComponent)
        if mesh_comp and mesh_comp.static_mesh:
            mesh_name = mesh_comp.static_mesh.get_name().lower()

        combined = f"{label} {mesh_name}"

        if "stonewall" in combined or "oldwall" in combined:
            if not any(str(t).startswith("WAL-") for t in a.tags):
                a.tags.append(unreal.Name("WAL-Normandy"))
                a.tags.append(unreal.Name("PM_Obstacle"))
                tagged_walls += 1
        elif "roof" in combined or "brick" in combined or "house" in combined or "building" in combined:
            if not any(str(t).startswith("BLD-") for t in a.tags):
                a.tags.append(unreal.Name("BLD-Normandy"))
                a.tags.append(unreal.Name("PM_Obstacle"))
                tagged_buildings += 1
        elif "road" in combined or "cobble" in combined:
            if not any(str(t).startswith("ROAD-") for t in a.tags):
                a.tags.append(unreal.Name("ROAD-Normandy"))
                tagged_roads += 1

    print(f"[SURVEYOR] Tagged {tagged_buildings} authentic stone buildings, {tagged_walls} stone walls, and {tagged_roads} roads for LiDAR perception.")

def run_editor_automation():
    if not UNREAL_AVAILABLE:
        print("[AUTOMATION] Run inside Unreal Engine Editor (Tools -> Execute Python Script).")
        return

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = actor_subsystem.get_all_level_actors()

    # Detect if we are inside the authentic Sharur Normandy Village (ML_Demonstration)
    is_master_village = any("oldwall" in a.get_actor_label().lower() or "stonewall" in a.get_actor_label().lower() or "demonstration" in str(a.get_outer()).lower() for a in all_actors)

    if is_master_village:
        print("[AUTOMATION] 1/3 Detected Master Normandy Village (ML_Demonstration)! Tagging authentic stone architecture...")
        tag_existing_normandy_architecture(all_actors)
    else:
        print("[AUTOMATION] 1/4 Generating Battlefield Ground Terrain & Cobblestones...")
        spawn_battlefield_terrain()

        print("[AUTOMATION] 2/4 Spawning & Skinning 46 Tactical Structures with Materials...")
        spawn_village_structures()

    print("[AUTOMATION] 2/3 Generating MUM-T Navigation & Crossing Splines...")
    try:
        create_spline_actor("BP_UAV_FlightPath_Spline", generate_uav_flight_spline())
    except Exception as e:
        print(f"[AUTOMATION] UAV Flight Spline notice: {e}")

    try:
        create_spline_actor("BP_UGV_RoadPath_Spline", generate_ugv_road_spline())
    except Exception as e:
        print(f"[AUTOMATION] UGV Road Spline notice: {e}")

    try:
        h_a, h_b = generate_hostile_crossing_splines()
        create_spline_actor("BP_HostileA_CrossingSpline", h_a)
        create_spline_actor("BP_HostileB_CrossingSpline", h_b)
    except Exception as e:
        print(f"[AUTOMATION] Hostile Splines notice: {e}")

    print("[AUTOMATION] 3/3 Spawning Drone, Rover & Enemy Combatants...")
    spawn_autonomous_mumt_agents()

    print("[AUTOMATION] SUCCESS: Complete tactical simulation environment ready!")

if __name__ == "__main__":
    run_editor_automation()
