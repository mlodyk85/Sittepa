#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "firmware-src")
m73 = root / "Marlin/src/gcode/lcd/M73.cpp"
dwin_h = root / "Marlin/src/lcd/dwin/e3v2/dwin.h"
dwin_cpp = root / "Marlin/src/lcd/dwin/e3v2/dwin.cpp"

def replace_once(path: Path, old: str, new: str):
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one match, got {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

replace_once(
    m73,
    '#include "../../sd/cardreader.h"\n',
    '#include "../../sd/cardreader.h"\n\n'
    '#if ENABLED(DWIN_CREALITY_LCD)\n'
    '  #include "../../lcd/dwin/e3v2/dwin.h"\n'
    '#endif\n'
)

replace_once(
    m73,
    '''  #if BOTH(LCD_SET_PROGRESS_MANUALLY, USE_M73_REMAINING_TIME)
    if (parser.seen('R')) ui.set_remaining_time(60 * parser.value_ulong());
  #endif
''',
    '''  #if BOTH(LCD_SET_PROGRESS_MANUALLY, USE_M73_REMAINING_TIME)
    if (parser.seen('R')) ui.set_remaining_time(60 * parser.value_ulong());
  #endif

  // Ender-3 V3 SE C13 custom extension:
  // M73 L<current layer, 1-based> T<total layers>
  #if ENABLED(DWIN_CREALITY_LCD)
    const uint16_t layer_now = parser.ushortval('L', 0),
                   layer_total = parser.ushortval('T', 0);
    if (layer_now && layer_total)
      DWIN_SetLayerInfo(layer_now, layer_total);
  #endif
'''
)

replace_once(
    dwin_h,
    'void DWIN_Show_M117(char* str);\n',
    'void DWIN_Show_M117(char* str);\n'
    'void DWIN_SetLayerInfo(const uint16_t current_layer, const uint16_t total_layers);\n'
)

layer_code = r'''
// --------------------------------------------------------------------------
// Lightweight layer counter for the C13/GD303 build.
// The slicer/helper sends: M73 L<current> T<total>
// No display asset update is needed; text is rendered by the existing DWIN UI.
// --------------------------------------------------------------------------
static uint16_t dwin_layer_current = 0;
static uint16_t dwin_layer_total = 0;

static void Draw_Print_LayerInfo()
{
#if ENABLED(DWIN_CREALITY_320_LCD)
  // Free strip between remaining-time area and the Tune/Pause/Stop buttons.
  DWIN_Draw_Rectangle(1, Color_Bg_Black, 12, 170, DWIN_WIDTH - 12, 188);

  if (!dwin_layer_current || !dwin_layer_total)
    return;

  char layer_text[24];
  snprintf(layer_text, sizeof(layer_text), "Layer %u/%u", dwin_layer_current, dwin_layer_total);
  const int16_t xpos = (DWIN_WIDTH - strlen(layer_text) * MENU_CHR_W) / 2;
  DWIN_Draw_String(false, false, font8x16, Color_White, Color_Bg_Black, xpos, 172, layer_text);
#endif
}

void DWIN_SetLayerInfo(const uint16_t current_layer, const uint16_t total_layers)
{
  dwin_layer_current = current_layer;
  dwin_layer_total = total_layers;

  if (checkkey == PrintProcess) {
    Draw_Print_LayerInfo();
    DWIN_UpdateLCD();
  }
}

'''

replace_once(
    dwin_cpp,
    'void Draw_Printing_Screen()\n{\n',
    layer_code + 'void Draw_Printing_Screen()\n{\n'
)

replace_once(
    dwin_cpp,
    '''  Draw_Print_ProgressBar();     // Show current printing progress
  Draw_Print_ProgressElapsed(); // Show current time
  Draw_Print_ProgressRemain();  // Show remaining time
}

void Goto_MainMenu()
''',
    '''  Draw_Print_ProgressBar();     // Show current printing progress
  Draw_Print_ProgressElapsed(); // Show current time
  Draw_Print_ProgressRemain();  // Show remaining time
  Draw_Print_LayerInfo();       // Show current / total layer
}

void Goto_MainMenu()
'''
)

print("Patch applied successfully.")
