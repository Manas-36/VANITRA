# Training guide: how to make Vanitra precise

Precision comes mostly from **data and evaluation discipline**. The model is the smaller part. The numbers in this repo today come from synthetic data and only prove that the code runs. Follow the steps in order.

## 0. Decide what "precise" means, and measure only that

| Metric | What it answers | Tool |
|---|---|---|
| **Sign accuracy, new signer** (leave-one-signer-out, top-1 / top-3) | Does it work for someone it has never seen? | `train_sign.py --val-user X`, `ml/train_cnn.py --by-user` |
| **Gloss error rate on sentences** (GER: like WER, on glosses) | Does continuous signing come out right? | `camera/eval_sentences.py` |
| **Exact-sentence accuracy** | Is the English correct end to end? | `eval_sentences.py` |
| **False triggers per minute of REST** | Does it stay quiet when nobody is signing? | `live.py --replay` on REST recordings |

- **Never** quote accuracy on signers or takes that were in training.
- Freeze a **test set**: 2 signers you never train on, plus ≥ 30 recorded sentences.

## 1. Collect the right data

- **Signers:** ≥ 5, including **at least 2 Deaf native ISL signers**. Hearing students learning from videos sign differently, and the model will learn their accent.
- **Takes:** ≥ 10 per sign per signer, over **2+ sessions on different days**. Re-wearing the gloves and changing the room is where real errors come from.
- **Vary everything you can't control later:**
  - distance from the phone (1–2.5 m) and angle;
  - light (window, tube light, evening);
  - background, sleeves, sitting or standing;
  - for the gloves, a glove re-worn and recalibrated.
- **REST is the most important class.** Record **3× more REST than any sign**: hands down, typing, phone in hand, scratching the face, fixing hair, talking with hands. Most real-world errors are the glove or camera "hearing" a sign in ordinary movement.
- **Record sentences too** (`record.py --sentences`). Isolated signs are cleaner than signs inside a sentence (co-articulation), and the decoder has to be tuned on the real thing.
- **Gloves and camera together:** record with both running. Use `collect_data.py` for the gloves and `record.py` for the camera at the same time, so you get paired data for fusion.

## 2. Use the public ISL data before your own (transfer learning)

Your 58 signs × 5 signers are a small dataset. Start from a model that has already seen thousands of ISL videos:

```bash
# 1. INCLUDE: 263 ISL word signs, ~4,300 videos, CC BY 4.0 (zenodo.org/records/4010759)
python camera/extract_videos.py  INCLUDE/  camera/data_include                 # landmarks only, resumable
python camera/train_sign.py --data camera/data_include --labels-from-data \
       --epochs 40 --out camera/models/pretrained.npz                         # learns general ISL motion
# 2. Your vocabulary, starting from those weights
python camera/train_sign.py --init camera/models/pretrained.npz --reset-head --epochs 25 --lr 7e-4
```

The convolution layers already know what ISL hands and movements look like, so only the last layer has to learn your label set. For bigger corpora:
- **iSign** (about 118k ISL video–sentence pairs; research use only, check its licence);
- **ISL-CSLTR** (100 sentences, 700 videos), for sentence-level testing.

## 3. Personalise for the user (biggest single gain for one device)

A device used by one person should be tuned to that person:

```bash
python camera/record.py --source phone --user meera --takes 5                         # ~15 min
python camera/train_sign.py --data camera/data_meera --init camera/models/sign_model.npz \
       --epochs 15 --lr 5e-4 --out camera/models/sign_model_meera.npz
```

For the gloves, the same idea is per-user calibration (hold BOOT 2 s each time the glove is put on) plus their own takes in `ml/data/`.

## 4. Augmentation (already on, and why each part exists)

| Augmentation | Simulates | Where |
|---|---|---|
| Time stretch 0.75–1.35× | fast and slow signers | both |
| Hand-shape rotation ±12°, size ±8 %, landmark jitter | MediaPipe noise, different hands | camera |
| Hand position/scale shift | standing closer, different body sizes | camera |
| Hand drop-out (3–10 frames) | the detector losing a hand during fast motion | camera |
| Face drop-out (25 %) | masks, side view: lexical signs must not depend on the face | camera |
| Flex gain/offset per finger, IMU tilt | glove re-worn, sensor creep | gloves |
| Left glove missing (10 %) | ESP-NOW link drop | gloves |
| `--mirror` | left-handed signers | camera |

## 5. Tune the decoder on recorded sentences, not by feel

```bash
python camera/eval_sentences.py --grid      # best --conf / --stable / --w-lm on held-out sentences
```

These settings trade missed signs against false ones:
- `--conf`: the probability needed;
- `--stable`: how long a sign must stay on top;
- `--w-lm`: how much grammar context may overrule the recogniser;
- `--gap`: the pause that ends a sentence.

Tune them on held-out signers, then fix them.

**The language model is part of the precision.** Grow `lang/data/isl_corpus.txt` with real sentences your Deaf signers actually use, with their English. More real sentences = a better gloss LM = more corrections of the recogniser's mistakes. Keep the LM weight modest (0.2–0.4). Too high, and the system "hears" what it expects.

## 6. Fuse gloves and camera

`live.py --glove COM5 --w-cam 0.5` combines the two models' probabilities (a weighted product). They fail differently:
- **gloves:** location and face blind;
- **camera:** finger occlusion, bad light.

The fused result is more precise than either. Tune `--w-cam` on a validation signer.

## 7. When the data grows, grow the model

The NumPy CNNs suit up to about 100 signs and a few thousand takes, and they need no GPU. Beyond that:
- **Model:** move training to PyTorch with a 1D-CNN + Transformer encoder on the same 148 features. Top solutions to Google's 2023 Kaggle ASL competitions used this kind of landmark model. Keep the feature code, so the data you collected stays usable.
- **Ensembles:** average 3–5 models trained with different seeds. This typically adds a few points at no data cost.
- **Continuous signing:** train with **CTC loss** on recorded sentences, so the model learns sign boundaries itself instead of relying on the spotter.
- **Translation:** once you have thousands of gloss→English pairs from signers, a small sequence-to-sequence model (or a local LLM given the glosses) can replace the rules for fluent English. Keep the rules as a fallback, because they never invent meaning.

## 8. Iterate on the confusion matrix

After every training run, open the report and take the 3 most confused pairs. For each pair, do one of these:
- record more takes of both signs;
- check that both signers really use the same variant;
- accept that the sign pair needs the other sensor (location → camera, finger contact → gloves);
- let the LM separate them in context.

**Example:** in the old vocabulary, THANK_YOU vs GOOD was a pair that only location could separate.

## 9. Before you claim a number

- [ ] The test signers are not in the training data, and the test set was frozen before tuning.
- [ ] Report sign accuracy, sentence GER and false triggers per minute together.
- [ ] Note the conditions (light, distance, glove re-worn or not).
- [ ] A Deaf ISL signer has checked the signs and the English translations.
