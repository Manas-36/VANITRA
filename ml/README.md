# ml/ — gesture model and voice for the glove

| File | Purpose |
|---|---|
| `vocabulary.csv` | signs, spoken text, how to sign them (REST must stay) |
| `collect_data.py` | record labelled takes from the glove over USB |
| `vanitra_features.py` | feature maths — mirror of `firmware/glove_unit/features.h` |
| `train.py` | v1 MLP: grouped cross-validation, report, export `model.h` + test vectors |
| `vanitra_cnn.py` | v2 temporal CNN in NumPy (forward, backward, Adam, augmentation) — mirror of `firmware/glove_unit/cnn.h` |
| `train_cnn.py` | v2: trains the CNN, compares it with the MLP (clean + drifted, by take or by user), exports `model_cnn.h` |
| `live_decoder.py` | runs the CNN live on the glove stream or a recorded take: top-3, transcript, optional speech |
| `models/` | `vanitra_cnn.npz` for the live decoder |
| `make_voice_clips.py` | `voice_clips.h` from espeak-ng or your own WAVs |
| `make_synthetic_data.py` | fake data for testing the pipeline only |
| `data/` | real recordings (commit them) |

Step by step: [../docs/ml_pipeline.md](../docs/ml_pipeline.md).
