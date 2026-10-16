# ml/ — gesture model and voice for the glove

| File | Purpose |
|---|---|
| `vocabulary.csv` | signs, spoken text, how to sign them (REST must stay) |
| `collect_data.py` | record labelled takes from the glove over USB |
| `vanitra_features.py` | feature maths — mirror of `firmware/glove_unit/features.h` |
| `train.py` | grouped cross-validation, report, export `model.h` + test vectors |
| `make_voice_clips.py` | `voice_clips.h` from espeak-ng or your own WAVs |
| `make_synthetic_data.py` | fake data for testing the pipeline only |
| `data/` | real recordings (commit them) |

Step by step: [../docs/ml_pipeline.md](../docs/ml_pipeline.md).
