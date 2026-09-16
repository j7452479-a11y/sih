// -----------------------------------------------------------------------------
// SIH26053 - MUM-T TACTICAL EDGE PERCEPTION ENGINE
// Hostile Patrol Controller (Walks across street and behind occlusion wall)
// -----------------------------------------------------------------------------

using UnityEngine;

namespace SIH.Perception
{
    public class HostilePatrol : MonoBehaviour
    {
        [Header("Patrol Parameters")]
        public float speed = 1.8f;
        public float minX = -14.0f;
        public float maxX = 14.0f;
        public float fixedZ = -12.0f;

        private bool movingRight = true;

        void Update()
        {
            float step = speed * Time.deltaTime;
            Vector3 pos = transform.position;

            if (movingRight)
            {
                pos.x += step;
                if (pos.x >= maxX)
                {
                    pos.x = maxX;
                    movingRight = false;
                }
                transform.rotation = Quaternion.Euler(0, 90, 0);
            }
            else
            {
                pos.x -= step;
                if (pos.x <= minX)
                {
                    pos.x = minX;
                    movingRight = true;
                }
                transform.rotation = Quaternion.Euler(0, -90, 0);
            }

            pos.z = fixedZ;
            transform.position = pos;
        }
    }
}
