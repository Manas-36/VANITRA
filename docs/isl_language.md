# How ISL actually works, and what that means for Vanitra

Vanitra v1 recognised 20 one-handed ASL-style signs and spoke them one word at a time. Deaf people in India sign **Indian Sign Language (ISL)**, which differs in three ways that matter here:
- **It uses two hands.** Most of its alphabet and many of its signs need both.
- **It has its own grammar.** Word order, questions and negation work differently from English.
- **Part of the grammar is on the face, not the hands.**

This page summarises the linguistics, then maps each feature to what the gloves, the camera and the language engine (`lang/vanitra_lang`) do with it.

> Sources: NIOS ISL course, Chapter 10 (sentence structure) · IIT Kanpur ISL grammar notes (ICoSAL 2008) · iSign benchmark (Joshi et al., 2024) · INCLUDE dataset (Sridhar et al., ACM MM 2020) · Zeshan's typological work on Indo-Pakistani Sign Language. **Every gloss sentence and sign choice in this repo should be checked by a Deaf ISL signer.** The rules below are the documented core, not the whole language, and ISL has regional variants (iSign reports about 75 % of vocabulary shared across India).

## 1. What a sign is made of

Every sign combines five parameters. Changing any one of them can change the meaning.

| Parameter | Example of a contrast | Gloves see it? | Camera sees it? |
|---|---|---|---|
| **Handshape**: which fingers are bent or touching | fist vs flat hand vs index point | ✅ flex + Hall contacts | ✅ 21 landmarks per hand |
| **Orientation**: palm up, down or sideways | | ✅ IMU (roll/pitch) | ✅ |
| **Movement**: path, repetition, speed | tap vs circle vs sweep | ✅ IMU gyro/accel | ✅ wrist trajectory |
| **Location**: where on or near the body | sign at the chin vs at the chest | ❌ **not at all** (an IMU knows tilt, not position) | ✅ body-relative coordinates |
| **Non-manual**: face, head, mouth, shoulders | raised brows = question, head shake = negation | ❌ | ✅ blendshapes + head pose |

This is the strongest argument for adding the camera. Gloves are precise on handshape and motion, and blind to location and the face. A camera is the opposite: it is weaker on occluded fingers and strong on location and face. `camera/live.py --glove` fuses them.

## 2. Two hands

Sign languages build two-handed signs in three ways, a pattern described for many sign languages since Battison (1978):

1. **One-handed:** only the dominant hand moves.
2. **Two-handed symmetric:** both hands have the same shape and move together or in mirror image.
3. **Two-handed asymmetric (base):** the dominant hand acts on a still non-dominant hand that holds a simple shape. Pointing at the fingers of the other hand is one example.

ISL also uses **both hands at once for two meanings**. NIOS gives WHILE as "WALK (one hand) + UMBRELLA (other hand)". **Fingerspelling** (names, and words without a sign; iSign) uses a mostly **two-handed** manual alphabet, a variant of the British two-handed alphabet.

What Vanitra does with this:
- **Gloves:** a second glove (role LEFT) radios its frames to the right glove over ESP-NOW. The model sees 30 channels, both hands at once ([firmware/glove_unit/glove_link.h](../firmware/glove_unit/glove_link.h)). It is trained with the left glove randomly missing, so it degrades gracefully when the link drops.
- **Camera:** both hands are tracked. They are ordered **dominant / non-dominant** by matching them to the pose skeleton's wrists, not by image side, so the order survives mirroring and crossing hands. `--left-handed` swaps them.
- **Fingerspelling:** add letter classes named `FS_A … FS_Z` to the vocabulary. The decoder joins consecutive letters into one name (`FS_R FS_A FS_M` → `FS:RAM` → "Ram"). This is not recorded or trained yet.

## 3. Grammar: how a sentence is built

| Rule | Example (gloss → English) | Source |
|---|---|---|
| **Time first.** Verbs do not change for tense; time signs set it. | `TOMORROW I HOSPITAL GO` → *I will go to the hospital tomorrow.* | NIOS ("time signs come early"); IIT-K (tense at discourse level) |
| **Predicate last** (subject–object–verb). | `I WATER WANT` → *I want water.* | IIT-K ("predicate final") |
| **No articles, no "be".** | `I SICK` → *I am sick.* | IIT-K |
| **Adjective after the noun.** | `HOME RAIN HEAVY`, `TIME GOOD` | NIOS examples |
| **Wh-sign at the end.** Many wh-questions are a content sign + the general question sign. | `YOU GO WHERE` → *Where are you going?* | NIOS ("WHERE = place sign + question sign") |
| **Yes/no question = facial expression only** (raised brows, head forward). There is no question word. | `[brows up] YOU HUNGRY` → *Are you hungry?* | NIOS; iSign |
| **Negation at the end**, with a head shake. There are several negative signs (NOT, DON'T WANT, NOT POSSIBLE, NOTHING, NONE). | `I UNDERSTAND NOT` → *I don't understand.* | NIOS |
| **Obligation: MUST at the end.** | `YOU TICKET MUST` → *You must have a ticket.* | NIOS |
| **Completed action: FINISH after the verb.** | `I EAT FINISH` → *I have eaten.* | common ISL pattern; verify with signers |
| **Signing space:** each person or place gets a location; pointing to it means *him/her/there*. **Directional verbs** move between locations (GIVE from giver to receiver). | `RAM(loc1) SITA(loc2) BOOK GIVE(loc1→loc2)` | IIT-K; NIOS |
| **Clauses:** a pause works like a comma. IF can be shown by the face alone. | `(IF) RAIN, SCHOOL GO NOT` | NIOS |

## 4. What the language engine implements

`lang/vanitra_lang` turns a stream of recognised signs into English:

1. **Sign events.** Each accepted sign carries the recogniser's top-4 guesses with probabilities.
2. **Gloss language model.** A bigram model trained on [lang/data/isl_corpus.txt](../lang/data/isl_corpus.txt) re-scores the sequence with beam search. A low-confidence guess that makes no sense in context is replaced by one that does: `I WATER WHERE` → `I WATER WANT`. A shaky spurious detection can be dropped.
3. **Non-manual markers** (camera only). Brows raised above the signer's own neutral for most of the sentence turn it into a yes/no question. A head shake negates it. With gloves only, sign `QUESTION` at the end instead.
4. **ISL → English rules** ([translate.py](../lang/vanitra_lang/translate.py)):
   - time → tense;
   - SOV → SVO;
   - the wh-word moves to the front, with *do/be* inversion;
   - NOT → *don't / isn't*;
   - MUST/CAN → modal;
   - FINISH → *have + past participle*;
   - articles added (*a doctor / the hospital / water*);
   - possessives (`I MOTHER SICK` → *My mother is sick.*);
   - infinitives (`I HOME GO WANT` → *I want to go home.*);
   - fixed phrases from [phrases.csv](../lang/data/phrases.csv).

**Tested:** all 79 corpus sentences translate exactly. On simulated noisy recognition (right 85 % of the time), the language model raises fully correct sentences from **67 % to 79 %** on sentences it was **not** trained on (`python lang/tests/test_lang.py`).

**Not handled yet:**
- spatial reference and directional verbs (pointing to a location is read as *he/she*);
- classifiers and role shift;
- simultaneous two-meaning constructions;
- conditionals without IF;
- plurals by repetition.

These need either many more labelled sentences or a learned translation model (training_guide.md §7).

## 5. Vocabulary

[ml/vocabulary.csv](../ml/vocabulary.csv) is shared by the gloves and the camera, so both can be fused. It has **58 core glosses + REST**:

| Group | Glosses |
|---|---|
| Pronouns | I, YOU, HE-SHE, WE |
| Questions | WHAT, WHERE, WHO, WHEN, WHY, HOW, QUESTION |
| Time | NOW, TODAY, TOMORROW, YESTERDAY |
| Negation | NOT, CAN-NOT, DONT-WANT |
| Verbs and modals | WANT, NEED, LIKE, CAN, MUST, HAVE, FINISH, GO, COME, EAT, DRINK, HELP, CALL, UNDERSTAND, WAIT, STOP |
| Nouns | WATER, FOOD, MEDICINE, TOILET, DOCTOR, HOSPITAL, HOME, NAME, PHONE, MOTHER, FATHER, FRIEND |
| Adjectives | GOOD, BAD, SICK, PAIN, HUNGRY, TIRED, HAPPY |
| Social | HELLO, THANK-YOU, SORRY, PLEASE, YES |

These were chosen so that everyday, health and emergency sentences, questions and negation can all be built. [lang/data/isl_lexicon.csv](../lang/data/isl_lexicon.csv) already covers about 100 glosses for growth.

**How to sign them:**
- Copy each sign from the **ISLRTC ISL dictionary videos** (the government reference; 2,500 terms were added in 2024).
- Note whether it is one- or two-handed.
- Record the variant your users actually use.

This repo deliberately does **not** describe the signs in words: a written description of a sign is easy to get wrong.
