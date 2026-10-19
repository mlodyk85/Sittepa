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

# M73 -> DWIN layer telemetry
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

# Safe globals. No new processID states are introduced.
replace_once(
    dwin_cpp,
    '''static millis_t pause_transition_guard_ms = 0;

constexpr float default_max_feedrate[] = DEFAULT_MAX_FEEDRATE;
''',
    '''static millis_t pause_transition_guard_ms = 0;

// Custom layer telemetry + one-shot scheduled layer pause.
// Pause target 0 = OFF. Editing reuses the existing PrintSpeed editor state,
// avoiding any new DWIN processID / screen-state values.
static uint16_t dwin_layer_current = 0;
static uint16_t dwin_layer_total = 0;
static uint16_t dwin_pause_layer = 0;
static bool dwin_pause_layer_edit = false;

constexpr float default_max_feedrate[] = DEFAULT_MAX_FEEDRATE;
'''
)

# Add one item to Tune.
replace_once(
    dwin_cpp,
    '''#define TUNE_CASE_ZOFF (TUNE_CASE_FAN + ENABLED(HAS_ZOFFSET_ITEM))
#define TUNE_CASE_TOTAL TUNE_CASE_ZOFF
''',
    '''#define TUNE_CASE_ZOFF (TUNE_CASE_FAN + ENABLED(HAS_ZOFFSET_ITEM))
#define TUNE_CASE_LAYER_PAUSE (TUNE_CASE_ZOFF + 1)
#define TUNE_CASE_TOTAL TUNE_CASE_LAYER_PAUSE
'''
)

replace_once(
    dwin_cpp,
    '''void Item_Tune_Zoffset(const uint8_t row)
{
#if ENABLED(DWIN_CREALITY_320_LCD)
#if HAS_ZOFFSET_ITEM
    DWIN_ICON_Show(HMI_flag.language, LANGUAGE_Zoffset, 42, MBASE(row) + JPN_OFFSET);
#endif
#endif  
  if (HMI_flag.language < Language_Max)
  {
    Draw_Menu_Icon(row, ICON_Zoffset);
    Draw_Menu_Line(row, ICON_Zoffset);
    DWIN_Draw_Signed_Float(font8x16, Color_Bg_Black, 2, 2, VALUERANGE_X - 14, MBASE(row), BABY_Z_VAR * 100);
  }
}



void Draw_Tune_Menu()
''',
    '''void Item_Tune_Zoffset(const uint8_t row)
{
#if ENABLED(DWIN_CREALITY_320_LCD)
#if HAS_ZOFFSET_ITEM
    DWIN_ICON_Show(HMI_flag.language, LANGUAGE_Zoffset, 42, MBASE(row) + JPN_OFFSET);
#endif
#endif  
  if (HMI_flag.language < Language_Max)
  {
    Draw_Menu_Icon(row, ICON_Zoffset);
    Draw_Menu_Line(row, ICON_Zoffset);
    DWIN_Draw_Signed_Float(font8x16, Color_Bg_Black, 2, 2, VALUERANGE_X - 14, MBASE(row), BABY_Z_VAR * 100);
  }
}

static void Item_Tune_LayerPause(const uint8_t row)
{
  DWIN_Draw_Label(MBASE(row), F("Pause Layer"));
  Draw_Menu_Line(row, ICON_Pause_0);
  DWIN_Draw_IntValue(true, true, 0, font8x16, Color_White, Color_Bg_Black,
                     3, VALUERANGE_X, MBASE(row) + PRINT_SET_OFFSET, dwin_pause_layer);
}



void Draw_Tune_Menu()
'''
)

replace_once(
    dwin_cpp,
    '''#if HAS_ZOFFSET_ITEM
  if(TVISI(TUNE_CASE_ZOFF))
    Item_Tune_Zoffset(TSCROL(TUNE_CASE_ZOFF));  // Z offset
#endif
  
  if (select_tune.now)
''',
    '''#if HAS_ZOFFSET_ITEM
  if(TVISI(TUNE_CASE_ZOFF))
    Item_Tune_Zoffset(TSCROL(TUNE_CASE_ZOFF));  // Z offset
#endif

  if(TVISI(TUNE_CASE_LAYER_PAUSE))
    Item_Tune_LayerPause(TSCROL(TUNE_CASE_LAYER_PAUSE));
  
  if (select_tune.now)
'''
)

# When scrolling to the new last item draw the correct row.
replace_once(
    dwin_cpp,
    '''#if HAS_ZOFFSET_ITEM
        if (index_tune == TUNE_CASE_ZOFF)         
          Item_Tune_Zoffset(MROWS);
#endif
      }
''',
    '''#if HAS_ZOFFSET_ITEM
        if (index_tune == TUNE_CASE_ZOFF)
          Item_Tune_Zoffset(MROWS);
#endif
        if (index_tune == TUNE_CASE_LAYER_PAUSE)
          Item_Tune_LayerPause(MROWS);
      }
'''
)

# Entering Pause Layer reuses PrintSpeed editor state.
replace_once(
    dwin_cpp,
    '''#if HAS_ZOFFSET_ITEM
    case TUNE_CASE_ZOFF: // With offset
#if EITHER(HAS_BED_PROBE, BABYSTEPPING)
      checkkey = Homeoffset;
      HMI_ValueStruct.offset_value = BABY_Z_VAR * 100;
      DWIN_Draw_Signed_Float(font8x16, Select_Color, 2, 2, VALUERANGE_X - 14, MBASE(TUNE_CASE_ZOFF + MROWS - index_tune), HMI_ValueStruct.offset_value);
      EncoderRate.enabled = true;
#else
                         // Apply workspace offset, making the current position 0,0,0
      queue.inject_P(PSTR("G92 X0 Y0 Z0"));
      HMI_AudioFeedback();
#endif
      break;
#endif
    default:
''',
    '''#if HAS_ZOFFSET_ITEM
    case TUNE_CASE_ZOFF: // With offset
#if EITHER(HAS_BED_PROBE, BABYSTEPPING)
      checkkey = Homeoffset;
      HMI_ValueStruct.offset_value = BABY_Z_VAR * 100;
      DWIN_Draw_Signed_Float(font8x16, Select_Color, 2, 2, VALUERANGE_X - 14, MBASE(TUNE_CASE_ZOFF + MROWS - index_tune), HMI_ValueStruct.offset_value);
      EncoderRate.enabled = true;
#else
                         // Apply workspace offset, making the current position 0,0,0
      queue.inject_P(PSTR("G92 X0 Y0 Z0"));
      HMI_AudioFeedback();
#endif
      break;
#endif
    case TUNE_CASE_LAYER_PAUSE:
      dwin_pause_layer_edit = true;
      checkkey = PrintSpeed; // safe reuse of an existing numeric editor state
      DWIN_Draw_IntValue(true, true, 0, font8x16, Color_White, Select_Color, 3,
                         VALUERANGE_X, MBASE(TUNE_CASE_LAYER_PAUSE + MROWS - index_tune) + PRINT_SET_OFFSET,
                         dwin_pause_layer);
      EncoderRate.enabled = true;
      break;
    default:
'''
)

# Replace HMI_PrintSpeed with a safe dual-mode editor.
replace_once(
    dwin_cpp,
    '''void HMI_PrintSpeed()
{
  ENCODER_DiffState encoder_diffState = Encoder_ReceiveAnalyze();
  if (encoder_diffState != ENCODER_DIFF_NO)
  {
    if (Apply_Encoder(encoder_diffState, HMI_ValueStruct.print_speed))
    {
      checkkey = Tune;
      EncoderRate.enabled = false;
      feedrate_percentage = HMI_ValueStruct.print_speed;
      DWIN_Draw_IntValue(true, true, 0, font8x16, Color_White, Color_Bg_Black, 3, VALUERANGE_X, MBASE(select_tune.now + MROWS - index_tune) + PRINT_SET_OFFSET, HMI_ValueStruct.print_speed);
      return;
    }
    // print_speed limit
    LIMIT(HMI_ValueStruct.print_speed, MIN_PRINT_SPEED, MAX_PRINT_SPEED);
    // print_speed value
    DWIN_Draw_IntValue(true, true, 0, font8x16, Color_White, Select_Color, 3, VALUERANGE_X, MBASE(select_tune.now + MROWS - index_tune) + PRINT_SET_OFFSET, HMI_ValueStruct.print_speed);
  }
}
''',
    '''void HMI_PrintSpeed()
{
  ENCODER_DiffState encoder_diffState = Encoder_ReceiveAnalyze();
  if (encoder_diffState == ENCODER_DIFF_NO)
    return;

  if (dwin_pause_layer_edit)
  {
    const uint16_t max_layer = dwin_layer_total ? dwin_layer_total : 999;
    const uint16_t step = _MAX((uint16_t)1, (uint16_t)EncoderRate.encoderMoveValue);

    if (encoder_diffState == ENCODER_DIFF_CW) {
      dwin_pause_layer = _MIN((uint16_t)(dwin_pause_layer + step), max_layer);
    }
    else if (encoder_diffState == ENCODER_DIFF_CCW) {
      dwin_pause_layer = dwin_pause_layer > step ? dwin_pause_layer - step : 0;
    }
    else if (encoder_diffState == ENCODER_DIFF_ENTER) {
      if (dwin_pause_layer && dwin_layer_current && dwin_pause_layer <= dwin_layer_current) {
        dwin_pause_layer = dwin_layer_current + 1;
        if (dwin_layer_total)
          NOMORE(dwin_pause_layer, dwin_layer_total);
      }

      dwin_pause_layer_edit = false;
      checkkey = Tune;
      EncoderRate.enabled = false;
      DWIN_Draw_IntValue(true, true, 0, font8x16, Color_White, Color_Bg_Black, 3,
                         VALUERANGE_X, MBASE(select_tune.now + MROWS - index_tune) + PRINT_SET_OFFSET,
                         dwin_pause_layer);
      DWIN_UpdateLCD();
      return;
    }

    DWIN_Draw_IntValue(true, true, 0, font8x16, Color_White, Select_Color, 3,
                       VALUERANGE_X, MBASE(select_tune.now + MROWS - index_tune) + PRINT_SET_OFFSET,
                       dwin_pause_layer);
    return;
  }

  if (Apply_Encoder(encoder_diffState, HMI_ValueStruct.print_speed))
  {
    checkkey = Tune;
    EncoderRate.enabled = false;
    feedrate_percentage = HMI_ValueStruct.print_speed;
    DWIN_Draw_IntValue(true, true, 0, font8x16, Color_White, Color_Bg_Black, 3, VALUERANGE_X, MBASE(select_tune.now + MROWS - index_tune) + PRINT_SET_OFFSET, HMI_ValueStruct.print_speed);
    return;
  }

  LIMIT(HMI_ValueStruct.print_speed, MIN_PRINT_SPEED, MAX_PRINT_SPEED);
  DWIN_Draw_IntValue(true, true, 0, font8x16, Color_White, Select_Color, 3, VALUERANGE_X, MBASE(select_tune.now + MROWS - index_tune) + PRINT_SET_OFFSET, HMI_ValueStruct.print_speed);
}
'''
)

# Layer counter + one-shot scheduled M600.
layer_code = r'''
// --------------------------------------------------------------------------
// Lightweight layer counter for C13/GD303.
// The slicer/helper sends: M73 L<current> T<total>
// Pause Layer is a one-shot target from Tune and uses the tested M600 path.
// --------------------------------------------------------------------------
static void Draw_Print_LayerInfo()
{
#if ENABLED(DWIN_CREALITY_320_LCD)
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
  // A new print starts at layer 1. Clear any untriggered stale target
  // left from a previously aborted job.
  if (current_layer == 1 && dwin_layer_current > 1)
    dwin_pause_layer = 0;

  dwin_layer_current = current_layer;
  dwin_layer_total = total_layers;

  const bool fire_pause = dwin_pause_layer && dwin_pause_layer == current_layer;
  if (fire_pause)
    dwin_pause_layer = 0; // one-shot; clear before injecting M600

  if (checkkey == PrintProcess) {
    Draw_Print_LayerInfo();
    DWIN_UpdateLCD();
  }

  if (fire_pause)
    queue.inject_P(PSTR("M600"));
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

print("SAFE C13 Layers + Tune Pause Layer patch applied successfully.")
