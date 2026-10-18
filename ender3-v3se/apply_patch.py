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

# ---------------------------------------------------------------------------
# M73 extension: current/total layer metadata from Cura helper.
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# DWIN header: states and public hooks.
# ---------------------------------------------------------------------------
replace_once(
    dwin_h,
    '''  Pstats,
  Tune,
  #if HAS_PREHEAT
''',
    '''  Pstats,
  Tune,
  LayerPauseMenu,
  LayerPauseValue,
  #if HAS_PREHEAT
'''
)

replace_once(
    dwin_h,
    'void DWIN_Show_M117(char* str);\n',
    'void DWIN_Show_M117(char* str);\n'
    'void DWIN_SetLayerInfo(const uint16_t current_layer, const uint16_t total_layers);\n'
    'void Draw_Layer_Pause_Menu();\n'
    'void HMI_LayerPauseMenu();\n'
    'void HMI_LayerPauseValue();\n'
)

# ---------------------------------------------------------------------------
# DWIN globals: 3 programmable one-shot layer pauses.
# ---------------------------------------------------------------------------
replace_once(
    dwin_cpp,
    '''select_t select_page{0}, select_file{0}, select_print{0}, select_prepare{0}, select_control{0}, select_axis{0}, select_temp{0}, select_motion{0}, select_tune{0}, select_advset{0},
         select_PLA{0}, select_TPU{0}, //select_ABS{0}, select_PETG{0}, 
''',
    '''select_t select_page{0}, select_file{0}, select_print{0}, select_prepare{0}, select_control{0}, select_axis{0}, select_temp{0}, select_motion{0}, select_tune{0}, select_advset{0},
         select_layer_pause{0},
         select_PLA{0}, select_TPU{0}, //select_ABS{0}, select_PETG{0}, 
'''
)

replace_once(
    dwin_cpp,
    '''static millis_t pause_transition_guard_ms = 0;

constexpr float default_max_feedrate[] = DEFAULT_MAX_FEEDRATE;
''',
    '''static millis_t pause_transition_guard_ms = 0;

// Custom layer counter / scheduled color-change pauses.
// Slot value 0 means OFF. Values are human-readable 1-based layer numbers.
static uint16_t dwin_layer_current = 0;
static uint16_t dwin_layer_total = 0;
static uint16_t dwin_layer_pause[3] = { 0, 0, 0 };
static uint8_t dwin_layer_pause_edit_slot = 0;

constexpr float default_max_feedrate[] = DEFAULT_MAX_FEEDRATE;
'''
)

# ---------------------------------------------------------------------------
# Tune menu: add Layer Pause submenu.
# ---------------------------------------------------------------------------
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
  DWIN_Draw_Label(MBASE(row), F("Layer Pause"));
  Draw_Menu_Line(row, ICON_Pause_0);
  Draw_More_Icon(row);
}

static void Draw_Layer_Pause_Value(const uint8_t row, const uint8_t slot, const bool selected=false)
{
  DWIN_Draw_Rectangle(1, Color_Bg_Black, VALUERANGE_X - 18, MBASE(row) - 3, DWIN_WIDTH - 12, MBASE(row) + 19);

  if (dwin_layer_pause[slot] == 0) {
    DWIN_Draw_String(false, false, font8x16, selected ? Select_Color : Color_White, Color_Bg_Black,
                     VALUERANGE_X - 10, MBASE(row), F("OFF"));
  }
  else {
    DWIN_Draw_IntValue(true, true, 0, font8x16,
                       selected ? Select_Color : Color_White,
                       Color_Bg_Black, 3, VALUERANGE_X, MBASE(row),
                       dwin_layer_pause[slot]);
  }
}

void Draw_Layer_Pause_Menu()
{
  Clear_Main_Window();
  Draw_Mid_Status_Area(true);
  HMI_flag.Refresh_bottom_flag = false;

  DWIN_Draw_String(false, false, font8x16, Color_White, Color_Bg_Black, 42, TITLE_Y, F("Layer Pause"));

  Draw_Back_First(select_layer_pause.now == 0);

  for (uint8_t i = 0; i < 3; ++i) {
    const uint8_t row = i + 1;
    char label[16];
    snprintf(label, sizeof(label), "Pause %u", i + 1);
    DWIN_Draw_Label(MBASE(row), label);
    Draw_Menu_Line(row, ICON_Pause_0);
    Draw_Layer_Pause_Value(row, i, false);
  }

  char now_text[24];
  snprintf(now_text, sizeof(now_text), "Now %u/%u", dwin_layer_current, dwin_layer_total);
  DWIN_Draw_Small_Label(MBASE(4), now_text);

  if (select_layer_pause.now)
    Draw_Menu_Cursor(select_layer_pause.now);
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

# ---------------------------------------------------------------------------
# Layer display and one-shot M600 trigger.
# ---------------------------------------------------------------------------
layer_code = r'''
// --------------------------------------------------------------------------
// Lightweight layer counter for the C13/GD303 build.
// The slicer/helper sends: M73 L<current> T<total>
// Scheduled layer pauses use the existing Advanced Pause / M600 mechanism.
// --------------------------------------------------------------------------
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

  bool fire_pause = false;
  for (uint8_t i = 0; i < 3; ++i) {
    if (dwin_layer_pause[i] && dwin_layer_pause[i] == current_layer) {
      dwin_layer_pause[i] = 0; // one-shot: clear before scheduling pause
      fire_pause = true;
    }
  }

  if (checkkey == PrintProcess) {
    Draw_Print_LayerInfo();
    DWIN_UpdateLCD();
  }

  if (fire_pause) {
    // Reuse the Community Edition's improved M600:
    // park head, raise Z, unload, alert, nozzle timeout, then reheat/load/purge on resume.
    queue.inject_P(PSTR("M600"));
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

# ---------------------------------------------------------------------------
# Tune navigation: show/open Layer Pause.
# ---------------------------------------------------------------------------
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
      checkkey = LayerPauseMenu;
      select_layer_pause.reset();
      Draw_Layer_Pause_Menu();
      break;
    default:
'''
)

# ---------------------------------------------------------------------------
# Layer Pause submenu interaction.
# ---------------------------------------------------------------------------
layer_pause_handlers = r'''
void HMI_LayerPauseMenu()
{
  const ENCODER_DiffState state = get_encoder_state();
  if (state == ENCODER_DIFF_NO)
    return;

  if (state == ENCODER_DIFF_CW) {
    if (select_layer_pause.inc(4))
      Move_Highlight(1, select_layer_pause.now);
  }
  else if (state == ENCODER_DIFF_CCW) {
    if (select_layer_pause.dec())
      Move_Highlight(-1, select_layer_pause.now);
  }
  else if (state == ENCODER_DIFF_ENTER) {
    if (select_layer_pause.now == 0) {
      checkkey = Tune;
      select_tune.set(TUNE_CASE_LAYER_PAUSE);
      index_tune = TUNE_CASE_LAYER_PAUSE;
      Draw_Tune_Menu();
    }
    else {
      dwin_layer_pause_edit_slot = select_layer_pause.now - 1;

      // If the slot is OFF, start editing at the next not-yet-printed layer.
      if (dwin_layer_pause[dwin_layer_pause_edit_slot] == 0) {
        uint16_t next_layer = dwin_layer_current ? dwin_layer_current + 1 : 1;
        if (dwin_layer_total && next_layer > dwin_layer_total)
          next_layer = dwin_layer_total;
        dwin_layer_pause[dwin_layer_pause_edit_slot] = next_layer;
      }

      checkkey = LayerPauseValue;
      EncoderRate.enabled = true;
      Draw_Layer_Pause_Value(select_layer_pause.now, dwin_layer_pause_edit_slot, true);
    }
  }

  DWIN_UpdateLCD();
}

void HMI_LayerPauseValue()
{
  const ENCODER_DiffState state = Encoder_ReceiveAnalyze();
  if (state == ENCODER_DIFF_NO)
    return;

  uint16_t &value = dwin_layer_pause[dwin_layer_pause_edit_slot];
  const uint16_t max_layer = dwin_layer_total ? dwin_layer_total : 999;
  const uint16_t step = _MAX((uint16_t)1, (uint16_t)EncoderRate.encoderMoveValue);

  if (state == ENCODER_DIFF_CW) {
    value = value > max_layer - _MIN(step, max_layer) ? max_layer : value + step;
    NOMORE(value, max_layer);
  }
  else if (state == ENCODER_DIFF_CCW) {
    value = value > step ? value - step : 0;
  }
  else if (state == ENCODER_DIFF_ENTER) {
    // Disallow a stale target that has already passed. 0 remains OFF.
    if (value && dwin_layer_current && value <= dwin_layer_current) {
      value = dwin_layer_current + 1;
      if (dwin_layer_total)
        NOMORE(value, dwin_layer_total);
    }

    checkkey = LayerPauseMenu;
    EncoderRate.enabled = false;
    Draw_Layer_Pause_Menu();
    DWIN_UpdateLCD();
    return;
  }

  Draw_Layer_Pause_Value(select_layer_pause.now, dwin_layer_pause_edit_slot, true);
  DWIN_UpdateLCD();
}

'''

replace_once(
    dwin_cpp,
    '''#if HAS_PREHEAT

/* PLA Preheat */
''',
    layer_pause_handlers + '''#if HAS_PREHEAT

/* PLA Preheat */
'''
)

# ---------------------------------------------------------------------------
# Screen dispatcher.
# ---------------------------------------------------------------------------
replace_once(
    dwin_cpp,
    '''  case Tune:
    HMI_Tune();
    break;
#if HAS_PREHEAT
''',
    '''  case Tune:
    HMI_Tune();
    break;
  case LayerPauseMenu:
    HMI_LayerPauseMenu();
    break;
  case LayerPauseValue:
    HMI_LayerPauseValue();
    break;
#if HAS_PREHEAT
'''
)

# ---------------------------------------------------------------------------
# Clear unused pause slots on completed/cancelled jobs.
# Triggered slots already clear themselves when they fire.
# ---------------------------------------------------------------------------
replace_once(
    dwin_cpp,
    '''      memset(model_information.filament, 0, sizeof(model_information.filament));
      memset(model_information.height,   0, sizeof(model_information.height));
      
      // Show remaining time
''',
    '''      memset(model_information.filament, 0, sizeof(model_information.filament));
      memset(model_information.height,   0, sizeof(model_information.height));
      memset(dwin_layer_pause, 0, sizeof(dwin_layer_pause));
      
      // Show remaining time
'''
)

replace_once(
    dwin_cpp,
    '''        thermalManager.zero_fan_speeds();

        recovery.info.sd_printing_flag = false; // rock_20210820
''',
    '''        thermalManager.zero_fan_speeds();
        memset(dwin_layer_pause, 0, sizeof(dwin_layer_pause));

        recovery.info.sd_printing_flag = false; // rock_20210820
'''
)

print("C13 Layers + 3x Layer Pause patch applied successfully.")
