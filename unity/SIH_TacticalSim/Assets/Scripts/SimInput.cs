using System;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace SIH.Common
{
    public static class SimInput
    {
        public static bool GetKeyDown(KeyCode legacyKey)
        {
#if ENABLE_INPUT_SYSTEM
            try
            {
                var kb = Keyboard.current;
                if (kb != null)
                {
                    switch (legacyKey)
                    {
                        case KeyCode.Alpha1: return kb.digit1Key.wasPressedThisFrame;
                        case KeyCode.Alpha2: return kb.digit2Key.wasPressedThisFrame;
                        case KeyCode.Alpha3: return kb.digit3Key.wasPressedThisFrame;
                        case KeyCode.Alpha4: return kb.digit4Key.wasPressedThisFrame;
                        case KeyCode.Alpha5: return kb.digit5Key.wasPressedThisFrame;
                        case KeyCode.Space: return kb.spaceKey.wasPressedThisFrame;
                        case KeyCode.Escape: return kb.escapeKey.wasPressedThisFrame;
                        case KeyCode.Tab: return kb.tabKey.wasPressedThisFrame;
                        default: break;
                    }
                    return false;
                }
            }
            catch
            {
            }
#endif

            // Fallback to legacy only if Keyboard is not available
            try
            {
                return Input.GetKeyDown(legacyKey);
            }
            catch
            {
                return false;
            }
        }
    }
}
