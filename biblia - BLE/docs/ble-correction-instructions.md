# BLE Correction Instructions

See the full rules in the project brief. Pipeline fixes glosses in MNA tokens, not hand-edited `.ble.md`.

```bash
cd "biblia - BLE"
python3 scripts/reapply_surface_glosses.py --all   # δεῖ → debe, etc.
python3 scripts/reapply_case_glosses.py --all      # de• genitives, fix double de
python3 scripts/reapply_verb_glosses.py --all
python3 scripts/tokens_to_ble.py --all             # • markers in published output
```

Token glosses use mid-dot `·` (`de·Dios`). Published BLE uses bullet `•` on inserted function words (`de•Dios`).
