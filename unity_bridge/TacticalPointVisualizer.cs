// -----------------------------------------------------------------------------
// SIH26053 - MUM-T TACTICAL EDGE PERCEPTION ENGINE
// Unity C# Bridge: TacticalPointVisualizer.cs
// Visualizes real-time LiDAR point returns & scanning beams in 3D world space
// -----------------------------------------------------------------------------

using System.Collections.Generic;
using UnityEngine;

namespace SIH.Perception
{
    public class TacticalPointVisualizer : MonoBehaviour
    {
        [Header("LiDAR Streamers to Visualize")]
        public LidarJobStreamer uavStreamer;
        public LidarJobStreamer ugvStreamer;

        [Header("Visual Styling")]
        public Color uavScanColor = new Color(0f, 0.94f, 1f, 0.6f);
        public Color ugvScanColor = new Color(1f, 0.6f, 0f, 0.6f);
        public int maxParticles = 600;
        public float pointSize = 0.25f;

        private ParticleSystem particleSys;
        private ParticleSystem.Particle[] particles;

        void Awake()
        {
            SetupParticleSystem();
        }

        void SetupParticleSystem()
        {
            particleSys = gameObject.AddComponent<ParticleSystem>();
            var main = particleSys.main;
            main.loop = true;
            main.playOnAwake = false;
            main.maxParticles = maxParticles;
            main.startLifetime = 0.25f;
            main.startSpeed = 0f;
            main.startSize = pointSize;
            main.simulationSpace = ParticleSystemSimulationSpace.World;

            var emission = particleSys.emission;
            emission.enabled = false;

            var shape = particleSys.shape;
            shape.enabled = false;

            var renderer = GetComponent<ParticleSystemRenderer>();
            Shader pShader = Shader.Find("Universal Render Pipeline/Unlit") 
                          ?? Shader.Find("Universal Render Pipeline/Particles/Unlit") 
                          ?? Shader.Find("Sprites/Default") 
                          ?? Shader.Find("UI/Default");
            if (pShader != null)
            {
                renderer.material = new Material(pShader);
                renderer.material.color = Color.white;
            }

            particles = new ParticleSystem.Particle[maxParticles];
        }

        void LateUpdate()
        {
            if (particleSys == null) return;

            int count = 0;

            // Sample UAV Nadir Points
            if (uavStreamer != null)
            {
                var uavHits = uavStreamer.GetRecentHits();
                for (int i = 0; i < uavHits.Count && count < maxParticles; i++)
                {
                    particles[count].position = uavHits[i];
                    particles[count].startColor = uavScanColor;
                    particles[count].startSize = pointSize;
                    particles[count].remainingLifetime = 0.2f;
                    count++;
                }
            }

            // Sample UGV Points
            if (ugvStreamer != null)
            {
                var ugvHits = ugvStreamer.GetRecentHits();
                for (int i = 0; i < ugvHits.Count && count < maxParticles; i++)
                {
                    particles[count].position = ugvHits[i];
                    particles[count].startColor = ugvScanColor;
                    particles[count].startSize = pointSize * 0.8f;
                    particles[count].remainingLifetime = 0.2f;
                    count++;
                }
            }

            particleSys.SetParticles(particles, count);
        }
    }
}
